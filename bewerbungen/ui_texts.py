"""The language the app speaks to the person (#414, #415, G10, docs/design/sprachen.md).

`sprache(k)` is the one source for pages, scripts and the server's messages. Until every page is translated (#95,
step 15) the switch stays off and the app speaks German whatever the person chose. For development and for verifying
an item, `BEWERBUNGSBEGLEITER_SPRACHE_VORSCHAU=1` turns it on: the app then speaks the stored app language.

A message for the person is `T("Abgabe bis {datum}", datum=…)`: the German text as a string, so code and tests read it
as before, keeping its template, which is the catalog's key. The server says T messages in the app language
(`uebersetze`, `translate_marked`); a plain German text only translates by exact match where it is surely a message,
an error, never inside the data of an answer.
"""
import functools
import logging
import os
import pathlib
import re
from typing import Any, Mapping

import language_settings
import translation_catalog

# Turned on once, with the last item of #95 (Andy, 23.11.2026).
SWITCH_ON = False
PREVIEW_ENV = "BEWERBUNGSBEGLEITER_SPRACHE_VORSCHAU"
GERMAN = language_settings.DEFAULT_APP
PLACEHOLDER = re.compile(r"\{(\w+)\}")
log = logging.getLogger("bewerbungsbegleiter")


def _fill(template: str, values: Mapping[str, Any]) -> str:
    """The placeholders with a value filled in; any other brace stays as written, so no German text can break it."""
    return PLACEHOLDER.sub(lambda found: str(values[found[1]]) if found[1] in values else found[0], template)


class T(str):
    """A message for the person: the German text itself, plus the template and values to say it in another language.

    Copies and pickles rebuild it from the German text and then restore template and values from its __dict__."""

    template: str
    _pairs: tuple[tuple[str, Any], ...]

    def __new__(cls, template: str, **values: Any) -> "T":
        message = super().__new__(cls, _fill(template, values))
        message.template = template
        message._pairs = tuple(values.items())
        return message

    @property
    def values(self) -> dict[str, Any]:
        return dict(self._pairs)

    def in_language(self, catalog: translation_catalog.Catalog, language: str) -> str:
        """The message from the catalog with its values, a T among them in the same language; German without entry."""
        template = catalog.text(self.template, language)
        if template is None:
            return str(self)
        values = {name: value.in_language(catalog, language) if isinstance(value, T) else value
                  for name, value in self._pairs}
        return _fill(template, values)


def is_on() -> bool:
    return SWITCH_ON or os.environ.get(PREVIEW_ENV) == "1"


def _stamp(path: pathlib.Path) -> int | None:
    try:
        return path.stat().st_mtime_ns
    except OSError:
        return None


@functools.lru_cache(maxsize=8)
def _stored(data_dir: pathlib.Path, stamp: int | None) -> str:
    return language_settings.app_language(data_dir)


def sprache(k: Any) -> str:
    """The app language for the data folder of `k`: de while the switch is off, else what `sprachen.yaml` says."""
    data_dir = getattr(k, "daten", None)
    if not is_on() or data_dir is None:
        return GERMAN
    folder = pathlib.Path(data_dir)
    return _stored(folder, _stamp(folder / language_settings.FILE))


def _catalog(catalog: translation_catalog.Catalog | None) -> translation_catalog.Catalog | None:
    if catalog is not None:
        return catalog
    try:
        return translation_catalog.current()
    except translation_catalog.CatalogError:
        log.exception("Katalog der Übersetzungen nicht lesbar, die Meldung bleibt deutsch")
        return None


def uebersetze(text: str, sprache: str, catalog: translation_catalog.Catalog | None = None) -> str:
    """A message in `sprache`: a T by its template, a plain German text by exact match (for errors and dialogs).

    German, a text without entry and a catalog the app cannot read keep the text as it is."""
    if sprache == GERMAN:
        return text
    found = _catalog(catalog)
    if found is None:
        return text
    if isinstance(text, T):
        return text.in_language(found, sprache)
    return found.text(text, sprache) or text


def translate_marked(value: Any, language: str, catalog: translation_catalog.Catalog | None = None) -> Any:
    """A copy of a JSON value with each T in `language`; every other string is data and stays, even one that equals a
    catalog key (a status name, a title)."""
    if language == GERMAN:
        return value
    found = _catalog(catalog)
    return value if found is None else _marked(value, language, found)


def _marked(value: Any, language: str, catalog: translation_catalog.Catalog) -> Any:
    if isinstance(value, T):
        return value.in_language(catalog, language)
    if isinstance(value, Mapping):
        return {key: _marked(item, language, catalog) for key, item in value.items()}
    if isinstance(value, list):
        return [_marked(item, language, catalog) for item in value]
    if isinstance(value, tuple):
        return tuple(_marked(item, language, catalog) for item in value)
    return value
