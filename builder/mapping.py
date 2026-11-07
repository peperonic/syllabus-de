"""S5 map, S6 certify, S7 cross-check.

S5 stores proposals as uncertified edges. S6 runs mechanical checks first
(any failure declines the edge on its own), then the independent judge.
Only certified edges are ever used by kb_api. Declined edges stay in the
table with certified = 0 and their audit rows, so nothing is silently kept
and nothing is silently lost. S6 then measures the certified edges against
the held-out gold set and rebuilds `expected_in`.
"""
from __future__ import annotations

import csv
import json

import yaml

from kb.validity import parse_grades

from . import providers
from .common import StageContext, dumps, now


USE_BY_CLASS = {"full_text": "full_text", "structure_only": "structure_only", "cross_check_only": "cross_check"}


def _leaf_nodes(sc: StageContext) -> list[dict]:
    where, params = sc.scope.doc_where("d")
    return [dict(r) for r in sc.conn.execute(
        f"""SELECT n.node_id, n.kind, n.label, n.text, n.grade_from, n.grade_to, d.subject
            FROM curriculum_node n JOIN document d ON d.document_id = n.document_id
            WHERE {where} AND NOT EXISTS (SELECT 1 FROM curriculum_node c WHERE c.parent_id = n.node_id)""", params)]


def s5_map(sc: StageContext) -> dict:
    conn = sc.conn
    nodes = _leaf_nodes(sc)
    topics = [dict(r) for r in conn.execute("SELECT topic_id, subject, label_de, description, grade_band FROM topic")]
    prop = providers.proposer(sc.pack)
    proposals = prop.propose(nodes, topics)
    method = sc.pack.get("mapping.proposer")
    n = 0
    for p in proposals:
        exists = conn.execute("SELECT curated FROM edge WHERE src=? AND rel=? AND dst=?", (p.src, p.rel, p.dst)).fetchone()
        if exists and exists["curated"]:
            continue
        conn.execute("""INSERT OR REPLACE INTO edge(src, rel, dst, confidence, method, certified, curated, created_at)
                        VALUES (?,?,?,?,?,0,0,?)""", (p.src, p.rel, p.dst, p.confidence, method, now()))
        n += 1
    conn.commit()
    sc.say(f"S5: {n} proposals from {method} over {len(nodes)} leaf nodes and {len(topics)} topics")
    return {"proposals": n, "leaf_nodes": len(nodes), "topics": len(topics)}


def _mechanical(conn, e: dict) -> list[tuple[str, str]]:
    """Returns (verdict, reason) pairs; any 'fail' declines the edge."""
    out = []
    if e["rel"] == "maps_to":
        node = conn.execute("""SELECT n.*, d.subject FROM curriculum_node n JOIN document d ON d.document_id = n.document_id
                               WHERE n.node_id = ?""", (e["src"],)).fetchone()
        topic = conn.execute("SELECT * FROM topic WHERE topic_id = ?", (e["dst"],)).fetchone()
        if node is None:
            out.append(("fail", f"node {e['src']} does not exist"))
        if topic is None:
            out.append(("fail", f"topic {e['dst']} does not exist"))
        if node is not None and topic is not None:
            if node["subject"] != topic["subject"]:
                out.append(("fail", f"subject mismatch: node {node['subject']}, topic {topic['subject']}"))
            lo, hi, _ = parse_grades(topic["grade_band"]) if topic["grade_band"] else (None, None, None)
            if lo is not None and node["grade_from"] is not None and (node["grade_to"] < lo or node["grade_from"] > hi):
                out.append(("warn", f"grade span {node['grade_from']}-{node['grade_to']} outside topic band {topic['grade_band']}"))
    elif e["rel"] == "requires":
        for t in (e["src"], e["dst"]):
            if conn.execute("SELECT 1 FROM topic WHERE topic_id = ?", (t,)).fetchone() is None:
                out.append(("fail", f"topic {t} does not exist"))
        if e["src"] == e["dst"]:
            out.append(("fail", "a topic cannot require itself"))
    else:
        out.append(("fail", f"relation {e['rel']} is not proposed by S5"))
    return out or [("pass", "all mechanical checks passed")]


def s6_certify(sc: StageContext) -> dict:
    conn = sc.conn
    jd = providers.judge(sc.pack)
    judge_name = sc.pack.get("mapping.judge")
    pending = [dict(r) for r in conn.execute(
        "SELECT * FROM edge WHERE rel IN ('maps_to','requires') AND curated = 0 AND certified = 0")]
    stats = {"certified": 0, "declined_mechanical": 0, "declined_judge": 0, "warnings": 0}
    for e in pending:
        checks = _mechanical(conn, e)
        for verdict, reason in checks:
            conn.execute("INSERT INTO audit(edge_src, edge_rel, edge_dst, stage, verdict, reason, judge, created_at) VALUES (?,?,?,?,?,?,?,?)",
                         (e["src"], e["rel"], e["dst"], "mechanical", verdict, reason, "rules", now()))
            stats["warnings"] += verdict == "warn"
        if any(v == "fail" for v, _ in checks):
            conn.execute("INSERT INTO audit(edge_src, edge_rel, edge_dst, stage, verdict, reason, judge, created_at) VALUES (?,?,?,?,?,?,?,?)",
                         (e["src"], e["rel"], e["dst"], "mechanical", "decline", "declined after failed mechanical check", "rules", now()))
            stats["declined_mechanical"] += 1
            continue
        node = conn.execute("SELECT node_id, kind, label, text, grade_from, grade_to FROM curriculum_node WHERE node_id = ?", (e["src"],)).fetchone()
        topic = conn.execute("SELECT * FROM topic WHERE topic_id = ?", (e["dst"],)).fetchone()
        # The judge sees the edge, the verbatim node text and the topic. Not the rationale.
        v = jd.judge({"src": e["src"], "rel": e["rel"], "dst": e["dst"]}, dict(node) if node else None, dict(topic) if topic else None)
        conn.execute("INSERT INTO audit(edge_src, edge_rel, edge_dst, stage, verdict, reason, judge, created_at) VALUES (?,?,?,?,?,?,?,?)",
                     (e["src"], e["rel"], e["dst"], "judged", v.verdict, v.reason, judge_name, now()))
        if v.verdict == "pass":
            conn.execute("UPDATE edge SET certified = 1 WHERE src=? AND rel=? AND dst=?", (e["src"], e["rel"], e["dst"]))
            stats["certified"] += 1
        else:
            stats["declined_judge"] += 1
    stats["gold"] = _gold_report(sc)
    stats["expected_in"] = _rebuild_expected_in(sc)
    conn.commit()
    sc.say(f"S6: {stats}")
    return stats


def _gold_report(sc: StageContext) -> dict | None:
    """Precision and recall of certified maps_to edges against the held-out gold set.
    The gold file is read here and nowhere else."""
    path = sc.pack.rel(sc.pack.get("mapping.held_out_gold"))
    if path is None or not path.exists():
        return None
    with path.open(encoding="utf-8") as fh:
        gold = [(r["node_id"], r["topic_id"], r["label"].strip() == "1") for r in csv.DictReader(fh)]
    certified = {(r[0], r[1]) for r in sc.conn.execute("SELECT src, dst FROM edge WHERE rel='maps_to' AND certified=1")}
    labelled = {(a, b): lab for a, b, lab in gold}
    pos = {k for k, lab in labelled.items() if lab}
    judged = certified & set(labelled)
    tp = len(judged & pos)
    return {
        "gold_pairs": len(labelled), "gold_positive": len(pos),
        "certified_in_gold": len(judged), "true_positive": tp,
        "precision": round(tp / len(judged), 3) if judged else None,
        "recall": round(tp / len(pos), 3) if pos else None,
    }


def _rebuild_expected_in(sc: StageContext) -> int:
    """expected_in(topic, context, via_node) for every school form and grade a
    certified node covers. Time is not encoded here; kb_api resolves the date."""
    conn = sc.conn
    conn.execute("DELETE FROM expected_in")
    n = 0
    for r in conn.execute("""SELECT e.dst topic_id, n.node_id, n.grade_from, n.grade_to, n.course_level, d.land, d.document_id
                             FROM edge e JOIN curriculum_node n ON n.node_id = e.src JOIN document d ON d.document_id = n.document_id
                             WHERE e.rel = 'maps_to' AND e.certified = 1""").fetchall():
        if r["grade_from"] is None:
            continue
        for f in conn.execute("SELECT school_form FROM document_school_form WHERE document_id = ?", (r["document_id"],)).fetchall():
            for g in range(r["grade_from"], r["grade_to"] + 1):
                cid = f"{r['land']}:{f['school_form']}:{g}:{r['course_level'] or ''}"
                conn.execute("INSERT OR IGNORE INTO context VALUES (?,?,?,?,?)", (cid, r["land"], f["school_form"], g, r["course_level"]))
                conn.execute("INSERT OR IGNORE INTO expected_in VALUES (?,?,?)", (r["topic_id"], cid, r["node_id"]))
                n += 1
    return n


def s7_crosscheck(sc: StageContext) -> dict:
    conn = sc.conn
    stats = {"evidence": 0, "coverage": 0, "rejected": 0}
    conn.execute("DELETE FROM evidence")
    for path in sc.pack.files("evidence"):
        for ev in yaml.safe_load(path.read_text(encoding="utf-8")) or []:
            if conn.execute("SELECT 1 FROM topic WHERE topic_id = ?", (ev["topic_id"],)).fetchone() is None:
                stats["rejected"] += 1
                continue
            conn.execute("INSERT INTO evidence(topic_id, source_kind, land, label, url, licence, use) VALUES (?,?,?,?,?,?,?)",
                         (ev["topic_id"], ev["source_kind"], ev.get("land"), ev["label"], ev.get("url"), ev.get("licence"),
                          USE_BY_CLASS[sc.pack.licence_class(ev.get("licence"))]))
            stats["evidence"] += 1
    files = sc.pack.files("coverage")
    if files:
        conn.execute("DELETE FROM assistant_coverage")
    for path in files:
        for c in yaml.safe_load(path.read_text(encoding="utf-8")) or []:
            conn.execute("INSERT INTO assistant_coverage VALUES (?,?,?)", (c["topic_id"], c.get("content_ref"), c["status"]))
            stats["coverage"] += 1
    flags = [dict(r) for r in conn.execute("""SELECT ev.topic_id, ev.land FROM evidence ev WHERE ev.land IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM edge e JOIN curriculum_node n ON n.node_id = e.src JOIN document d ON d.document_id = n.document_id
        WHERE e.rel='maps_to' AND e.certified=1 AND e.dst = ev.topic_id AND d.land = ev.land)""")]
    stats["evidence_without_curriculum_node"] = flags
    conn.commit()
    sc.say(f"S7: {stats}")
    return stats
