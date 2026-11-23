"""Languages (G10, G12, #94): the language of the app and the languages the person applies in.

Stored in the data folder (`sprachen.yaml`) like the choice of the setup (preferences.py), so it moves with the
person's files; written with drafts before and after. Each key counts on its own: a file may hold only the app's
language, and the application languages stay a suggestion until the person confirms them.

Without a choice the app speaks German. The application languages are suggested from `languages` in cv.yaml: every
language the app offers that the CV names at C1 or better. A missing CV, or one that names none of them at that
level, suggests German. Translating the pages is #95; this module only keeps the setting.
"""
import dataclasses
import pathlib

import yaml

import pfade  # noqa: F401  (makes the module lebenslauf importable)
import build as cv_build
import precheck
from dateien import schreibe_atomar

FILE = "sprachen.yaml"
APP_LANGUAGES = ("de", "fr", "en")
DEFAULT_APP = "de"
# The order of the checkboxes on the page and in the file.
APPLICATION_LANGUAGES = ("de", "en", "fr")
DEFAULT_APPLICATIONS = ("de",)
# Writing a cover letter in a language takes more than reading an ad in it: C1 („fliessend“) or better.
SUGGEST_FROM_LEVEL = 5
APP_KEY = "app"
APPLICATIONS_KEY = "bewerbung"
CODE_OF_LANGUAGE = {"deutsch": "de", "englisch": "en", "französisch": "fr"}
NAMES = {"de": "Deutsch", "en": "Englisch", "fr": "Französisch"}
HEADER = "# Sprachen: Sprache der App und Bewerbungssprachen. Geschrieben vom Bewerbungsbegleiter.\n"
BAD_APP = "Bitte wählen: Deutsch, Französisch oder Englisch als Sprache der App."
BAD_APPLICATIONS = "Bitte mindestens eine Bewerbungssprache wählen: Deutsch, Englisch oder Französisch."
BAD_VALUES = "Bitte die Sprache der App oder die Bewerbungssprachen angeben."


@dataclasses.dataclass(frozen=True)
class Suggested:
    language: str
    level: str  # as the CV writes it, for the page to quote


@dataclasses.dataclass(frozen=True)
class Settings:
    app: str
    app_chosen: bool
    applications: tuple[str, ...]
    applications_chosen: bool
    suggested: tuple[Suggested, ...]

    def as_dict(self) -> dict:
        return {"app": self.app, "app_gewaehlt": self.app_chosen, "bewerbung": list(self.applications),
                "bewerbung_gewaehlt": self.applications_chosen,
                "vorschlag": [{"sprache": entry.language, "stufe": entry.level} for entry in self.suggested]}


def _app(value) -> str:
    if not isinstance(value, str) or value not in APP_LANGUAGES:
        raise ValueError(BAD_APP)
    return value


def _applications(value) -> tuple[str, ...]:
    valid = (isinstance(value, list) and value and len(set(value)) == len(value)
             and all(isinstance(code, str) and code in APPLICATION_LANGUAGES for code in value))
    if not valid:
        raise ValueError(BAD_APPLICATIONS)
    return tuple(code for code in APPLICATION_LANGUAGES if code in value)


CHECKS = {APP_KEY: _app, APPLICATIONS_KEY: _applications}


def parse(values) -> dict:
    """The keys the page sends, checked; ValueError with a German message. Unknown keys are ignored."""
    if not isinstance(values, dict) or not any(key in values for key in CHECKS):
        raise ValueError(BAD_VALUES)
    return {key: check(values[key]) for key, check in CHECKS.items() if key in values}


def _stored(data_dir: pathlib.Path) -> dict:
    """The valid keys of the file; a broken file or a strange value counts as not chosen."""
    path = data_dir / FILE
    try:
        stored = yaml.safe_load(path.read_text(encoding="utf-8")) if path.is_file() else None
    except (OSError, yaml.YAMLError):
        return {}
    if not isinstance(stored, dict):
        return {}
    return dict(_valid_items(stored))


def _valid_items(stored: dict):
    for key, check in CHECKS.items():
        try:
            yield key, check(stored[key])
        except (KeyError, ValueError):
            continue


def _cv_languages(data_dir: pathlib.Path) -> list[dict]:
    try:
        cv = yaml.safe_load((data_dir / "cv.yaml").read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return []
    entries = cv.get("languages") if isinstance(cv, dict) else None
    return [entry for entry in entries if isinstance(entry, dict)] if isinstance(entries, list) else []


def _text(entry: dict, field: str) -> str:
    # Since #181 a field may hold German and English; the German one is what the page quotes.
    value = cv_build.waehle_sprache(entry.get(field), "de")
    return "" if value is None else str(value).strip()


def _suggested_entry(entry: dict) -> tuple[str, int, str] | None:
    named = precheck.LANGUAGE_IN_NAME.search(_text(entry, "language"))
    code = CODE_OF_LANGUAGE.get(precheck.LANGUAGES[named[0].lower()]) if named else None
    if not code:
        return None
    # The written level first; the dossier's `x-level` (A1–C2) where the CV has no words for it.
    for level_text in (_text(entry, "fluency"), _text(entry, "x-level")):
        level = precheck.level_of(level_text)
        if level:
            return code, level, level_text
    return None


def suggestion(data_dir: pathlib.Path) -> tuple[Suggested, ...]:
    """The application languages cv.yaml suggests, in the order of the page, each with the CV's level."""
    best: dict[str, tuple[int, str]] = {}
    for found in filter(None, map(_suggested_entry, _cv_languages(data_dir))):
        code, level, text = found
        if level >= SUGGEST_FROM_LEVEL and level > best.get(code, (0, ""))[0]:
            best = {**best, code: (level, text)}
    return tuple(Suggested(code, best[code][1]) for code in APPLICATION_LANGUAGES if code in best)


def load(data_dir: pathlib.Path) -> Settings:
    """The stored settings; what is not chosen yet is German, or the suggestion from the CV."""
    stored = _stored(data_dir)
    suggested = suggestion(data_dir)
    proposed = tuple(entry.language for entry in suggested) or DEFAULT_APPLICATIONS
    return Settings(app=stored.get(APP_KEY, DEFAULT_APP), app_chosen=APP_KEY in stored,
                    applications=stored.get(APPLICATIONS_KEY, proposed), applications_chosen=APPLICATIONS_KEY in stored,
                    suggested=suggested)


def _description(changes: dict) -> str:
    parts = []
    if APP_KEY in changes:
        parts.append(f"App auf {NAMES[changes[APP_KEY]]}")
    if APPLICATIONS_KEY in changes:
        parts.append("Bewerbungen auf " + ", ".join(NAMES[code] for code in changes[APPLICATIONS_KEY]))
    return "Sprachen: " + "; ".join(parts)


def _file_text(values: dict) -> str:
    data = {key: (list(value) if isinstance(value, tuple) else value) for key, value in values.items()}
    return HEADER + yaml.safe_dump(data, allow_unicode=True, sort_keys=False)


def save(k, values) -> Settings:
    """Store what the page sends over what is stored, with drafts before and after like every file in the data folder."""
    changes = parse(values)
    path = k.daten / FILE

    def write():
        merged = {**_stored(k.daten), **changes}
        ordered = {key: merged[key] for key in CHECKS if key in merged}
        schreibe_atomar(path, _file_text(ordered).encode("utf-8"))

    k.mit_entwurf(path, _description(changes), write)
    return load(k.daten)
