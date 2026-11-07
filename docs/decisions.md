# Decisions

Running log of design decisions. Newest first. Each entry says what was decided, by whom, and why.

## 2026-11-07: owner answers before M0

1. **Crawler contact.** `chiaramariaperrrone@pm.me`, set in `design/pack.yaml` (`fetch.contact`, `fetch.user_agent`). Used only in the User-Agent of the S1 fetcher.
2. **Mapping models.** Proposer `claude-sonnet-4-6`, judge `claude-opus-5-5` (`mapping.proposer`, `mapping.judge` in `design/pack.yaml`).
   - The package design asked for a judge from a *different model family*. The owner chose two Anthropic models. They differ in size and generation, which gives some independence but not the vendor-level independence the design intended.
   - Mitigations kept in the design: the judge sees only the verbatim curriculum text and the proposed edge, never the proposer's reasoning; mechanical checks run first and can fail an edge on their own; the held-out gold set (`data/gold_mappings.csv`) measures how good the certified edges are, so a shared blind spot shows up as low precision there rather than staying invisible.
   - Revisit if gold-set precision of certified edges falls below the threshold set in M1.
3. **Network access.** Skipped for now. M0 runs fully offline; network questions are settled when M1 needs them.

## 2026-11-07: answers taken from the brief (`prompts/build_kg_and_mcp.md`)

1. Scope: all 16 Länder, Mathematik, Chemie, Physik, Biologie, Politik/Wirtschaft, Arbeitslehre/WAT, integrated science and social-studies courses, Sachunterricht; general-education school forms, Primar to Abitur.
2. Format: SQLite knowledge graph with FTS5, Python builder, API and MCP server.
3. Sources: the inventory only; raw downloads outside git; full text only where the licence policy allows.
4. Language: curriculum text verbatim in German; code, keys and docs in English; `summary_de` in German; no em dashes in generated text.
5. Repo: commits straight to `main`, pushed after every step.
6. First real slice: MV Mathematik through S6, shown to the owner before widening.

## 2026-11-07: architecture additions to the draft design

See `docs/architecture-map.html`.

- **S0b validity normaliser** turns the free-text `in_force_since` field (about 130 distinct phrasings) into `valid_from`, `valid_to`, `rollout` and a confidence flag. Anything it cannot read with confidence is marked `needs_review` instead of guessed. Manual corrections go in `inventory/validity_overrides.yaml`, which a rebuild never overwrites.
- **Rollout rule.** `all_grades` or `ascending_from_grade:N`, where *N* is the highest grade that uses the new plan in its first school year *Y0*. A pupil in grade *g* in school year *y* is bound by the new plan exactly when *y* >= *Y0* and *g* <= *N* + (*y* - *Y0*). "Klassen 1 und 2 aufsteigend" is therefore `ascending_from_grade:2`. Stage labels (EF, Q1) are kept as written and resolved per Land through `grade_alias`.
- **When a cohort changes plan.** Along a cohort *g* - *y* is constant, so *g* <= *N* + (*y* - *Y0*) is equivalent to *g* - *y* <= *N* - *Y0*, which is cohort-invariant. The other condition, *y* >= *Y0*, is not. A cohort therefore changes plan at most once, in year *Y0*, and exactly the cohorts in grades *a* < *g* <= *N* then do so (*a* = the plan's lowest grade): *N* - *a* cohorts, none when the rollout starts with a single grade. For those cohorts `curriculum_status` names the content the new plan assumes from earlier grades that the old plan never taught. Checked by `tests/test_validity.py::test_rollout_switches_cohorts_only_at_start`.
- **Parallel plans.** Two `current` plans for the same Land, subject, school form and grades are usually parallel (an elective group, Politik vs Wirtschaft), not two versions. S0b notes them; kb_api reports them and asks for the course, instead of flagging their dates.
- **Placeholder Länder** (TH, SL): their inventory entries are returned as unverified candidates, never as binding.
- **Cohort trace.** `taught_before` and `not_yet` are computed along the pupil's own cohort: grade *g* - *k* is looked up in school year *y* - *k*, grade *g* + *k* in *y* + *k*, each against the plan that binds then, and the school form the pupil attends at that grade (`pathway` table). A pupil does not inherit a plan they never had.
- New tables: `land`, `school_form_alias`, `grade_alias`, `pathway`, `convention`; new columns on `document` (`doc_slug`, `rollout`, `school_year_start`, `validity_note`, `validity_confidence`), `competence` (`land`, `subject`, `afb`) and `topic` (`keywords`, `land_specific`).
