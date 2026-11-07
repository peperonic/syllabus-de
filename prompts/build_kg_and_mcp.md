# Prompt for Claude Code: build the curriculum knowledge graph and the MCP server

Paste everything below the line into Claude Code, started in the unpacked `curricula-kb/` folder.

---

You are building a local knowledge graph of German school curricula and a read-only MCP server on top of it. The main consumer is an LLM that writes exercises (Aufgaben) for pupils. Before it writes any exercise, it must ask the MCP server what the curriculum says for this exact pupil context, and it must write the exercise within that frame.

## Read first

1. `README.md`, `CLAUDE.md`, `design/knowledge_graph.md`, `design/schema.sql`, `design/pack.yaml`.
2. `inventory/curricula_inventory.yaml` (16 Länder, 399 curriculum documents, 129 ancillary resources). This is the only source of what to fetch. Do not invent URLs.
3. The research notes in `research_notes/` when a Land needs special handling.

Follow all rules in `CLAUDE.md` (robots.txt, about 1 request per second, licence policy, keep superseded and upcoming versions, no em dashes in generated text). Ask me for the crawler contact address before the first network request.

## Scope

Subjects: Mathematik, Chemie, Physik, Biologie, Politik/Wirtschaft, Arbeitslehre/WAT, integrated science and social-studies courses, Sachunterricht. All general-education school forms, Primar to Abitur.

## Part 1: knowledge graph (staged builder)

Build the stages from `design/knowledge_graph.md` as a resumable, cached pipeline with `builder/run.py` (`--list`, `--from`, named stages):

- S1 fetch, S2 extract, S3 parse (one parser profile per Land), S4 backbone, S5 map, S6 certify, S7 cross-check.
- Start end to end with one Land and one subject (Mecklenburg-Vorpommern Mathematik: clean PDF index, all URLs verified), get it fully through S6, then widen Land by Land.
- Keep verbatim curriculum text with page numbers. Stable node ids: `{land}:{doc_slug}:{path}`.
- Model-proposed mappings (node to backbone topic, prerequisite edges) must pass mechanical checks and an independent judge audit before they count (certify or decline, as in Opening-Science/conjecture). Keep a held-out gold set the proposer never sees.

Validity in time is a first-class property, because the exercise model needs the status as of a given date:
- Each document has `valid_from`, `valid_to`, `status`, and a rollout rule. Many plans roll in year by year (aufsteigend): a new plan from 01.08.2027 may apply only to grade 5 in 2027/28, grade 6 in 2028/29, and so on, while older cohorts keep the old plan. Encode the rollout rule per document (`rollout: all_grades | ascending_from_grade:N`) and compute which version applies to a pupil from Land, school form, grade and date.
- School year starts 1 August in all Länder unless the inventory says otherwise.
- Grade information is often a band (5/6, 7/8, 9/10, Einführungsphase, Q1 to Q4). Keep bands; do not pretend to know the half-year unless the plan says so (Bayern LehrplanPLUS gives per-grade Lernbereiche, many others give double grades).

## Part 2: MCP server (the main deliverable)

Build `mcp_server.py` (stdio, Python MCP SDK) plus an identical Python API and CLI in `kb_api.py`, so every client sees the same data. All tools are read-only, annotated read-only and closed-world. Log every call to a JSONL file (path from env `CURRICULA_CALL_LOG`).

Input context used by most tools:

```json
{"land": "BW", "school_form": "Gymnasium", "grade": 8, "subject": "Physik",
 "course_level": null, "date": "2026-11-07"}
```

`date` defaults to today. `land` accepts codes or names. `school_form` is normalised to the Land's official names (return the mapping used).

Tools:

1. `resolve_context(context)` returns the normalised context and the applicable curriculum documents for that date (title, version, status, valid_from, rollout rule, why this version applies, source URL). If two versions could apply (transition year), return both and say which one is binding for this cohort.

2. `curriculum_status(context)`: the core call the exercise model makes first. Returns:
   - `taught_before`: backbone topics expected in earlier grades (prerequisites the pupil should already know), grouped by grade band.
   - `current`: topics expected in the current grade or band, each with the verbatim Kompetenzerwartung or Inhalt it comes from, node id, page and document.
   - `not_yet`: topics that come later in this Land and track (to be avoided in exercises), with the grade where they appear.
   - `process_competences` and `operators` that apply (KMK competence areas, Anforderungsbereiche I to III, Land operator list where available).
   - `conventions`: notation, units, formula sheet or Merkhilfe in use, calculator rules (WTR or CAS) where the inventory records them.
   - `uncertainty`: what the curriculum does not determine (for example sequence within a double grade left to the school, or a Land still marked placeholder), stated plainly.
   - `citations`: every node id used. Nothing in the response without a node id behind it.

3. `topics_for(context, query)`: search within the applicable documents (FTS5 plus optional embeddings) and return matching nodes with their backbone topics.

4. `topic_detail(topic_id, context)`: definition, prerequisites (`requires` edges), what follows, where it appears in every Land (grade and track), and the nodes for this context.

5. `exercise_brief(context, topic_id or query)`: a compact brief for the exercise writer: learning goal phrased from the curriculum text, allowed prerequisite concepts, concepts to avoid (`not_yet`), suggested Anforderungsbereich mix, operators to use, conventions, and citations. This is what the exercise model puts into its prompt.

6. `check_exercise(context, exercise_text)`: validates a drafted Aufgabe against the context: flags concepts that are `not_yet` taught, missing prerequisites, operators outside the list, wrong notation conventions; returns pass, warn or fail per finding, each with the node id it rests on. This is a mechanical and retrieval-based check first; an optional judge model may add findings, but every finding must cite a node.

7. `compare_lands(topic_id)`: grade and track where a topic appears in each Land, for content that must work across Länder.

8. `coverage_gap(context)`: topics expected up to this grade that the assistant's own content does not cover yet (from the `assistant_coverage` table).

9. `sources(document_id)`: provenance, licence and legal basis of a document, so outputs can cite correctly.

Rules for the server:
- Never return full text of sources whose licence is structure-only or cross-check-only (KMK, IQB, exam focus documents, textbooks). Return labels and links for those.
- Every answer states the curriculum version and the date it was evaluated for.
- If the context cannot be resolved (unknown school form, placeholder Land like Thüringen or Saarland), say so and return the nearest reliable information with the uncertainty, never a silent guess.
- Responses are compact JSON designed to be pasted into another model's prompt; keep a `summary_de` field (2 to 4 sentences in German) for direct use.

## Part 3: exercise-writer integration

Provide `examples/exercise_agent.md`: a system prompt for the exercise-writing LLM that requires this order: `resolve_context`, then `curriculum_status`, then `exercise_brief`, write the Aufgabe, then `check_exercise`, revise until no fail remains, and cite the curriculum version in the exercise metadata. Provide a matching config snippet for connecting the MCP server in Claude Code and Claude Desktop.

## Tests and acceptance

- `tests/` with a toy fixture (two fictional Länder, one subject, a few pages, one ascending rollout) that runs offline. Test: version selection across a rollout year, `not_yet` filtering, citations always resolve, licence filter never leaks full text.
- Acceptance on real data, at least for MV and one further Land with clean PDFs: for three contexts (Grundschule Klasse 3 Mathematik, Gymnasium Klasse 8 Physik, Oberstufe Biologie), `curriculum_status` returns topics with citations a human can verify against the PDF page.
- A short `STATUS.md` listing per Land and subject what is ingested, certified and still placeholder.

Work in small steps and show me the MV Mathematik end-to-end result (graph counts, one `curriculum_status` response, one `check_exercise` response) before widening to all Länder.
