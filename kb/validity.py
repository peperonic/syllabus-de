"""Validity in time: school years, rollout rules, and which plan binds a pupil.

Definitions (see docs/decisions.md):

* The school year of a date d is the calendar year y in which that school
  year started: y = year(d) if (month, day) >= start else year(d) - 1, with
  start = 1 August unless the Land or document says otherwise.
* A document is in force in school years Y0 .. Y1, where Y0 is the school
  year of valid_from and Y1 the school year of valid_to (inclusive).
* rollout = all_grades: every grade the document covers uses it from Y0.
* rollout = ascending_from_grade:N: in school year y >= Y0 the document is
  used by grades g <= N + (y - Y0). N is the highest grade on the new plan
  in its first year ("Klassen 1 und 2 aufsteigend" gives N = 2).
* A document binds a pupil when it is in its window for (g, y) and no
  document that supersedes it is in its own window for (g, y).
"""
from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass

DEFAULT_START = "08-01"


def parse_date(value: str | dt.date | None) -> dt.date | None:
    if value is None or value == "":
        return None
    if isinstance(value, dt.date):
        return value
    return dt.date.fromisoformat(str(value)[:10])


def school_year(d: dt.date, start: str = DEFAULT_START) -> int:
    m, day = (int(x) for x in start.split("-"))
    return d.year if (d.month, d.day) >= (m, day) else d.year - 1


def school_year_label(y: int) -> str:
    return f"{y}/{str(y + 1)[2:]}"


def school_year_start_date(y: int, start: str = DEFAULT_START) -> dt.date:
    m, day = (int(x) for x in start.split("-"))
    return dt.date(y, m, day)


# --------------------------------------------------------------------------
# Rollout rules
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Rollout:
    kind: str              # all_grades | ascending
    n: int | None = None   # highest grade on the plan in its first year
    stage: str | None = None  # unresolved stage label such as EF

    @staticmethod
    def parse(s: str | None) -> "Rollout":
        s = (s or "all_grades").strip()
        if s == "all_grades":
            return Rollout("all_grades")
        m = re.fullmatch(r"ascending_from_grade:(\d+)", s)
        if m:
            return Rollout("ascending", n=int(m.group(1)))
        m = re.fullmatch(r"ascending_from_grades:(\d+)-(\d+)", s)
        if m:
            return Rollout("ascending", n=int(m.group(2)))
        m = re.fullmatch(r"ascending_from_stage:(\w+)", s)
        if m:
            return Rollout("ascending", stage=m.group(1))
        raise ValueError(f"unknown rollout rule: {s!r}")


@dataclass
class DocWindow:
    """The time facts of one document, enough to decide whether it binds."""
    document_id: str
    grade_from: int | None
    grade_to: int | None
    valid_from: dt.date | None
    valid_to: dt.date | None
    rollout: Rollout
    status: str | None
    start: str = DEFAULT_START

    @property
    def y0(self) -> int | None:
        return school_year(self.valid_from, self.start) if self.valid_from else None

    @property
    def y1(self) -> int | None:
        return school_year(self.valid_to, self.start) if self.valid_to else None

    def covers_grade(self, g: int) -> bool:
        if self.grade_from is None or self.grade_to is None:
            return False
        return self.grade_from <= g <= self.grade_to

    def in_window(self, g: int, y: int, stage_grade: int | None = None) -> tuple[bool, str]:
        """Is this document used by grade g in school year y, ignoring successors?
        Returns (answer, reason in plain words)."""
        if self.status == "draft":
            return False, "Entwurf, nicht in Kraft"
        if not self.covers_grade(g):
            return False, f"Klasse {g} nicht im Geltungsbereich"
        if self.y0 is None and self.status == "upcoming":
            return False, "angekündigt, Beginn unbekannt"
        if self.y0 is not None and y < self.y0:
            return False, f"gilt erst ab {school_year_label(self.y0)}"
        if self.y1 is not None and y > self.y1:
            return False, f"galt bis {school_year_label(self.y1)}"
        if self.rollout.kind == "ascending":
            n = self.rollout.n if self.rollout.n is not None else stage_grade
            if n is None or self.y0 is None:
                return True, "aufsteigend, Einführungsklasse oder Beginn unbekannt"
            reach = n + (y - self.y0)
            if g > reach:
                return False, f"aufsteigend ab {school_year_label(self.y0)}, erreicht {school_year_label(y)} erst Klasse {reach}"
            return True, f"aufsteigend ab {school_year_label(self.y0)}, gilt {school_year_label(y)} bis Klasse {reach}"
        if self.y0 is None:
            return True, "Beginn unbekannt, laut Inventar in Kraft"
        return True, f"gilt ab {school_year_label(self.y0)} für alle Klassen"

    def first_year_for_grade(self, g: int) -> int | None:
        """First school year in which grade g uses this document."""
        if self.y0 is None or not self.covers_grade(g):
            return None
        if self.rollout.kind == "ascending" and self.rollout.n is not None:
            return self.y0 + max(0, g - self.rollout.n)
        return self.y0


def effective_status(w: DocWindow, y: int, has_active_successor: bool) -> str:
    """Status of a document as of school year y (inventory status is only a snapshot)."""
    if w.status == "draft":
        return "draft"
    if w.y0 is not None and y < w.y0:
        return "upcoming"
    if w.y1 is not None and y > w.y1:
        return "superseded"
    if has_active_successor:
        return "phasing_out"
    if w.rollout.kind == "ascending" and w.rollout.n is not None and w.y0 is not None and w.grade_to is not None:
        if w.rollout.n + (y - w.y0) < w.grade_to:
            return "phasing_in"
    if w.y0 is None and w.status in ("superseded", "upcoming"):
        return w.status
    return "current"


# --------------------------------------------------------------------------
# S0b: parse the inventory's free-text validity fields
# --------------------------------------------------------------------------

_HEDGES = re.compile(
    r"inferred|unverified|knowledge|probably|exact date|not stated|planned|analogy|"
    r"not determined|believed|likely|may take effect|or later|unknown", re.I)
_ROLLOUT = re.compile(r"aufwachsend|aufsteigend|ascending|beginning with|rollout|phased|ab jg", re.I)
_ISO = re.compile(r"\b(19|20)(\d\d)-(\d\d)-(\d\d)\b")
_DE = re.compile(r"\b(\d{1,2})\.(\d{1,2})\.((?:19|20)\d\d)\b")
_SY = re.compile(r"\b((?:19|20)\d\d)/(\d\d)\b")
_YEAR = re.compile(r"\b((?:19|20)\d\d)\b")
_GRADE_AFTER = re.compile(
    r"(?:Klassen?|Kl\.|Jg\.?|Jgst\.?|Jahrgangsstufen?|grades?|Klasse)\s*(\d{1,2})(?:\s*(?:and|und|,|/|-)\s*(\d{1,2}))?",
    re.I)
_STAGE = re.compile(r"beginning with (EF|E|Q1|Einführungsphase)|ab (EF|E|Q1)\b", re.I)
_ENDPOINT = re.compile(
    r"(?:Jgst\.?|Klasse|Jg\.?)\s*(\d{1,2})\s+reached\s+(?:in\s+)?((?:19|20)\d\d)/\d\d"
    r"|ascending to (?:Klasse|Jgst\.?|Jg\.?)\s*(\d{1,2}) in ((?:19|20)\d\d)/\d\d",
    re.I)
_STAGE_PAIR = re.compile(r"((?:19|20)\d\d)/\d\d \(Einführungsphase\),\s*((?:19|20)\d\d)/\d\d \(Qualifikationsphase\)")
_UNTIL = re.compile(r"(?:gültig bis|valid until|bis zum|bis)\s+(\d{1,2})\.(\d{1,2})\.((?:19|20)\d\d)", re.I)


@dataclass
class ParsedValidity:
    valid_from: str | None
    valid_to: str | None
    rollout: str
    confidence: str          # stated, inferred, needs_review
    note: str


def parse_grades(s: str | None) -> tuple[int | None, int | None, str | None]:
    """'5-10' -> (5, 10). '11-12 / 11-13' -> (11, 13) with a note. Stage labels only -> (None, None)."""
    if not s:
        return None, None, "keine Klassenangabe"
    nums = [int(x) for x in re.findall(r"\b(\d{1,2})\b", s) if 1 <= int(x) <= 13]
    if not nums:
        return None, None, f"Klassenangabe ohne Zahlen: {s!r}"
    lo, hi = min(nums), max(nums)
    note = None
    if re.search(r"/|;|\(|unverified|knowledge", s):
        note = f"Klassenangabe vereinfacht von {s!r} zu {lo}-{hi}"
    return lo, hi, note


def parse_validity(in_force: str | None, notes: str | None, grade_from: int | None,
                   start: str = DEFAULT_START) -> ParsedValidity:
    raw = (in_force or "").strip()
    text = raw
    msgs: list[str] = []
    m_, d_ = (int(x) for x in start.split("-"))

    if not raw or re.fullmatch(r"unknown.*|not stated.*", raw, re.I):
        vt = _parse_until(notes)
        return ParsedValidity(None, vt, "all_grades", "needs_review",
                              "kein Beginn angegeben" + (f"; Ende aus Notiz {vt}" if vt else ""))

    dates: list[tuple[int, dt.date]] = []  # (position, date)
    for m in _ISO.finditer(text):
        dates.append((m.start(), dt.date(int(m.group(1) + m.group(2)), int(m.group(3)), int(m.group(4)))))
    for m in _DE.finditer(text):
        try:
            dates.append((m.start(), dt.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))))
        except ValueError:
            pass
    sy_dates = []
    for m in _SY.finditer(text):
        sy_dates.append((m.start(), dt.date(int(m.group(1)), m_, d_)))

    staged = _staged_rollout(text, start)
    if staged is not None:
        y0_date, n = staged
        return ParsedValidity(y0_date.isoformat(), _parse_until(notes), f"ascending_from_grade:{n}", "stated",
                              "gestaffelte Daten je Klasse, als aufsteigende Einführung erkannt und geprüft")

    valid_from: dt.date | None = None
    if dates:
        dates.sort()
        valid_from = dates[0][1]
        # "(Mttlg. 238/2022)" or "Erl. 14/2008" contain no ISO date, fine. Several real dates:
        distinct = sorted({d for _, d in dates})
        if len(distinct) > 1:
            msgs.append("mehrere Daten im Text, erstes verwendet")
    elif sy_dates:
        sy_dates.sort()
        valid_from = sy_dates[0][1]
        msgs.append("Schuljahr ohne Tagesdatum, Beginn am Schuljahresanfang angenommen")
    else:
        ym = _YEAR.search(text)
        if ym:
            valid_from = dt.date(int(ym.group(1)), m_, d_)
            msgs.append("nur Jahreszahl, Beginn am Schuljahresanfang angenommen")

    if re.search(r"half-year|halbjahr", text, re.I) and valid_from is not None:
        valid_from = dt.date(valid_from.year + 1, 2, 1)
        msgs.append("Halbjahreswechsel, Beginn 1. Februar angenommen")

    rollout = "all_grades"
    # An end point such as "Jgst 13 reached 2025/26" or "ascending to Klasse 13 in
    # 2032/33" is not an entry grade. Take it out of the text, keep it as a check.
    endpoint = None
    em = _ENDPOINT.search(text)
    if em:
        g_end = int(em.group(1) or em.group(3))
        y_end = int(em.group(2) or em.group(4))
        endpoint = (g_end, y_end)
        text = text[:em.start()] + text[em.end():]
    stage_pair = _STAGE_PAIR.search(text)
    if stage_pair and int(stage_pair.group(2)) == int(stage_pair.group(1)) + 1:
        rollout = "ascending_from_stage:E"
        msgs.append("Einführungsphase und Qualifikationsphase in Folgejahren, aufsteigend ab Stufe E")
    elif _ROLLOUT.search(raw) or re.search(r"\bab Jg", raw):
        st = _STAGE.search(text)
        mentions = _GRADE_AFTER.findall(text)
        gm = _GRADE_AFTER.search(text)
        if len(mentions) > 1:
            msgs.append("mehrere Klassenangaben, prüfen")
        if st:
            label = next(g for g in st.groups() if g)
            label = "E" if label.casefold() == "einführungsphase" else label.upper()
            rollout = f"ascending_from_stage:{label}"
            msgs.append(f"aufsteigend ab Stufe {label}, Klasse je Land über grade_alias")
        elif gm:
            a = int(gm.group(1))
            b = int(gm.group(2)) if gm.group(2) else a
            if re.search(r"ab Jg\s*\d+\s*und\s*\d+", text):
                msgs.append("zwei Einstiegsklassen genannt, prüfen")
                rollout = f"ascending_from_grade:{a}"
            else:
                rollout = f"ascending_from_grade:{max(a, b)}"
        elif endpoint is not None and valid_from is not None:
            n = endpoint[0] - (endpoint[1] - school_year(valid_from, start))
            rollout = f"ascending_from_grade:{n}"
            msgs.append(f"Einstiegsklasse aus Endpunkt berechnet: N = {endpoint[0]} - ({endpoint[1]} - {school_year(valid_from, start)}) = {n}")
            endpoint = None  # used, not checked
        elif grade_from is not None:
            rollout = f"ascending_from_grade:{grade_from}"
            msgs.append(f"aufsteigend ohne Klasse, unterste Klasse {grade_from} des Dokuments angenommen")
        else:
            rollout = "ascending_from_stage:unknown"
            msgs.append("aufsteigend, Einstiegsklasse unbekannt")
        if endpoint is not None and rollout.startswith("ascending_from_grade:") and valid_from is not None:
            n = int(rollout.split(":")[1])
            reach = n + (endpoint[1] - school_year(valid_from, start))
            if reach == endpoint[0]:
                msgs.append(f"Endpunkt Klasse {endpoint[0]} in {endpoint[1]}/.. geprüft, passt")
            else:
                msgs.append(f"Endpunkt widerspricht der Regel: erwartet Klasse {reach}, Text nennt {endpoint[0]}, prüfen")

    if re.search(r"all grades (\d{4})/", text):
        msgs.append("Text nennt eigenen Endpunkt der Einführung, prüfen")

    valid_to = _parse_until(notes) or _parse_until(raw)

    if valid_from is None:
        conf = "needs_review"
    elif any(k in m for m in msgs for k in ("prüfen", "unbekannt", "mehrere")):
        conf = "needs_review"
    elif _HEDGES.search(text) or msgs:
        conf = "inferred"
    else:
        conf = "stated"
    return ParsedValidity(valid_from.isoformat() if valid_from else None, valid_to, rollout, conf, "; ".join(msgs))


_STAGED_ITEM = re.compile(r"((?:19|20)\d\d-\d\d-\d\d)\s*\(\s*(?:Kl\.|Klassen?|Jg\.?)\s*(\d{1,2})(?:\s*-\s*(\d{1,2}))?\s*\)", re.I)


def _staged_rollout(text: str, start: str) -> tuple[dt.date, int] | None:
    """Recognise 'D0 (Kl. a-b), D1 (Kl. b+1), D2 (Kl. b+2)': an ascending rollout
    with N = b, accepted only if the dates fall in consecutive school years and
    each step adds exactly one grade."""
    items = _STAGED_ITEM.findall(text)
    if len(items) < 2:
        return None
    parsed = []
    for d, a, b in items:
        hi = int(b) if b else int(a)
        parsed.append((school_year(dt.date.fromisoformat(d), start), int(a), hi, dt.date.fromisoformat(d)))
    parsed.sort()
    for (y_prev, _, hi_prev, _), (y, lo, hi, _) in zip(parsed, parsed[1:]):
        if y != y_prev + 1 or lo != hi_prev + 1 or hi != lo:
            return None
    return parsed[0][3], parsed[0][2]


def _parse_until(s: str | None) -> str | None:
    if not s:
        return None
    m = _UNTIL.search(s)
    if not m:
        return None
    try:
        return dt.date(int(m.group(3)), int(m.group(2)), int(m.group(1))).isoformat()
    except ValueError:
        return None
