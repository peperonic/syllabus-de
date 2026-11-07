"""S0 inventory load and S0b validity normalisation.

S0 reads the merged inventory (schema curricula-inventory/v1) into the
`land`, `document`, `document_school_form`, `school_form_alias`, `pathway`
and `grade_alias` tables. S0b turns the free-text validity fields into
valid_from, valid_to, rollout and a confidence flag, applies manual
overrides, and links successor plans with `supersedes` edges.
"""
from __future__ import annotations

import hashlib
import re
from itertools import combinations

import yaml

from kb.text import fold, slug
from kb.validity import parse_grades, parse_validity

from .common import StageContext, now

STATUS_RANK = {"superseded": 0, "phasing_out": 1, "current": 2, "phasing_in": 3, "upcoming": 4, "draft": 5}


def split_school_forms(s: str | None) -> list[str]:
    """'Gymnasium, Gesamtschule (gymnasiale Oberstufe)' -> ['Gymnasium', 'Gesamtschule']."""
    if not s:
        return []
    base = re.sub(r"\([^)]*\)", "", s)
    parts = re.split(r",|/|;|\bund\b|\band\b", base)
    out = []
    for p in parts:
        p = p.strip(" .")
        if p and p not in out:
            out.append(p)
    return out


def _load_yaml(path):
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def s0_inventory(sc: StageContext) -> dict:
    conn, pack = sc.conn, sc.pack
    inv = _load_yaml(pack.inventory_path)
    states = inv["states"]
    default_licence = pack.get("licence_policy.curriculum_default", "amtliches Werk (§ 5 UrhG)")
    by_land_licence = pack.get("licence_policy.curriculum_by_land", {}) or {}
    n_docs = 0
    seen_ids: set[str] = set()
    for st in states:
        code = st["code"]
        if sc.scope.lands and code not in sc.scope.lands:
            continue
        placeholder = "placeholder" in (st.get("notes") or "").lower()
        conn.execute("INSERT OR REPLACE INTO land(code, name, school_year_start, inventory_status, note) VALUES (?,?,?,?,?)",
                     (code, st["name"], st.get("school_year_start", "08-01"), "placeholder" if placeholder else "ok",
                      (st.get("notes") or "")[:500]))
        for d in st.get("documents") or []:
            if sc.scope.subjects and d["subject"] not in sc.scope.subjects:
                continue
            doc_id = document_id_for(code, d, seen_ids)
            seen_ids.add(doc_id)
            lo, hi, gnote = parse_grades(str(d.get("grades")) if d.get("grades") is not None else None)
            licence = d.get("licence") or by_land_licence.get(code) or default_licence
            conn.execute(
                """INSERT INTO document(document_id, land, doc_slug, subject, school_form, level, grades,
                   grade_from, grade_to, title, version, status, rollout, validity_raw, validity_note,
                   source_url, licence, legal_basis, inventory_notes)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?, 'all_grades', ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(document_id) DO UPDATE SET
                     land=excluded.land, doc_slug=excluded.doc_slug, subject=excluded.subject,
                     school_form=excluded.school_form, level=excluded.level, grades=excluded.grades,
                     grade_from=excluded.grade_from, grade_to=excluded.grade_to, title=excluded.title,
                     version=excluded.version, status=excluded.status, validity_raw=excluded.validity_raw,
                     validity_note=excluded.validity_note, source_url=excluded.source_url,
                     licence=excluded.licence, legal_basis=excluded.legal_basis,
                     inventory_notes=excluded.inventory_notes""",
                (doc_id, code, doc_id.split(":", 1)[1], d["subject"], d.get("school_form"), d.get("level"),
                 None if d.get("grades") is None else str(d.get("grades")), lo, hi, d["title"],
                 _version_of(d), d.get("status"), d.get("in_force_since"), gnote, d.get("url"), licence,
                 ((st.get("legal_basis") or {}).get("instrument") or "")[:300], d.get("notes")))
            conn.execute("DELETE FROM document_school_form WHERE document_id = ?", (doc_id,))
            for f in split_school_forms(d.get("school_form")):
                conn.execute("INSERT OR IGNORE INTO document_school_form VALUES (?,?)", (doc_id, f))
                conn.execute("INSERT OR IGNORE INTO school_form_alias VALUES (?,?,?)", (code, fold(f), f))
            n_docs += 1
    n_alias = _load_context_aliases(sc)
    conn.commit()
    sc.say(f"S0: {n_docs} documents, {n_alias} curated context rows")
    return {"documents": n_docs, "context_rows": n_alias}


def document_id_for(code: str, d: dict, taken: set[str]) -> str:
    """Stable, readable id: {land}:{subject}-{title}. If two inventory entries share
    it (BW lists one shared Sek I title per subject, NW one GOSt title for many),
    a short hash of the entry's identifying fields tells them apart."""
    base = f"{slug(d['subject'], 24)}-{slug(d['title'], 60)}"
    doc_id = f"{code}:{base}"
    if doc_id in taken:
        key = "|".join(str(d.get(k) or "") for k in ("title", "url", "subject", "school_form", "grades", "in_force_since", "status"))
        doc_id = f"{code}:{base}-{hashlib.sha256(key.encode()).hexdigest()[:6]}"
    return doc_id


def _version_of(d: dict) -> str | None:
    m = re.search(r"\b(19|20)\d\d\b", d.get("title") or "")
    return m.group(0) if m else None


def _load_context_aliases(sc: StageContext) -> int:
    """Curated school form aliases, pathways and grade aliases (carried over on rebuild)."""
    conn = sc.conn
    n = 0
    for path in sc.pack.files("context_aliases"):
        data = _load_yaml(path) or {}
        for code, spec in data.items():
            if sc.scope.lands and code not in sc.scope.lands:
                continue
            for alias, official in (spec.get("school_form_aliases") or {}).items():
                conn.execute("INSERT OR REPLACE INTO school_form_alias VALUES (?,?,?)", (code, fold(alias), official))
                conn.execute("INSERT OR IGNORE INTO school_form_alias VALUES (?,?,?)", (code, fold(official), official))
                n += 1
            conn.execute("DELETE FROM pathway WHERE land = ?", (code,))
            for p in spec.get("pathways") or []:
                for track in p["tracks"]:
                    conn.execute("INSERT OR REPLACE INTO pathway VALUES (?,?,?,?,?)",
                                 (code, track, p["grades"][0], p["grades"][1], p["attends"]))
                    n += 1
            conn.execute("DELETE FROM grade_alias WHERE land = ?", (code,))
            for g in spec.get("grade_aliases") or []:
                for form in g["school_forms"]:
                    for label, grade in g["labels"].items():
                        conn.execute("INSERT OR REPLACE INTO grade_alias VALUES (?,?,?,?)", (code, form, str(label).upper(), grade))
                        n += 1
    return n


# --------------------------------------------------------------------------
# S0b
# --------------------------------------------------------------------------

def s0b_validity(sc: StageContext) -> dict:
    conn = sc.conn
    where, params = sc.scope.doc_where("d")
    docs = [dict(r) for r in conn.execute(f"SELECT d.* FROM document d WHERE {where}", params)]
    counts = {"stated": 0, "inferred": 0, "needs_review": 0, "override": 0}
    for d in docs:
        p = parse_validity(d["validity_raw"], d.get("inventory_notes"), d["grade_from"],
                           d.get("school_year_start") or "08-01")
        note = "; ".join(x for x in (p.note, d.get("validity_note")) if x)
        conn.execute("""UPDATE document SET valid_from=?, valid_to=?, rollout=?, validity_confidence=?, validity_note=?
                        WHERE document_id=?""", (p.valid_from, p.valid_to, p.rollout, p.confidence, note or None, d["document_id"]))
        counts[p.confidence] += 1

    # Manual overrides win over the parser and survive rebuilds.
    for path in sc.pack.files("validity_overrides"):
        data = _load_yaml(path) or {}
        for doc_id, ov in data.items():
            if not conn.execute("SELECT 1 FROM document WHERE document_id = ?", (doc_id,)).fetchone():
                sc.say(f"S0b: override for unknown document {doc_id} ignored")
                continue
            for k in ("valid_from", "valid_to", "rollout", "school_year_start", "grade_from", "grade_to"):
                if k in ov:
                    conn.execute(f"UPDATE document SET {k} = ? WHERE document_id = ?", (ov[k], doc_id))
            conn.execute("UPDATE document SET validity_confidence = 'stated', validity_note = ? WHERE document_id = ?",
                         (f"manuell festgelegt: {ov.get('reason', '')}".strip(), doc_id))
            counts["override"] += 1

    n_sup = _link_successors(sc, docs)
    for path in sc.pack.files("validity_overrides"):
        for doc_id, ov in (_load_yaml(path) or {}).items():
            for old in ov.get("supersedes", []) or []:
                conn.execute("INSERT OR REPLACE INTO edge(src, rel, dst, confidence, method, certified, curated, created_at) "
                             "VALUES (?,?,?,?,?,?,?,?)", (doc_id, "supersedes", old, 1.0, "manual", 1, 1, now()))
            for old in ov.get("not_supersedes", []) or []:
                conn.execute("DELETE FROM edge WHERE src=? AND rel='supersedes' AND dst=?", (doc_id, old))
    conn.commit()
    sc.say(f"S0b: validity {counts}, {n_sup} supersedes edges")
    return {**counts, "supersedes": n_sup}


def _link_successors(sc: StageContext, docs: list[dict]) -> int:
    """Rule: within one Land and subject, two documents whose school forms and grade
    ranges overlap form a predecessor/successor pair when their inventory status
    ranks differ (superseded < phasing_out < current < phasing_in < upcoming),
    or when both have start dates and these differ. Only the nearest successor is linked."""
    conn = sc.conn
    conn.execute("DELETE FROM edge WHERE rel = 'supersedes' AND curated = 0 AND method = 'rule:s0b' AND src IN "
                 f"(SELECT document_id FROM document d WHERE {sc.scope.doc_where('d')[0]})", sc.scope.doc_where('d')[1])
    forms = {}
    for r in conn.execute("SELECT document_id, school_form FROM document_school_form"):
        forms.setdefault(r[0], set()).add(r[1])
    docs = [dict(r) for r in conn.execute(
        f"SELECT * FROM document d WHERE {sc.scope.doc_where('d')[0]}", sc.scope.doc_where('d')[1])]
    groups: dict[tuple, list[dict]] = {}
    for d in docs:
        groups.setdefault((d["land"], d["subject"]), []).append(d)
    n = 0
    for _, ds in groups.items():
        pairs = []
        for a, b in combinations(ds, 2):
            if not (forms.get(a["document_id"], set()) & forms.get(b["document_id"], set())):
                continue
            if a["grade_from"] is None or b["grade_from"] is None:
                continue
            if a["grade_to"] < b["grade_from"] or b["grade_to"] < a["grade_from"]:
                continue
            older, newer = _order(a, b)
            if older is None:
                if a.get("status") == b.get("status") == "current":
                    for x, y in ((a, b), (b, a)):
                        conn.execute("UPDATE document SET validity_note = trim(coalesce(validity_note,'') || '; überschneidet sich mit ' || ?, '; '), "
                                     "validity_confidence = 'needs_review' WHERE document_id = ?", (y["document_id"], x["document_id"]))
                continue
            pairs.append((older, newer))
        # Keep one successor per predecessor: the one whose school forms match best
        # (Jaccard |A & B| / |A | B|), then the nearest in time. Gesamtschule appears
        # in both MV Sek I plans, so overlap alone would pair AHR with Mittlere Reife.
        best: dict[str, dict] = {}

        def rank(older, newer):
            a, b = forms.get(older["document_id"], set()), forms.get(newer["document_id"], set())
            return (-len(a & b) / len(a | b), _key(newer))

        for older, newer in pairs:
            cur = best.get(older["document_id"])
            if cur is None or rank(older, newer) < rank(older, cur):
                best[older["document_id"]] = newer
        for old_id, newer in best.items():
            conn.execute("INSERT OR IGNORE INTO edge(src, rel, dst, confidence, method, certified, curated, created_at) "
                         "VALUES (?,?,?,?,?,?,?,?)", (newer["document_id"], "supersedes", old_id, 0.7, "rule:s0b", 1, 0, now()))
            n += 1
    return n


def _key(d: dict) -> tuple:
    return (d.get("valid_from") or "9999", STATUS_RANK.get(d.get("status") or "", 9))


def _order(a: dict, b: dict):
    ra, rb = STATUS_RANK.get(a.get("status") or "", 2), STATUS_RANK.get(b.get("status") or "", 2)
    va, vb = a.get("valid_from"), b.get("valid_from")
    if va and vb and va != vb:
        return (a, b) if va < vb else (b, a)
    if ra != rb:
        return (a, b) if ra < rb else (b, a)
    return None, None
