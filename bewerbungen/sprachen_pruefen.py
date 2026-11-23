"""Missing translations (#414, G10, docs/design/sprachen.md).

    python -m sprachen_pruefen [--alle] [--katalog <ordner>] [datei …]

Prints `datei:zeile: text [fr,en]` for each text that lacks a language in the catalog, `[Texte.t]` for a German
literal a script shows without Texte.t and `[T]` for a Python message built with an f-string outside T; the exit code is 1 with a gap. Without files it checks FERTIG, with --alle
every source of the app. tests/test_sprachen.py runs the same checks in the gate, together with the catalog's own
consistency (catalog_problems) and entries no source uses (orphans).
"""
import argparse
import dataclasses
import pathlib
import re
import sys
from typing import Iterable, Iterator, Mapping

import language_sources
import translation_catalog
from translation_catalog import FALLBACK, LANGUAGES, SET_PREFIX

BASE = language_sources.BASE
DESKTOP = BASE.parent / "desktop"
# Files whose every text is in the catalog in fr and en; each item of #95 adds the files of its page, the last one
# replaces the list with every source (Andy, 23.11.2026: after the switch, every new text needs fr and en).
# Entries as BASE / "seiten/heute.html".
FERTIG: tuple[pathlib.Path, ...] = (
    # The shared frame of every page (#416): navigation, messages, update and backup, consent and the window
    # „KI einrichten“, with the server's own messages and the routes of the AI and of Suche einstellen.
    BASE / "seiten/nur-in-der-app.html", BASE / "seiten/app.js", BASE / "seiten/sidebar.js",
    BASE / "seiten/sidebar-logic.js", BASE / "seiten/meldungen.js", BASE / "seiten/einwilligung.js",
    BASE / "seiten/ki-zugang.js", BASE / "seiten/ki-fenster.js",
    BASE / "server.py", BASE / "ai/errors.py", BASE / "routes_ai.py", BASE / "ai/consent.py", BASE / "routes_frame.py",
    # The page Einstellungen (#417): its scripts, texte.js and uebersicht-logik.js that it loads, and the routes it
    # calls, also those the desktop app adds.
    BASE / "seiten/einstellungen.html", BASE / "seiten/texte.js", BASE / "seiten/dot-line.js",
    BASE / "seiten/uebersicht-logik.js", BASE / "seiten/einstellungen-logik.js", BASE / "seiten/einstellungen.js",
    BASE / "seiten/claude-abo.js", BASE / "seiten/vorabversionen.js", BASE / "seiten/browser-wahl-logik.js",
    BASE / "seiten/browser-wahl.js", BASE / "seiten/seitengrenze.js", BASE / "seiten/sprache-logik.js",
    BASE / "seiten/sprache.js",
    BASE / "routes_own_key.py", BASE / "ai/own_key.py", BASE / "routes_language_settings.py",
    BASE / "language_settings.py", BASE / "routes_preferences.py", BASE / "preferences.py",
    BASE / "routes_page_limit.py", BASE / "page_limit.py", BASE / "ai/connection.py",
    DESKTOP / "routes_app.py", DESKTOP / "routes_claude.py", DESKTOP / "routes_browser.py",
)
LEFTOVER = "Texte.t"
PYTHON_LEFTOVER = "T"
REQUIRED_FORMS = {"fr": ("sie", "du"), "en": ("sie",)}
FORMS = ("sie", "du", "lehrstelle")
PLACEHOLDER = re.compile(r"\{(\w+)\}")


@dataclasses.dataclass(frozen=True)
class Gap:
    path: str
    line: int
    text: str
    missing: tuple[str, ...]

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {self.text} [{','.join(self.missing)}]"


def _shown(path: pathlib.Path) -> str:
    resolved = path.resolve()
    return str(resolved.relative_to(BASE)) if resolved.is_relative_to(BASE) else str(path)


def _missing(item: language_sources.Item, catalog: translation_catalog.Catalog) -> tuple[str, ...]:
    if item.kind == "leftover":
        return (PYTHON_LEFTOVER if item.path.suffix == ".py" else LEFTOVER,)
    if item.kind == "set":
        return tuple(language for language in LANGUAGES if not catalog.form(item.text, language, "sie"))
    return tuple(language for language in LANGUAGES if not catalog.text(item.text, language))


def gaps(paths: Iterable[pathlib.Path], catalog: translation_catalog.Catalog) -> tuple[Gap, ...]:
    found = ((item, _missing(item, catalog)) for item in language_sources.items(paths))
    return tuple(Gap(_shown(item.path), item.line, SET_PREFIX + item.text if item.kind == "set" else item.text, missing)
                 for item, missing in found if missing)


def _placeholders(text: str) -> set[str]:
    return set(PLACEHOLDER.findall(text))


def _value_problems(key: str, where: str, value, german: str) -> Iterator[str]:
    if not isinstance(value, str) or not value.strip():
        yield f"{key}: {where} empty"
    elif _placeholders(value) != _placeholders(german):
        yield f"{key}: {where} placeholders {sorted(_placeholders(value))} instead of {sorted(_placeholders(german))}"


def _languages(key: str, entry) -> Iterator[str]:
    if not isinstance(entry, Mapping):
        yield f"{key}: expected an object with fr and en"
        return
    yield from (f"{key}: unknown language {language}" for language in entry if language not in LANGUAGES)
    yield from (f"{key}: {language} missing" for language in LANGUAGES if language not in entry)


def _text_problems(key: str, entry) -> Iterator[str]:
    yield from _languages(key, entry)
    if isinstance(entry, Mapping):
        for language in LANGUAGES:
            if language in entry:
                yield from _value_problems(key, language, entry[language], key)


def _german_form(german: Mapping[str, str], form: str) -> str:
    return next(german[name] for name in FALLBACK[form] if german.get(name))


def _form_problems(key: str, language: str, forms, german: Mapping[str, str]) -> Iterator[str]:
    if not isinstance(forms, Mapping):
        yield f"{key}: {language} expected the forms sie, du, lehrstelle"
        return
    required = REQUIRED_FORMS[language] + (("lehrstelle",) if "lehrstelle" in german else ())
    yield from (f"{key}: {language} unknown form {form}" for form in forms if form not in FORMS)
    yield from (f"{key}: {language} {form} missing" for form in required if form not in forms)
    for form in (form for form in FORMS if form in forms):
        yield from _value_problems(key, f"{language} {form}", forms[form], _german_form(german, form))


def _set_problems(key: str, entry, sets: Mapping[str, Mapping[str, str]]) -> Iterator[str]:
    german = sets.get(key[len(SET_PREFIX):])
    if german is None:
        yield f"{key}: not in texte.js"
        return
    yield from _languages(key, entry)
    if isinstance(entry, Mapping):
        for language in (language for language in LANGUAGES if language in entry):
            yield from _form_problems(key, language, entry[language], german)


def catalog_problems(catalog: translation_catalog.Catalog, sets: Mapping[str, Mapping[str, str]]) -> tuple[str, ...]:
    """fr and en present and not empty, the same placeholders as the German, text sets that texte.js has."""
    return tuple(problem for key, entry in catalog.entries.items()
                 for problem in (_set_problems(key, entry, sets) if key.startswith(SET_PREFIX)
                                 else _text_problems(key, entry)))


def orphans(catalog: translation_catalog.Catalog, items: Iterable[language_sources.Item],
            sets: Mapping[str, Mapping[str, str]]) -> tuple[str, ...]:
    """Plain entries no source shows; a text set is checked against texte.js in catalog_problems."""
    used = {item.text for item in items if item.kind != "set"}
    return tuple(key for key in catalog.entries if not key.startswith(SET_PREFIX) and key not in used)


def app_sources() -> tuple[pathlib.Path, ...]:
    """The pages, scripts and modules of bewerbungen, and the routes the desktop app adds to them (#417)."""
    patterns = ((BASE, "seiten/*.html"), (BASE, "seiten/*.js"), (BASE, "*.py"), (BASE, "ai/*.py"),
                (DESKTOP, "routes_*.py"))
    return tuple(path for folder, pattern in patterns for path in sorted(folder.glob(pattern)))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m sprachen_pruefen", description="Fehlende Übersetzungen")
    parser.add_argument("dateien", nargs="*", type=pathlib.Path, help="Dateien (Standard: FERTIG)")
    parser.add_argument("--alle", action="store_true", help="jede Quelle der App")
    parser.add_argument("--katalog", type=pathlib.Path, default=translation_catalog.CATALOG_DIR, help="Ordner des Katalogs")
    args = parser.parse_args(argv)
    try:
        catalog = translation_catalog.load(args.katalog)
    except translation_catalog.CatalogError as error:
        print(f"Katalog: {error}", file=sys.stderr)
        return 2
    paths = app_sources() if args.alle else tuple(args.dateien) or FERTIG
    found = gaps(paths, catalog)
    for gap in found:
        print(gap)
    if found:
        print(f"{len(found)} Texte ohne Übersetzung", file=sys.stderr)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
