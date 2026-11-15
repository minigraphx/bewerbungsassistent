"""The limits of a search profile line, as Meine Angaben sets them for its field in onboarding/form.json (#302).

Suche einstellen and Meine Angaben write the same lines of suchprofil.md. Both take a value only within the limits of
the form field, so what one page saves the other takes in full. The app package puts form.json next to the modules.
"""
import dataclasses
import functools
import json
import pathlib

import search_plan

HERE = pathlib.Path(__file__).resolve().parent
FORM_PATHS = (HERE / "form.json", HERE.parent / "onboarding" / "form.json")
SECTIONS = {search_plan.KIND_JOB: "searchJob", search_plan.KIND_APPRENTICESHIP: "searchApprenticeship"}
# Where Suche einstellen adds an own term (#310): a job term joins the Kernliste, and without one it becomes a direction,
# whose field takes longer lines; so the keywords decide.
TERM_FIELDS = {search_plan.KIND_JOB: "keywords", search_plan.KIND_APPRENTICESHIP: "professions"}


@dataclasses.dataclass(frozen=True)
class Limit:
    lines: int  # entries of a list
    chars: int  # of each entry, or of a text


@functools.cache
def _form() -> dict:
    path = next((p for p in FORM_PATHS if p.is_file()), None)
    if path is None:
        raise FileNotFoundError(f"form.json is missing: looked in {', '.join(map(str, FORM_PATHS))}")
    return json.loads(path.read_text(encoding="utf-8"))


def of(kind: str, field_id: str) -> Limit:
    """The limits of a field in the search section of this kind; LookupError if the form has no such field."""
    form = _form()
    section = next(s for s in form["sections"] if s["id"] == SECTIONS[kind])
    field = next((f for f in section["fields"] if f["id"] == field_id), None)
    if field is None:
        raise LookupError(f"{SECTIONS[kind]}.{field_id}")
    limits = form["limits"]
    return Limit(field.get("maxItems", limits["listItems"]),
                 field.get("max", limits["textarea" if field["type"] == "textarea" else "text"]))


def of_term(kind: str) -> Limit:
    """The limits of a search term the person adds on Suche einstellen, as Meine Angaben takes it (#310)."""
    return of(kind, TERM_FIELDS[kind])
