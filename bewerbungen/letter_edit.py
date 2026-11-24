"""Editing the letter paragraph by paragraph (G94, #332): what a request may hold, and how it goes into anschreiben.yaml.

The page sends subject, salutation, paragraphs and closing with the fingerprint of the file it loaded. Every other key
of the letter stays as it is and where it is; the text is written as a literal block, the paragraphs joined by a blank
line, as `anschreiben.absaetze` reads them.
"""
import dataclasses

import yaml

import pfade  # noqa: F401  (makes the module lebenslauf importable)
import anschreiben
from ui_message import T

# The body of a letter (themes/brief.typ): A4 less 2.5 cm left and 2 cm right, DM Sans at 10 pt. A line holds about
# this many characters of German prose; measured on the example letter (tests/test_letter_edit.py).
PAGE_WIDTH_MM = 210
MARGINS_MM = (25, 20)
FONT_PT = 10
AVERAGE_CHARACTER_EM = 0.47
POINTS_PER_MM = 72 / 25.4
CHARS_PER_LINE = int((PAGE_WIDTH_MM - sum(MARGINS_MM)) * POINTS_PER_MM / (FONT_PT * AVERAGE_CHARACTER_EM))

MAX_PARAGRAPHS = 40
MAX_PARAGRAPH_CHARS = 4000
MAX_FIELD_CHARS = 300
# What a field must be, one sentence per field, so French and English can name each in its own words
NOT_TEXT = {"betreff": T("Betreff muss Text sein"), "anrede": T("Anrede muss Text sein"),
            "gruss": T("Gruss muss Text sein")}
TOO_LONG = {"betreff": T("Betreff hat mehr als {anzahl} Zeichen", anzahl=MAX_FIELD_CHARS),
            "anrede": T("Anrede hat mehr als {anzahl} Zeichen", anzahl=MAX_FIELD_CHARS),
            "gruss": T("Gruss hat mehr als {anzahl} Zeichen", anzahl=MAX_FIELD_CHARS)}

NO_PARAGRAPH = T("Das Anschreiben braucht mindestens einen Absatz mit Text.")
CHANGED = T("Das Anschreiben hat sich inzwischen geändert.")


@dataclasses.dataclass(frozen=True)
class LetterEdit:
    subject: str
    salutation: str
    paragraphs: tuple[str, ...]
    closing: str
    fingerprint: str


class LetterChanged(Exception):
    """The file is no longer the one the page loaded: a new draft or another tab wrote it meanwhile."""


def _field(body: dict, key: str) -> str:
    value = body.get(key)
    if not isinstance(value, str):
        raise ValueError(NOT_TEXT[key])
    if len(value) > MAX_FIELD_CHARS:
        raise ValueError(TOO_LONG[key])
    return value.strip()


def _cleaned(paragraph: str) -> str:
    """Each line trimmed, so the block stays literal; a blank line inside stays and splits it on the next load."""
    return "\n".join(line.strip() for line in paragraph.strip().splitlines())


def _paragraphs(body: dict) -> tuple[str, ...]:
    value = body.get("absaetze")
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(T("absaetze muss eine Liste von Texten sein"))
    if len(value) > MAX_PARAGRAPHS:
        raise ValueError(T("Höchstens {anzahl} Absätze", anzahl=MAX_PARAGRAPHS))
    if any(len(item) > MAX_PARAGRAPH_CHARS for item in value):
        raise ValueError(T("Ein Absatz hat mehr als {anzahl} Zeichen", anzahl=MAX_PARAGRAPH_CHARS))
    kept = tuple(_cleaned(item) for item in value if item.strip())
    if not kept:
        raise ValueError(NO_PARAGRAPH)
    return kept


def request_of(body) -> LetterEdit:
    """The edit from the page, checked at the boundary; empty paragraphs fall away."""
    if not isinstance(body, dict):
        raise ValueError(T("Erwartet: betreff, anrede, absaetze, gruss und fingerabdruck"))
    fingerprint = body.get("fingerabdruck")
    if not isinstance(fingerprint, str) or not fingerprint:
        raise ValueError(T("fingerabdruck fehlt"))
    return LetterEdit(subject=_field(body, "betreff"), salutation=_field(body, "anrede"), paragraphs=_paragraphs(body),
                      closing=_field(body, "gruss"), fingerprint=fingerprint)


def _letter(text: str) -> dict:
    try:
        letter = yaml.safe_load(text)
    except yaml.YAMLError as error:
        raise ValueError(T("Das Anschreiben ist kein lesbares YAML: {fehler}", fehler=error)) from error
    if not isinstance(letter, dict):
        raise ValueError(T("Das Anschreiben muss eine YAML-Zuordnung sein"))
    return letter


def _shown(text: str) -> list[str]:
    """The paragraphs as the build sets them, white space folded."""
    return [" ".join(part.split()) for part in anschreiben.absaetze(text)]


def _plain(value) -> str:
    return str(value or "").strip()


def unchanged(current: str, edit: LetterEdit) -> bool:
    """Whether the edit would build the same letter, so nothing is written and no draft is made."""
    letter = _letter(current)
    return (_plain(letter.get("betreff")) == edit.subject and _plain(letter.get("anrede")) == edit.salutation
            and _plain(letter.get("gruss")) == edit.closing
            and _shown(str(letter.get("text") or "")) == _shown("\n\n".join(edit.paragraphs)))


class _Literal(str):
    pass


class _LetterDumper(yaml.SafeDumper):
    pass


_LetterDumper.add_representer(_Literal, lambda dumper, value: dumper.represent_scalar("tag:yaml.org,2002:str", value,
                                                                                    style="|"))


def merged(current: str, edit: LetterEdit) -> str:
    """The letter with the edited fields; the other keys keep their values and their order."""
    letter = {**_letter(current), "betreff": edit.subject, "anrede": edit.salutation,
              "text": _Literal("\n\n".join(edit.paragraphs)), "gruss": edit.closing}
    return yaml.dump(letter, Dumper=_LetterDumper, allow_unicode=True, sort_keys=False, width=4096)
