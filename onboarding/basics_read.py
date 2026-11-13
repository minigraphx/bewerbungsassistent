"""Read the Markdown basics of a data folder back into the answers of the form (#217).

The page „Meine Angaben“ opens with these answers next to those from cv.yaml (`cv_read.py`), so a person whose search
profile, style profile or building blocks came from the skill einstieg or from „Inhalte als Text“ sees them there. A
value the form cannot take (too long, too many, not one of its options) stays out and its line counts as unknown.
Unknown lines come along with their file and the section of the form they belong to: the page shows them as text,
because saving keeps them (`basics_merge.py`). Lines the app writes itself from other answers are not listed while
they still say what the app would write.
"""
import pathlib

import basics_slots
import markdown_files
import search_plan
import validation
from basics_slots import APPRENTICESHIP, BLOCKS, FILES, PROFILE, STYLE, TITLES

BLOCK_SECTIONS = {"Stärken": "strengths", "Lücken (offen benennen)": "gaps", "Rahmen": "frame",
                  "Stationen": "work", "Schnupperlehren und Erfahrungen": "work"}


def search_section(track: str) -> str:
    return "searchApprenticeship" if track == APPRENTICESHIP else "searchJob"


def track_fits(folder: pathlib.Path, track: str) -> bool:
    """A search profile of the other kind holds other sections: then nothing is read back or merged."""
    kind = search_plan.kind_of_folder(folder)
    return (kind == search_plan.KIND_APPRENTICESHIP) == (track == APPRENTICESHIP)


def read_text(folder: pathlib.Path, rel: str) -> str | None:
    path = folder / rel
    if not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def generated(form: dict, data: dict, track: str, rel: str) -> str:
    """The file as the form would write it from these answers."""
    note = ""
    if rel == PROFILE:
        return markdown_files.search_profile(data, track, note)
    if rel == STYLE:
        return markdown_files.style_profile(form, data, track, note)
    return markdown_files.building_blocks(data, track, note)


def _field(form: dict, section_id: str, field_id: str) -> dict:
    section = next(s for s in form["sections"] if s["id"] == section_id)
    return next(f for f in section["fields"] if f["id"] == field_id)


def _fits(form: dict, track: str, section_id: str, field_id: str, value) -> bool:
    if value in ("", []):
        return False
    return not validation.field_errors(form, _field(form, section_id, field_id), track, value)


def _entries(form: dict, track: str, slot: basics_slots.Slot, values: list[tuple]) -> list[dict] | None:
    section = next(s for s in form["sections"] if s["id"] == slot.form_section)
    if len(values) > section.get("maxItems", form["limits"]["repeatItems"]):
        return None
    entries = [{f: v for f, v in zip(slot.fields, entry) if v} for entry in values]
    errors = validation.section_errors(form, section, track, entries)
    return None if errors else entries


def _value(form: dict, track: str, slot: basics_slots.Slot, found: tuple) -> dict | list | None:
    """The answers of a slot for the form, or None if the form cannot take them."""
    if slot.repeat:
        return _entries(form, track, slot, found[0])
    pairs = {f: v for f, v in zip(slot.fields, found) if v not in ("", [])}
    if not pairs or not all(_fits(form, track, slot.form_section, f, v) for f, v in pairs.items()):
        return None
    return pairs


def _answers_of(form: dict, track: str, text: str, rel: str) -> tuple[dict, set[int]]:
    """The answers a file holds by form section, and the lines they came from."""
    answers: dict = {}
    understood: set[int] = set()
    for slot, (found, lines) in basics_slots.read_slots(text, rel, track).values():
        if slot.hidden:
            understood.update(lines)
        if not slot.form_section or found is None:
            continue
        value = _value(form, track, slot, found)
        if value is None:
            continue
        understood.update(lines)
        answers[slot.form_section] = value if slot.repeat else {**answers.get(slot.form_section, {}), **value}
    return answers, understood


def _empty(form: dict, track: str, rel: str) -> dict:
    ids = {slot.form_section for slot in basics_slots.slots(rel, track) if slot.form_section}
    repeat = {s["id"] for s in form["sections"] if s.get("repeat")}
    return {sid: ([] if sid in repeat else {}) for sid in ids}


def _derived_lines(form: dict, data: dict, track: str, rel: str) -> dict[str, set[str]]:
    """The lines the app would write in each section from these answers."""
    sections = basics_slots.sections(generated(form, data, track, rel))
    return {heading: {line.strip() for _, line in lines} for heading, lines in sections.items()}


def _form_section(rel: str, heading: str, track: str) -> str:
    if rel == STYLE:
        return "style"
    if rel == BLOCKS:
        return BLOCK_SECTIONS.get(heading, search_section(track) if heading == "Berufswahl" else "strengths")
    return search_section(track)


def _unknown(text: str, rel: str, track: str, understood: set[int], derived: dict[str, set[str]]) -> list[dict]:
    groups = []
    for heading, lines in _all_lines(text).items():
        known = derived.get(heading, set())
        rest = [line for number, line in lines if number not in understood and line.strip() not in known]
        if rest:
            groups.append({"datei": rel, "titel": TITLES[rel], "ueberschrift": heading,
                           "abschnitt": _form_section(rel, heading, track), "zeilen": rest})
    return groups


def _all_lines(text: str) -> dict[str, list[tuple[int, str]]]:
    """Every non-empty line of each section, indented ones too; the part before the first section is the title."""
    found: dict[str, list[tuple[int, str]]] = {}
    current = None
    for number, line in enumerate(text.split("\n")):
        if line.startswith("## "):
            current = found.setdefault(line[3:].strip(), [])
        elif current is not None and line.strip():
            current.append((number, line.rstrip()))
    return found


def read_back(form: dict, folder: pathlib.Path, track: str, cv_answers: dict | None) -> dict:
    """{"daten": answers by form section, "fremd": unknown lines by file and section} of the existing basics."""
    if not track_fits(folder, track):
        return {"daten": {}, "fremd": []}
    texts = {rel: read_text(folder, rel) for rel in FILES}
    answers: dict = {}
    understood: dict[str, set[int]] = {}
    for rel, text in texts.items():
        if text is None:
            continue
        found, lines = _answers_of(form, track, text, rel)
        answers = {**_empty(form, track, rel), **answers}
        answers = {**answers, **{k: _joined(answers.get(k), v) for k, v in found.items()}}
        understood[rel] = lines
    data = {**(cv_answers or {}), **answers}
    other = [group for rel, text in texts.items() if text is not None
             for group in _unknown(text, rel, track, understood[rel], _derived_lines(form, data, track, rel))]
    return {"daten": answers, "fremd": other}


def _joined(before, value):
    """Two files can fill the same form section (the search profile and the building blocks for apprenticeships)."""
    if isinstance(before, dict) and isinstance(value, dict):
        return {**before, **value}
    return value
