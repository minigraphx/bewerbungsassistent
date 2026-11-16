"""Colour and mark of one CV (G77, #295), chosen in „Lebenslauf erstellen“ and given to build.py as --akzent and --zeichen.

build.py writes them into cv.json as `x-aussehen`; the CV designs draw the colour on their lines and headings and the
mark small in the footer of every page (themes/cv-look.typ). Without the options nothing is written, so every other
CV keeps its design's colours and no mark: the mark and colour cv.yaml holds for the dossier (G18) are not read here,
only its initials and its logo file. The rules for colours and marks are those of the dossier (mark.py).
"""
import pathlib

import yaml

import dossier_data
import mark

FIELD = "x-aussehen"


def _monogram(data_path: pathlib.Path, basics: dict) -> str:
    """The initials as cv.yaml writes them (#248); none when the field holds something else."""
    text = data_path.read_text(encoding="utf-8")
    written = dossier_data.with_written_monogram({"basics": basics}, text)["basics"]
    try:
        return dossier_data.monogram(written)
    except ValueError:
        return ""


def chosen(data_path: pathlib.Path, zeichen: str | None, akzent: str | None) -> dict:
    """What the options ask for: {akzent: colour} and {zeichen: {variant, logo (path or None), monogram}}, each only
    when it is not „passend“. A logo whose file is gone, or „Verschränkt“ without two letters, leaves the mark out.
    ValueError with the message for the person for a colour that does not read well."""
    found: dict = {}
    accent = mark.stored_accent(akzent.strip().lower() if akzent else None)
    if accent != mark.FITTING:
        found["akzent"] = accent
    if mark.variant(zeichen) == mark.FITTING:
        return found
    cv = yaml.safe_load(data_path.read_text(encoding="utf-8")) or {}
    basics = cv.get("basics") if isinstance(cv.get("basics"), dict) else {}
    monogram = _monogram(data_path, basics)
    settings = mark.settings({**basics, "x-zeichen": zeichen}, data_path.parent, monogram)
    if settings["variant"] != mark.FITTING:
        found["zeichen"] = {"variant": settings["variant"], "logo": settings["logo"], "monogram": monogram}
    return found


def logo_of(look: dict) -> pathlib.Path | None:
    """The logo file the mark draws, which Typst must be able to read."""
    return (look.get("zeichen") or {}).get("logo")


def with_look(cv: dict, look: dict, typst_path) -> dict:
    """A new cv with the look for the theme, the logo as a path Typst reads; the cv as it is without a look."""
    if not look:
        return cv
    drawn = dict(look)
    if "zeichen" in look:
        logo = look["zeichen"]["logo"]
        drawn["zeichen"] = {**look["zeichen"], "logo": typst_path(logo) if logo is not None else None}
    return {**cv, FIELD: drawn}
