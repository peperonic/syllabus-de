"""Time rules: school years, the rollout rule, and the S0b validity parser."""
import datetime as dt
import itertools

import pytest

from kb.validity import DocWindow, Rollout, parse_validity, school_year


def test_school_year_boundary():
    assert school_year(dt.date(2027, 7, 31)) == 2026
    assert school_year(dt.date(2027, 8, 1)) == 2027
    assert school_year(dt.date(2028, 2, 1)) == 2027
    assert school_year(dt.date(2027, 9, 1), start="09-01") == 2027
    assert school_year(dt.date(2027, 8, 31), start="09-01") == 2026


def new_plan(n=5, y0=2027, grades=(5, 10)):
    return DocWindow("new", grades[0], grades[1], dt.date(y0, 8, 1), None, Rollout("ascending", n=n), "upcoming")


def test_ascending_grid():
    """In school year y, grades g <= N + (y - Y0) use the new plan."""
    w = new_plan()
    grid = {(y, g): w.in_window(g, y)[0] for y in range(2026, 2033) for g in range(5, 11)}
    assert not any(grid[(2026, g)] for g in range(5, 11))
    assert [g for g in range(5, 11) if grid[(2027, g)]] == [5]
    assert [g for g in range(5, 11) if grid[(2029, g)]] == [5, 6, 7]
    assert all(grid[(2032, g)] for g in range(5, 11))


def test_rollout_switches_cohorts_only_at_start():
    """Along a cohort g - y is constant, so g <= N + (y - Y0) iff g - y <= N - Y0 is
    cohort-invariant; the other condition, y >= Y0, is not. Hence a cohort changes
    plan at most once, in year Y0, and exactly the cohorts in grades a < g <= N
    then (a = the plan's lowest grade) do so: N - a cohorts, none if N = a."""
    for a, n, y0 in [(1, 1, 2020), (1, 2, 2024), (5, 5, 2027), (5, 6, 2019), (7, 7, 2027), (5, 8, 2030)]:
        w = new_plan(n, y0, grades=(a, 13))
        switchers = set()
        for g, y in itertools.product(range(a, 13), range(y0 - 4, y0 + 14)):
            now, nxt = w.in_window(g, y)[0], w.in_window(g + 1, y + 1)[0]
            assert not (now and not nxt), "a cohort never switches back to the old plan"
            if nxt and not now:
                assert y + 1 == y0, "switching happens only into the first school year"
                switchers.add(g + 1)
        assert switchers == set(range(a + 1, n + 1)), (a, n, switchers)
        assert len(switchers) == n - a


def test_all_grades_and_end_date():
    w = DocWindow("old", 5, 10, dt.date(2016, 8, 1), dt.date(2032, 7, 31), Rollout("all_grades"), "current")
    assert w.in_window(8, 2016)[0]
    assert w.in_window(10, 2031)[0]
    assert not w.in_window(10, 2032)[0]
    assert not w.in_window(4, 2020)[0]


def test_first_year_for_grade():
    assert new_plan().first_year_for_grade(5) == 2027
    assert new_plan().first_year_for_grade(8) == 2030


@pytest.mark.parametrize("raw,notes,gfrom,expect", [
    # MV: 'aufwachsend' without a grade: start at the document's lowest grade, flagged as inferred
    ("2027/28 aufwachsend (gültig ab 01.08.2027)", None, 7, ("2027-08-01", "ascending_from_grade:7", "inferred")),
    # BW: two entry grades in the first year -> N = 2
    ("2024/25 (Klassen 1 and 2, ascending)", None, 1, ("2024-08-01", "ascending_from_grade:2", "inferred")),
    # SN: staged dates per grade, checked to be one grade per consecutive school year
    ("2019-08-01 (Kl. 7-8), 2020-08-01 (Kl. 9), 2021-08-01 (Kl. 10)", None, 7, ("2019-08-01", "ascending_from_grade:8", "stated")),
    # BY: N derived from a stated end point, 13 - (2025 - 2018) = 6
    ("G9 ascending from 2018/19; Jgst 13 reached 2025/26 (knowledge, unverified)", None, 8, ("2018-08-01", "ascending_from_grade:6", "inferred")),
    # Plain dates
    ("2016-08-01", None, 5, ("2016-08-01", "all_grades", "stated")),
    ("01.08.2022", None, 5, ("2022-08-01", "all_grades", "stated")),
    # No start at all: review, never a guess
    ("unknown", "'gültig bis 31.07.2031, auslaufend'", 7, (None, "all_grades", "needs_review")),
    ("", None, 5, (None, "all_grades", "needs_review")),
])
def test_parse_validity(raw, notes, gfrom, expect):
    p = parse_validity(raw, notes, gfrom)
    assert (p.valid_from, p.rollout, p.confidence) == expect


def test_end_point_is_checked():
    ok = parse_validity("2025/26 (Klassen 5 and 6), ascending to Klasse 13 in 2032/33", None, 5)
    assert ok.rollout == "ascending_from_grade:6" and "passt" in ok.note
    bad = parse_validity("2025/26 (Klassen 5 and 6), ascending to Klasse 13 in 2031/32", None, 5)
    assert bad.confidence == "needs_review" and "widerspricht" in bad.note


def test_valid_to_from_notes():
    p = parse_validity("unknown", "Listed ... 'gültig bis 31.07.2031, auslaufend'.", 7)
    assert p.valid_to == "2031-07-31"


def test_real_inventory_parses(tmp_path):
    """S0 and S0b must run over the full real inventory offline, and every rollout
    rule they write must be one the resolver understands."""
    import sqlite3
    from builder.run import run
    run(stages=["S0", "S0b"], data_dir=tmp_path)
    c = sqlite3.connect(tmp_path / "kb.sqlite")
    n = c.execute("SELECT COUNT(*) FROM document").fetchone()[0]
    assert n == 399
    for (r,) in c.execute("SELECT rollout FROM document"):
        Rollout.parse(r)
    conf = dict(c.execute("SELECT validity_confidence, COUNT(*) FROM document GROUP BY 1").fetchall())
    assert set(conf) <= {"stated", "inferred", "needs_review"}
    # The MV 2026 Sek I plans succeed the right predecessors (school form overlap, not order).
    sup = dict(c.execute("SELECT dst, src FROM edge WHERE rel='supersedes' AND src LIKE 'MV:mathematik%'").fetchall())
    assert sup["MV:mathematik-rahmenplan-mathematik-7-10-allgemeine-hochschulreife"].endswith("gymnasium-2026")
    assert sup["MV:mathematik-rahmenplan-mathematik-7-10-mittlere-reife"].endswith("regionale-schule-202")
    placeholders = {r[0] for r in c.execute("SELECT code FROM land WHERE inventory_status = 'placeholder'")}
    assert placeholders == {"TH", "SL"}
