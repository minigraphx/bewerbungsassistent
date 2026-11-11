"""Mark and accent colour of the dossier, once per person (G18, docs/design/monogramm.md, option B).

Stored in cv.yaml under `basics` next to the photo: `x-zeichen`, `x-akzent`, `x-logo` and `x-monogramm`, written
with ruamel.yaml so comments and order stay, and with drafts before and after. Every choice is saved at once.
`lebenslauf/mark.py` holds the rules; this file reads and writes them for the page. The logo never goes to the AI.
"""
import hashlib
import io
import pathlib

import yaml
from ruamel.yaml.comments import CommentedMap

import pfade  # noqa: F401  (makes the module lebenslauf importable)
import dossier_data
import fotoausschnitt
import logo_file
import mark
from dateien import im_ordner, relativ, schreibe_atomar

CV = "cv.yaml"
LOGO_FOLDER = "logos"
HASH_DIGITS = 12

NO_CV = "Es gibt noch keinen Lebenslauf. Bitte zuerst die Angaben erfassen."
NO_LOGO = "Zuerst ein Logo wählen."
BAD_INITIALS = "Initialen: 1 bis 3 Buchstaben."
SAVED = {
    "zeichen": "Zeichen gespeichert. Mit «Unterlagen erstellen» entsteht das Dossier im neuen Zeichen.",
    "akzent": "Akzentfarbe gespeichert. Mit «Unterlagen erstellen» entsteht das Dossier in der neuen Farbe.",
    "initialen": "Initialen gespeichert. Mit «Unterlagen erstellen» entsteht das Dossier mit den neuen Initialen.",
    "logo": "Logo gespeichert. Mit «Unterlagen erstellen» entsteht das Dossier mit dem Logo.",
}
LOGO_REMOVED = "Logo entfernt. Das Dossier zeigt wieder die Initialen."
RESET = "Zeichen und Farbe stehen wieder auf «Passend zum Design»."
DRAFT = "Zeichen und Farbe des Dossiers"


def _cv(k) -> pathlib.Path:
    path = k.daten / CV
    if not path.is_file():
        raise ValueError(NO_CV)
    return path


def basics(daten: pathlib.Path) -> dict:
    try:
        found = (yaml.safe_load((daten / CV).read_text(encoding="utf-8")) or {}).get("basics")
    except (OSError, yaml.YAMLError, AttributeError):
        return {}
    return found if isinstance(found, dict) else {}


def write_basics(path: pathlib.Path, changes: dict) -> None:
    """Set keys under `basics` in cv.yaml, None removes one; comments and order of the file stay."""
    y = fotoausschnitt._yaml()
    document = y.load(path.read_text(encoding="utf-8")) or CommentedMap()
    if document.get("basics") is None:
        document["basics"] = CommentedMap()
    for key, value in changes.items():
        if value is None:
            document["basics"].pop(key, None)
        else:
            document["basics"][key] = value
    out = io.StringIO()
    y.dump(document, out)
    schreibe_atomar(path, out.getvalue().encode("utf-8"))


def _initials(raw: object) -> str | None:
    """None for empty (from the name), otherwise 1 to 3 letters."""
    text = str(raw or "").strip()
    if not text:
        return None
    if not text.isalpha() or not 1 <= len(text) <= dossier_data.MAX_MONOGRAM:
        raise ValueError(BAD_INITIALS)
    return text


def _monogram(found: dict) -> str:
    try:
        return dossier_data.monogram(found)
    except ValueError:
        return ""


def _variant(found: dict) -> str:
    try:
        return mark.variant(found.get("x-zeichen"))
    except ValueError:
        return mark.FITTING  # the file is data the person may have edited


def _accent(found: dict) -> str:
    try:
        return mark.stored_accent(found.get("x-akzent"))
    except ValueError:
        return mark.FITTING


def logo_info(k, path: pathlib.Path) -> dict:
    """Pixels, transparency, hints and the logo's colour; rendered once per file content."""
    data = path.read_bytes()
    key = ("logo", hashlib.sha256(data).hexdigest())
    if key not in k.cache:
        extension = "jpg" if path.suffix.lower() == ".jpeg" else path.suffix.lower().lstrip(".")
        k.cache[key] = logo_file.inspect(extension, data, k.build)
    return {**k.cache[key], "datei": relativ(path, k.daten), "version": key[1][:HASH_DIGITS]}


def state_of_logo(daten: pathlib.Path) -> str:
    """„fehlt“ when the logo is the chosen mark but its file is gone, else „gut“ or „ohne“."""
    found = basics(daten)
    if _variant(found) != mark.LOGO:
        return "ohne"
    return "gut" if mark.logo_file(found, daten) else "fehlt"


def state(k) -> dict:
    found = basics(k.daten)
    variant = _variant(found)
    logo = mark.logo_file(found, k.daten)
    return {
        "zeichen": variant,
        "initialen": str(found.get("x-monogramm") or ""),
        "initialen_wirksam": _monogram(found),
        "akzent": _accent(found),
        "logo": logo_info(k, logo) if logo else None,
        "logo_fehlt": variant == mark.LOGO and logo is None,
        "lebenslauf": (k.daten / CV).is_file(),
    }


def _checked(k, body: dict) -> dict:
    """The changes a body asks for, as cv.yaml keys; ValueError with the reason for the person."""
    found = basics(k.daten)
    changes = {}
    if "initialen" in body:
        changes["x-monogramm"] = _initials(body["initialen"])
    if "zeichen" in body:
        chosen = mark.variant(body["zeichen"])
        if chosen == mark.LOGO and mark.logo_file(found, k.daten) is None:
            raise ValueError(NO_LOGO)
        initials = _monogram({**found, "x-monogramm": changes.get("x-monogramm", found.get("x-monogramm"))})
        if chosen == mark.TWO_LETTERS_ONLY and len(initials) != 2:
            raise ValueError(mark.NEEDS_TWO)
        changes["x-zeichen"] = None if chosen == mark.FITTING else chosen
    if "akzent" in body:
        chosen = mark.stored_accent(body["akzent"])
        changes["x-akzent"] = None if chosen == mark.FITTING else chosen
    return changes


def save(k, body) -> dict:
    if not isinstance(body, dict):
        raise ValueError("Zeichen, Initialen oder Akzentfarbe erwartet")
    path = _cv(k)
    changes = _checked(k, body)
    if changes:
        k.mit_entwurf(path, DRAFT, lambda: write_basics(path, changes))
    what = next((field for field in ("zeichen", "akzent", "initialen") if field in body), "zeichen")
    return {**state(k), "meldung": SAVED[what]}


def upload(k, data: bytes) -> dict:
    """Store the logo under logos/ with a hash in its name, so an upload never overwrites, and make it the mark."""
    path = _cv(k)
    extension, clean = logo_file.cleaned(data)
    logo_file.inspect(extension, clean, k.build)  # Typst must read it, as the dossier will
    name = f"{LOGO_FOLDER}/logo-{hashlib.sha256(clean).hexdigest()[:HASH_DIGITS]}.{extension}"
    target = im_ordner(k.daten, name)

    def write() -> None:
        if not target.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            schreibe_atomar(target, clean)
        write_basics(path, {"x-logo": name, "x-zeichen": mark.LOGO})

    k.mit_entwurf(path, f"{DRAFT}: Logo", write)
    return {**state(k), "meldung": SAVED["logo"]}


def remove_logo(k) -> dict:
    """The mark goes back to the initials; the file stays, for drafts and versions that name it."""
    path = _cv(k)
    found = basics(k.daten)
    changes = {"x-logo": None, **({"x-zeichen": None} if _variant(found) == mark.LOGO else {})}
    k.mit_entwurf(path, f"{DRAFT}: Logo entfernt", lambda: write_basics(path, changes))
    return {**state(k), "meldung": LOGO_REMOVED}


def reset(k) -> dict:
    """Mark and colour back to „Passend zum Design“; initials and logo stay for a later choice."""
    path = _cv(k)
    k.mit_entwurf(path, f"{DRAFT}: Voreinstellung", lambda: write_basics(path, {"x-zeichen": None, "x-akzent": None}))
    return {**state(k), "meldung": RESET}


def logo_bytes(k) -> tuple[str, bytes]:
    """The logo cv.yaml names, for the page's <img>; KeyError when there is none."""
    logo = mark.logo_file(basics(k.daten), k.daten)
    if logo is None:
        raise KeyError(NO_LOGO)
    types = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".svg": "image/svg+xml"}
    return types[logo.suffix.lower()], logo.read_bytes()
