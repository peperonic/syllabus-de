# M1 results: Baden-Württemberg Mathematik, end to end

Status 2026-11-09. First real slice of the curricula knowledge base, built from the official BW plans on www.bildungsplaene-bw.de. The owner chose BW instead of the brief's MV; MV follows in a later step.

## What was built

| Stage | Result |
|---|---|
| S0, S0b inventory and validity | 9 BW Mathematik plan versions; start and rollout read as stated for 1, inferred for 7, review for 1 (Gemeinschaftsschule Oberstufe V2: no start date found) |
| S1 fetch | 9 plans, 240 pages (index pages plus 231 sub-pages), robots.txt honoured, Crawl-delay 2 s, no errors |
| S2, S3 extract and parse | 3,064 nodes: 2,600 content standards (Teilkompetenzen) with 801 distinct wordings, 73 process competences (G9 plan), operator tables |
| S4 backbone | 91 curated topics (Grundschule to Abitur), 114 prerequisite edges, 206 operator verbs from the plans' own operator tables, a detection-only verb lexicon |
| S5 propose | 2,946 node-to-topic proposals (917 distinct text-topic pairs), written by the build session's model |
| S6 certify | 2,827 certified, 119 declined by the judge (43 distinct pairs), 0 failed mechanically; 498 warn-level grade-band notes |
| Gold set | 60 texts labelled blind by a separate agent (177 nodes) |

Every node keeps its verbatim text and a locator: the plan page URL with the standard's official anchor, for example
`https://www.bildungsplaene-bw.de/,Lde/BP2016BW_ALLG_GYM_M.V2_IK_7-8_01#BP2016BW_ALLG_GYM_M.V2_IK_7-8_01_00_01`.
BW forbids PDF downloads in robots.txt, so citations point to web anchors instead of PDF pages.

## How the mapping was checked without an API key

- **Proposer:** the model in the build session read all 801 distinct texts and chose topics. Two texts were left unmapped on purpose (solving puzzles by trial, a process skill).
- **Judge:** three independent agents, one per batch of about 306 pairs. They saw only the curriculum text, its section, subheading and grade band, and the topic label. They saw no proposer reasoning and no gold labels. A pair counts only after an explicit pass (`file:` judge). Result: 874 pass, 43 decline. The judges wrote item-specific reasons for declines but generic reasons for passes, so pass decisions are less well documented than declines.
- **Gold set:** a fourth agent labelled a seeded random sample of 60 texts blind, from the full topic list, without seeing proposals or verdicts.

## Quality against the blind gold set

| Level | Precision | Recall | Note |
|---|---:|---:|---|
| Nodes (S6 report) | 0.864 | 0.856 | texts shared by several nodes count several times |
| Distinct texts | 0.868 | 0.831 | 49 of 60 texts agree exactly |

The 11 disagreements are mostly about granularity, and both readings are usually defensible. Examples: "Formeln nach jeder Variablen auflösen" mapped to Terme where gold says Lineare Gleichungen; measuring with instruments mapped to the general measuring topic where gold lists the specific quantities (lengths, time, money); "Winkelsummensatz" mapped to both Winkel and Dreiecke where gold has only Dreiecke. The gold set is agent-made, not human-verified: a person should spot-check it before these numbers are used as a quality bar.

Proposer and judge are the same kind of model, and the gold annotator too, so shared blind spots would not show up in these numbers. This is the main limitation of working without an API key or a human reviewer.

## Example answers

Stored in `examples/m1_bw/`:

- `curriculum_status_gym8.json`: Gymnasium grade 8, 9 Nov 2026. The binding plan is G8 V2 ("aufsteigend ab 2024/25, gilt 2026/27 bis Klasse 8"). The answer has 23 current topics with verbatim text and anchors, the taught-before topics grouped by band along the cohort's own plans, 26 not-yet topics (for example Pythagoras from grade 9), 29 operators with their Anforderungsbereich, and 528 citations. It names its uncertainties: the cohort switched plan in 2024/25 (grades 5 to 6), grades 7/8 form a double band, the course ends after grade 12 for this G8 cohort, and no notation conventions are on record.
- `check_exercise_gym8.json`: a sample exercise for the same pupil. Result `fail`, because Pythagoras is taught only from grade 9 in this cohort's plan. It also warns that `diskutieren` and `lösen` are not in the plan's operator list.
- `curriculum_status_gs3.json`: Grundschule grade 3. The binding plan is V2 (since 2024/25, ascending, all grades by 2026/27), and the answer notes that not_yet stops at grade 4 because the next plan depends on the secondary school form.

## Known gaps

1. Process competences of the 2016 plans (V1, V2) are not parsed yet; only the G9 plan's are.
2. No notation, unit or calculator conventions are curated for BW, so `check_exercise` does not check decimal commas or calculators there.
3. Gemeinschaftsschule Oberstufe V2 has no known start date; S0b sends it to review, and answers say so.
4. 66 of 2,600 standards have no certified topic (judge declines without an alternative, plus the 2 deliberate gaps); they appear under `current_unmapped`.
5. The brief's acceptance contexts for Physik and Biologie need those subjects ingested (M2).
