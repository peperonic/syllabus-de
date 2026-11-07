# Knowledge graph design

The knowledge graph answers one question for the learning assistant: for a child in Land L, track T, grade G, which topics are expected, and which of them does the assistant not yet cover? It is built from the official curricula (the source of truth), anchored on a national backbone taxonomy, and cross-checked against exam and open-content sources.

## What we take from Opening-Science/conjecture

Conjecture is a hypothesis hub, not a curriculum tool, but five of its design decisions transfer directly. Its AGPL-3.0 licence applies if code is reused; reusing the ideas does not trigger it.

| conjecture pattern | Where it lives there | Adaptation here |
|---|---|---|
| Domain pack: one `pack.yaml` holds everything field-specific; hub code stays generic; `extends:` for overrides | `pack.py`, README "Domain packs" | `design/pack.yaml`: one pack per subject group or per Land set. Scraper, parser and graph code never hard-code a Land; portal quirks live in the pack and in `inventory/states/*.yaml`. |
| Staged, cached, resumable builder (stages A to K), each stage idempotent, run by `builder/run.py --from X` | `builder/run.py` | Stages S0 to S7 below, same runner pattern, raw downloads cached by URL hash. |
| Rebuild keeps curated tables | `build_knowledgebase.py` (OWNED tables vs carried-over tables) | Human-reviewed topic mappings and backbone edits are curated tables: a rebuild of extracted nodes never drops them. |
| One read-only interface: SQLite + FTS5 behind a small API, the same calls exposed as an MCP server | `corpus_api.py` (search, get_work, statements, neighbors), `mcp_server.py` | `kb_api.py` with search, get_node, topics_for, coverage_gap, neighbors; the same calls as an MCP server so the assistant (and any agent) reads the graph identically and read-only. Log every call. |
| Semantic validation: a cited id that does not exist fails the payload | `hof.py`, README "One output shape" | Every topic mapping and every assistant claim about a curriculum must cite a `node_id` that exists and whose text supports it. Unresolvable ids are rejected before any human or model review. |
| Certify or decline: mechanical checks first, then an independent judged audit of each step; one failed step declines | `judge/certify.py`, theoria | LLM-proposed mappings (Land node to backbone topic, prerequisite edges) are proposals. Mechanical checks first (ids exist, grade spans plausible, subject matches), then an independent judge model audits each mapping against the verbatim text; failures are declined, not silently kept. |
| Toy pack and conformance tests | `conformance/toy_pack/` | A tiny fixture (two Länder, one subject, a few pages) that every parser and the mapping step must pass offline before running on real data. |
| Blinding | `hypothesis_evidence` never shown to engines | Keep a held-out set of human-verified mappings that the mapping model never sees, to measure mapping accuracy honestly. |

Not taken: OpenAlex citation expansion, author tables, hypothesis engines and scoreboards, which have no equivalent here.

## Build stages

| Stage | Script (suggested) | Input | Output |
|---|---|---|---|
| S0 inventory | `scripts/merge_inventory.py` | `inventory/states/*.yaml` | `curricula_inventory.yaml`, seed CSV |
| S1 fetch | `builder/fetch.py` | seed CSV, portal profiles | `raw/<sha256>.pdf|html` + `fetch_log` rows (URL, status, hash, retrieved_at) |
| S2 extract | `builder/extract.py` | raw files | page-level text with layout hints (PyMuPDF or pdfplumber; HTML via selectolax) |
| S3 parse | `builder/parse_<land>.py` | page text | `curriculum_node` rows: hierarchy per document (Lernbereich, Inhaltsfeld, Themenfeld, Kompetenzerwartung, Inhalt), verbatim text, page, grades, track, course level |
| S4 backbone | `builder/backbone.py` | KMK Leitideen and Basiskonzepte (Mathematik, Biologie, Chemie, Physik), IQB Inhaltliche Vereinbarungen (labels and structure only), EPA Sozialkunde/Politik and Wirtschaft, GPJE and DeGÖB competence vocabularies, KMK Empfehlungen Verbraucherbildung 2025 and Demokratiebildung, OpenEduHub vocabs | `topic` rows (national backbone, curated) |
| S5 map | `builder/map_topics.py` | nodes + backbone | proposed `maps_to` edges with confidence |
| S6 certify | `builder/certify.py` | proposals | accepted or declined edges, `audit` rows |
| S7 cross-check | `builder/crosscheck.py` | exam focus docs, IQB pool categories, cosh catalogue, Serlo/LEIFI topic labels | `evidence` rows and coverage flags |

## Graph model

Nodes:
- `document`: one curriculum document version (Land, subject, school form, grades, version, valid_from, valid_to, status, source_url, licence).
- `curriculum_node`: one element of a document's own hierarchy, with verbatim text. Ids are stable: `{land}:{doc_slug}:{path}` (for example `NW:klp-gost-mathematik-2023:Q1/Analysis/KE3`).
- `topic`: a backbone concept, Land-independent (for example `math.geometry.pythagoras`, `phys.mechanics.newton_second_law`, `chem.reactions.redox`), with labels in German, KMK Leitidee or Basiskonzept, and typical grade band.
- `competence`: process competences (KMK K1 to K6, Kompetenzbereiche in Chemie/Physik) and IQB operators as a vocabulary.
- `context`: Land x school form x grade x course level, the key the assistant queries with.

Edges:
- `part_of` (curriculum_node to parent or document)
- `maps_to` (curriculum_node to topic), with confidence, method, certified flag
- `requires` (topic to topic, prerequisite), curated or certified
- `expected_in` (topic to context), derived from maps_to plus node grades
- `assessed_by` (topic to exam focus document or IQB pool category), cross-check evidence
- `supersedes` (document to document) for version transitions

## The coverage query

For context (L, T, G): all topics with an `expected_in` edge up to grade G, minus topics the assistant's content already covers (tracked in a separate `assistant_coverage` table). The difference is the gap list. Because every topic links back to verbatim curriculum nodes, each gap is explainable with a citation.

## Backbone for subjects without national standards

Politik/Wirtschaft and Arbeitslehre/WAT have no KMK Bildungsstandards. Their backbone is built bottom-up: cluster the Land curriculum nodes into topics, then anchor the clusters on the EPA Sozialkunde/Politik and EPA Wirtschaft Inhaltsbereiche, the four Handlungsfelder of the KMK Empfehlung Verbraucherbildung (2025), and the KMK Demokratiebildung and Berufliche Orientierung papers. Expect more Land-specific topics here than in the sciences, and mark them as such rather than forcing a national match.

## Licence-aware storage

- Curriculum documents: full verbatim text in `curriculum_node.text`.
- KMK, IQB, exam focus documents, textbook plans: store labels, structure and links only (`evidence.label`, `evidence.url`), never full text, unless a licence permits it (cosh catalogue CC BY-SA 4.0, Serlo CC BY-SA 4.0, Sachsen-Anhalt PDFs CC BY-SA).
- Keep `licence` on every row so an export can filter by it.
