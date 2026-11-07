#!/usr/bin/env python3
"""Merge per-state and ancillary YAML files into one inventory for the scraper.

Usage: python3 -I merge_inventory.py <inventory_dir> <out_dir>
"""
import csv
import datetime as dt
import sys
from pathlib import Path

import yaml

STATE_CODES = [
    "BW", "BY", "BE", "BB", "HB", "HH", "HE", "MV",
    "NI", "NW", "RP", "SL", "SN", "ST", "SH", "TH",
]
REQUIRED_STATE_KEYS = [
    "code", "name", "ministry", "curriculum_institute", "curriculum_terms",
    "legal_basis", "licence_notice", "school_structure", "portals",
    "documents", "official_supplementary", "notes", "sources_checked",
]
REQUIRED_DOC_KEYS = [
    "subject", "school_form", "level", "grades", "title", "url", "format",
    "in_force_since", "status", "verified", "notes",
]
REQUIRED_RES_KEYS = [
    "name", "url", "publisher", "scope", "content_type", "format",
    "api_or_bulk_access", "curriculum_mapping", "licence",
    "use_in_knowledge_base", "value_for_topic_coverage", "verified", "notes",
]


def load(path: Path):
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def main(inv_dir: str, out_dir: str) -> int:
    inv = Path(inv_dir)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    problems = []
    states = {}
    ancillary = {}

    for path in sorted(inv.glob("*.yaml")):
        try:
            data = load(path)
        except Exception as exc:  # noqa: BLE001
            problems.append(f"{path.name}: YAML parse error: {exc}")
            continue
        if not isinstance(data, dict):
            problems.append(f"{path.name}: top level is not a mapping")
            continue
        schema = data.get("schema")
        if schema == "curricula-inventory/v1":
            st = data.get("state") or {}
            code = st.get("code")
            if code not in STATE_CODES:
                problems.append(f"{path.name}: unknown state code {code!r}")
                continue
            for key in REQUIRED_STATE_KEYS:
                if key not in st:
                    problems.append(f"{path.name}: missing key state.{key}")
            docs = st.get("documents") or []
            for i, doc in enumerate(docs):
                for key in REQUIRED_DOC_KEYS:
                    if key not in (doc or {}):
                        problems.append(f"{path.name}: documents[{i}] missing {key}")
            states[code] = st
        elif schema == "ancillary-resources/v1":
            cat = data.get("category") or path.stem
            res = data.get("resources") or []
            for i, r in enumerate(res):
                for key in REQUIRED_RES_KEYS:
                    if key not in (r or {}):
                        problems.append(f"{path.name}: resources[{i}] missing {key}")
            ancillary.setdefault(cat, []).extend(res)
        else:
            problems.append(f"{path.name}: unknown schema {schema!r}")

    missing = [c for c in STATE_CODES if c not in states]

    merged = {
        "schema": "curricula-knowledgebase-inventory/v1",
        "generated": dt.date.today().isoformat(),
        "scope": {
            "subjects": ["Mathematik", "Chemie", "Physik", "Biologie",
                         "Politik/Wirtschaft (Politik, Sozialkunde, Gemeinschaftskunde, Wirtschaft, Sozialwissenschaften, integrated Gesellschaftslehre)",
                         "Arbeitslehre/WAT (Arbeitslehre, Wirtschaft-Arbeit-Technik and equivalents)",
                         "Naturwissenschaften (integrated, lower Sek I)",
                         "Sachunterricht (Primar, all strands)"],
            "levels": ["Primar", "Sek I (all general-education tracks)", "Sek II"],
            "excluded": ["berufliche Schulen", "Förderschulen"],
        },
        "legal_note": (
            "Curriculum texts are amtliche Werke (§ 5 UrhG) and may be extracted; "
            "keep source metadata per chunk (Land, title, version, URL), keep text verbatim, "
            "tag supplementary material separately and check its rights_note before ingesting."
        ),
        "states": [states[c] for c in STATE_CODES if c in states],
        "ancillary": ancillary,
    }

    out_yaml = out / "curricula_inventory.yaml"
    with out_yaml.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(merged, fh, allow_unicode=True, sort_keys=False, width=120)

    # Flat CSV of curriculum documents for quick review / seeding a scraper queue
    out_csv = out / "curricula_documents.csv"
    with out_csv.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["state", "subject", "school_form", "level", "grades", "title",
                    "url", "format", "in_force_since", "status", "verified", "notes"])
        for code in STATE_CODES:
            st = states.get(code)
            if not st:
                continue
            for doc in st.get("documents") or []:
                doc = doc or {}
                w.writerow([code] + [doc.get(k, "") for k in REQUIRED_DOC_KEYS])

    # Summary
    print(f"states merged: {len(states)}/16; missing: {missing or 'none'}")
    for code in STATE_CODES:
        st = states.get(code)
        if not st:
            continue
        docs = st.get("documents") or []
        verified = sum(1 for d in docs if d and str(d.get("verified", "")).startswith("20"))
        subjects = sorted({(d or {}).get("subject", "?") for d in docs})
        print(f"  {code}: {len(docs)} documents ({verified} verified), portals={len(st.get('portals') or [])}, "
              f"supplementary={len(st.get('official_supplementary') or [])}, subjects={subjects}")
    for cat, res in ancillary.items():
        print(f"ancillary[{cat}]: {len(res)} resources")
    if problems:
        print("\nPROBLEMS:")
        for p in problems:
            print("  -", p)
    print(f"\nwrote {out_yaml} and {out_csv}")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
