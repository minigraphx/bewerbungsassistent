"""The design the app builds the CV with (G61, #280), chosen with „Aussehen wählen“ on „Lebenslauf und Dateien“.

Once per person in `aussehen.yaml` of the data folder, with drafts before and after. Every build resolves it anew, so
new applications take it, while PDFs already built or sent stay as they are. An application with a design of its own
(`lebenslauf_design` in the register, G17) keeps that one.

Only the designs that build a CV on their own count here; Siegel, Raster and Register need a letter, so they stay the
dossier's design per application (G39).
"""
import pathlib

import yaml

from dateien import schreibe_atomar
from register import CV_DESIGNS

FILE = "aussehen.yaml"
KEY = "lebenslauf"
PRESET = CV_DESIGNS[0]
NAMES = {"zweispaltig": "Zweispaltig", "einspaltig": "Einspaltig"}
HEADER = "# Aussehen des Lebenslaufs, gewählt unter „Lebenslauf und Dateien“. Geschrieben vom Bewerbungsbegleiter.\n"
UNKNOWN = f"Bitte {' oder '.join(NAMES[name] for name in CV_DESIGNS)} wählen."
DRAFT = "Aussehen des Lebenslaufs"


def parse(value: object) -> str:
    """A design as the page sends it; ValueError with a German message."""
    if not isinstance(value, str) or value not in CV_DESIGNS:
        raise ValueError(UNKNOWN)
    return value


def load(data_dir: pathlib.Path) -> str:
    """The person's choice; without one, or with one this app does not know, the preset."""
    try:
        stored = yaml.safe_load((data_dir / FILE).read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return PRESET
    value = stored.get(KEY) if isinstance(stored, dict) else None
    return value if value in CV_DESIGNS else PRESET


def save(data_dir: pathlib.Path, design: str) -> str:
    """Write the choice; drafts are the caller's (`Kontext.mit_entwurf`)."""
    chosen = parse(design)
    schreibe_atomar(data_dir / FILE, (HEADER + yaml.safe_dump({KEY: chosen}, allow_unicode=True)).encode("utf-8"))
    return chosen


def for_application(data_dir: pathlib.Path, entry: dict) -> str:
    """The design one application's CV is built with: its own, otherwise the person's."""
    own = entry.get("lebenslauf_design")
    return own if own in CV_DESIGNS else load(data_dir)


def theme_arguments(design: str) -> list[str]:
    """For lebenslauf/build.py, whose themes carry the same names."""
    return ["--theme", design]
