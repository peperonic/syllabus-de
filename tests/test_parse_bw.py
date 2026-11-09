"""BW parser profile on small excerpts of the real markup (tests/fixture_bw/)."""
from pathlib import Path

from builder.parse.bw import clean, parse

F = Path(__file__).parent / "fixture_bw"
U = "https://www.bildungsplaene-bw.de/,Lde/"
DOC = {"grade_from": 5, "grade_to": 13}


def page(name, pid, n=1):
    return {"page": n, "url": U + pid, "html": (F / name).read_text(encoding="utf-8")}


def test_sek1_levels_ids_and_text():
    ns = parse(DOC, [page("sek1_v2_ik_7-8-9_01_00.html", "BP2016BW_ALLG_SEK1_M.V2_IK_7-8-9_01_00")])
    tk = [n for n in ns if n["kind"] == "Teilkompetenz"]
    # standard (1): G and M cells; the E cell is the placeholder "[Teilkompetenz schon in Klassen 5/6]"
    assert [n["path"] for n in tk[:2]] == ["IK_7-8-9_01_00/01_G", "IK_7-8-9_01_00/01_M"]
    assert not any("schon in Klassen" in n["text"] for n in tk)
    assert {n["course_level"] for n in tk} == {"G", "M", "E"}
    assert all((n["grade_from"], n["grade_to"]) == (7, 9) for n in tk)
    g = tk[0]
    assert g["text"] == "mit natürlichen, gebrochenen und negativen Zahlen rechnen, die im täglichen Leben vorkommen"
    assert g["label"] == "(1) Zahlterme berechnen"
    assert g["locator"].endswith("#BP2016BW_ALLG_SEK1_M.V2_IK_7-8-9_01_00_01_G")
    assert "­" not in "".join(n["text"] for n in ns)


def test_operator_table():
    ns = parse(DOC, [page("gym_v2_op.html", "BP2016BW_ALLG_GYM_M.V2_OP")])
    ops = [n for n in ns if n["kind"] == "Operator"]
    assert ops[0]["label"] == "angeben [AFB I]"
    assert ops[1]["label"] == "anwenden, durchführen [AFB II]"


def test_gen2x_rows_and_bands():
    pid = "DE_BW_BILDUNGSPLAENE_GEN2X_BPBW_ALLG_GYM_M%28V3.0%29"
    ns = parse(DOC, [page("gym_v3_excerpt.html", pid)])
    tk = [n for n in ns if n["kind"] == "Teilkompetenz"]
    assert len(tk) == 2
    assert all((n["grade_from"], n["grade_to"]) == (7, 8) for n in tk)
    assert tk[0]["path"] == "3.2.1/01" and tk[0]["locator"].endswith("#3.2.1(1)")


def test_clean():
    assert clean("Ach­sen  sym­metrie , und ( a )") == "Achsen symmetrie, und (a)"
    assert clean("Potenz‑, Exponential - und Wurzelfunktion") == "Potenz‑, Exponential- und Wurzelfunktion"
    assert clean("a - b") == "a - b"   # a real minus or dash between words stays
    assert clean("im Grad - als auch") == "im Grad- als auch"
    assert clean("Zeit (- spanne)") == "Zeit (-spanne)"


def test_text_of_joins_split_words_and_keeps_superscripts():
    from bs4 import BeautifulSoup
    from builder.parse.bw import text_of
    el = BeautifulSoup('<div><p><span>Prozent</span><span>angaben</span> und 1<sup>2</sup> bis 20<sup>2</sup></p>'
                       '<p>zweiter Satz</p></div>', "html.parser").div
    assert text_of(el) == "Prozentangaben und 1^2 bis 20^2 zweiter Satz"
