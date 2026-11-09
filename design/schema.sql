-- Knowledge base schema (SQLite) for the curricula knowledge graph.
-- Pattern follows conjecture's knowledgebase: plain tables, an FTS5 index,
-- curated tables carried over on rebuild, and an audit trail.
-- Lines marked "M0" were added to the draft design; see docs/decisions.md.
-- builder and kb_api load this file directly, so it is the live schema.

PRAGMA foreign_keys = ON;

-- Build bookkeeping (M0): which stage ran when, with which inputs
CREATE TABLE IF NOT EXISTS build_run (
  run_id INTEGER PRIMARY KEY,
  stage TEXT NOT NULL,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  pack TEXT,
  stats TEXT                             -- JSON
);

-- Länder (M0): names, school-year start, whether the inventory is reliable
CREATE TABLE IF NOT EXISTS land (
  code TEXT PRIMARY KEY,                 -- BW, BY, ...
  name TEXT NOT NULL,
  school_year_start TEXT NOT NULL DEFAULT '08-01',   -- MM-DD
  inventory_status TEXT NOT NULL DEFAULT 'ok',      -- ok, placeholder
  note TEXT
);

-- School form names as people write them, mapped to the Land's official name (M0)
CREATE TABLE IF NOT EXISTS school_form_alias (
  land TEXT NOT NULL,
  alias TEXT NOT NULL,                   -- normalised lower-case key
  official TEXT NOT NULL,
  PRIMARY KEY (land, alias)
);

-- Stage labels such as E, EF, Q1 mapped to a grade number per Land and school form (M0)
CREATE TABLE IF NOT EXISTS grade_alias (
  land TEXT NOT NULL,
  school_form TEXT NOT NULL,
  label TEXT NOT NULL,
  grade INTEGER NOT NULL,
  PRIMARY KEY (land, school_form, label)
);

-- Which school form a pupil on track school_form attends at a given grade (M0).
-- Without a row, the pupil attends school_form itself.
CREATE TABLE IF NOT EXISTS pathway (
  land TEXT NOT NULL,
  school_form TEXT NOT NULL,             -- the pupil's track, e.g. Gymnasium
  grade_from INTEGER NOT NULL,
  grade_to INTEGER NOT NULL,
  attends TEXT NOT NULL,                 -- e.g. Grundschule for 1-4
  PRIMARY KEY (land, school_form, grade_from)
);

-- S1: every fetch, for provenance and polite re-runs
CREATE TABLE IF NOT EXISTS fetch_log (
  url TEXT NOT NULL,
  sha256 TEXT,
  http_status INTEGER,
  content_type TEXT,
  bytes INTEGER,
  retrieved_at TEXT NOT NULL,
  error TEXT
);

-- One curriculum document version
CREATE TABLE IF NOT EXISTS document (
  document_id TEXT PRIMARY KEY,          -- {land}:{doc_slug}
  land TEXT NOT NULL,
  doc_slug TEXT NOT NULL,                -- M0
  subject TEXT NOT NULL,
  school_form TEXT,
  level TEXT,                            -- Primar, Sek I, Sek II
  grades TEXT,                           -- e.g. "5-10"
  grade_from INTEGER,                    -- M0, parsed from grades
  grade_to INTEGER,                      -- M0
  title TEXT NOT NULL,
  version TEXT,
  valid_from TEXT,                       -- ISO date
  valid_to TEXT,                         -- ISO date, last day in force
  status TEXT,                           -- inventory status as of its verification date
  rollout TEXT NOT NULL DEFAULT 'all_grades',   -- M0: all_grades | ascending_from_grade:N
  school_year_start TEXT,                -- M0: overrides land.school_year_start
  validity_raw TEXT,                     -- M0: inventory in_force_since, verbatim
  validity_note TEXT,                    -- M0: what S0b inferred or could not
  validity_confidence TEXT,              -- M0: stated, inferred, needs_review
  inventory_notes TEXT,                  -- M0: the inventory entry's notes, verbatim
  source_url TEXT,
  sha256 TEXT,
  licence TEXT,
  legal_basis TEXT,
  retrieved_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_doc_lookup ON document(land, subject, school_form);

-- The official school forms a document applies to (M0). The inventory writes
-- composite strings such as "Gymnasium, Gesamtschule (gymnasiale Oberstufe)".
CREATE TABLE IF NOT EXISTS document_school_form (
  document_id TEXT NOT NULL REFERENCES document(document_id),
  school_form TEXT NOT NULL,
  PRIMARY KEY (document_id, school_form)
);

-- Element of a document's own hierarchy, verbatim text
CREATE TABLE IF NOT EXISTS curriculum_node (
  node_id TEXT PRIMARY KEY,              -- {land}:{doc_slug}:{path}
  document_id TEXT NOT NULL REFERENCES document(document_id),
  parent_id TEXT REFERENCES curriculum_node(node_id),
  kind TEXT,                             -- Lernbereich, Inhaltsfeld, Themenfeld, Kompetenzerwartung, Inhalt, ...
  ordinal INTEGER,
  label TEXT,
  text TEXT,
  grade_from INTEGER,
  grade_to INTEGER,
  course_level TEXT,                     -- grundlegend, erhöht, GK, LK, Basisfach, Leistungsfach
  page INTEGER,
  locator TEXT                           -- M1: where a reader finds it, e.g. a URL with #anchor for HTML plans
);
CREATE INDEX IF NOT EXISTS idx_node_doc ON curriculum_node(document_id);
CREATE INDEX IF NOT EXISTS idx_node_parent ON curriculum_node(parent_id);

CREATE VIRTUAL TABLE IF NOT EXISTS node_fts USING fts5(
  node_id UNINDEXED, label, text, tokenize = 'unicode61 remove_diacritics 0'
);

-- National backbone (CURATED: carried over on rebuild)
CREATE TABLE IF NOT EXISTS topic (
  topic_id TEXT PRIMARY KEY,             -- e.g. math.geometry.pythagoras
  subject TEXT NOT NULL,
  label_de TEXT NOT NULL,
  description TEXT,
  kmk_anchor TEXT,                       -- Leitidee L1-L5 / Basiskonzept
  grade_band TEXT,                       -- e.g. "7-9"
  parent_topic TEXT REFERENCES topic(topic_id),
  keywords TEXT,                         -- M0: JSON list of German terms used by check_exercise
  land_specific TEXT                     -- M0: Land code when the topic has no national match
);

-- Process competences and operators (CURATED)
CREATE TABLE IF NOT EXISTS competence (
  competence_id TEXT PRIMARY KEY,        -- e.g. KMK.M.AHR.K2, ZA.OP.begruenden
  kind TEXT,                             -- process_competence, operator, afb
  label_de TEXT,
  description TEXT,
  source TEXT,
  land TEXT,                             -- M0: NULL for national
  subject TEXT,                          -- M0: NULL for all subjects
  afb TEXT,                              -- M0: Anforderungsbereich of an operator (I, II, III, or I-II)
  source_node TEXT                       -- M0: node id the entry rests on, if any
);

-- Notation, units, Merkhilfe, calculator rules (M0, CURATED)
CREATE TABLE IF NOT EXISTS convention (
  convention_id TEXT PRIMARY KEY,
  land TEXT NOT NULL,
  subject TEXT NOT NULL,
  school_form TEXT,                      -- NULL for all school forms
  grade_from INTEGER,
  grade_to INTEGER,
  kind TEXT NOT NULL,                    -- notation, units, merkhilfe, calculator
  text_de TEXT NOT NULL,
  check_regex TEXT,                      -- optional: text that violates the convention
  severity TEXT DEFAULT 'warn',          -- warn or fail when check_regex matches
  source_node TEXT NOT NULL              -- every convention rests on a node
);

-- Edges between any of the above
CREATE TABLE IF NOT EXISTS edge (
  src TEXT NOT NULL,
  rel TEXT NOT NULL,                     -- maps_to, requires, assessed_by, supersedes, uses_competence
  dst TEXT NOT NULL,
  confidence REAL,
  method TEXT,                           -- manual, rule, llm:<model>, fixture
  certified INTEGER DEFAULT 0,           -- 1 = passed mechanical + judged audit
  curated INTEGER DEFAULT 0,             -- 1 = human decision, keep on rebuild
  created_at TEXT,
  PRIMARY KEY (src, rel, dst)
);
CREATE INDEX IF NOT EXISTS idx_edge_dst ON edge(dst, rel);

-- Context key the assistant queries with
CREATE TABLE IF NOT EXISTS context (
  context_id TEXT PRIMARY KEY,           -- {land}:{school_form}:{grade}:{course_level}
  land TEXT, school_form TEXT, grade INTEGER, course_level TEXT
);

-- Derived: which topics a document expects in which grade band (rebuilt after S6).
-- Time is resolved at query time, because the binding document depends on the date.
CREATE TABLE IF NOT EXISTS expected_in (
  topic_id TEXT REFERENCES topic(topic_id),
  context_id TEXT REFERENCES context(context_id),
  via_node TEXT REFERENCES curriculum_node(node_id),
  PRIMARY KEY (topic_id, context_id, via_node)
);

-- Cross-check evidence (labels and links only for non-open sources)
CREATE TABLE IF NOT EXISTS evidence (
  evidence_id INTEGER PRIMARY KEY,
  topic_id TEXT REFERENCES topic(topic_id),
  source_kind TEXT,                      -- abitur_focus, iqb_pool, cosh, serlo, leifi, textbook_plan
  land TEXT,
  label TEXT,
  url TEXT,
  licence TEXT,
  use TEXT                               -- full_text, structure_only, cross_check
);

-- What the learning assistant already covers (filled by the downstream project)
CREATE TABLE IF NOT EXISTS assistant_coverage (
  topic_id TEXT REFERENCES topic(topic_id),
  content_ref TEXT,
  status TEXT                            -- covered, partial, missing
);

-- Certify-or-decline audit trail
CREATE TABLE IF NOT EXISTS audit (
  audit_id INTEGER PRIMARY KEY,
  edge_src TEXT, edge_rel TEXT, edge_dst TEXT,
  stage TEXT,                            -- mechanical, judged
  verdict TEXT,                          -- pass, warn, fail, decline
  reason TEXT,
  judge TEXT,
  created_at TEXT
);

-- Coverage gap for a context: topics expected but not covered
CREATE VIEW IF NOT EXISTS coverage_gap AS
SELECT e.context_id, t.topic_id, t.label_de, t.subject
FROM expected_in e
JOIN topic t ON t.topic_id = e.topic_id
LEFT JOIN assistant_coverage c ON c.topic_id = t.topic_id AND c.status = 'covered'
WHERE c.topic_id IS NULL
GROUP BY e.context_id, t.topic_id;
