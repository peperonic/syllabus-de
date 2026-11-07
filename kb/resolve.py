"""Context normalisation and the choice of binding documents.

The cohort trace: a pupil in grade g in school year y was in grade g - k in
school year y - k and will be in grade g + k in year y + k. Earlier and later
content is looked up against the plan that binds the pupil *then*, at the
school form they attend *then* (table `pathway`). So a pupil who started
grade 7 under an old plan is not credited with content of the new plan.
"""
from __future__ import annotations

import datetime as dt
import sqlite3
from dataclasses import dataclass, field

from .db import one, rows
from .text import fold
from .validity import (DocWindow, Rollout, effective_status, parse_date, school_year,
                       school_year_label)

SUBJECT_ALIASES = {
    "mathe": "Mathematik", "math": "Mathematik", "mathematics": "Mathematik",
    "bio": "Biologie", "biology": "Biologie", "physics": "Physik", "chemistry": "Chemie",
    "sowi": "Sozialwissenschaften", "pw": "Politik/Wirtschaft", "wat": "Arbeitslehre/WAT",
    "su": "Sachunterricht", "nawi": "Naturwissenschaften",
}


class ContextError(ValueError):
    """The context cannot be resolved. Carries candidates for the caller."""

    def __init__(self, message: str, field_name: str, candidates: list[str] | None = None):
        super().__init__(message)
        self.field_name = field_name
        self.candidates = candidates or []


@dataclass
class Context:
    land: str
    land_name: str
    school_form: str
    grade: int
    subject: str
    course_level: str | None
    date: dt.date
    school_year: int
    start: str
    land_status: str
    mapping: dict = field(default_factory=dict)  # input value -> normalised value, per field

    def as_dict(self) -> dict:
        return {
            "land": self.land, "land_name": self.land_name, "school_form": self.school_form,
            "grade": self.grade, "subject": self.subject, "course_level": self.course_level,
            "date": self.date.isoformat(), "school_year": school_year_label(self.school_year),
        }


def normalise_context(conn: sqlite3.Connection, ctx: dict) -> Context:
    mapping: dict = {}
    # -- land
    raw_land = str(ctx.get("land") or "").strip()
    if not raw_land:
        raise ContextError("land fehlt", "land")
    lands = rows(conn, "SELECT code, name, school_year_start, inventory_status FROM land")
    land = next((l for l in lands if l["code"].upper() == raw_land.upper()), None) or \
        next((l for l in lands if fold(l["name"]) == fold(raw_land)), None)
    if land is None:
        raise ContextError(f"Land {raw_land!r} unbekannt", "land", [l["code"] for l in lands])
    mapping["land"] = {"input": raw_land, "used": land["code"]}

    # -- subject
    raw_subject = str(ctx.get("subject") or "").strip()
    subjects = [r["subject"] for r in rows(conn, "SELECT DISTINCT subject FROM document WHERE land = ?", (land["code"],))]
    subject = next((s for s in subjects if fold(s) == fold(raw_subject)), None)
    if subject is None:
        alias = SUBJECT_ALIASES.get(fold(raw_subject))
        subject = next((s for s in subjects if alias and fold(s) == fold(alias)), None)
    if subject is None:
        raise ContextError(f"Fach {raw_subject!r} in {land['code']} nicht im Bestand", "subject", sorted(subjects))
    mapping["subject"] = {"input": raw_subject, "used": subject}

    # -- school form
    raw_form = str(ctx.get("school_form") or "").strip()
    alias = one(conn, "SELECT official FROM school_form_alias WHERE land = ? AND alias = ?", (land["code"], fold(raw_form)))
    if alias is None:
        forms = sorted({r["official"] for r in rows(conn, "SELECT official FROM school_form_alias WHERE land = ?", (land["code"],))})
        raise ContextError(f"Schulform {raw_form!r} in {land['code']} unbekannt", "school_form", forms)
    school_form = alias["official"]
    mapping["school_form"] = {"input": raw_form, "used": school_form, "source": "school_form_alias"}

    # -- grade
    raw_grade = ctx.get("grade")
    grade: int | None = None
    if isinstance(raw_grade, int) or (isinstance(raw_grade, str) and raw_grade.strip().isdigit()):
        grade = int(raw_grade)
    elif raw_grade is not None:
        ga = one(conn, "SELECT grade FROM grade_alias WHERE land = ? AND school_form = ? AND label = ?",
                 (land["code"], school_form, str(raw_grade).strip().upper()))
        if ga:
            grade = ga["grade"]
            mapping["grade"] = {"input": raw_grade, "used": grade, "source": "grade_alias"}
    if grade is None or not 1 <= grade <= 13:
        raise ContextError(f"Klasse {raw_grade!r} nicht auflösbar", "grade")

    # -- date
    raw_date = ctx.get("date")
    date = parse_date(raw_date) if raw_date else dt.date.today()
    start = land["school_year_start"] or "08-01"
    return Context(
        land=land["code"], land_name=land["name"], school_form=school_form, grade=grade, subject=subject,
        course_level=(ctx.get("course_level") or None), date=date, school_year=school_year(date, start),
        start=start, land_status=land["inventory_status"], mapping=mapping,
    )


# --------------------------------------------------------------------------
# Documents and binding
# --------------------------------------------------------------------------

def attends(conn: sqlite3.Connection, land: str, track: str, grade: int) -> str:
    r = one(conn, "SELECT attends FROM pathway WHERE land = ? AND school_form = ? AND ? BETWEEN grade_from AND grade_to",
            (land, track, grade))
    return r["attends"] if r else track


def track_grade_range(conn: sqlite3.Connection, land: str, track: str, subject: str) -> tuple[int, int]:
    """Lowest and highest grade a pupil on this track can have content for."""
    p = one(conn, "SELECT MIN(grade_from) lo, MAX(grade_to) hi FROM pathway WHERE land = ? AND school_form = ?", (land, track))
    d = one(conn, """SELECT MIN(d.grade_from) lo, MAX(d.grade_to) hi FROM document d
                     JOIN document_school_form f ON f.document_id = d.document_id
                     WHERE d.land = ? AND d.subject = ? AND f.school_form = ?""", (land, subject, track))
    los = [x for x in (p and p["lo"], d and d["lo"]) if x is not None]
    his = [x for x in (p and p["hi"], d and d["hi"]) if x is not None]
    return (min(los) if los else 1, max(his) if his else 13)


def window(doc: dict, start: str) -> DocWindow:
    return DocWindow(
        document_id=doc["document_id"], grade_from=doc["grade_from"], grade_to=doc["grade_to"],
        valid_from=parse_date(doc["valid_from"]), valid_to=parse_date(doc["valid_to"]),
        rollout=Rollout.parse(doc["rollout"]), status=doc["status"], start=doc.get("school_year_start") or start,
    )


def _stage_grade(conn, land: str, school_form: str, rollout: str) -> int | None:
    r = Rollout.parse(rollout)
    if r.stage is None:
        return None
    g = one(conn, "SELECT grade FROM grade_alias WHERE land = ? AND school_form = ? AND label = ?", (land, school_form, r.stage))
    return g["grade"] if g else None


@dataclass
class Binding:
    grade: int
    school_year: int
    school_form: str
    binding: list[dict]           # documents that bind (normally one)
    also_in_force: list[dict]     # other versions in force this year for other cohorts
    notes: list[str]


def binding_for(conn: sqlite3.Connection, land: str, subject: str, school_form: str, grade: int, y: int,
                start: str, course_level: str | None = None) -> Binding:
    docs = rows(conn, """SELECT d.* FROM document d JOIN document_school_form f ON f.document_id = d.document_id
                         WHERE d.land = ? AND d.subject = ? AND f.school_form = ?""", (land, subject, school_form))
    succ: dict[str, list[str]] = {}
    for e in rows(conn, "SELECT src, dst FROM edge WHERE rel = 'supersedes'"):
        succ.setdefault(e["dst"], []).append(e["src"])
    by_id = {d["document_id"]: d for d in docs}
    notes: list[str] = []

    def in_win(d: dict) -> tuple[bool, str]:
        return window(d, start).in_window(grade, y, _stage_grade(conn, land, school_form, d["rollout"]))

    binding, also = [], []
    for d in docs:
        ok, why = in_win(d)
        if not window(d, start).covers_grade(grade):
            continue
        active_succ = [by_id[s] for s in succ.get(d["document_id"], []) if s in by_id and in_win(by_id[s])[0]]
        if ok and not active_succ:
            binding.append({**d, "why": why})
        elif ok and active_succ:
            also.append({**d, "why": f"{why}; für diese Kohorte abgelöst durch {active_succ[0]['document_id']}"})
        else:
            # in force this school year for another cohort?
            w = window(d, start)
            other = any(w.in_window(g2, y)[0] for g2 in range((w.grade_from or 1), (w.grade_to or 13) + 1))
            if other:
                also.append({**d, "why": f"{why}; gilt {school_year_label(y)} für andere Klassen"})
    if len(binding) > 1:
        notes.append("mehrere Fassungen binden gleichzeitig: " + ", ".join(b["document_id"] for b in binding))
    if not binding:
        notes.append(f"kein bindender Plan für Klasse {grade} im Schuljahr {school_year_label(y)} gefunden")
    for b in binding:
        if b.get("validity_confidence") == "needs_review":
            notes.append(f"Gültigkeit von {b['document_id']} ungeprüft: {b.get('validity_note') or b.get('validity_raw')}")
        elif b.get("validity_confidence") == "inferred":
            notes.append(f"Gültigkeit von {b['document_id']} erschlossen, nicht wörtlich belegt: {b.get('validity_note') or ''}".rstrip(": "))
    return Binding(grade, y, school_form, binding, also, notes)


def cohort_trace(conn: sqlite3.Connection, c: Context) -> dict[int, Binding]:
    """Binding documents for every grade of the pupil's track, along the cohort."""
    lo, hi = track_grade_range(conn, c.land, c.school_form, c.subject)
    out: dict[int, Binding] = {}
    for g in range(lo, hi + 1):
        y = c.school_year + (g - c.grade)
        out[g] = binding_for(conn, c.land, c.subject, attends(conn, c.land, c.school_form, g), g, y, c.start, c.course_level)
    return out


def doc_public(conn: sqlite3.Connection, d: dict, y: int, start: str) -> dict:
    """The document facts every answer cites: title, version, validity, status as of y."""
    w = window(d, start)
    has_succ = bool(one(conn, "SELECT 1 x FROM edge WHERE rel='supersedes' AND dst = ?", (d["document_id"],)))
    succ_active = False
    if has_succ:
        for e in rows(conn, "SELECT src FROM edge WHERE rel='supersedes' AND dst = ?", (d["document_id"],)):
            s = one(conn, "SELECT * FROM document WHERE document_id = ?", (e["src"],))
            sw = window(s, start)
            if s and sw.y0 is not None and y >= sw.y0:
                succ_active = True
    out = {
        "document_id": d["document_id"], "title": d["title"], "version": d.get("version"),
        "school_form": d.get("school_form"), "grades": d.get("grades"),
        "valid_from": d.get("valid_from"), "valid_to": d.get("valid_to"), "rollout": d.get("rollout"),
        "status_inventory": d.get("status"), "status_on_date": effective_status(w, y, succ_active),
        "validity_confidence": d.get("validity_confidence"), "source_url": d.get("source_url"),
    }
    if "why" in d:
        out["why"] = d["why"]
    return out
