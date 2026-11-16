"""Photo, colour and mark of one CV created in „Lebenslauf erstellen“ (G77, #295).

Chosen under «Aussehen» beside the design and saved with the variant: in its tailoring `jobs/<variant>.yaml` as
`aussehen`, which lebenslauf/tailor.py does not read. Every build of that tailoring (unterlagen.py, also the preview
of G76) passes it to lebenslauf/build.py: the photo before the switch on „Lebenslauf und Dateien“, colour and mark as
--akzent and --zeichen. Tailorings without it, Claude's variants and the whole CV build as before.

The defaults are those of „Lebenslauf und Dateien“: the photo as „Im Lebenslauf zeigen“ says (G62), colour and mark
„Passend zum Design“, which for the CV designs means their own colours and no mark. A dossier takes the photo from
here; its colour and mark stay the ones for all dossiers (G18).
"""
import dataclasses
import pathlib

import yaml

import pfade  # noqa: F401  (makes the module lebenslauf importable)
import dossier_data
import mark
import photo_shown

KEY = "aussehen"
FITTING = mark.FITTING
BAD_LOOK = "Das Aussehen fehlt: Foto, Zeichen und Farbe."
BAD_PHOTO = "Bitte wählen: mit Foto oder ohne."
NO_LOGO = "Zuerst ein Logo wählen, unter «Dossier gestalten»."
NEEDS_TWO = "«Verschränkt» geht nur mit genau zwei Initialen."


@dataclasses.dataclass(frozen=True)
class Look:
    photo: bool
    mark: str = FITTING
    accent: str = FITTING


def _basics(cv: dict) -> dict:
    return cv.get("basics") if isinstance(cv.get("basics"), dict) else {}


def _initials(cv: dict) -> str:
    try:
        return dossier_data.monogram(_basics(cv))
    except ValueError:
        return ""


def defaults(data_dir: pathlib.Path) -> Look:
    return Look(photo=photo_shown.load(data_dir))


def offer(data_dir: pathlib.Path, cv: dict) -> dict:
    """What the page can offer: whether there is a photo, the initials a mark shows, and whether a logo is there."""
    basics = _basics(cv)
    return {"foto_vorhanden": bool(basics.get("image")), "initialen": _initials(cv),
            "logo": mark.logo_file(basics, data_dir) is not None}


def parse(value: object, cv: dict, data_dir: pathlib.Path) -> Look:
    """The look as the page sends it, the defaults when it sends none; ValueError with a German message."""
    if value is None:
        return defaults(data_dir)
    if not isinstance(value, dict):
        raise ValueError(BAD_LOOK)
    photo = value.get("foto")
    if not isinstance(photo, bool):
        raise ValueError(BAD_PHOTO)
    chosen = mark.variant(value.get("zeichen"))
    if chosen == mark.LOGO and mark.logo_file(_basics(cv), data_dir) is None:
        raise ValueError(NO_LOGO)
    if chosen == mark.TWO_LETTERS_ONLY and len(_initials(cv)) != 2:
        raise ValueError(NEEDS_TWO)
    return Look(photo=photo, mark=chosen, accent=mark.stored_accent(value.get("akzent")))


def stored(look: Look) -> dict:
    """For the tailoring and the page."""
    return {"foto": look.photo, "zeichen": look.mark, "akzent": look.accent}


def of_job(job: object) -> Look | None:
    """The look a tailoring holds; None without one, or when it was changed by hand into something not drawable."""
    value = job.get(KEY) if isinstance(job, dict) else None
    if not isinstance(value, dict) or not isinstance(value.get("foto"), bool):
        return None
    try:
        return Look(photo=value["foto"], mark=mark.variant(value.get("zeichen")),
                    accent=mark.stored_accent(value.get("akzent")))
    except ValueError:
        return None


def of_file(path: pathlib.Path | None) -> Look | None:
    try:
        return of_job(yaml.safe_load(path.read_text(encoding="utf-8"))) if path and path.is_file() else None
    except (OSError, yaml.YAMLError):
        return None


def photo_arguments(look: Look | None, data_dir: pathlib.Path) -> list[str]:
    """This CV's photo goes before the switch on „Lebenslauf und Dateien“ (G62), which counts for all others."""
    if look is None:
        return photo_shown.build_arguments(data_dir)
    return [] if look.photo else [photo_shown.WITHOUT_PHOTO]


def mark_arguments(look: Look | None) -> list[str]:
    """Colour and mark for lebenslauf/build.py; nothing for „Passend zum Design“."""
    if look is None:
        return []
    return [*(["--zeichen", look.mark] if look.mark != FITTING else []),
            *(["--akzent", look.accent] if look.accent != FITTING else [])]
