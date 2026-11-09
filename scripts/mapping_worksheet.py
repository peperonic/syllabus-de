"""Mapping without an API key: worksheets for a proposer, a judge and a blind gold annotator.

The three roles work on files, so any model in a session (or a person) can fill them,
and each role sees only what it should:

    python3 scripts/mapping_worksheet.py export   --land BW --subject Mathematik
        -> data/mapping/<slug>_worksheet.json: one entry per distinct standard text,
           with grades, section, the nodes sharing it, and keyword-ranked candidate topics.
    (proposer writes data/mapping/<slug>_proposals_by_text.yaml: {text_key: [topic_id, ...]})
    python3 scripts/mapping_worksheet.py expand   --land BW --subject Mathematik
        -> data/mapping/<slug>_proposals.yaml: node-level proposals for S5 (file: provider)
    python3 scripts/mapping_worksheet.py judge-input --land BW --subject Mathematik
        -> data/mapping/<slug>_judge_input.json: (text, topic) pairs, no proposer rationale,
           no candidate scores, no gold set
    (judge writes data/mapping/<slug>_verdicts.json: {"verdicts": [{text_key, dst, verdict, reason}]})
    python3 scripts/mapping_worksheet.py gold-sample --land BW --subject Mathematik --n 40
        -> data/mapping/<slug>_gold_input.json: sampled texts and the full topic list, no proposals
    (annotator writes data/mapping/<slug>_gold_labels.json: {text_key: [topic_id, ...]})
    python3 scripts/mapping_worksheet.py gold-csv --land BW --subject Mathematik
        -> data/gold_mappings.csv (node_id, topic_id, label) for S6
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

from builder.providers import text_key  # noqa: E402
from kb.pack import load_pack  # noqa: E402
from kb.text import contains_phrase, slug, words  # noqa: E402
from kb.validity import parse_grades  # noqa: E402

OUT = ROOT / "data" / "mapping"


def _conn(a):
    pack = load_pack(a.pack, a.data_dir)
    c = sqlite3.connect(pack.db_path)
    c.row_factory = sqlite3.Row
    return pack, c


def _groups(c, land, subject, kinds):
    q = ",".join("?" * len(kinds))
    rows = c.execute(f"""SELECT n.node_id, n.text, n.label, n.grade_from, n.grade_to, n.course_level, n.document_id,
                                p.label AS section, n.locator
                         FROM curriculum_node n JOIN document d ON d.document_id = n.document_id
                         LEFT JOIN curriculum_node p ON p.node_id = n.parent_id
                         WHERE d.land = ? AND d.subject = ? AND n.kind IN ({q}) AND n.text IS NOT NULL
                         ORDER BY n.document_id, n.ordinal""", (land, subject, *kinds)).fetchall()
    groups: dict[str, dict] = {}
    for r in rows:
        k = text_key(r["text"])
        g = groups.setdefault(k, {"text_key": k, "text": r["text"], "grades": set(), "levels": set(), "sections": set(),
                                  "subheads": set(), "nodes": [], "documents": set()})
        g["grades"].add(f"{r['grade_from']}-{r['grade_to']}" if r["grade_from"] != r["grade_to"] else f"{r['grade_from']}")
        if r["course_level"]:
            g["levels"].add(r["course_level"])
        if r["section"]:
            g["sections"].add(r["section"])
        sub = (r["label"] or "").split(")", 1)[-1].strip() if r["label"] else ""
        if sub:
            g["subheads"].add(sub)
        g["nodes"].append(r["node_id"])
        g["documents"].add(r["document_id"])
    for g in groups.values():
        for k in ("grades", "levels", "sections", "subheads", "documents"):
            g[k] = sorted(g[k])
    return list(groups.values())


def _topics(c, subject):
    out = []
    for r in c.execute("SELECT * FROM topic WHERE subject = ? ORDER BY topic_id", (subject,)):
        t = dict(r)
        t["keywords"] = json.loads(t["keywords"] or "[]")
        out.append(t)
    return out


def _candidates(g, topics, k=5):
    tw = words(g["text"] + " " + " ".join(g["subheads"]))
    lo = min(int(x.split("-")[0]) for x in g["grades"])
    hi = max(int(x.split("-")[-1]) for x in g["grades"])
    scored = []
    for t in topics:
        hits = [kw for kw in t["keywords"] if contains_phrase(tw, kw)]
        if not hits:
            continue
        a, b, _ = parse_grades(t["grade_band"])
        overlap = a is not None and not (b < lo - 1 or a > hi + 1)
        scored.append((len(hits) + (0.5 if overlap else 0), t["topic_id"], hits))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [{"topic_id": tid, "hits": h} for _, tid, h in scored[:k]]


def cmd_export(a):
    pack, c = _conn(a)
    kinds = pack.get("nodes.content_kinds", ["Teilkompetenz"])
    groups = _groups(c, a.land, a.subject, kinds)
    topics = _topics(c, a.subject)
    for g in groups:
        g["candidates"] = _candidates(g, topics)
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{_slug(a)}_worksheet.json"
    path.write_text(json.dumps({"land": a.land, "subject": a.subject, "groups": groups,
                                "topics": [{k: t[k] for k in ("topic_id", "label_de", "kmk_anchor", "grade_band")} for t in topics]},
                               ensure_ascii=False, indent=1), encoding="utf-8")
    nodes = sum(len(g["nodes"]) for g in groups)
    print(f"{path}: {len(groups)} distinct texts covering {nodes} nodes; "
          f"{sum(1 for g in groups if not g['candidates'])} without a keyword candidate")


def cmd_expand(a):
    ws = json.loads((OUT / f"{_slug(a)}_worksheet.json").read_text(encoding="utf-8"))
    by_text = yaml.safe_load((OUT / f"{_slug(a)}_proposals_by_text.yaml").read_text(encoding="utf-8")) or {}
    known = {t["topic_id"] for t in ws["topics"]}
    props, unknown = [], set()
    for g in ws["groups"]:
        for tid in by_text.get(g["text_key"], []) or []:
            if tid not in known:
                unknown.add(tid)   # kept: S6 declines it mechanically, which is the point of S6
            for nid in g["nodes"]:
                props.append({"src": nid, "rel": "maps_to", "dst": tid, "confidence": 0.8})
    path = OUT / f"{_slug(a)}_proposals.yaml"
    path.write_text(f"# Node-level proposals expanded from {_slug(a)}_proposals_by_text.yaml.\n"
                    + yaml.safe_dump(props, allow_unicode=True, sort_keys=False, width=200), encoding="utf-8")
    covered = sum(1 for g in ws["groups"] if by_text.get(g["text_key"]))
    print(f"{path}: {len(props)} node proposals; {covered}/{len(ws['groups'])} texts mapped; unknown topics: {sorted(unknown) or 'none'}")


def cmd_judge_input(a):
    ws = json.loads((OUT / f"{_slug(a)}_worksheet.json").read_text(encoding="utf-8"))
    by_text = yaml.safe_load((OUT / f"{_slug(a)}_proposals_by_text.yaml").read_text(encoding="utf-8")) or {}
    pack, c = _conn(a)
    topics = {t["topic_id"]: t for t in _topics(c, a.subject)}
    items = []
    for g in ws["groups"]:
        for tid in by_text.get(g["text_key"], []) or []:
            t = topics.get(tid, {"label_de": "(unknown topic)", "grade_band": None, "kmk_anchor": None})
            items.append({"text_key": g["text_key"], "text": g["text"], "grades": g["grades"], "section": g["sections"],
                          "subheading": g["subheads"], "dst": tid, "topic_label": t["label_de"],
                          "topic_anchor": t.get("kmk_anchor"), "topic_band": t.get("grade_band")})
    path = OUT / f"{_slug(a)}_judge_input.json"
    path.write_text(json.dumps({"instructions": JUDGE_INSTRUCTIONS, "items": items}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{path}: {len(items)} pairs to judge")


def cmd_gold_sample(a):
    ws = json.loads((OUT / f"{_slug(a)}_worksheet.json").read_text(encoding="utf-8"))
    rng = random.Random(a.seed)
    sample = rng.sample(ws["groups"], min(a.n, len(ws["groups"])))
    items = [{"text_key": g["text_key"], "text": g["text"], "grades": g["grades"], "section": g["sections"],
              "subheading": g["subheads"]} for g in sample]
    path = OUT / f"{_slug(a)}_gold_input.json"
    path.write_text(json.dumps({"instructions": GOLD_INSTRUCTIONS, "seed": a.seed, "items": items, "topics": ws["topics"]},
                               ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{path}: {len(items)} texts sampled with seed {a.seed}")


def cmd_gold_csv(a):
    ws = json.loads((OUT / f"{_slug(a)}_worksheet.json").read_text(encoding="utf-8"))
    labels = json.loads((OUT / f"{_slug(a)}_gold_labels.json").read_text(encoding="utf-8"))
    nodes = {g["text_key"]: g["nodes"] for g in ws["groups"]}
    rows = []
    for tk, tids in labels.items():
        for nid in nodes.get(tk, []):
            if not tids:
                rows.append((nid, "", 0))   # sampled, no topic fits: any certified edge is a false positive
            for tid in tids:
                rows.append((nid, tid, 1))
    path = ROOT / "data" / "gold_mappings.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["node_id", "topic_id", "label"])
        w.writerows(rows)
    print(f"{path}: {len(rows)} rows from {len(labels)} labelled texts")


def _slug(a):
    return f"{a.land.lower()}_{slug(a.subject, 20)}"


JUDGE_INSTRUCTIONS = """You audit proposed links between a curriculum standard (verbatim text from an official
German school curriculum) and a backbone topic. For each item decide independently:
pass = the standard's text is substantially about this topic, so a pupil meeting the standard is
       learning this topic; decline = it is not, or only in passing, or the link is too broad or wrong.
Judge only from the text, section and subheading given. Do not guess what the proposer intended.
Grade bands of topics are typical placements, not rules: a standard outside the band can still pass.
Write {"verdicts": [{"text_key": ..., "dst": ..., "verdict": "pass" | "decline", "reason": "<one short sentence, German or English>"}]}
covering every item."""

GOLD_INSTRUCTIONS = """You label curriculum standards (verbatim text from an official German school curriculum)
with backbone topics, blind: you see no one else's labels. For each item, list every topic from `topics`
that the standard is substantially about (usually one, sometimes two; an empty list if none fits).
Write {"<text_key>": ["topic_id", ...], ...} covering every item."""


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["export", "expand", "judge-input", "gold-sample", "gold-csv"])
    ap.add_argument("--land", required=True)
    ap.add_argument("--subject", required=True)
    ap.add_argument("--pack")
    ap.add_argument("--data-dir")
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--seed", type=int, default=20261109)
    a = ap.parse_args(argv)
    {"export": cmd_export, "expand": cmd_expand, "judge-input": cmd_judge_input,
     "gold-sample": cmd_gold_sample, "gold-csv": cmd_gold_csv}[a.cmd](a)


if __name__ == "__main__":
    main()
