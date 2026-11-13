"""Write the answers of „Meine Angaben“ into the existing Markdown basics, changing only what changed (#217).

The page sends what it read back from the files (`basics_read.py`) along with the answers. Each slot of a file
(`basics_slots.py`) whose value differs between the two gets the lines the form would write now, in place of the lines
it understood in the file; every other line stays as it is, unknown ones included. A slot the person left alone is
not written, so a term added on the search page while the form was open stays too.
"""
import pathlib

import basics_read
import basics_slots
from basics_slots import FILES

UNKNOWN_BASE = "Die gelesenen Angaben haben eine unbekannte Form."


def clean_base(form: dict, track: str, base: object) -> dict:
    """The sections of the read-back answers in a form `markdown_files.py` can use; others are left out, so the
    answers count as unchanged there."""
    if not isinstance(base, dict):
        raise ValueError(UNKNOWN_BASE)
    repeat = {s["id"] for s in form["sections"] if s.get("repeat")}
    kept = {}
    for sid in basics_slots.section_ids(track):
        value = base.get(sid)
        fits = (isinstance(value, list) and all(isinstance(v, dict) for v in value)) if sid in repeat \
            else isinstance(value, dict)
        if fits:
            kept = {**kept, sid: value}
    return kept


def merged_files(form: dict, bundle: dict, base: object, folder: pathlib.Path) -> dict[str, str | None]:
    """For each existing basic file that can merge: its new text, or None if nothing in it changes."""
    track, data = bundle["track"], bundle["data"]
    before = {**data, **clean_base(form, track, base)}
    if not basics_read.track_fits(folder, track):
        return {}
    result = {}
    for rel in FILES:
        text = basics_read.read_text(folder, rel)
        if text is None:
            continue
        merged = merged_text(form, text, rel, track, before, data)
        result = {**result, rel: None if merged == text else merged}
    return result


def merged_text(form: dict, text: str, rel: str, track: str, before: dict, after: dict) -> str:
    """The text with the lines of every slot whose value differs between `before` and `after` written anew."""
    was = basics_slots.read_slots(basics_read.generated(form, before, track, rel), rel, track)
    new_text = basics_read.generated(form, after, track, rel)
    now = basics_slots.read_slots(new_text, rel, track)
    current = basics_slots.read_slots(text, rel, track)
    new_lines = new_text.split("\n")
    changes = [change for key, (slot, found) in now.items() if found[0] != was[key][1][0]
               for change in _changes(slot, text, current[key][1][1], found, new_lines)]
    return _applied(text, changes) if changes else text


def _changes(slot: basics_slots.Slot, text: str, old: tuple[int, ...], found: basics_slots.Found,
             new_lines: list[str]) -> list[tuple[basics_slots.Slot, tuple[int, ...], list[str]]]:
    """The lines of the slot written anew, or with `write` only those that differ from the new value."""
    if slot.write is None:
        return [(slot, old, [new_lines[n] for n in found[1]])]
    lines = text.split("\n")
    replaced, added = slot.write([(n, lines[n]) for n in old], found[0])
    return [*((slot, (n, ), rows) for n, rows in replaced.items()), *([(slot, (), added)] if added else [])]


def _applied(text: str, changes: list[tuple[basics_slots.Slot, tuple[int, ...], list[str]]]) -> str:
    lines = text.split("\n")
    ends = _section_ends(lines)
    replaced: dict[int, list[str]] = {}
    added: dict[int, list[str]] = {}
    appended: dict[str, list[str]] = {}
    for slot, old, new in changes:
        if old:
            replaced = {**replaced, old[0]: new, **{n: [] for n in old[1:]}}
        elif slot.section in ends:
            end = ends[slot.section]
            added = {**added, end: [*added.get(end, []), *new]}
        elif new:
            appended = {**appended, slot.section: [*appended.get(slot.section, []), *new]}
    out = [part for number, line in enumerate(lines)
           for part in [*replaced.get(number, [line]), *added.get(number, [])]]
    return _with_sections(out, appended)


def _section_ends(lines: list[str]) -> dict[str, int]:
    """The last non-empty line of each section (its heading if it is empty); the first section of a name counts."""
    ends: dict[str, int] = {}
    current = None
    for number, line in enumerate(lines):
        if line.startswith("## "):
            heading = line[3:].strip()
            current = heading if heading not in ends else None
            if current:
                ends = {**ends, current: number}
        elif current and line.strip():
            ends = {**ends, current: number}
    return ends


def _with_sections(lines: list[str], appended: dict[str, list[str]]) -> str:
    if not appended:
        return "\n".join(lines)
    body = "\n".join(lines).rstrip("\n")
    blocks = "\n\n".join("\n".join([f"## {heading}", *rows]) for heading, rows in appended.items())
    return f"{body}\n\n{blocks}\n"
