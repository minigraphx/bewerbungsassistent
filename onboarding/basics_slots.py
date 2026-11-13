"""Where the answers of the form stand in the Markdown basics (#217): the inverse of `markdown_files.py`.

A slot is one place in a file that holds one or more fields: a line such as „- Pensum: 80–100 %“, a numbered list or
the blocks of strengths. It reads the lines of its section and says what they hold and which lines it understood;
everything else in the file is the person's own and stays as it is. The same slots read a file of the person and a
file just written by `markdown_files.py`, so reading back and merging see the same values. A slot without `fields`
only keeps a line up to date that the app derives from other answers (the gaps also listed in the search profile);
a hidden one marks lines the app writes from cv.yaml and the work evidence, which the form does not read back.
A slot with `write` changes only the lines of its file that differ from the new value, such as one row of the table of
portals (#291), instead of writing all its lines anew.
"""
import dataclasses
import re
from typing import Callable

import markdown_files
import search_plan

PROFILE = "suchprofil.md"
STYLE = "anschreiben/stil.md"
BLOCKS = "anschreiben/bausteine.md"
FILES = (PROFILE, STYLE, BLOCKS)
TITLES = {PROFILE: "Suchprofil", STYLE: "Stilprofil", BLOCKS: "Bausteine"}
JOB, APPRENTICESHIP = "job", "apprenticeship"

PAIR = re.compile(r"^- ([^:]+): (.*)$")
NUMBERED = re.compile(r"^\d+\. (.+?)(?: \(Priorität \d+\))?$")
BULLET = re.compile(r"^- (.+)$")
QUOTED = re.compile(r"^- „(.*)“$")
GREETING = re.compile(r"^- Gruss: „(.*)“(?:; Ort im Datum: (.*))?\.$")
BLOCK = re.compile(r"^- \*\*(.+?)\*\* –(?: (.*?))? \*Beleg: (.*)\.\*$")
INFORMAL = f"- {markdown_files.SALUTATION_INFORMAL}"
FORMAL_ELSE = f"- Sonst {markdown_files.SALUTATION_FORMAL}"
FORMAL_ALWAYS = f"- Immer {markdown_files.SALUTATION_FORMAL}"
ADDRESS_OPTIONS = ("Sie-Form; Du-Form, wenn das Inserat duzt", "Immer Sie-Form")  # as in form.json, style.address
NO_GAPS = markdown_files.GAPS_LATER
LIST_SEPARATOR = ", "

TABLE_ROW = re.compile(r"^\|([^|]*)\|([^|]*)\|")
TABLE_HEAD = re.compile(r"^\|\s*portal\s*\|\s*modus\s*\|$|^\|[\s|:-]+\|$", re.IGNORECASE)

Lines = list[tuple[int, str]]  # (line number in the file, line without the line break)
Found = tuple[tuple | None, tuple[int, ...]]  # (one value per field, or None if not understood; lines understood)
NOTHING: Found = (None, ())
Writes = tuple[dict[int, list[str]], list[str]]  # (lines in place of a line by its number, lines added to the section)


@dataclasses.dataclass(frozen=True)
class Slot:
    section: str  # the heading without „## “
    read: Callable[[Lines], Found]
    form_section: str | None = None
    fields: tuple[str, ...] = ()  # empty: the slot only keeps a derived line up to date
    repeat: bool = False  # the value is a list of entries, each with one value per field
    hidden: bool = False  # its lines are in the app's own format and need not be listed as unknown
    keeps_empty: bool = False  # an empty list is an answer too, such as no portal switched off
    write: Callable[[Lines, tuple | None], Writes] | None = None  # changes only the lines that differ

    @property
    def key(self) -> str:
        return f"{self.section}/{self.form_section}/{','.join(self.fields)}"


def sections(text: str) -> dict[str, Lines]:
    """The top-level lines of each section by heading; the first section of a name counts."""
    found: dict[str, Lines] = {}
    current: Lines | None = None
    for number, line in enumerate(text.split("\n")):
        if line.startswith("## "):
            heading = line[3:].strip()
            current = found.setdefault(heading, []) if heading not in found else None
        elif current is not None and line.strip():
            current.append((number, line.rstrip()))
    return found


def _top(lines: Lines) -> Lines:
    return [(n, line) for n, line in lines if not line[:1].isspace()]


def pair(label: str, as_list: bool = False) -> Callable[[Lines], Found]:
    def read(lines: Lines) -> Found:
        for number, line in _top(lines):
            match = PAIR.match(line)
            if match and match.group(1) == label:
                value = match.group(2).strip()
                return ((value.split(LIST_SEPARATOR) if as_list else value,), (number,))
        return NOTHING
    return read


def numbered(lines: Lines) -> Found:
    found = [(n, NUMBERED.match(line)) for n, line in _top(lines)]
    found = [(n, m.group(1).strip()) for n, m in found if m and "(Priorität" not in m.group(1)]
    return ((([v for _, v in found]),), tuple(n for n, _ in found)) if found else NOTHING


def bullets(skip: frozenset[str] = frozenset()) -> Callable[[Lines], Found]:
    """Every top-level bullet; lines in `skip` are understood but hold no value (text the app writes itself)."""
    def read(lines: Lines) -> Found:
        found = [(n, line) for n, line in _top(lines) if BULLET.match(line)]
        values = [line[2:].strip() for _, line in found if line not in skip]
        return ((values,), tuple(n for n, _ in found)) if found else NOTHING
    return read


def first_bullet(lines: Lines) -> Found:
    found = [(n, line) for n, line in _top(lines) if BULLET.match(line)]
    return ((found[0][1][2:].strip(),), (found[0][0],)) if found else NOTHING


def tone(lines: Lines) -> Found:
    """The first bullet, written as „<tone>.“; the fixed sentences after it are the app's own."""
    found = [(n, line) for n, line in _top(lines) if BULLET.match(line)]
    if not found or not found[0][1].endswith(".") or found[0][1] in _FIXED_TONE:
        return NOTHING
    return ((found[0][1][2:-1].strip(),), (found[0][0],))


def address(lines: Lines) -> Found:
    texts = {line: n for n, line in _top(lines)}
    if INFORMAL in texts and FORMAL_ELSE in texts:
        return ((ADDRESS_OPTIONS[0],), (texts[INFORMAL], texts[FORMAL_ELSE]))
    if FORMAL_ALWAYS in texts:
        return ((ADDRESS_OPTIONS[1],), (texts[FORMAL_ALWAYS],))
    return NOTHING


def greeting(lines: Lines) -> Found:
    for number, line in _top(lines):
        match = GREETING.match(line)
        if match:
            return ((match.group(1).strip(), (match.group(2) or "").strip()), (number,))
    return NOTHING


def quoted(label: str) -> Callable[[Lines], Found]:
    prefix = f"- {label}: „"
    def read(lines: Lines) -> Found:
        for number, line in _top(lines):
            if line.startswith(prefix) and line.endswith("“"):
                return ((line[len(prefix):-1].strip(),), (number,))
        return NOTHING
    return read


def phrases(lines: Lines) -> Found:
    found = [(n, QUOTED.match(line)) for n, line in _top(lines)]
    found = [(n, m.group(1).strip()) for n, m in found if m]
    return (([v for _, v in found],), tuple(n for n, _ in found)) if found else NOTHING


def blocks(lines: Lines) -> Found:
    """Strengths as „- **<strength>** – <example> *Beleg: <evidence>.*“; „eigene Angabe“ means no evidence."""
    found = [(n, BLOCK.match(line)) for n, line in _top(lines)]
    entries = [(n, (m.group(1).strip(), (m.group(2) or "").strip(), _evidence(m.group(3)))) for n, m in found if m]
    return (([e for _, e in entries],), tuple(n for n, _ in entries)) if entries else NOTHING


def _evidence(value: str) -> str:
    value = value.strip()
    return "" if value == markdown_files.OWN_STATEMENT else value


def window(lines: Lines) -> Found:
    """„- Zeitfenster: 14 Tage“ as the number of days, read as the search reads it; others stay unknown."""
    found, numbers = pair(markdown_files.WINDOW_LABEL)(lines)
    days = search_plan.window_days(found[0]) if found else None
    return ((str(days),), numbers) if days else NOTHING


def _portal_rows(lines: Lines) -> dict[str, tuple[int, str]]:
    """The rows of the job portals by portal: (line number, mode); a later row counts, as in the search."""
    rows = {}
    for number, line in _top(lines):
        match = TABLE_ROW.match(line)
        name = match.group(1).strip().lower() if match else ""
        if name in search_plan.PORTALS:
            rows = {**rows, name: (number, match.group(2).strip().lower())}
    return rows


def portals(lines: Lines) -> Found:
    """The job portals switched off („aus“) in the table under „Portale und Rhythmus“, with its head (#291)."""
    rows = _portal_rows(lines)
    if not rows:
        return NOTHING
    off = [portal for portal in search_plan.PORTALS if portal in rows and rows[portal][1] == search_plan.MODE_OFF]
    head = tuple(n for n, line in _top(lines) if TABLE_HEAD.match(line))
    return ((off,), tuple(sorted({*head, *(n for n, _ in rows.values())})))


def write_portals(lines: Lines, found: tuple | None) -> Writes:
    """Only the rows whose portal goes on or off; a missing portal searches, so a row is added only to switch it off."""
    off = set(found[0]) if found else set()
    rows = _portal_rows(lines)
    if not rows:
        table = [markdown_files.portal_row(p, p in off) for p in search_plan.PORTALS]
        return ({}, ["", *markdown_files.PORTAL_HEAD, *table] if off else [])
    replaced = {n: [markdown_files.portal_row(p, p in off)] for p, (n, mode) in rows.items()
                if (mode == search_plan.MODE_OFF) != (p in off)}
    missing = [markdown_files.portal_row(p, True) for p in search_plan.PORTALS if p in off and p not in rows]
    if missing:
        last = max(n for n, _ in rows.values())
        line = dict(lines)[last]
        replaced = {**replaced, last: [*replaced.get(last, [line]), *missing]}
    return replaced, []


_FIXED_TONE = frozenset({"- Aussagen mit konkreten Beispielen belegen; Lücken offen und knapp benennen, mit Lernbereitschaft.",
                         "- Schweizer Schreibweise (ss statt ß)."})
_GAPS = bullets(frozenset({NO_GAPS}))


def _region_job() -> list[Slot]:
    return [Slot("Region", pair("Wohnort"), "searchJob", ("home",)),
            Slot("Region", pair("Pendelgrenze"), "searchJob", ("commute",)),
            Slot("Region", pair("Kantone (job-room)", True), "searchJob", ("cantons",)),
            Slot("Region", pair("Remote"), "searchJob", ("remote",))]


def _profile_job() -> list[Slot]:
    search = "searchJob"
    return [Slot("Suchrichtungen", numbered, search, ("directions",)),
            Slot("Suchrichtungen", pair("Ausschluss", True), search, ("exclusions",)),
            *_region_job(),
            Slot("Keywords", pair("Kernliste", True), search, ("keywords",)),
            Slot("Titelfilter", pair("Positiv", True), search, ("titlePositive",)),
            Slot("Titelfilter", pair("Ausschluss", True), search, ("titleExclude",)),
            Slot(markdown_files.RHYTHM, window, search, ("window",)),
            Slot(markdown_files.RHYTHM, portals, search, ("portalsOff",), keeps_empty=True, write=write_portals),
            Slot("Rahmen", pair("Frühester Start"), search, ("start",)),
            Slot("Rahmen", pair("Pensum"), search, ("workload",)),
            Slot("Rahmen", pair("Befristung möglich"), search, ("temporary",)),
            Slot("Zielfirmen mit Karriereseite", bullets(), search, ("targetCompanies",)),
            Slot("Stärken", first_bullet),
            Slot("Typische Haken (offen benennen)", _GAPS)]


def _profile_apprenticeship() -> list[Slot]:
    search = "searchApprenticeship"
    return [Slot("Person", pair("Begleitperson"), search, ("companion",)),
            Slot("Gesucht", first_bullet, search, ("offers",)),
            Slot("Lehrbeginn", first_bullet, search, ("start",)),
            Slot("Berufe (mit Priorität)", numbered, search, ("professions",)),
            Slot("Berufswahl", first_bullet, search, ("howFound",)),
            Slot("Region", pair("Wohnort"), search, ("home",)),
            Slot("Region", pair("Schulweg"), search, ("commute",)),
            Slot("Region", pair("Kantone", True), search, ("cantons",)),
            Slot("Region", pair("Umkreis"), search, ("radius",)),
            Slot("Schule", pair("Berufsmaturität"), search, ("vocationalBaccalaureate",)),
            Slot("Stärken", first_bullet),
            Slot("Typische Haken (offen benennen)", _GAPS)]


def _style(track: str) -> list[Slot]:
    words = "Typische Formulierungen"
    own = [Slot("Anrede und Form", address, "style", ("address",))] if track == JOB else []
    return [Slot("Ton", tone, "style", ("tone",)), *own,
            Slot("Anrede und Form", greeting, "style", ("greeting", "place")),
            Slot(words, quoted("Einstieg"), "style", ("opening",)),
            Slot(words, quoted("Schluss"), "style", ("closing",)),
            Slot(words, phrases, "style", ("phrases",))]


def _blocks(track: str) -> list[Slot]:
    common = [Slot("Stärken", blocks, "strengths", ("strength", "example", "evidence"), repeat=True),
              Slot("Lücken (offen benennen)", _GAPS, "gaps", ("gaps",)),
              Slot("Rahmen", pair("Referenz"), "frame", ("reference",))]
    if track == APPRENTICESHIP:
        return [*common, Slot("Schnupperlehren und Erfahrungen", blocks, hidden=True), Slot("Berufswahl", first_bullet),
                Slot("Rahmen", pair("Schnuppern möglich"), "frame", ("availability",))]
    return [*common, Slot("Stationen", blocks, hidden=True), Slot("Rahmen", pair("Verfügbar ab")),
            Slot("Rahmen", pair("Kündigungsfrist"), "frame", ("notice",)),
            Slot("Rahmen", pair("Lohnvorstellung"), "frame", ("salary",))]


def slots(rel: str, track: str) -> list[Slot]:
    """The slots of one basic file for a track."""
    if rel == PROFILE:
        return _profile_apprenticeship() if track == APPRENTICESHIP else _profile_job()
    return _style(track) if rel == STYLE else _blocks(track)


def read_slots(text: str, rel: str, track: str) -> dict[str, tuple[Slot, Found]]:
    """What each slot finds in the text, by slot key."""
    found = sections(text)
    return {slot.key: (slot, slot.read(found.get(slot.section, []))) for slot in slots(rel, track)}


def section_ids(track: str) -> tuple[str, ...]:
    """The sections of the form that the basics hold, so the page can take them from the files."""
    ids = (slot.form_section for rel in FILES for slot in slots(rel, track) if slot.form_section)
    return tuple(dict.fromkeys(ids))
