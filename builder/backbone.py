"""S4 backbone: curated topics, prerequisite edges, competences and conventions.

All of it is curated (human-reviewed YAML under the pack's `curated.backbone`),
so a rebuild reloads it from files and never loses it. Conventions and Land
operator lists must rest on a curriculum node that exists; entries pointing at
a missing node are rejected with a message rather than stored without a source.
"""
from __future__ import annotations

import json

import yaml

from .common import StageContext, now


def s4_backbone(sc: StageContext) -> dict:
    conn = sc.conn
    stats = {"topics": 0, "requires": 0, "competences": 0, "conventions": 0, "rejected": 0}
    files = sc.pack.files("backbone")
    conn.execute("DELETE FROM edge WHERE rel = 'requires' AND curated = 1")
    conn.execute("DELETE FROM convention")
    conn.execute("DELETE FROM competence")
    if not files:
        sc.say("S4: no curated backbone files in the pack")
    topics, requires = [], []
    for path in files:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for t in data.get("topics") or []:
            topics.append(t)
            for r in t.get("requires") or []:
                requires.append((t["id"], r))
        for c in data.get("competences") or []:
            if c.get("source_node") and not _node_exists(conn, c["source_node"]):
                sc.say(f"S4: competence {c['id']} rejected, source node {c['source_node']} missing")
                stats["rejected"] += 1
                continue
            conn.execute("INSERT OR REPLACE INTO competence VALUES (?,?,?,?,?,?,?,?,?)",
                         (c["id"], c["kind"], c["label_de"], c.get("description"), c.get("source"), c.get("land"),
                          c.get("subject"), c.get("afb"), c.get("source_node")))
            stats["competences"] += 1
        for v in data.get("conventions") or []:
            if not _node_exists(conn, v["source_node"]):
                sc.say(f"S4: convention {v['id']} rejected, source node {v['source_node']} missing")
                stats["rejected"] += 1
                continue
            conn.execute("INSERT OR REPLACE INTO convention VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                         (v["id"], v["land"], v["subject"], v.get("school_form"), v.get("grade_from"), v.get("grade_to"),
                          v["kind"], v["text_de"], v.get("check_regex"), v.get("severity", "warn"), v["source_node"]))
            stats["conventions"] += 1
    stats["operators_from_plans"] = _operators_from_nodes(conn) if sc.pack.get("backbone_auto.operators_from_plans") else 0
    known = {t["id"] for t in topics}
    for t in topics:
        conn.execute(
            """INSERT INTO topic(topic_id, subject, label_de, description, kmk_anchor, grade_band, parent_topic, keywords, land_specific)
               VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(topic_id) DO UPDATE SET subject=excluded.subject,
               label_de=excluded.label_de, description=excluded.description, kmk_anchor=excluded.kmk_anchor,
               grade_band=excluded.grade_band, parent_topic=excluded.parent_topic, keywords=excluded.keywords,
               land_specific=excluded.land_specific""",
            (t["id"], t["subject"], t["label_de"], t.get("description"), t.get("kmk_anchor"), t.get("grade_band"),
             t.get("parent"), json.dumps(t.get("keywords") or [], ensure_ascii=False), t.get("land_specific")))
        stats["topics"] += 1
    for a, b in requires:
        if b not in known:
            sc.say(f"S4: requires edge {a} -> {b} rejected, unknown topic")
            stats["rejected"] += 1
            continue
        conn.execute("INSERT OR REPLACE INTO edge(src, rel, dst, confidence, method, certified, curated, created_at) "
                     "VALUES (?,?,?,?,?,?,?,?)", (a, "requires", b, 1.0, "manual", 1, 1, now()))
        stats["requires"] += 1
    cycle = _find_cycle(requires)
    if cycle:
        raise ValueError(f"S4: prerequisite cycle in backbone: {' -> '.join(cycle)}")
    conn.commit()
    sc.say(f"S4: {stats}")
    return stats


def _operators_from_nodes(conn) -> int:
    """Operator lists printed in the plans become competence rows, one per verb,
    each resting on the node of its table row. Label format from the parser:
    'begründen, nachweisen, zeigen [AFB III]'."""
    import re
    n = 0
    for r in conn.execute("""SELECT c.node_id, c.label, d.land, d.subject FROM curriculum_node c
                             JOIN document d ON d.document_id = c.document_id WHERE c.kind = 'Operator'""").fetchall():
        m = re.match(r"^(.*?)\s*\[AFB ([IV\-– ]+)\]$", r["label"] or "")
        if not m:
            continue
        afb = m.group(2).replace("–", "-").replace(" ", "")
        for verb in [v.strip() for v in m.group(1).split(",") if v.strip()]:
            cid = f"{r['node_id']}#{verb}"
            conn.execute("INSERT OR REPLACE INTO competence VALUES (?,?,?,?,?,?,?,?,?)",
                         (cid, "operator", verb, None, "operator table of the plan", r["land"], r["subject"], afb, r["node_id"]))
            n += 1
    return n


def _node_exists(conn, node_id: str) -> bool:
    return conn.execute("SELECT 1 FROM curriculum_node WHERE node_id = ?", (node_id,)).fetchone() is not None


def _find_cycle(edges: list[tuple[str, str]]) -> list[str] | None:
    """`requires` must be a DAG: a topic cannot be its own prerequisite."""
    graph: dict[str, list[str]] = {}
    for a, b in edges:
        graph.setdefault(a, []).append(b)
    state: dict[str, int] = {}
    stack: list[str] = []

    def dfs(v):
        state[v] = 1
        stack.append(v)
        for w in graph.get(v, []):
            if state.get(w) == 1:
                return stack[stack.index(w):] + [w]
            if state.get(w) is None:
                c = dfs(w)
                if c:
                    return c
        state[v] = 2
        stack.pop()
        return None

    for v in list(graph):
        if state.get(v) is None:
            c = dfs(v)
            if c:
                return c
    return None
