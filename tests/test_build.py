"""The staged builder on the toy fixture: counts, certify-or-decline, licence at storage."""
import sqlite3


def db(toy_dir):
    c = sqlite3.connect(toy_dir / "kb.sqlite")
    c.row_factory = sqlite3.Row
    return c


def test_stage_counts(build_results):
    assert build_results["S0"]["documents"] == 8
    assert build_results["S1"]["fetched"] == 7 and build_results["S1"]["skipped"] == 1  # ZC has no verified URL
    assert build_results["S3"]["documents"] == 7
    assert build_results["S4"]["rejected"] == 0


def test_node_ids_are_stable_and_paged(toy_dir):
    c = db(toy_dir)
    n = c.execute("SELECT * FROM curriculum_node WHERE node_id = ?",
                  ("ZA:mathematik-rahmenplan-mathematik-gymnasium-2016:LB3/KE1",)).fetchone()
    assert n["page"] == 4 and n["grade_from"] == 9 and n["grade_to"] == 10
    assert n["parent_id"] == "ZA:mathematik-rahmenplan-mathematik-gymnasium-2016:LB3"
    assert "Satz des Pythagoras" in n["text"]


def test_certify_or_decline(toy_dir, build_results):
    s6 = build_results["S6"]
    assert s6["declined_mechanical"] == 2   # missing node, subject mismatch
    assert s6["declined_judge"] == 1        # quadratic functions text mapped to Pythagoras
    c = db(toy_dir)
    bad = c.execute("SELECT certified FROM edge WHERE src LIKE '%gymnasium-2016:LB3/KE2' AND dst = 'math.geometry.pythagoras'").fetchone()
    assert bad["certified"] == 0
    audits = {r["verdict"] for r in c.execute("SELECT verdict FROM audit WHERE edge_dst = 'phys.mechanics.speed'")}
    assert "fail" in audits and "decline" in audits
    # a proposed prerequisite edge goes through the same gate
    req = c.execute("SELECT certified, curated FROM edge WHERE src='math.functions.exponential' AND rel='requires' AND dst='math.numbers.percent'").fetchone()
    assert req["certified"] == 1 and req["curated"] == 0


def test_gold_set_measures_certified_edges(build_results):
    g = build_results["S6"]["gold"]
    assert g["precision"] == 1.0      # the wrong mapping was declined, not certified
    assert g["recall"] == 0.75        # the proposer skipped one gold mapping


def test_crosscheck_flags_missing_mapping(build_results):
    # ZA's 2016 plan has a node on tree diagrams that the proposer never mapped; exam evidence exposes it.
    assert build_results["S7"]["evidence_without_curriculum_node"] == [{"topic_id": "math.stochastics.tree_diagrams", "land": "ZA"}]


def test_structure_only_text_is_not_stored(toy_dir):
    c = db(toy_dir)
    rows = c.execute("SELECT text, label FROM curriculum_node WHERE document_id LIKE 'ZA:mathematik-kmk-%'").fetchall()
    assert rows and all(r["text"] is None for r in rows)
    assert all("GEHEIM" not in (r["label"] or "") for r in rows)
    fts = c.execute("SELECT COUNT(*) FROM node_fts WHERE node_fts MATCH 'GEHEIMER'").fetchone()[0]
    assert fts == 0


def test_supersedes_edge(toy_dir):
    c = db(toy_dir)
    e = c.execute("SELECT src, dst FROM edge WHERE rel='supersedes' ORDER BY src").fetchall()
    assert [(r["src"], r["dst"]) for r in e] == [
        ("ZA:mathematik-rahmenplan-mathematik-gymnasium-2027", "ZA:mathematik-rahmenplan-mathematik-gymnasium-2016"),
        ("ZB:mathematik-lehrplan-mathematik-gymnasium-2028", "ZB:mathematik-lehrplan-mathematik-gymnasium-2019")]


def test_rebuild_is_idempotent(toy_dir, tmp_path):
    """Running the whole pipeline twice gives the same graph."""
    import shutil
    from builder.run import run
    from tests.conftest import FIXTURE_PACK
    d = tmp_path / "again"
    shutil.copytree(toy_dir, d)
    run(pack_path=FIXTURE_PACK, data_dir=d, start="S0")
    a, b = db(toy_dir), db(d)
    q = "SELECT src, rel, dst, certified FROM edge ORDER BY 1, 2, 3"
    assert [tuple(r) for r in a.execute(q)] == [tuple(r) for r in b.execute(q)]
    q = "SELECT node_id, text, page FROM curriculum_node ORDER BY 1"
    assert [tuple(r) for r in a.execute(q)] == [tuple(r) for r in b.execute(q)]
