"""Parser profile for the offline fixture: a line-based markup.

    @<Kind> <path> [<a>-<b>] {<course level>} <text>

* path segments are separated by '/', the parent is the path without its last segment;
* the grade band [a-b] or [a] is optional and inherited from the parent;
* the course level {LK} is optional and inherited;
* a line without '@' continues the text of the previous node.

Real Länder get their own profiles (builder/parse/mv.py, ...), which return
the same node dicts.
"""
from __future__ import annotations

import re

LINE = re.compile(r"^@(\S+)\s+(\S+)(?:\s+\[(\d{1,2})(?:-(\d{1,2}))?\])?(?:\s+\{([^}]+)\})?\s*(.*)$")


def parse(document: dict, pages: list[dict]) -> list[dict]:
    nodes: dict[str, dict] = {}
    order: list[str] = []
    last = None
    for page in pages:
        for raw in page["text"].splitlines():
            line = raw.rstrip()
            if not line.strip():
                continue
            m = LINE.match(line)
            if not m:
                if last is not None:
                    last["text"] = (last["text"] + " " + line.strip()).strip()
                continue
            kind, path, a, b, level, text = m.groups()
            parent = path.rsplit("/", 1)[0] if "/" in path else None
            p = nodes.get(parent) if parent else None
            gf = int(a) if a else (p["grade_from"] if p else document.get("grade_from"))
            gt = int(b) if b else (int(a) if a else (p["grade_to"] if p else document.get("grade_to")))
            node = {
                "path": path, "parent_path": parent, "kind": kind, "ordinal": len(order) + 1,
                "label": text.split(":")[0][:120] if kind not in ("Kompetenzerwartung", "Inhalt") else None,
                "text": text, "grade_from": gf, "grade_to": gt,
                "course_level": level or (p["course_level"] if p else None), "page": page["page"],
            }
            nodes[path] = node
            order.append(path)
            last = node
    return [nodes[p] for p in order]
