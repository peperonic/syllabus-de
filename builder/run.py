"""Stage runner for the knowledge base build.

    python -m builder.run --list
    python -m builder.run                      # all stages
    python -m builder.run --from S3            # S3 and everything after
    python -m builder.run S0 S0b               # named stages only
    python -m builder.run --land MV --subject Mathematik
    python -m builder.run --pack tests/fixture/pack.yaml --data-dir /tmp/kb

Every stage is idempotent: re-running it gives the same tables. Curated
tables (backbone, overrides, human mapping decisions) are reloaded from files
or kept, never dropped.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):  # allow `python builder/run.py`
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from builder.backbone import s4_backbone  # noqa: E402
from builder.common import Scope, StageContext, dumps, now  # noqa: E402
from builder.extract import s2_extract  # noqa: E402
from builder.fetch import s1_fetch  # noqa: E402
from builder.inventory import s0_inventory, s0b_validity  # noqa: E402
from builder.mapping import s5_map, s6_certify, s7_crosscheck  # noqa: E402
from builder.parse_stage import s3_parse  # noqa: E402
from kb.db import connect, init_schema  # noqa: E402
from kb.pack import load_pack  # noqa: E402

STAGES = [
    ("S0", "inventory", s0_inventory),
    ("S0b", "validity", s0b_validity),
    ("S1", "fetch", s1_fetch),
    ("S2", "extract", s2_extract),
    ("S3", "parse", s3_parse),
    ("S4", "backbone", s4_backbone),
    ("S5", "map", s5_map),
    ("S6", "certify", s6_certify),
    ("S7", "crosscheck", s7_crosscheck),
]


def select(names: list[str], start: str | None) -> list[tuple]:
    keys = [s[0] for s in STAGES]
    lookup = {s[0].lower(): s for s in STAGES} | {s[1]: s for s in STAGES}
    if names:
        missing = [n for n in names if n.lower() not in lookup]
        if missing:
            raise SystemExit(f"unknown stage(s): {missing}; known: {keys}")
        wanted = {lookup[n.lower()][0] for n in names}
        return [s for s in STAGES if s[0] in wanted]
    if start:
        if start.lower() not in lookup:
            raise SystemExit(f"unknown stage {start}; known: {keys}")
        i = keys.index(lookup[start.lower()][0])
        return STAGES[i:]
    return STAGES


def run(pack_path=None, data_dir=None, stages=None, start=None, lands=None, subjects=None) -> dict:
    pack = load_pack(pack_path, data_dir)
    conn = connect(pack.db_path)
    init_schema(conn)
    sc = StageContext(conn, pack, Scope(lands or [], subjects or []))
    results = {}
    for key, name, fn in select(stages or [], start):
        print(f"{key} {name}")
        started = now()
        stats = fn(sc)
        conn.execute("INSERT INTO build_run(stage, started_at, finished_at, pack, stats) VALUES (?,?,?,?,?)",
                     (key, started, now(), str(pack.path), dumps(stats)))
        conn.commit()
        results[key] = stats
    conn.close()
    return results


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stages", nargs="*", help="named stages to run (default: all)")
    ap.add_argument("--list", action="store_true", help="list stages and exit")
    ap.add_argument("--from", dest="start", help="run this stage and all after it")
    ap.add_argument("--pack", help="domain pack (default design/pack.yaml)")
    ap.add_argument("--data-dir", help="data directory (default data/)")
    ap.add_argument("--land", action="append", default=[], help="limit to a Land (repeatable)")
    ap.add_argument("--subject", action="append", default=[], help="limit to a subject (repeatable)")
    a = ap.parse_args(argv)
    if a.list:
        for key, name, fn in STAGES:
            print(f"{key:4} {name:11} {(fn.__module__)}")
        return 0
    run(a.pack, a.data_dir, a.stages, a.start, a.land, a.subject)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
