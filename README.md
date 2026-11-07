# German curricula knowledge base

A knowledge graph of the official school curricula of the 16 Länder, and a read-only MCP server on top of it. Its main user is a model that writes exercises (Aufgaben): before writing, it asks what the curriculum expects for this exact pupil (Land, school form, grade, subject, date) and writes inside that frame.

Architecture: `docs/architecture-map.html`. Decisions: `docs/decisions.md`. Progress per Land and subject: `STATUS.md`.

## Build and use

```bash
pip install -r requirements.txt
python3 -m pytest -q                                   # offline, builds the toy fixture
python3 -m builder.run --list                          # stages S0 to S7
python3 -m builder.run S0 S0b                          # real inventory, no network
python3 -m builder.run --land MV --subject Mathematik  # one slice end to end (needs network, from M1)
python3 scripts/status_report.py                       # regenerate STATUS.md
```

Query the knowledge base from Python or the shell, or connect the MCP server (`examples/mcp_config/`):

```bash
python3 kb_api.py tools
python3 kb_api.py curriculum_status --context '{"land":"MV","school_form":"Gymnasium","grade":8,"subject":"Mathematik","date":"2026-11-07"}'
python3 mcp_server.py
```

Try everything on the offline fixture with `--pack tests/fixture/pack.yaml --data-dir /tmp/toykb` (fictional Länder ZA, ZB, ZC).

| Path | What it is |
|---|---|
| `builder/` | Staged builder: `run.py` runner, one module per stage, parser profiles in `builder/parse/` |
| `kb/` | Core library: validity rules, context resolution, the tool logic (`service.py`) |
| `kb_api.py`, `mcp_server.py` | The same read-only tools as Python API and CLI, and as an MCP server |
| `inventory/context_aliases.yaml`, `inventory/validity_overrides.yaml` | Curated corrections, kept across rebuilds |
| `examples/exercise_agent.md` | System prompt for the exercise-writing model |
| `tests/` | Offline tests and the toy fixture |

## The handoff package

Status: 2026-11-07. Source inventory complete for 16 Länder (Mathematik, Chemie, Physik, Biologie, Politik/Wirtschaft, Arbeitslehre/WAT, integrated science and social-studies courses, Sachunterricht). Nothing has been scraped yet. This package is the input for building (1) the scraper and (2) the knowledge graph.

Goal of the downstream project: a learning assistant that knows which topics a child in Germany is expected to learn, at which grade, in which school track and in which Land, so it misses no topic. The goal is coverage, not copying content.

## Contents

| Path | What it is |
|---|---|
| `prompts/build_kg_and_mcp.md` | Ready-to-paste Claude Code prompt for the knowledge graph and the MCP server. |
| `CLAUDE.md` | Instructions for Claude Code: what to build, in which order, which rules apply. Start here. |
| `inventory/curricula_inventory.yaml` | Merged inventory: 16 Länder (portals, legal basis, licence notice, school structure, 399 curriculum documents, official supplementary material) plus 129 ancillary resources. |
| `inventory/curricula_documents.csv` | Flat list of the 399 curriculum documents: the scraper's seed queue. |
| `inventory/states/*.yaml` | One file per Land, schema `curricula-inventory/v1`. Edit these, then re-run the merge script. |
| `inventory/ancillary/*.yaml` | National frameworks and structure, assessment material, open content, and national/open sources for Biologie and Politik/Wirtschaft (schema `ancillary-resources/v1`). |
| `research_notes/*.md` | The research behind every entry, with sources, verification dates, uncertainties. |
| `design/knowledge_graph.md` | Knowledge graph design, adapted from the Opening-Science/conjecture strategy. |
| `design/schema.sql` | SQLite schema for the knowledge base (nodes, edges, FTS5, audit). |
| `design/pack.yaml` | Draft domain-pack file in the conjecture style. |
| `scripts/merge_inventory.py` | Rebuilds the merged YAML and CSV from the per-state and ancillary files. |

Rebuild the merged inventory after editing a state file:

```bash
pip install pyyaml
python3 scripts/merge_inventory.py <folder with all state and ancillary YAMLs> inventory
```

(Copy `inventory/states/*.yaml` and `inventory/ancillary/*.yaml` into one folder first.)

## Documents per subject group

| Subject group | Documents |
|---|---|
| Politik/Wirtschaft (Politik, Sozialkunde, Gemeinschaftskunde, PGW, Wirtschaft, Sozialwissenschaften, Gesellschaftslehre) | 92 |
| Mathematik | 79 |
| Biologie | 54 |
| Chemie | 45 |
| Physik | 45 |
| Arbeitslehre/WAT (incl. WBS, AWT, WTH, Wirtschaft und Beruf, Verbraucherbildung) | 38 |
| Integrated science (BNT, NuT, NaWi, MNT) | 31 |
| Sachunterricht | 15 |

## Readiness per Land

- Ready for plain HTTP scraping: BW, BE, BB, HB, HH, HE, MV, NI, NW, SH (NRW Sek I PDF links must be read from the Lehrplannavigator pages).
- Need a headless browser: BY (LehrplanPLUS bot protection), RP (JS download list), ST (JS links), SN (database index with per-file tokens; index disallowed in robots.txt).
- Placeholders only, redo with a real browser first: TH, SL.

## Legal position in one paragraph

Curriculum texts are amtliche Werke (§ 5 UrhG) and may be extracted; keep Land, title, version, date and URL with every chunk and keep the text verbatim. Everything else on the portals (Handreichungen, sample tasks, exam papers, KMK and IQB documents) is protected unless a licence says otherwise; the `licence` and `use_in_knowledge_base` fields say per resource whether to ingest full text, structure only, or use as a cross-check. Not legal advice.

The full written report is the doc "German school curricula: source inventory and ancillary resources" (exportable as Markdown, Word or PDF from the doc).
