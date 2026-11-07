-- Knowledge base schema (SQLite). Draft for the curricula knowledge graph.
-- Pattern follows conjecture's knowledgebase: plain tables, an FTS5 index,
-- curated tables carried over on rebuild, and an audit trail.

PRAGMA foreign_keys = ON;

-- S1: every fetch, for provenance and polite re-runs
CREATE TABLE fetch_log (
  url TEXT NOT NULL,
  sha256 TEXT,
  http_status INTEGER,
  content_type TEXT,
  bytes INTEGER,
  retrieved_at TEXT NOT NULL,
  error TEXT
);

-- One curriculum document version
CREATE TABLE document (
  document_id TEXT PRIMARY KEY,          -- e.g. NW:klp-gost-mathematik-2023
  land TEXT NOT NULL,                    -- BW, BY, ... (ISO 3166-2:DE suffix)
  subject TEXT NOT NULL,                 -- Mathematik, Chemie, Physik, Naturwissenschaften, Sachunterricht
  school_form TEXT,
  level TEXT,                            -- Primar, Sek I, Sek II
  grades TEXT,                           -- e.g. "5-10"
  title TEXT NOT NULL,
  version TEXT,
  valid_from TEXT,
  valid_to TEXT,
  status TEXT,                           -- current, phasing_in, phasing_out, upcoming, superseded
  source_url TEXT,
  sha256 TEXT,
  licence TEXT,                          -- "amtliches Werk (§ 5 UrhG)", "CC BY-SA 4.0", ...
  legal_basis TEXT
);

-- Element of a document's own hierarchy, verbatim text
CREATE TABLE curriculum_node (
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
  page INTEGER
);
CREATE INDEX idx_node_doc ON curriculum_node(document_id);
CREATE INDEX idx_node_parent ON curriculum_node(parent_id);

CREATE VIRTUAL TABLE node_fts USING fts5(
  node_id UNINDEXED, label, text, tokenize = 'unicode61 remove_diacritics 0'
);

-- National backbone (CURATED: carried over on rebuild)
CREATE TABLE topic (
  topic_id TEXT PRIMARY KEY,             -- e.g. math.geometry.pythagoras
  subject TEXT NOT NULL,
  label_de TEXT NOT NULL,
  description TEXT,
  kmk_anchor TEXT,                       -- Leitidee L1-L5 / Basiskonzept
  grade_band TEXT,
  parent_topic TEXT REFERENCES topic(topic_id)
);

CREATE TABLE competence (
  competence_id TEXT PRIMARY KEY,        -- e.g. KMK.M.AHR.K2, IQB.OP.begruenden
  kind TEXT,                             -- process_competence, operator
  label_de TEXT,
  source TEXT
);

-- Edges between any of the above
CREATE TABLE edge (
  src TEXT NOT NULL,
  rel TEXT NOT NULL,                     -- maps_to, requires, assessed_by, supersedes, uses_competence
  dst TEXT NOT NULL,
  confidence REAL,
  method TEXT,                           -- manual, rule, llm:<model>
  certified INTEGER DEFAULT 0,           -- 1 = passed mechanical + judged audit
  curated INTEGER DEFAULT 0,             -- 1 = human decision, keep on rebuild
  created_at TEXT,
  PRIMARY KEY (src, rel, dst)
);
CREATE INDEX idx_edge_dst ON edge(dst, rel);

-- Context key the assistant queries with
CREATE TABLE context (
  context_id TEXT PRIMARY KEY,           -- {land}:{school_form}:{grade}:{course_level}
  land TEXT, school_form TEXT, grade INTEGER, course_level TEXT
);

-- Derived: which topics are expected in which context (rebuilt from edges)
CREATE TABLE expected_in (
  topic_id TEXT REFERENCES topic(topic_id),
  context_id TEXT REFERENCES context(context_id),
  via_node TEXT REFERENCES curriculum_node(node_id),
  PRIMARY KEY (topic_id, context_id, via_node)
);

-- Cross-check evidence (labels and links only for non-open sources)
CREATE TABLE evidence (
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
CREATE TABLE assistant_coverage (
  topic_id TEXT REFERENCES topic(topic_id),
  content_ref TEXT,
  status TEXT                            -- covered, partial, missing
);

-- Certify-or-decline audit trail
CREATE TABLE audit (
  audit_id INTEGER PRIMARY KEY,
  edge_src TEXT, edge_rel TEXT, edge_dst TEXT,
  stage TEXT,                            -- mechanical, judged
  verdict TEXT,                          -- pass, fail, decline
  reason TEXT,
  judge TEXT,
  created_at TEXT
);

-- Coverage gap for a context: topics expected but not covered
CREATE VIEW coverage_gap AS
SELECT e.context_id, t.topic_id, t.label_de, t.subject
FROM expected_in e
JOIN topic t ON t.topic_id = e.topic_id
LEFT JOIN assistant_coverage c ON c.topic_id = t.topic_id AND c.status = 'covered'
WHERE c.topic_id IS NULL
GROUP BY e.context_id, t.topic_id;
