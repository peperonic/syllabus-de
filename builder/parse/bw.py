"""Parser profile for Baden-Württemberg (www.bildungsplaene-bw.de).

Two page formats are in use:

* Bildungsplan 2016, V1 and V2 (ids BP2016BW_ALLG_<SCHULART>_M[.V2]): an index page
  with one sub-page per section. Each standard is an element with an official
  `data-bpid` such as BP2016BW_ALLG_SEK1_M.V2_IK_7-8-9_01_00_02_G, holding a number
  "(2)" and the text. The id carries the grade band (IK_7-8-9 = grades 7 to 9),
  the course level (_G/_M/_E in Sek I, -LF/-BF in the Oberstufe) and the
  Leitidee (01 to 05).
* Bildungsplan GEN2X, V3.0 (G9, one long page): each standard is a table row with
  id "3.2.4(7)"; grade bands come from the section headings "3.2 Klassen 7/8",
  "3.5 Klassen 12/13 (Leistungsfach)".

Kept: the content standards (Teilkompetenzen), the process competences and the
operator list. Skipped: placeholders such as "[Teilkompetenz schon in Klassen 5/6]",
the Grundschule's "Denkanstöße" (questions for teachers, not standards), and
cross-reference link rows. Text is verbatim apart from removing soft hyphens and
normalising white space.
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

SHY = "­"
LEITIDEE = {"01": "Zahl, Variable, Operation", "02": "Messen", "03": "Raum und Form",
            "04": "Funktionaler Zusammenhang", "05": "Daten und Zufall"}
LEVEL_NAMES = {"G": "G", "M": "M", "E": "E", "LF": "Leistungsfach", "BF": "Basisfach"}


def clean(s: str | None) -> str:
    if not s:
        return ""
    s = s.replace(SHY, "")
    s = re.sub(r"\s+", " ", s).strip()
    # get_text(" ") puts a space at every inline tag; undo it before punctuation
    s = re.sub(r"\s+([,.;:!?)\]])", r"\1", s)
    return re.sub(r"([(\[])\s+", r"\1", s)


def _operators(soup, url: str, page: int, document: dict) -> list[dict]:
    """The operator table: one node per row, label 'op1, op2 [AFB X]', text = the description."""
    out = []
    for t in soup.find_all("table"):
        rows = t.find_all("tr")
        head = [clean(c.get_text(" ")) for c in rows[0].find_all(["td", "th"])] if rows else []
        if len(head) < 3 or not head[0].startswith("Operator") or head[-1] != "AFB":
            continue
        for i, r in enumerate(rows[1:], 1):
            cells = [clean(c.get_text(" ")) for c in r.find_all(["td", "th"])]
            if len(cells) < 3 or not cells[0]:
                continue
            out.append(dict(path=f"OP/{i:02d}", parent_path="OP", kind="Operator", label=f"{cells[0]} [AFB {cells[-1]}]",
                            text=cells[1], grade_from=document["grade_from"], grade_to=document["grade_to"],
                            course_level=None, page=page, locator=url))
        break
    return out


def parse(document: dict, pages: list[dict]) -> list[dict]:
    if any("GEN2X" in (p.get("url") or "") for p in pages[:1]):
        return _parse_gen2x(document, pages)
    return _parse_bp2016(document, pages)


# --------------------------------------------------------------------------
# Bildungsplan 2016 (V1, V2)
# --------------------------------------------------------------------------

IK_ID = re.compile(r"_IK_(?P<band>[0-9-]+?)(?:-(?P<lvl>LF|BF))?_(?P<li>\d\d)(?:_(?P<sub>\d\d))?_(?P<n>\d\d)(?:_(?P<cell>[GME]))?$")
PK_PAGE = re.compile(r"_PK_(\d\d)$")


def _band(band: str) -> tuple[int, int]:
    nums = [int(x) for x in band.split("-") if x.isdigit()]
    return min(nums), max(nums)


def _parse_bp2016(document: dict, pages: list[dict]) -> list[dict]:
    nodes: list[dict] = []
    seen: set[str] = set()

    def add(**n):
        if n["path"] in seen:
            return
        seen.add(n["path"])
        n["ordinal"] = len(nodes) + 1
        nodes.append(n)

    for page in pages:
        url = page.get("url") or ""
        soup = BeautifulSoup(page["html"], "html.parser")
        h2 = soup.find("h2")
        heading = clean(h2.get_text(" ")) if h2 else ""
        page_id = url.rsplit("/,Lde/", 1)[-1]

        # process competences: one page per area, a list of statements
        m = PK_PAGE.search(page_id)
        if m:
            area = f"PK_{m.group(1)}"
            add(path=area, parent_path=None, kind="Prozessbezogener Kompetenzbereich", label=heading, text=heading,
                grade_from=document["grade_from"], grade_to=document["grade_to"], course_level=None,
                page=page["page"], locator=url)
            for i, li in enumerate(_main(soup).select("ol li, ul li"), 1):
                t = clean(li.get_text(" "))
                if t and len(t) > 15:
                    add(path=f"{area}/{i:02d}", parent_path=area, kind="Prozessbezogene Kompetenz", label=None, text=t,
                        grade_from=document["grade_from"], grade_to=document["grade_to"], course_level=None,
                        page=page["page"], locator=url)
            continue

        if page_id.endswith("_OP"):
            ops = _operators(soup, url, page["page"], document)
            if ops:
                add(path="OP", parent_path=None, kind="Operatorenliste", label="Operatoren", text="Operatoren",
                    grade_from=document["grade_from"], grade_to=document["grade_to"], course_level=None,
                    page=page["page"], locator=url)
                for o in ops:
                    add(**o)
            continue

        if "_IK_" not in page_id:
            continue
        # one content page: a Leitidee (or Grundschule sub-area) for one grade band
        sec = page_id.split("_IK_", 1)[1]
        mband = re.match(r"([0-9-]+?)(?:-(LF|BF))?_", sec + "_")
        a, b = _band(mband.group(1))
        lvl = mband.group(2)
        sec_path = f"IK_{sec}"
        add(path=sec_path, parent_path=None, kind="Leitidee" if "Leitidee" in heading else "Bereich",
            label=heading, text=heading, grade_from=a, grade_to=b,
            course_level=LEVEL_NAMES.get(lvl) if lvl else None, page=page["page"], locator=url)
        subhead = None
        for el in soup.find_all(["td", "th"]):
            classes = " ".join(el.get("class") or [])
            if "SUBHEAD" in classes:
                subhead = clean(el.get_text(" "))
                continue
            bpid = el.get("data-bpid") or el.get("id") or ""
            mid = IK_ID.search(bpid)
            if not mid:
                continue
            num_el = el.find(class_="teilkompetenzNumber")
            txt_el = el.find(class_="teilkompetenzText")
            if txt_el is None:
                continue
            text = clean(txt_el.get_text(" "))
            if not text or re.fullmatch(r"\[.*\]", text):   # "[Teilkompetenz schon in Klassen 5/6]"
                continue
            number = clean(num_el.get_text(" ")).split(" ")[0] if num_el else ""
            cell = mid.group("cell")
            level = cell or (LEVEL_NAMES.get(lvl) if lvl else None)
            path = f"{sec_path}/{mid.group('n')}" + (f"_{cell}" if cell else "")
            label = f"{number} {subhead}".strip() if subhead else number or None
            add(path=path, parent_path=sec_path, kind="Teilkompetenz", label=label, text=text,
                grade_from=a, grade_to=b, course_level=level, page=page["page"], locator=f"{url}#{bpid}")
    return nodes


def _main(soup):
    """The plan's own content, without navigation, link boxes and footers."""
    h2 = soup.find("h2")
    root = h2.find_parent("div", class_=re.compile("page__section")) if h2 else None
    root = root or soup
    for junk in root.select(".bplink-cont, .ls-lefthand, .BP_LEFTHAND, nav, footer, script, style"):
        junk.decompose()
    return root


# --------------------------------------------------------------------------
# Bildungsplan GEN2X (V3.0, G9)
# --------------------------------------------------------------------------

ROW_ID = re.compile(r"^(\d+(?:\.\d+)+)\((\d+)\)$")
SEC_HEAD = re.compile(r"^(3\.\d+)\s+Klassen?\s+([0-9/]+)(?:\s*\((Leistungsfach|Basisfach)\))?")
SUB_HEAD = re.compile(r"^(3\.\d+\.\d+)\s+(.*)$")
PK_HEAD = re.compile(r"^(2\.\d+)\s+(.*)$")


def _parse_gen2x(document: dict, pages: list[dict]) -> list[dict]:
    page = pages[0]
    url = page["url"]
    soup = BeautifulSoup(page["html"], "html.parser")
    for junk in soup.select(".references_boxes, .references_icons, nav, footer, script, style"):
        junk.decompose()
    nodes: list[dict] = []
    bands: dict[str, tuple[int, int, str | None]] = {}
    sections: dict[str, str] = {}
    for h in soup.find_all(re.compile("^h[1-6]$")):
        t = clean(h.get_text(" "))
        m = SEC_HEAD.match(t)
        if m:
            nums = [int(x) for x in m.group(2).split("/")]
            bands[m.group(1)] = (min(nums), max(nums), m.group(3))
            sections[m.group(1)] = t
            continue
        m = SUB_HEAD.match(t) or PK_HEAD.match(t)
        if m:
            sections[m.group(1)] = t

    def add(**n):
        n["ordinal"] = len(nodes) + 1
        nodes.append(n)

    made: set[str] = set()
    subhead_by_table = {}
    for tr in soup.find_all("tr"):
        classes = " ".join(tr.get("class") or [])
        if "subhead" in classes:
            subhead_by_table[id(tr.find_parent("table"))] = clean(tr.get_text(" "))
            continue
        m = ROW_ID.match(tr.get("id") or "")
        if not m:
            continue
        sec, n = m.group(1), m.group(2)
        body = tr.find(class_="text-body")
        text = clean(body.get_text(" ")) if body else ""
        if not text or re.fullmatch(r"\[.*\]", text):
            continue
        top = ".".join(sec.split(".")[:2])
        if sec.startswith("2."):
            a, b, lvl, kind = document["grade_from"], document["grade_to"], None, "Prozessbezogene Kompetenz"
        elif top in bands:
            a, b, lvl = bands[top]
            kind = "Teilkompetenz"
        else:
            continue
        if sec not in made:
            made.add(sec)
            add(path=sec, parent_path=None, kind="Leitidee" if "Leitidee" in sections.get(sec, "") else "Bereich",
                label=sections.get(sec, sec), text=sections.get(sec, sec), grade_from=a, grade_to=b,
                course_level=lvl, page=1, locator=url)
        sub = subhead_by_table.get(id(tr.find_parent("table")))
        add(path=f"{sec}/{int(n):02d}", parent_path=sec, kind=kind, label=f"({n}) {sub}".strip() if sub else f"({n})",
            text=text, grade_from=a, grade_to=b, course_level=lvl, page=1,
            locator=f"{url}#{tr.get('id')}")
    ops = _operators(soup, url, 1, document)
    if ops:
        add(path="OP", parent_path=None, kind="Operatorenliste", label="4.4 Liste der Operatoren", text="Liste der Operatoren",
            grade_from=document["grade_from"], grade_to=document["grade_to"], course_level=None, page=1, locator=url)
        for o in ops:
            add(**o)
    return nodes
