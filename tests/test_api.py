"""kb_api on the toy fixture: version selection, not_yet, citations, licence filter."""
import json
import sqlite3

import pytest

from tests.conftest import ctx

G16 = "ZA:mathematik-rahmenplan-mathematik-gymnasium-2016"
G27 = "ZA:mathematik-rahmenplan-mathematik-gymnasium-2027"
HS = {"land": "ZA", "school_form": "hs", "grade": 7, "subject": "Mathematik", "date": "2026-11-07"}

CONTEXTS = [ctx(g, d) for g in (3, 5, 6, 8, 10) for d in ("2026-11-07", "2027-08-01", "2030-11-07")] + \
           [ctx(8, "2026-11-07", land="ZB"), HS, ctx(4, "2026-11-07", school_form="gs")]


def all_outputs(api):
    """Every tool on every context, so properties can be checked across the board."""
    for c in CONTEXTS:
        yield api.resolve_context(c)
        yield api.curriculum_status(c)
        yield api.topics_for(c, "Bruchzahlen Pythagoras Funktion")
        yield api.exercise_brief(c, topic_id="math.geometry.pythagoras")
        yield api.exercise_brief(c, query="Prozentrechnung")
        yield api.check_exercise(c, "Berechne die Hypotenuse mit Pythagoras. Vergleiche die Brüche 1/2 und 2/3. Nutze ein CAS. 3.5")
        yield api.coverage_gap(c)
        yield api.topic_detail("math.numbers.fractions", c)
    for t in ("math.geometry.pythagoras", "math.numbers.fractions", "math.functions.exponential"):
        yield api.compare_lands(t, "2027-11-07")
        yield api.neighbors(t)
    yield api.sources(G16)
    yield api.get_node(f"{G16}:LB3/KE1")


def walk_node_ids(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("node_id", "source_node") and isinstance(v, str):
                yield v
            elif k == "node_ids" and isinstance(v, list):
                yield from v
            else:
                yield from walk_node_ids(v)
    elif isinstance(obj, list):
        for x in obj:
            yield from walk_node_ids(x)


# --- version selection across a rollout year -------------------------------------------

@pytest.mark.parametrize("grade,date,expected", [
    (5, "2027-07-31", G16),   # last day of 2026/27
    (5, "2027-08-01", G27),   # first day of 2027/28: grade 5 starts the new plan
    (6, "2027-11-07", G16),   # grade 6 in 2027/28 stays on the old plan
    (6, "2028-11-07", G27),
    (8, "2029-11-07", G16),   # reach in 2029/30 is grade 7
    (8, "2030-11-07", G27),
    (10, "2031-11-07", G16),  # last old cohort
    (10, "2032-11-07", G27),
])
def test_version_selection(api, grade, date, expected):
    r = api.resolve_context(ctx(grade, date))
    assert [d["document_id"] for d in r["binding"]] == [expected]
    assert r["evaluated_for"]["date"] == date


def test_transition_year_returns_both_versions(api):
    r = api.resolve_context(ctx(6, "2027-11-07"))
    assert r["transition_year"] is True
    assert [d["document_id"] for d in r["binding"]] == [G16]
    assert G27 in [d["document_id"] for d in r["also_in_force_this_year"]]
    assert "bindend" in r["summary_de"]


def test_status_on_date(api):
    r = api.resolve_context(ctx(8, "2026-11-07"))
    assert r["binding"][0]["status_on_date"] == "current"
    r = api.resolve_context(ctx(8, "2028-11-07"))
    assert r["binding"][0]["status_on_date"] == "phasing_out"


# --- not_yet filtering ------------------------------------------------------------------

def topic_ids(section):
    if section and "topics" in section[0]:
        return {t["topic_id"] for g in section for t in g["topics"]}
    return {t["topic_id"] for t in section}


def test_not_yet_depends_on_the_binding_plan(api):
    old = api.curriculum_status(ctx(8, "2027-11-07"))
    new = api.curriculum_status(ctx(8, "2030-11-07"))
    assert "math.geometry.pythagoras" in topic_ids(old["not_yet"])
    assert "math.geometry.pythagoras" not in topic_ids(old["current"])
    assert "math.geometry.pythagoras" in topic_ids(new["current"])
    first = {t["topic_id"]: t["first_grade"] for t in old["not_yet"]}
    assert first["math.geometry.pythagoras"] == 9


@pytest.mark.parametrize("c", CONTEXTS)
def test_buckets_are_disjoint(api, c):
    r = api.curriculum_status(c)
    if "error" in r:
        return
    nyet = topic_ids(r["not_yet"])
    assert not nyet & topic_ids(r["current"])
    assert not nyet & topic_ids(r["taught_before"])


def test_cohort_never_credited_with_a_plan_it_did_not_have(api):
    """Grade 8 in 2027/28 learnt grades 5-6 under the 2016 plan, so taught_before
    cites the 2016 plan, not the 2027 one."""
    r = api.curriculum_status(ctx(8, "2027-11-07"))
    ids = [i for g in r["taught_before"] for t in g["topics"] for i in t["node_ids"]]
    assert ids and not any(i.startswith(G27) for i in ids)
    assert any(i.startswith("ZA:mathematik-rahmenplan-mathematik-grundschule-2015") for i in ids)


def test_check_exercise_flags_not_yet(api):
    r = api.check_exercise(ctx(8, "2027-11-07"), "Berechne mit dem Satz des Pythagoras die Hypotenuse.")
    assert r["result"] == "fail"
    fails = [f for f in r["findings"] if f["verdict"] == "fail"]
    assert fails and all(f["node_ids"] for f in fails)
    r2 = api.check_exercise(ctx(8, "2030-11-07"), "Berechne mit dem Satz des Pythagoras die Hypotenuse.")
    assert r2["result"] == "pass"


def test_check_exercise_operators_and_conventions(api):
    r = api.check_exercise(ctx(9, "2027-11-07"), "Beweise, dass die Lösung 2.5 ist. Nutze dabei ein CAS.")
    by = {(f["check"], f["verdict"]) for f in r["findings"]}
    assert ("operator", "warn") in by          # 'beweisen' is not in the 2016 list
    assert ("convention", "fail") in by        # CAS not allowed in 9/10
    assert ("convention", "warn") in by        # decimal point instead of comma


def test_exercise_brief(api):
    b = api.exercise_brief(ctx(8, "2027-11-07"), topic_id="math.geometry.pythagoras")
    assert b["status"] == "fail" and b["relation"] == "not_yet"
    b = api.exercise_brief(ctx(8, "2030-11-07"), topic_id="math.geometry.pythagoras")
    assert b["status"] == "pass" and b["relation"] == "current"
    assert "math.algebra.linear_equations" in {p["topic_id"] for p in b["allowed_prerequisites"]}
    assert b["learning_goal"][0]["page"] == 3 and "Pythagoras" in b["learning_goal"][0]["text"]
    assert "math.geometry.trigonometry" in {a["topic_id"] for a in b["avoid_concepts"]}


def test_coverage_gap(api):
    r = api.coverage_gap(ctx(8, "2027-11-07"))
    gaps = {g["topic_id"] for g in r["gaps"]}
    assert "math.numbers.fractions" in r["covered"] and "math.numbers.fractions" not in gaps
    assert "math.numbers.decimals" in {p["topic_id"] for p in r["partial"]}
    assert "math.algebra.linear_equations" in gaps


def test_compare_lands(api):
    r = api.compare_lands("math.geometry.pythagoras", "2027-11-07")
    first = {l["land"]: l["first_grade"] for l in r["lands"]}
    assert first == {"ZA": 8, "ZB": 7}
    assert any("ZC" in u for u in r["uncertainty"])


# --- citations always resolve -----------------------------------------------------------

def test_citations_resolve_and_cover_every_node_mentioned(api, toy_dir):
    c = sqlite3.connect(toy_dir / "kb.sqlite")
    known = {r[0] for r in c.execute("SELECT node_id FROM curriculum_node")}
    n = 0
    for out in all_outputs(api):
        assert set(out["citations"]) <= known, out["tool"]
        mentioned = set(walk_node_ids({k: v for k, v in out.items() if k != "citations"}))
        assert mentioned <= set(out["citations"]) | known, out["tool"]
        if out["tool"] not in ("sources", "neighbors", "compare_lands", "get_node", "resolve_context"):
            assert mentioned <= set(out["citations"]), (out["tool"], mentioned - set(out["citations"]))
        n += 1
    assert n > 100


def test_every_check_finding_cites_a_node(api):
    for c in CONTEXTS:
        r = api.check_exercise(c, "Berechne und beweise mit Pythagoras, Sinus und Prozent: 3.5 mit CAS.")
        for f in r.get("findings", []):
            assert f["node_ids"], f


# --- licence filter never leaks full text -----------------------------------------------

def test_licence_filter_never_leaks(api):
    for out in all_outputs(api):
        assert "GEHEIMER VOLLTEXT" not in json.dumps(out, ensure_ascii=False), out["tool"]


def test_licence_filter_holds_even_if_text_was_stored(tampered_api):
    for out in all_outputs(tampered_api):
        assert "GEHEIMER VOLLTEXT" not in json.dumps(out, ensure_ascii=False), out["tool"]
    r = tampered_api.curriculum_status(HS)
    nodes = [n for t in r["current"] for n in t["nodes"]]
    assert nodes and all("text" not in n and "text_withheld" in n for n in nodes)


# --- no silent guesses ------------------------------------------------------------------

def test_placeholder_land_is_reported(api):
    r = api.resolve_context(ctx(8, "2026-11-07", land="Xenland"))
    assert r["binding"] == []
    assert any("Platzhalter" in u for u in r["uncertainty"])
    s = api.curriculum_status(ctx(8, "2026-11-07", land="ZC"))
    assert s["current"] == [] and "kein bindender Plan" in s["summary_de"]


def test_unknown_school_form_returns_candidates(api):
    r = api.curriculum_status(ctx(8, "2026-11-07", school_form="Waldorfschule"))
    assert r["error"]["field"] == "school_form"
    assert "Gymnasium" in r["error"]["candidates"]


def test_land_by_name_and_alias_mapping(api):
    r = api.resolve_context(ctx(8, "2026-11-07", land="zettland", school_form="gym", subject="mathe"))
    assert r["context"]["land"] == "ZA" and r["context"]["school_form"] == "Gymnasium"
    assert r["context_mapping"]["school_form"] == {"input": "gym", "used": "Gymnasium", "source": "school_form_alias"}


# --- house style and logging ------------------------------------------------------------

def test_every_answer_has_summary_without_dashes(api):
    for out in all_outputs(api):
        s = out["summary_de"]
        assert s and "—" not in s and "–" not in s
        assert 1 <= s.count(".") <= 8, s


def test_versions_and_dates_are_stated(api):
    for c in CONTEXTS:
        for out in (api.curriculum_status(c), api.exercise_brief(c, query="Bruch"), api.check_exercise(c, "Berechne 1/2.")):
            if "error" in out:
                continue
            assert out["evaluated_for"]["date"] == c["date"]
            assert "curriculum_version" in out


def test_call_log(api, tmp_path):
    api.curriculum_status(ctx(8, "2027-11-07"))
    api.sources(G16)
    lines = [json.loads(x) for x in (tmp_path / "calls.jsonl").read_text().splitlines()]
    assert [l["tool"] for l in lines] == ["curriculum_status", "sources"]
    assert lines[0]["ok"] and lines[0]["citations"] > 0


# --- a cohort that changes plan mid-course -----------------------------------------------

ZB28 = "ZB:mathematik-lehrplan-mathematik-gymnasium-2028"


def test_switching_cohort_gap_is_reported(api):
    """ZB 2028 starts with Klassen 5 and 6 (N = 6, a = 5): only the grade-6 cohort of
    2028/29 switches plan. The new plan has tree diagrams in grade 5, which that
    cohort never had under the old plan."""
    r = api.curriculum_status(ctx(6, "2028-11-07", land="ZB"))
    assert [d["document_id"] for d in r["curriculum_version"]] == [ZB28]
    assert any("Planwechsel" in u and "Baumdiagramme" in u for u in r["uncertainty"])
    assert r["plan_switch_gap"] == [f"{ZB28}:LB1/KE1"]
    assert set(r["plan_switch_gap"]) <= set(r["citations"])


@pytest.mark.parametrize("grade,date", [(5, "2028-11-07"), (6, "2029-11-07"), (7, "2028-11-07")])
def test_non_switching_cohorts_have_no_gap(api, grade, date):
    r = api.curriculum_status(ctx(grade, date, land="ZB"))
    assert not any("Planwechsel" in u for u in r["uncertainty"]), r["uncertainty"]
