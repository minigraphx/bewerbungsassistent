"""The limits of a field of Meine Angaben, as onboarding/form.json sets them (#302, #316).

The search, Suche einstellen and Meine Angaben read the same lines of suchprofil.md, so each takes a value only within
the limits of the form field for that line. This module imports nothing of the app, so that search_plan can read the
limits too. The app package puts form.json next to the modules.
"""
import dataclasses
import functools
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
FORM_PATHS = (HERE / "form.json", HERE.parent / "onboarding" / "form.json")
JOB_SECTION = "searchJob"
APPRENTICESHIP_SECTION = "searchApprenticeship"


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


def of(section_id: str, field_id: str) -> Limit:
    """The limits of a field in this section of the form; LookupError if the form has no such field."""
    form = _form()
    section = next((s for s in form["sections"] if s["id"] == section_id), None)
    field = next((f for f in section["fields"] if f["id"] == field_id), None) if section else None
    if field is None:
        raise LookupError(f"{section_id}.{field_id}")
    limits = form["limits"]
    return Limit(field.get("maxItems", limits["listItems"]),
                 field.get("max", limits["textarea" if field["type"] == "textarea" else "text"]))
