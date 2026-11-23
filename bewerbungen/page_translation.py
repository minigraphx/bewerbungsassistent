"""Pages in the app language (#414, G10, docs/design/sprachen.md).

`Server._seite` hands every page through `translate`. In German the page stays byte for byte as it is. In French or
English `<html lang>` names the language, text nodes outside script and style and the attributes aria-label,
placeholder, title and alt come from the catalog, and `/uebersetzung.js` goes before the first script, so texte.js
finds the catalog for `Texte.t`. A text without an entry stays German. Scripts and styles are never touched, so the
hashes of a page with its own policy (Meine Angaben) still hold, and the catalog script comes from 'self'.
"""
import dataclasses
import html as html_text
import logging
import re
from typing import Iterator

import translation_catalog

SCRIPT_PATH = "/uebersetzung.js"
GERMAN = "de"
# Comments, script and style blocks pass whole; every other tag is one token, what lies between tags a text node.
TOKEN = re.compile(r"<!--.*?-->|<(script|style)\b[^>]*>.*?</\1\s*>|<[^>]*>", re.S | re.I)
ATTRIBUTE = re.compile(r'(\s(?:aria-label|placeholder|title|alt)=")([^"]*)(")')
TEXT_SET = re.compile(r'\sdata-text="([^"]+)"')
HTML_TAG = re.compile(r"<html\b", re.I)
LANG = re.compile(r'(\slang=")[^"]*(")')
SPACES = re.compile(r"[ \t\r\n]+")
WHITESPACE = " \t\r\n"
# The German in a page with a text set is its Sie form, the default set (texte.js VORGABE).
DEFAULT_FORM = "sie"
log = logging.getLogger("bewerbungsbegleiter")


@dataclasses.dataclass(frozen=True)
class Segment:
    kind: str  # "text", "tag" or "raw" (comment, script, style)
    start: int
    value: str


@dataclasses.dataclass(frozen=True)
class PageText:
    offset: int
    kind: str  # "text": a German text; "set": the key of a text set in texte.js
    text: str


def segments(page: str) -> Iterator[Segment]:
    position = 0
    for found in TOKEN.finditer(page):
        if found.start() > position:
            yield Segment("text", position, page[position:found.start()])
        raw = found[0].startswith("<!--") or found[1] is not None
        yield Segment("raw" if raw else "tag", found.start(), found[0])
        position = found.end()
    if position < len(page):
        yield Segment("text", position, page[position:])


def key_of(raw: str) -> str:
    """The catalog key of a text node or attribute: unescaped, runs of spaces and line breaks as one space."""
    return SPACES.sub(" ", html_text.unescape(raw.strip(WHITESPACE)))


def page_texts(page: str) -> Iterator[PageText]:
    """Every text of a page the catalog translates, for the scanner (sprachen_pruefen)."""
    text_set = None
    for segment in segments(page):
        if segment.kind == "text":
            key = key_of(segment.value)
            if text_set and key:
                yield PageText(segment.start, "set", text_set)
            elif key:
                yield PageText(segment.start + len(segment.value) - len(segment.value.lstrip(WHITESPACE)), "text", key)
            text_set = None
        elif segment.kind == "tag":
            for found in ATTRIBUTE.finditer(segment.value):
                if key_of(found[2]):
                    yield PageText(segment.start + found.start(2), "text", key_of(found[2]))
            named = TEXT_SET.search(segment.value)
            text_set = named[1] if named else None


def _text_node(raw: str, translation: str | None) -> str:
    if translation is None:
        return raw
    lead = raw[:len(raw) - len(raw.lstrip(WHITESPACE))]
    trail = raw[len(raw.rstrip(WHITESPACE)):]
    return lead + html_text.escape(translation, quote=False) + trail


def _tag(tag: str, catalog: translation_catalog.Catalog, language: str) -> str:
    def attribute(found: re.Match) -> str:
        translation = catalog.text(key_of(found[2]), language)
        return found[1] + html_text.escape(translation, quote=True) + found[3] if translation else found[0]

    translated = ATTRIBUTE.sub(attribute, tag)
    if not HTML_TAG.match(translated):
        return translated
    if LANG.search(translated):
        return LANG.sub(lambda found: f"{found[1]}{language}{found[2]}", translated, count=1)
    return translated.replace("<html", f'<html lang="{language}"', 1)


def _translated(page: str, catalog: translation_catalog.Catalog, language: str) -> str:
    parts = []
    text_set = None
    script_added = False
    for segment in segments(page):
        if segment.kind == "text":
            key = key_of(segment.value)
            translation = (catalog.form(text_set, language, DEFAULT_FORM) if text_set
                           else catalog.text(key, language) if key else None)
            parts.append(_text_node(segment.value, translation))
            text_set = None
            continue
        if segment.kind == "raw" and not script_added and segment.value[:7].lower() == "<script":
            parts.append(f'<script src="{SCRIPT_PATH}?sprache={language}"></script>\n')
            script_added = True
        parts.append(_tag(segment.value, catalog, language) if segment.kind == "tag" else segment.value)
        named = TEXT_SET.search(segment.value) if segment.kind == "tag" else None
        text_set = named[1] if named else None
    return "".join(parts)


def translate(page: str, language: str, catalog: translation_catalog.Catalog | None = None) -> str:
    """`page` in `language`; German, and a catalog the app cannot read, leave it as it is."""
    if language == GERMAN:
        return page
    try:
        return _translated(page, catalog or translation_catalog.current(), language)
    except translation_catalog.CatalogError:
        log.exception("Katalog der Übersetzungen nicht lesbar, die Seite bleibt deutsch")
        return page
