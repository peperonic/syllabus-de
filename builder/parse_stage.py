"""S3 parse: page text to curriculum_node rows via the Land's parser profile.

Node ids are stable: {land}:{doc_slug}:{path}. Text is stored only when the
document's licence allows full text; otherwise label and structure only.
Rebuilding a document drops its nodes and their non-curated edges, keeps
curated decisions.
"""
from __future__ import annotations

import importlib
import json

from .common import StageContext


def s3_parse(sc: StageContext) -> dict:
    conn, pack = sc.conn, sc.pack
    where, params = sc.scope.doc_where("d")
    stats = {"documents": 0, "nodes": 0, "no_profile": 0, "text_withheld": 0}
    docs = [dict(r) for r in conn.execute(f"SELECT d.* FROM document d WHERE sha256 IS NOT NULL AND {where}", params)]
    for d in docs:
        profile = pack.parse_profile(d["land"])
        src = pack.extract_dir / f"{d['sha256']}.json"
        if not profile or not src.exists():
            stats["no_profile"] += 1
            continue
        mod = importlib.import_module(f"builder.parse.{profile}")
        pages = json.loads(src.read_text(encoding="utf-8"))
        parsed = mod.parse(d, pages)
        full_text = pack.licence_class(d["licence"]) == "full_text"
        _drop_document_nodes(conn, d["document_id"])
        for n in parsed:
            node_id = f"{d['document_id']}:{n['path']}"
            parent_id = f"{d['document_id']}:{n['parent_path']}" if n.get("parent_path") else None
            text = n["text"] if full_text else None
            label = n.get("label")
            if not full_text:
                stats["text_withheld"] += 1
                # Structure only: keep a neutral label, never a fragment of the text.
                label = label or f"{n['kind']} {n['path']}"
            conn.execute(
                """INSERT INTO curriculum_node(node_id, document_id, parent_id, kind, ordinal, label, text,
                   grade_from, grade_to, course_level, page) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (node_id, d["document_id"], parent_id, n["kind"], n["ordinal"], label, text,
                 n.get("grade_from"), n.get("grade_to"), n.get("course_level"), n.get("page")))
            conn.execute("INSERT INTO node_fts(node_id, label, text) VALUES (?,?,?)", (node_id, label or "", text or ""))
            stats["nodes"] += 1
        stats["documents"] += 1
    conn.commit()
    sc.say(f"S3: {stats}")
    return stats


def _drop_document_nodes(conn, document_id: str) -> None:
    ids = [r[0] for r in conn.execute("SELECT node_id FROM curriculum_node WHERE document_id = ?", (document_id,))]
    if not ids:
        return
    q = ",".join("?" * len(ids))
    conn.execute(f"DELETE FROM edge WHERE curated = 0 AND (src IN ({q}) OR dst IN ({q}))", ids + ids)
    conn.execute(f"DELETE FROM expected_in WHERE via_node IN ({q})", ids)
    conn.execute(f"DELETE FROM node_fts WHERE node_id IN ({q})", ids)
    conn.execute("UPDATE curriculum_node SET parent_id = NULL WHERE document_id = ?", (document_id,))
    conn.execute("DELETE FROM curriculum_node WHERE document_id = ?", (document_id,))
