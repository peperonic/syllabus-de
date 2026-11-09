"""Merge the judge's batch files into one verdicts file for S6 (file: judge).

    python3 scripts/merge_verdicts.py data/mapping/bw_mathematik_judge_batch*.json

Each batch input pairs with ..._verdicts_batchN.json. Item ids are "<text_key>|<topic_id>".
Fails loudly if any item lacks a verdict or a verdict names an unknown item.
"""
import json
import re
import sys
from pathlib import Path

out, problems = [], []
for inp in sorted(sys.argv[1:]):
    inp = Path(inp)
    n = re.search(r"batch(\d+)", inp.name).group(1)
    ver = inp.with_name(inp.name.replace(f"judge_batch{n}", f"verdicts_batch{n}"))
    items = {i["id"] for i in json.loads(inp.read_text(encoding="utf-8"))["items"]}
    data = json.loads(ver.read_text(encoding="utf-8"))
    got = {}
    for v in data["verdicts"]:
        if v["id"] not in items:
            problems.append(f"{ver.name}: unknown id {v['id']}")
            continue
        if v["verdict"] not in ("pass", "decline"):
            problems.append(f"{ver.name}: bad verdict {v['verdict']!r} for {v['id']}")
        got[v["id"]] = v
    missing = items - set(got)
    if missing:
        problems.append(f"{ver.name}: {len(missing)} items without verdict")
    for v in got.values():
        tk, dst = v["id"].split("|", 1)
        out.append({"text_key": tk, "rel": "maps_to", "dst": dst, "verdict": v["verdict"], "reason": v.get("reason", ""),
                    "judge": data.get("judge", ver.name)})
if problems:
    sys.exit("\n".join(problems))
target = Path(sys.argv[1]).with_name(re.sub(r"_judge_batch\d+\.json$", "_verdicts.json", Path(sys.argv[1]).name))
target.write_text(json.dumps({"verdicts": out}, ensure_ascii=False, indent=0), encoding="utf-8")
p = sum(v["verdict"] == "pass" for v in out)
print(f"{target}: {len(out)} verdicts, {p} pass, {len(out) - p} decline")
