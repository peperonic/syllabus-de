"""The read-only knowledge base service behind kb_api.py and mcp_server.py.

Every public method returns compact JSON-ready dicts that state the curriculum
version and the date they were evaluated for, list every node id they rest on
under `citations`, and carry a short German `summary_de`.

Two guards apply to every answer:
* licence filter: curriculum text is returned only for documents whose licence
  class is full_text; for anything else the answer gives label and link;
* citation check: every cited node id must exist, otherwise the call fails
  loudly instead of returning an unfounded claim.
"""
from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass, field

from .db import connect, one, rows
from .pack import Pack, load_pack
from .resolve import (Context, ContextError, attends, cohort_trace, doc_public, normalise_context)
from .text import contains_phrase, fold, operator_forms, words
from .validity import school_year, school_year_label

AFB_DEFAULT = {"I": 0.3, "II": 0.5, "III": 0.2}


class CitationError(RuntimeError):
    pass


@dataclass
class Status:
    """Internal result of the cohort analysis, shared by several tools."""
    ctx: Context
    trace: dict
    current_docs: list[dict]
    current: dict = field(default_factory=dict)      # topic_id -> list of node dicts
    before: dict = field(default_factory=dict)       # topic_id -> list of node dicts
    later: dict = field(default_factory=dict)        # topic_id -> list of node dicts
    unmapped_current: list = field(default_factory=list)
    uncertainty: list = field(default_factory=list)
    cited: set = field(default_factory=set)


class KnowledgeBase:
    def __init__(self, db_path=None, pack: Pack | None = None):
        self.pack = pack or load_pack()
        self.db_path = db_path or self.pack.db_path
        self.conn: sqlite3.Connection = connect(self.db_path, read_only=True)
        self.content_kinds = set(self.pack.get("nodes.content_kinds", ["Kompetenzerwartung", "Inhalt"]) or [])
        self._doc_cache: dict[str, dict] = {}
        self._topic_cache: dict[str, dict] = {}

    # ------------------------------------------------------------------
    # small helpers
    # ------------------------------------------------------------------
    def _doc(self, document_id: str) -> dict:
        if document_id not in self._doc_cache:
            d = one(self.conn, "SELECT * FROM document WHERE document_id = ?", (document_id,))
            if d is None:
                raise KeyError(document_id)
            self._doc_cache[document_id] = d
        return self._doc_cache[document_id]

    def _topic(self, topic_id: str) -> dict | None:
        if topic_id not in self._topic_cache:
            t = one(self.conn, "SELECT * FROM topic WHERE topic_id = ?", (topic_id,))
            if t is not None:
                t["keywords"] = json.loads(t.get("keywords") or "[]")
            self._topic_cache[topic_id] = t
        return self._topic_cache[topic_id]

    def _full_text_allowed(self, doc: dict) -> bool:
        return self.pack.licence_class(doc.get("licence")) == "full_text"

    def node_out(self, n: dict) -> dict:
        """Public view of a node, with the licence filter applied."""
        doc = self._doc(n["document_id"])
        gf = n["grade_from"] if n["grade_from"] is not None else doc["grade_from"]
        gt = n["grade_to"] if n["grade_to"] is not None else doc["grade_to"]
        out = {"node_id": n["node_id"], "kind": n["kind"], "label": n.get("label"),
               "grades": f"{gf}" if gf == gt else f"{gf}-{gt}", "page": n.get("page"),
               "document_id": n["document_id"]}
        if n.get("course_level"):
            out["course_level"] = n["course_level"]
        if n.get("locator"):
            out["locator"] = n["locator"]
        if self._full_text_allowed(doc):
            out["text"] = n.get("text")
        else:
            out["text_withheld"] = f"Lizenz {doc.get('licence')!r}: nur Struktur, kein Volltext"
            out["source_url"] = doc.get("source_url")
        return out

    def _nodes_of(self, document_id: str, course_level: str | None) -> list[dict]:
        ns = rows(self.conn, """SELECT n.* FROM curriculum_node n WHERE n.document_id = ?
                                AND NOT EXISTS (SELECT 1 FROM curriculum_node c WHERE c.parent_id = n.node_id)
                                ORDER BY n.ordinal""", (document_id,))
        doc = self._doc(document_id)
        out = []
        for n in ns:
            if self.content_kinds and n["kind"] not in self.content_kinds:
                continue
            if course_level and n.get("course_level") and fold(n["course_level"]) != fold(course_level):
                continue
            n["_a"] = n["grade_from"] if n["grade_from"] is not None else doc["grade_from"]
            n["_b"] = n["grade_to"] if n["grade_to"] is not None else doc["grade_to"]
            out.append(n)
        return out

    def _topics_of_node(self, node_id: str) -> list[str]:
        return [r["dst"] for r in rows(self.conn, "SELECT dst FROM edge WHERE rel='maps_to' AND certified=1 AND src = ?", (node_id,))]

    def _requires_closure(self, topic_id: str) -> list[str]:
        seen, stack = [], [topic_id]
        while stack:
            t = stack.pop()
            for r in rows(self.conn, "SELECT dst FROM edge WHERE rel='requires' AND certified=1 AND src = ?", (t,)):
                if r["dst"] not in seen:
                    seen.append(r["dst"])
                    stack.append(r["dst"])
        return seen

    def _check_citations(self, ids: set[str]) -> list[str]:
        ids = sorted(i for i in ids if i)
        if not ids:
            return []
        q = ",".join("?" * len(ids))
        found = {r[0] for r in self.conn.execute(f"SELECT node_id FROM curriculum_node WHERE node_id IN ({q})", ids)}
        missing = [i for i in ids if i not in found]
        if missing:
            raise CitationError(f"unresolvable citations: {missing}")
        return ids

    def _envelope(self, tool: str, c: Context | None, docs: list[dict] | None, payload: dict,
                  uncertainty: list[str], cited: set[str], summary: str) -> dict:
        out = {"tool": tool}
        if c is not None:
            out["context"] = c.as_dict()
            out["context_mapping"] = c.mapping
            out["evaluated_for"] = {"date": c.date.isoformat(), "school_year": school_year_label(c.school_year)}
            out["curriculum_version"] = [doc_public(self.conn, d, c.school_year, c.start) for d in (docs or [])]
        out.update(payload)
        out["uncertainty"] = _dedup(uncertainty)
        out["citations"] = self._check_citations(cited)
        out["summary_de"] = _no_dashes(summary)
        return out

    def _error(self, tool: str, e: ContextError) -> dict:
        return {"tool": tool, "error": {"field": e.field_name, "message_de": str(e), "candidates": e.candidates},
                "citations": [], "uncertainty": [str(e)],
                "summary_de": _no_dashes(f"Der Kontext ist nicht auflösbar: {e}. Bitte {e.field_name} prüfen.")}

    # ------------------------------------------------------------------
    # the cohort analysis
    # ------------------------------------------------------------------
    def _status(self, c: Context) -> Status:
        trace = cohort_trace(self.conn, c)
        cur = trace.get(c.grade)
        current_docs = cur.binding if cur else []
        st = Status(ctx=c, trace=trace, current_docs=current_docs)
        if c.land_status == "placeholder":
            st.uncertainty.append(f"Das Inventar für {c.land_name} ist ein Platzhalter; keine Angabe ist geprüft.")
        for g, b in sorted(trace.items()):
            for note in b.notes:
                if g == c.grade:
                    st.uncertainty.append(note)
                elif "kein bindender Plan" in note:
                    st.uncertainty.append(f"Klasse {g} ({school_year_label(b.school_year)}): {note}")
        bands_seen, partial_seen = set(), set()
        cur_ids = {d["document_id"] for d in current_docs}
        for g, b in sorted(trace.items()):
            for d in b.binding:
                if not self._full_text_allowed(d):
                    st.uncertainty.append(f"{d['title']}: nur Struktur gespeichert, Text nicht wiedergegeben (Lizenz {d.get('licence')}).")
                for n in self._nodes_of(d["document_id"], c.course_level):
                    if not (n["_a"] <= g <= n["_b"]):
                        continue
                    topics = self._topics_of_node(n["node_id"])
                    if g == c.grade:
                        bucket = st.current
                        if n["_a"] < n["_b"] and (n["_a"], n["_b"]) not in bands_seen:
                            bands_seen.add((n["_a"], n["_b"]))
                            st.uncertainty.append(
                                f"Klassen {n['_a']}-{n['_b']} sind im Plan ein Doppeljahrgang: ob ein Inhalt in Klasse {n['_a']} "
                                f"oder {n['_b']} behandelt wird, legt die Schule fest.")
                        if not topics:
                            st.unmapped_current.append(n)
                    elif g < c.grade:
                        if n["_b"] >= c.grade:
                            if d["document_id"] in cur_ids:
                                continue  # band still running in the current grade, reported there
                            # The band began under a plan that no longer binds this pupil:
                            # it was taught in part, so it counts as before, with a note.
                            if (d["document_id"], n["_a"], n["_b"]) not in partial_seen:
                                partial_seen.add((d["document_id"], n["_a"], n["_b"]))
                                st.uncertainty.append(
                                    f"Klassen {n['_a']}-{n['_b']} begannen nach {d['title']}; dieser Doppeljahrgang wurde nur "
                                    f"bis Klasse {c.grade - 1} nach diesem Plan unterrichtet.")
                        bucket = st.before
                    else:
                        if n["_a"] <= c.grade and d["document_id"] in cur_ids:
                            continue
                        bucket = st.later
                    for t in topics:
                        lst = bucket.setdefault(t, [])
                        if all(x["node_id"] != n["node_id"] for x in lst):
                            lst.append(n)
        if st.unmapped_current:
            st.uncertainty.append(f"{len(st.unmapped_current)} Inhalte der aktuellen Klasse sind noch keinem Thema zugeordnet; sie stehen unter current_unmapped.")
        self._switch_gap(c, st)
        return st

    def _switch_gap(self, c: Context, st: Status) -> None:
        """A cohort that changed plan mid-course (possible only in the rollout's first
        year, for grades a < g <= N) never had the new plan's earlier grades. Topics
        the new plan places there but the old plan never taught are a gap."""
        cur_ids = {d["document_id"] for d in st.current_docs}
        earlier_ids = {d["document_id"] for g, b in st.trace.items() if g < c.grade for d in b.binding}
        for d in st.current_docs:
            preds = {r["dst"] for r in rows(self.conn, "SELECT dst FROM edge WHERE rel='supersedes' AND src=?", (d["document_id"],))}
            if not (preds & earlier_ids):
                continue
            missed = {}
            for n in self._nodes_of(d["document_id"], c.course_level):
                if n["_b"] < c.grade:
                    for t in self._topics_of_node(n["node_id"]):
                        if t not in st.before and t not in st.current:
                            missed.setdefault(t, n)
            if missed:
                labels = ", ".join((self._topic(t) or {}).get("label_de", t) for t in missed)
                st.uncertainty.append(f"Planwechsel in dieser Kohorte: der neue Plan setzt aus früheren Klassen {labels} voraus, "
                                      f"das nach dem alten Plan nicht unterrichtet wurde.")
                st.cited |= {n["node_id"] for n in missed.values()}
            elif cur_ids:
                st.uncertainty.append("Planwechsel in dieser Kohorte: frühere Klassen liefen nach dem Vorgängerplan.")

    def _competences(self, c: Context, docs: list[dict]) -> tuple[list, list, list, list[str], set[str]]:
        doc_ids = {d["document_id"] for d in docs}
        proc = rows(self.conn, """SELECT competence_id, label_de, source FROM competence WHERE kind='process_competence'
                                  AND (subject IS NULL OR subject = ?) AND (land IS NULL OR land = ?)""", (c.subject, c.land))
        afb = rows(self.conn, "SELECT competence_id, label_de FROM competence WHERE kind='afb' ORDER BY competence_id")
        ops_all = rows(self.conn, """SELECT competence_id, label_de, afb, source_node FROM competence WHERE kind='operator'
                                     AND land = ? AND (subject IS NULL OR subject = ?)""", (c.land, c.subject))
        ops = [o for o in ops_all if o["source_node"] and o["source_node"].rsplit(":", 1)[0] in doc_ids]
        unc, cited = [], {o["source_node"] for o in ops}
        if not ops:
            unc.append(f"Für {c.land} {c.subject} liegt im Bestand keine Operatorenliste des geltenden Plans vor.")
        return proc, afb, ops, unc, cited

    def _conventions(self, c: Context, docs: list[dict]) -> list[dict]:
        doc_ids = {d["document_id"] for d in docs}
        form = attends(self.conn, c.land, c.school_form, c.grade)
        out = []
        for v in rows(self.conn, "SELECT * FROM convention WHERE land = ? AND subject = ?", (c.land, c.subject)):
            if v["source_node"].rsplit(":", 1)[0] not in doc_ids:
                continue
            if v["school_form"] and v["school_form"] != form:
                continue
            if v["grade_from"] is not None and not (v["grade_from"] <= c.grade <= v["grade_to"]):
                continue
            out.append(v)
        return out

    def _topic_entry(self, tid: str, nodes: list[dict], with_nodes: bool = True) -> dict:
        t = self._topic(tid) or {"label_de": tid, "kmk_anchor": None}
        e = {"topic_id": tid, "label_de": t["label_de"], "kmk_anchor": t.get("kmk_anchor")}
        if with_nodes:
            e["nodes"] = [self.node_out(n) for n in nodes]
        else:
            e["node_ids"] = [n["node_id"] for n in nodes]
        return e

    # ------------------------------------------------------------------
    # tools
    # ------------------------------------------------------------------
    def resolve_context(self, context: dict) -> dict:
        try:
            c = normalise_context(self.conn, context)
        except ContextError as e:
            return self._error("resolve_context", e)
        trace = cohort_trace(self.conn, c)
        b = trace.get(c.grade)
        binding = b.binding if b else []
        also = b.also_in_force if b else []
        unc = list(b.notes if b else ["Klasse liegt außerhalb der Pläne dieses Bildungsgangs."])
        if c.land_status == "placeholder":
            unc.insert(0, f"Das Inventar für {c.land_name} ist ein Platzhalter; keine Angabe ist geprüft.")
        payload = {
            "attends_school_form": attends(self.conn, c.land, c.school_form, c.grade),
            "binding": [doc_public(self.conn, d, c.school_year, c.start) for d in binding],
            "also_in_force_this_year": [doc_public(self.conn, d, c.school_year, c.start) for d in also],
            "transition_year": bool(binding and also),
        }
        if binding:
            t = binding[0]
            summary = (f"Für {c.subject}, {c.school_form} Klasse {c.grade} in {c.land_name} gilt am {_de(c.date)} "
                       f"(Schuljahr {school_year_label(c.school_year)}) {t['title']}.")
            if also:
                summary += f" Im selben Schuljahr gilt für andere Jahrgänge außerdem {also[0]['title']}; für diese Kohorte bindend ist {t['title']}."
        else:
            summary = f"Für {c.subject}, {c.school_form} Klasse {c.grade} in {c.land_name} ist am {_de(c.date)} kein bindender Plan im Bestand."
        return self._envelope("resolve_context", c, binding, payload, unc, set(), summary)

    def curriculum_status(self, context: dict) -> dict:
        try:
            c = normalise_context(self.conn, context)
        except ContextError as e:
            return self._error("curriculum_status", e)
        st = self._status(c)
        cited: set[str] = set()
        current = [self._topic_entry(t, ns) for t, ns in sorted(st.current.items(), key=lambda kv: kv[1][0]["ordinal"])]
        for ns in st.current.values():
            cited |= {n["node_id"] for n in ns}
        before_groups: dict[str, list] = {}
        for t, ns in st.before.items():
            band = _band(min(n["_a"] for n in ns), max(n["_b"] for n in ns))
            before_groups.setdefault(band, []).append(self._topic_entry(t, ns, with_nodes=False))
            cited |= {n["node_id"] for n in ns}
        taught_before = [{"grades": k, "topics": v} for k, v in sorted(before_groups.items(), key=lambda kv: _band_key(kv[0]))]
        not_yet = []
        for t, ns in st.later.items():
            if t in st.current or t in st.before:
                continue
            first = min(n["_a"] for n in ns)
            e = self._topic_entry(t, ns, with_nodes=False)
            e["first_grade"] = first
            e["expected_school_year"] = school_year_label(c.school_year + (first - c.grade))
            not_yet.append(e)
            cited |= {n["node_id"] for n in ns}
        not_yet.sort(key=lambda e: (e["first_grade"], e["topic_id"]))
        unmapped = [self.node_out(n) for n in st.unmapped_current]
        cited |= {n["node_id"] for n in st.unmapped_current}
        proc, afb, ops, unc_ops, cited_ops = self._competences(c, st.current_docs)
        conv = self._conventions(c, st.current_docs)
        cited |= cited_ops | {v["source_node"] for v in conv}
        payload = {
            "taught_before": taught_before,
            "current": current,
            "current_unmapped": unmapped,
            "not_yet": not_yet,
            "process_competences": [{"id": p["competence_id"], "label_de": p["label_de"]} for p in proc],
            "anforderungsbereiche": [{"id": a["competence_id"], "label_de": a["label_de"]} for a in afb],
            "operators": [{"id": o["competence_id"], "label_de": o["label_de"], "afb": o["afb"], "node_id": o["source_node"]} for o in ops],
            "conventions": [{"id": v["convention_id"], "kind": v["kind"], "text_de": v["text_de"], "node_id": v["source_node"]} for v in conv],
        }
        unc = st.uncertainty + unc_ops
        if not conv:
            unc.append("Zu Notation, Einheiten, Merkhilfe oder Taschenrechner liegt für diesen Kontext keine Vorgabe im Bestand vor.")
        cited |= st.cited
        payload["plan_switch_gap"] = sorted(st.cited)
        summary = _status_summary(c, st, current, not_yet)
        return self._envelope("curriculum_status", c, st.current_docs, payload, unc, cited, summary)

    def topics_for(self, context: dict, query: str, limit: int = 10) -> dict:
        try:
            c = normalise_context(self.conn, context)
        except ContextError as e:
            return self._error("topics_for", e)
        st = self._status(c)
        relation = {}
        for bucket, name in ((st.before, "taught_before"), (st.later, "not_yet"), (st.current, "current")):
            for t, ns in bucket.items():
                for n in ns:
                    relation[n["node_id"]] = name
        doc_ids = {d["document_id"] for b in st.trace.values() for d in b.binding}
        toks = [w.lower() for w in re.findall(r"[0-9A-Za-zÄÖÜäöüß]+", query or "") if len(w) >= 3]
        hits = []
        if toks and doc_ids:
            match = " OR ".join(f'"{t}"*' for t in toks)
            for r in self.conn.execute("SELECT node_id, bm25(node_fts) AS score FROM node_fts WHERE node_fts MATCH ? ORDER BY score LIMIT 200", (match,)):
                n = one(self.conn, "SELECT * FROM curriculum_node WHERE node_id = ?", (r["node_id"],))
                if n and n["document_id"] in doc_ids:
                    hits.append((r["score"], n))
        qwords = words(query)
        topic_hits = []
        for t in rows(self.conn, "SELECT topic_id FROM topic WHERE subject = ?", (c.subject,)):
            tt = self._topic(t["topic_id"])
            if any(contains_phrase(qwords, k) for k in tt["keywords"] + [tt["label_de"]]) or \
               any(contains_phrase(words(tt["label_de"] + " " + " ".join(tt["keywords"])), w) for w in qwords if len(w) >= 4):
                topic_hits.append({"topic_id": tt["topic_id"], "label_de": tt["label_de"],
                                   "relation": "current" if tt["topic_id"] in st.current else "taught_before" if tt["topic_id"] in st.before
                                   else "not_yet" if tt["topic_id"] in st.later else "not_in_this_track"})
        nodes = []
        cited = set()
        for _, n in hits[:limit]:
            e = self.node_out(n)
            e["topics"] = self._topics_of_node(n["node_id"])
            e["relation"] = relation.get(n["node_id"], "other_grade_or_kind")
            nodes.append(e)
            cited.add(n["node_id"])
        summary = (f"Suche nach {query!r} in den Plänen dieses Bildungsgangs: {len(nodes)} Fundstellen, "
                   f"{len(topic_hits)} passende Themen.")
        return self._envelope("topics_for", c, st.current_docs, {"query": query, "nodes": nodes, "topics": topic_hits},
                              st.uncertainty, cited, summary)

    def topic_detail(self, topic_id: str, context: dict | None = None) -> dict:
        t = self._topic(topic_id)
        if t is None:
            return {"tool": "topic_detail", "error": {"field": "topic_id", "message_de": f"Thema {topic_id!r} unbekannt", "candidates": []},
                    "citations": [], "uncertainty": [], "summary_de": f"Das Thema {topic_id} ist nicht im Bestand."}
        req = [{"topic_id": x, "label_de": (self._topic(x) or {}).get("label_de")} for x in
               [r["dst"] for r in rows(self.conn, "SELECT dst FROM edge WHERE rel='requires' AND certified=1 AND src=?", (topic_id,))]]
        follows = [{"topic_id": x, "label_de": (self._topic(x) or {}).get("label_de")} for x in
                   [r["src"] for r in rows(self.conn, "SELECT src FROM edge WHERE rel='requires' AND certified=1 AND dst=?", (topic_id,))]]
        appearances, cited = self._appearances(topic_id)
        payload = {"topic": {"topic_id": topic_id, "label_de": t["label_de"], "description": t.get("description"),
                             "kmk_anchor": t.get("kmk_anchor"), "grade_band": t.get("grade_band"), "keywords": t["keywords"]},
                   "requires": req, "required_by": follows, "appears_in": appearances}
        c, docs, unc = None, None, []
        if context:
            try:
                c = normalise_context(self.conn, context)
            except ContextError as e:
                return self._error("topic_detail", e)
            st = self._status(c)
            docs = st.current_docs
            rel = "current" if topic_id in st.current else "taught_before" if topic_id in st.before else \
                  "not_yet" if topic_id in st.later else "not_in_this_track"
            nodes = (st.current.get(topic_id) or st.before.get(topic_id) or st.later.get(topic_id) or [])
            payload["for_context"] = {"relation": rel, "nodes": [self.node_out(n) for n in nodes]}
            cited |= {n["node_id"] for n in nodes}
            unc = st.uncertainty
        lands = ", ".join(f"{a['land']} ab Klasse {a['first_grade']}" for a in appearances) or "in keinem Land zertifiziert zugeordnet"
        summary = f"{t['label_de']}: setzt {len(req)} Themen voraus und wird von {len(follows)} Themen vorausgesetzt. Vorkommen: {lands}."
        return self._envelope("topic_detail", c, docs, payload, unc, cited, summary)

    def _appearances(self, topic_id: str, date=None) -> tuple[list[dict], set[str]]:
        rs = rows(self.conn, """SELECT n.*, d.land FROM edge e JOIN curriculum_node n ON n.node_id = e.src
                                JOIN document d ON d.document_id = n.document_id
                                WHERE e.rel='maps_to' AND e.certified=1 AND e.dst = ? ORDER BY d.land, n.document_id, n.ordinal""", (topic_id,))
        by_land: dict[str, dict] = {}
        cited = set()
        for n in rs:
            d = self._doc(n["document_id"])
            a = n["grade_from"] if n["grade_from"] is not None else d["grade_from"]
            b = n["grade_to"] if n["grade_to"] is not None else d["grade_to"]
            forms = [r["school_form"] for r in rows(self.conn, "SELECT school_form FROM document_school_form WHERE document_id=?", (d["document_id"],))]
            land = by_land.setdefault(n["land"], {"land": n["land"], "first_grade": a, "documents": {}})
            land["first_grade"] = min(land["first_grade"], a)
            entry = land["documents"].setdefault(d["document_id"], {"document_id": d["document_id"], "title": d["title"],
                                                                     "school_forms": forms, "status_inventory": d["status"],
                                                                     "valid_from": d["valid_from"], "rollout": d["rollout"],
                                                                     "grades": [], "node_ids": []})
            if date is not None:
                start = one(self.conn, "SELECT school_year_start FROM land WHERE code=?", (n["land"],))["school_year_start"]
                entry["status_on_date"] = doc_public(self.conn, d, school_year(date, start), start)["status_on_date"]
            entry["grades"].append(_band(a, b))
            entry["node_ids"].append(n["node_id"])
            cited.add(n["node_id"])
        out = []
        for land in by_land.values():
            land["documents"] = list(land["documents"].values())
            for e in land["documents"]:
                e["grades"] = sorted(set(e["grades"]), key=_band_key)
            out.append(land)
        return out, cited

    def exercise_brief(self, context: dict, topic_id: str | None = None, query: str | None = None) -> dict:
        try:
            c = normalise_context(self.conn, context)
        except ContextError as e:
            return self._error("exercise_brief", e)
        st = self._status(c)
        unc = list(st.uncertainty)
        if topic_id is None and query:
            qw = words(query)
            cands = []
            for t in rows(self.conn, "SELECT topic_id FROM topic WHERE subject = ?", (c.subject,)):
                tt = self._topic(t["topic_id"])
                score = sum(contains_phrase(qw, k) for k in tt["keywords"] + [tt["label_de"]])
                score += sum(contains_phrase(words(tt["label_de"] + " " + " ".join(tt["keywords"])), w) for w in qw if len(w) >= 4)
                if score:
                    cands.append((-(score + (2 if tt["topic_id"] in st.current else 0)), tt["topic_id"]))
            if cands:
                topic_id = sorted(cands)[0][1]
                unc.append(f"Thema aus der Anfrage {query!r} erschlossen: {topic_id}.")
        if topic_id is None or self._topic(topic_id) is None:
            return self._envelope("exercise_brief", c, st.current_docs,
                                  {"topic": None, "status": "fail", "message_de": "Kein passendes Thema gefunden; topic_id angeben oder topics_for nutzen."},
                                  unc, set(), "Kein passendes Thema im Lehrplan dieses Kontexts gefunden.")
        t = self._topic(topic_id)
        cited: set[str] = set()
        if topic_id in st.current:
            relation, nodes = "current", st.current[topic_id]
        elif topic_id in st.before:
            relation, nodes = "taught_before", st.before[topic_id]
        elif topic_id in st.later:
            relation, nodes = "not_yet", st.later[topic_id]
        else:
            relation, nodes = "not_in_this_track", []
        cited |= {n["node_id"] for n in nodes}
        goals = []
        for n in nodes:
            o = self.node_out(n)
            goals.append({"node_id": o["node_id"], "page": o["page"], "text": o.get("text") or o.get("label"),
                          **({"text_withheld": o["text_withheld"]} if "text_withheld" in o else {})})
        known = set(st.current) | set(st.before)
        prereq = self._requires_closure(topic_id)
        allowed = [{"topic_id": p, "label_de": self._topic(p)["label_de"],
                    "node_ids": [n["node_id"] for n in (st.before.get(p) or st.current.get(p) or [])]} for p in prereq if p in known]
        missing = []
        for p in prereq:
            if p in known:
                continue
            later = st.later.get(p) or []
            missing.append({"topic_id": p, "label_de": self._topic(p)["label_de"],
                            "first_grade": min((n["_a"] for n in later), default=None), "node_ids": [n["node_id"] for n in later]})
            cited |= {n["node_id"] for n in later}
        for a in allowed:
            cited |= set(a["node_ids"])
        avoid = []
        for tid, ns in sorted(st.later.items(), key=lambda kv: min(n["_a"] for n in kv[1])):
            if tid in known or tid == topic_id:
                continue
            tt = self._topic(tid)
            avoid.append({"topic_id": tid, "label_de": tt["label_de"], "keywords": tt["keywords"],
                          "first_grade": min(n["_a"] for n in ns), "node_ids": [n["node_id"] for n in ns]})
            cited |= {n["node_id"] for n in ns}
        proc, afb, ops, unc_ops, cited_ops = self._competences(c, st.current_docs)
        conv = self._conventions(c, st.current_docs)
        cited |= cited_ops | {v["source_node"] for v in conv}
        unc += unc_ops
        if relation == "not_yet":
            status = "fail"
            msg = f"{t['label_de']} kommt in diesem Bildungsgang erst ab Klasse {min(n['_a'] for n in nodes)}; keine Aufgabe für Klasse {c.grade} schreiben."
        elif relation == "not_in_this_track":
            status, msg = "fail", f"{t['label_de']} ist im Plan dieses Bildungsgangs keinem Inhalt zugeordnet."
        elif missing:
            status, msg = "warn", "Voraussetzungen fehlen laut Lehrplan; nur ohne diese Voraussetzungen arbeiten oder sie in der Aufgabe einführen."
        elif relation == "taught_before":
            status, msg = "pass", "Thema ist Vorwissen aus früheren Klassen; geeignet für Wiederholung und Anwendung."
        else:
            status, msg = "pass", "Thema ist Stoff der aktuellen Klasse."
        payload = {
            "topic": {"topic_id": topic_id, "label_de": t["label_de"], "kmk_anchor": t.get("kmk_anchor")},
            "relation": relation, "status": status, "message_de": msg,
            "learning_goal": goals,
            "allowed_prerequisites": allowed,
            "missing_prerequisites": missing,
            "avoid_concepts": avoid,
            "afb_mix": {**AFB_DEFAULT, "basis": "Vorschlag, nicht aus dem Lehrplan; KMK-Anforderungsbereiche I bis III"},
            "operators": [{"label_de": o["label_de"], "afb": o["afb"], "node_id": o["source_node"]} for o in ops],
            "conventions": [{"kind": v["kind"], "text_de": v["text_de"], "node_id": v["source_node"]} for v in conv],
            "process_competences": [p["label_de"] for p in proc],
        }
        summary = (f"Aufgabenrahmen {t['label_de']} für {c.subject}, {c.school_form} Klasse {c.grade} ({c.land_name}, Stand {_de(c.date)}): "
                   f"{msg} Vermeiden: {', '.join(a['label_de'] for a in avoid[:3]) or 'nichts Bestimmtes'}.")
        return self._envelope("exercise_brief", c, st.current_docs, payload, unc, cited, summary)

    def check_exercise(self, context: dict, exercise_text: str) -> dict:
        try:
            c = normalise_context(self.conn, context)
        except ContextError as e:
            return self._error("check_exercise", e)
        st = self._status(c)
        tw = words(exercise_text)
        findings: list[dict] = []
        cited: set[str] = set()

        def add(check, verdict, message, node_ids):
            node_ids = [n for n in node_ids if n]
            if not node_ids:
                return  # a finding without a node behind it is not reported
            findings.append({"check": check, "verdict": verdict, "message_de": _no_dashes(message), "node_ids": node_ids})
            cited.update(node_ids)

        # 1. concepts
        detected = []
        for t in rows(self.conn, "SELECT topic_id FROM topic WHERE subject = ?", (c.subject,)):
            tt = self._topic(t["topic_id"])
            hit = next((k for k in tt["keywords"] if contains_phrase(tw, k)), None)
            if hit:
                detected.append((tt, hit))
        known = set(st.current) | set(st.before)
        for tt, hit in detected:
            tid = tt["topic_id"]
            if tid in st.current:
                add("concept", "pass", f"{tt['label_de']} ({hit!r}) ist Stoff der Klasse {c.grade}.", [n["node_id"] for n in st.current[tid]][:2])
            elif tid in st.before:
                add("concept", "pass", f"{tt['label_de']} ({hit!r}) ist Vorwissen aus früheren Klassen.", [n["node_id"] for n in st.before[tid]][:2])
            elif tid in st.later:
                first = min(n["_a"] for n in st.later[tid])
                add("concept", "fail", f"{tt['label_de']} ({hit!r}) kommt in diesem Bildungsgang erst ab Klasse {first}.",
                    [n["node_id"] for n in st.later[tid]][:2])
            else:
                elsewhere, _ = self._appearances(tid)
                ids = [i for a in elsewhere for d in a["documents"] for i in d["node_ids"]][:2]
                add("concept", "warn", f"{tt['label_de']} ({hit!r}) ist im Plan dieses Bildungsgangs nicht vorgesehen.", ids)
            if tid in known:
                for p in self._requires_closure(tid):
                    if p in known:
                        continue
                    pt = self._topic(p)
                    later = st.later.get(p) or []
                    add("prerequisite", "warn",
                        f"{tt['label_de']} setzt {pt['label_de']} voraus; das ist laut Plan noch nicht behandelt"
                        + (f" (erst ab Klasse {min(n['_a'] for n in later)})." if later else "."),
                        [n["node_id"] for n in later][:2] or [n["node_id"] for n in (st.current.get(tid) or st.before.get(tid))][:1])

        # 2. operators
        proc, afb, ops, unc_ops, _ = self._competences(c, st.current_docs)
        allowed = {}
        for o in ops:
            for f in operator_forms(o["label_de"]):
                allowed[f] = o
        lexicon = {}
        for o in rows(self.conn, "SELECT label_de, source_node FROM competence WHERE kind='operator'"):
            for f in operator_forms(o["label_de"]):
                lexicon.setdefault(f, o["label_de"])
        used = []
        for w in set(tw):
            if w in lexicon:
                used.append((w, lexicon[w]))
        list_node = ops[0]["source_node"] if ops else None
        for w, inf in sorted(used):
            if not ops:
                continue
            if w in allowed:
                add("operator", "pass", f"Operator {inf!r} steht in der Operatorenliste.", [allowed[w]["source_node"]])
            else:
                add("operator", "warn", f"Operator {inf!r} steht nicht in der Operatorenliste des geltenden Plans.", [list_node])

        # 3. conventions
        for v in self._conventions(c, st.current_docs):
            if not v["check_regex"]:
                continue
            m = re.search(v["check_regex"], exercise_text)
            if m:
                add("convention", v["severity"] or "warn", f"{v['text_de']} Gefunden: {m.group(0)!r}.", [v["source_node"]])
            else:
                add("convention", "pass", f"{v['text_de']} Eingehalten.", [v["source_node"]])

        verdicts = [f["verdict"] for f in findings]
        overall = "fail" if "fail" in verdicts else "warn" if "warn" in verdicts else "pass"
        unc = list(st.uncertainty) + unc_ops
        if not detected:
            unc.append("Kein Lehrplanbegriff erkannt; die Prüfung stützt sich nur auf Operatoren und Konventionen.")
        unc.append("Mechanische Prüfung über Schlüsselwörter: sie erkennt Begriffe, nicht jede Idee einer Aufgabe.")
        n_fail, n_warn = verdicts.count("fail"), verdicts.count("warn")
        summary = (f"Prüfung für {c.subject}, {c.school_form} Klasse {c.grade} ({c.land_name}, Stand {_de(c.date)}): "
                   f"Ergebnis {overall}, {n_fail} Fehler und {n_warn} Warnungen bei {len(findings)} Befunden.")
        if n_fail:
            summary += " " + "; ".join(f["message_de"].rstrip(".") for f in findings if f["verdict"] == "fail")[:300] + "."
        return self._envelope("check_exercise", c, st.current_docs, {"result": overall, "findings": findings}, unc, cited, summary)

    def compare_lands(self, topic_id: str, date: str | None = None) -> dict:
        from .validity import parse_date
        import datetime as _dt
        t = self._topic(topic_id)
        if t is None:
            return {"tool": "compare_lands", "error": {"field": "topic_id", "message_de": f"Thema {topic_id!r} unbekannt", "candidates": []},
                    "citations": [], "uncertainty": [], "summary_de": f"Das Thema {topic_id} ist nicht im Bestand."}
        d = parse_date(date) if date else _dt.date.today()
        appearances, cited = self._appearances(topic_id, date=d)
        lands_all = [r["code"] for r in rows(self.conn, "SELECT code FROM land ORDER BY code")]
        missing = [l for l in lands_all if l not in {a["land"] for a in appearances}]
        unc = []
        if missing:
            unc.append(f"Keine zertifizierte Zuordnung in: {', '.join(missing)} (nicht erfasst oder nicht im Plan).")
        out = {"tool": "compare_lands", "evaluated_for": {"date": d.isoformat()},
               "topic": {"topic_id": topic_id, "label_de": t["label_de"]}, "lands": appearances,
               "uncertainty": unc, "citations": self._check_citations(cited)}
        out["summary_de"] = _no_dashes(f"{t['label_de']} im Ländervergleich: " +
                                       ("; ".join(f"{a['land']} ab Klasse {a['first_grade']}" for a in appearances) or "keine Zuordnung") + ".")
        return out

    def coverage_gap(self, context: dict) -> dict:
        try:
            c = normalise_context(self.conn, context)
        except ContextError as e:
            return self._error("coverage_gap", e)
        st = self._status(c)
        cov = {r["topic_id"]: r["status"] for r in rows(self.conn, "SELECT topic_id, status FROM assistant_coverage")}
        expected = {**st.before, **st.current}
        gaps, partial, covered, cited = [], [], [], set()
        for tid, ns in sorted(expected.items(), key=lambda kv: min(n["_a"] for n in kv[1])):
            e = self._topic_entry(tid, ns, with_nodes=False)
            e["relation"] = "current" if tid in st.current else "taught_before"
            s = cov.get(tid)
            cited |= {n["node_id"] for n in ns}
            (covered if s == "covered" else partial if s == "partial" else gaps).append(e)
        summary = (f"Bis Klasse {c.grade} ({c.subject}, {c.school_form}, {c.land_name}) erwartet der Plan {len(expected)} Themen; "
                   f"abgedeckt {len(covered)}, teilweise {len(partial)}, offen {len(gaps)}.")
        return self._envelope("coverage_gap", c, st.current_docs,
                              {"gaps": gaps, "partial": partial, "covered": [e["topic_id"] for e in covered]},
                              st.uncertainty, cited, summary)

    def sources(self, document_id: str) -> dict:
        d = one(self.conn, "SELECT * FROM document WHERE document_id = ?", (document_id,))
        if d is None:
            return {"tool": "sources", "error": {"field": "document_id", "message_de": f"Dokument {document_id!r} unbekannt", "candidates": []},
                    "citations": [], "uncertainty": [], "summary_de": f"Das Dokument {document_id} ist nicht im Bestand."}
        fetches = rows(self.conn, "SELECT url, sha256, http_status, content_type, bytes, retrieved_at, error FROM fetch_log WHERE url = ? ORDER BY retrieved_at DESC LIMIT 3",
                       (d["source_url"],))
        sup = [r["dst"] for r in rows(self.conn, "SELECT dst FROM edge WHERE rel='supersedes' AND src=?", (document_id,))]
        sup_by = [r["src"] for r in rows(self.conn, "SELECT src FROM edge WHERE rel='supersedes' AND dst=?", (document_id,))]
        n_nodes = one(self.conn, "SELECT COUNT(*) n FROM curriculum_node WHERE document_id = ?", (document_id,))["n"]
        cls = self.pack.licence_class(d.get("licence"))
        payload = {
            "document": {k: d.get(k) for k in ("document_id", "land", "subject", "school_form", "grades", "title", "version",
                                               "valid_from", "valid_to", "rollout", "status", "validity_raw", "validity_note",
                                               "validity_confidence", "source_url", "sha256", "retrieved_at")},
            "licence": d.get("licence"), "licence_class": cls, "legal_basis": d.get("legal_basis"),
            "supersedes": sup, "superseded_by": sup_by, "nodes": n_nodes, "fetches": fetches,
            "citation_de": f"{d['title']}, {d.get('land')}, Fassung {d.get('version') or 'o. J.'}, {d.get('source_url')}"
                           + (f", abgerufen {d['retrieved_at'][:10]}" if d.get("retrieved_at") else ""),
        }
        unc = []
        if d.get("validity_confidence") != "stated":
            unc.append(f"Gültigkeit {d.get('validity_confidence')}: {d.get('validity_note') or d.get('validity_raw')}")
        if not d.get("sha256"):
            unc.append("Dokument noch nicht abgerufen.")
        summary = (f"{d['title']} ({d['land']}), Lizenz {d.get('licence')}: "
                   f"{'Volltext darf wiedergegeben werden' if cls == 'full_text' else 'nur Struktur und Link'}.")
        return {"tool": "sources", **payload, "uncertainty": unc, "citations": [], "summary_de": _no_dashes(summary)}

    def get_node(self, node_id: str) -> dict:
        n = one(self.conn, "SELECT * FROM curriculum_node WHERE node_id = ?", (node_id,))
        if n is None:
            return {"tool": "get_node", "error": {"field": "node_id", "message_de": f"Knoten {node_id!r} unbekannt", "candidates": []},
                    "citations": [], "uncertainty": [], "summary_de": f"Der Knoten {node_id} ist nicht im Bestand."}
        chain, p = [], n["parent_id"]
        while p:
            pn = one(self.conn, "SELECT node_id, kind, label, parent_id FROM curriculum_node WHERE node_id = ?", (p,))
            if not pn:
                break
            chain.insert(0, {"node_id": pn["node_id"], "kind": pn["kind"], "label": pn["label"]})
            p = pn["parent_id"]
        d = self._doc(n["document_id"])
        out = {"tool": "get_node", "node": self.node_out(n), "path": chain, "topics": self._topics_of_node(node_id),
               "document": {k: d[k] for k in ("document_id", "title", "land", "version", "valid_from", "status", "source_url")},
               "uncertainty": [], "citations": self._check_citations({node_id} | {x["node_id"] for x in chain})}
        out["summary_de"] = f"{n['kind']} aus {d['title']}, Seite {n['page']}."
        return out

    def neighbors(self, topic_id: str) -> dict:
        t = self._topic(topic_id)
        if t is None:
            return {"tool": "neighbors", "error": {"field": "topic_id", "message_de": f"Thema {topic_id!r} unbekannt", "candidates": []},
                    "citations": [], "uncertainty": [], "summary_de": f"Das Thema {topic_id} ist nicht im Bestand."}
        req = [r["dst"] for r in rows(self.conn, "SELECT dst FROM edge WHERE rel='requires' AND certified=1 AND src=?", (topic_id,))]
        by = [r["src"] for r in rows(self.conn, "SELECT src FROM edge WHERE rel='requires' AND certified=1 AND dst=?", (topic_id,))]
        children = [r["topic_id"] for r in rows(self.conn, "SELECT topic_id FROM topic WHERE parent_topic = ?", (topic_id,))]
        return {"tool": "neighbors", "topic_id": topic_id, "label_de": t["label_de"], "requires": req, "required_by": by,
                "parent": t.get("parent_topic"), "children": children, "uncertainty": [], "citations": [],
                "summary_de": f"{t['label_de']}: {len(req)} Voraussetzungen, {len(by)} Folgethemen."}


# ----------------------------------------------------------------------
# formatting helpers
# ----------------------------------------------------------------------

def _dedup(xs):
    out = []
    for x in xs:
        if x and x not in out:
            out.append(x)
    return out


def _band(a, b) -> str:
    return f"{a}" if a == b else f"{a}-{b}"


def _band_key(s: str):
    p = s.split("-")
    return (int(p[0]), int(p[-1]))


def _de(d) -> str:
    return d.strftime("%d.%m.%Y")


def _no_dashes(s: str) -> str:
    """House style: no em or en dashes in generated text."""
    return s.replace("—", ",").replace("–", "-")


def _status_summary(c: Context, st: Status, current: list, not_yet: list) -> str:
    if not st.current_docs:
        return (f"Für {c.subject}, {c.school_form} Klasse {c.grade} in {c.land_name} ist am {_de(c.date)} kein bindender Plan "
                f"im Bestand. Die Angaben sind deshalb unvollständig.")
    title = st.current_docs[0]["title"]
    cur = ", ".join(e["label_de"] for e in current[:4]) or "keine zugeordneten Themen"
    nxt = ", ".join(f"{e['label_de']} (ab Klasse {e['first_grade']})" for e in not_yet[:3]) or "nichts"
    s = (f"{c.subject}, {c.school_form} Klasse {c.grade} in {c.land_name}, Stand {_de(c.date)} (Schuljahr {school_year_label(c.school_year)}): "
         f"bindend ist {title}. Aktuell: {cur}. Noch nicht behandelt: {nxt}.")
    if st.uncertainty:
        s += f" {len(st.uncertainty)} Hinweise zu Unsicherheiten beachten."
    return s
