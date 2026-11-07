# CLAUDE.md: building the curricula scraper and knowledge graph

Read `README.md`, then `design/knowledge_graph.md`. The inventory in `inventory/` is the single source for what to fetch; do not invent URLs.

## What to build, in order

1. **Repo skeleton** following `design/knowledge_graph.md`: `builder/` with one script per stage (S1 fetch, S2 extract, S3 parse, S4 backbone, S5 map, S6 certify, S7 cross-check), a `builder/run.py` stage runner (`--list`, `--from`, named stages), `kb_api.py`, `mcp_server.py`, `tests/` with a toy fixture.
2. **S1 fetch** from `inventory/curricula_documents.csv` and the `portals` entries in each state YAML. Plain HTTP first; Playwright for Länder listed under `fetch.headless_browser_for` in `design/pack.yaml`. Cache by sha256, write `fetch_log`, never re-download unchanged files.
3. **S2/S3 extract and parse** one Land at a time, starting with a well-structured one (MV or SH: clean PDF indexes, all URLs verified). Parsers are per-Land profiles because document structures differ; keep text verbatim and record page numbers.
4. **S4 backbone** from KMK and IQB structure (labels only), then **S5/S6** mapping with certify-or-decline.
5. **kb_api + MCP server**: read-only calls `search`, `get_node`, `topics_for(context)`, `coverage_gap(context)`, `neighbors(topic)`.

## Rules

- Respect robots.txt, about 1 request per second, identify the crawler in the User-Agent (ask the user for a contact address; never use one found elsewhere).
- Sachsen's Lehrplandatenbank index is disallowed for bots: do not crawl it; ask the user to export the link list manually or request it from the LaSuB.
- Full text only for rows whose licence allows it (see `licence_policy` in `design/pack.yaml`); for everything else store label, structure and URL.
- Every stored chunk carries Land, document title, version, valid_from, status, source URL, retrieved_at.
- Keep superseded and upcoming versions; several Länder change plans on 01.08.2027.
- Status values in the inventory: current, phasing_in, phasing_out, upcoming, superseded, draft.
- An LLM-proposed mapping is not a fact until it passes S6. Cite node ids that exist.
- No em dashes in generated docs (user preference).

## Known gaps to close before or during S1

- TH and SL: inventory entries are placeholders; fetch the portal index in a real browser and fill `inventory/states/TH.yaml` and `SL.yaml`, then re-run `scripts/merge_inventory.py`.
- BY: LehrplanPLUS subject URLs are pattern-built and unverified; Realschule Mathematik slugs are guesses.
- RP: no URL yet for Naturwissenschaften 5/6 and MSS Physik/Chemie.
- NW Sek I: G9 Kernlehrplan PDF links must be read from the Lehrplannavigator subject pages.
- SN: 7 of 8 plans lack their database file link.
- Biologie and Politik/Wirtschaft additions: BY LehrplanPLUS URLs unverified (Sozialkunde is now "Politik und Gesellschaft", slug pug); BW new Gemeinschaftskunde and WBS plans (in force 01.08.2027) not yet published; RP Sek I Sozialkunde only 1998/99 found; HB social-studies and WAT plans date from 2006 to 2012; NW G9 Biologie and Wirtschaft-Politik PDF links not extracted; ST Sozialkunde PDF missing; TH and SL placeholders.
- Classification calls to review: NI Wirtschaft and ST Sekundarschule Wirtschaft (economics vs. pre-vocational), SH Verbraucherbildung (filed under Arbeitslehre/WAT), MV Weltkunde (may contain no politics), BW AES (borderline).
- Full gap list: section "Gaps, risks and open questions" of the report and the `notes` fields in each state YAML.

## Reference

The knowledge graph borrows patterns from https://github.com/Opening-Science/conjecture (domain pack, staged cached builder, one read-only corpus API with an MCP twin, semantic citation validation, certify-or-decline). That repository is AGPL-3.0-or-later: reuse ideas freely, but copying its code makes the copied parts AGPL.
