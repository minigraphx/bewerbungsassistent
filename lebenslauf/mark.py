"""Mark and accent colour of the dossier (G18, docs/design/monogramm.md): which variant, which colour, and the checks.

The choice is stored once per person in cv.yaml under `basics`: `x-zeichen` (variant), `x-akzent` (`passend` or a
colour), `x-logo` (an image in the data folder) and the existing `x-monogramm`. Without a choice every design shows
its own mark in its own main colour. The contrast rules are the same in bewerbungen/seiten/zeichen-logik.js; the
shared cases are in tests/accent_cases.json.
"""
import math
import pathlib
import re

FITTING = "passend"
VARIANTS = (FITTING, "ring", "block", "verschraenkt", "linie", "punkt", "logo")
LOGO = "logo"
TWO_LETTERS_ONLY = "verschraenkt"
NEEDS_TWO = "Nur mit zwei Buchstaben"

# Main colour of each design: „Passend zum Design“ is this colour (decision of 10.11.2026)
MAIN_COLOURS = {"dossier-siegel": "#38495d", "dossier-raster": "#7a2e3a", "dossier-register": "#2f5d50"}
SWATCHES = (
    ("Schieferblau", "#38495d"), ("Weinrot", "#7a2e3a"), ("Tannengrün", "#2f5d50"), ("Petrol", "#1d5c6b"),
    ("Aubergine", "#5b3f6b"), ("Bronze", "#7a5418"), ("Graphit", "#3a3d42"),
)
LOGO_SUFFIXES = (".png", ".jpg", ".jpeg", ".svg")

PAPER = "#fdfcfa"
WHITE = "#ffffff"
TEXT_STRONG = "#27333f"
MIN_TEXT = 4.5  # text on the colour
MIN_PAPER = 3.0  # rings, lines and dots on the paper
LIGHTNESS_STEP = 0.01

COLOUR = re.compile(r"#[0-9a-f]{6}")
BAD_COLOUR = "Bitte eine Farbe wie #38495d eingeben."
BAD_VARIANT = "Unbekanntes Zeichen: {value!r}. Erlaubt: " + ", ".join(VARIANTS)
SVG_REMOTE = "Dieses SVG lädt Inhalte aus dem Internet. Bitte das Logo als PNG speichern und nochmals wählen."
SVG_SCRIPT = "Dieses SVG enthält ein Skript. Bitte das Logo als PNG speichern und nochmals wählen."
# Scripts, event handlers and embedded HTML; and anything fetched from outside: links, url(), @import, entities
SVG_ACTIVE = re.compile(r"<\s*(?:script|foreignObject)\b|\son[a-z]+\s*=|javascript:", re.IGNORECASE)
SVG_OUTSIDE = re.compile(r"(?:href|src)\s*=\s*[\"']\s*(?!#|data:)|url\(\s*[\"']?\s*(?!#|data:)[^)\s]"
                         r"|@import|<!ENTITY|\bSYSTEM\b", re.IGNORECASE)
TOO_LIGHT = "Zu hell: Ring, Linien und Punkte wären auf dem Papier kaum zu sehen. Gespeichert wird diese Farbe nicht."
MID_TONE = "Weder weisse noch dunkle Schrift ist auf dieser Farbe gut lesbar. Gespeichert wird sie nicht."


def colour(value: object) -> str:
    """A colour as lowercase #rrggbb; ValueError with the message for the person otherwise."""
    text = str(value or "").strip().lower()
    if not COLOUR.fullmatch(text):
        raise ValueError(BAD_COLOUR)
    return text


def _channels(value: str) -> tuple[float, float, float]:
    return tuple(int(value[i:i + 2], 16) / 255 for i in (1, 3, 5))


def _linear(v: float) -> float:
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def luminance(value: str) -> float:
    r, g, b = _channels(value)
    return 0.2126 * _linear(r) + 0.7152 * _linear(g) + 0.0722 * _linear(b)


def contrast(a: str, b: str) -> float:
    la, lb = luminance(a), luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def text_on(value: str) -> str:
    """White or text-strong on the colour, whichever reads better (as `on-accent` in themes/tokens.typ)."""
    return WHITE if contrast(value, WHITE) >= contrast(value, TEXT_STRONG) else TEXT_STRONG


def readable(value: str) -> bool:
    return contrast(value, text_on(value)) >= MIN_TEXT and contrast(value, PAPER) >= MIN_PAPER


def _to_hsl(value: str) -> tuple[float, float, float]:
    r, g, b = _channels(value)
    high, low = max(r, g, b), min(r, g, b)
    lightness = (high + low) / 2
    if high == low:
        return 0.0, 0.0, lightness
    span = high - low
    saturation = span / (2 - high - low) if lightness > 0.5 else span / (high + low)
    if high == r:
        hue = ((g - b) / span) % 6
    elif high == g:
        hue = (b - r) / span + 2
    else:
        hue = (r - g) / span + 4
    return hue / 6, saturation, lightness


def _from_hsl(hue: float, saturation: float, lightness: float) -> str:
    chroma = (1 - abs(2 * lightness - 1)) * saturation
    sector = hue * 6
    second = chroma * (1 - abs(sector % 2 - 1))
    r, g, b = [(chroma, second, 0), (second, chroma, 0), (0, chroma, second), (0, second, chroma),
               (second, 0, chroma), (chroma, 0, second)][int(sector) % 6]
    base = lightness - chroma / 2
    return "#" + "".join(f"{math.floor((v + base) * 255 + 0.5):02x}" for v in (r, g, b))


def darker(value: str) -> str:
    """The same colour with less lightness until text on it and the colour on the paper both read well."""
    hue, saturation, lightness = _to_hsl(value)
    while lightness > 0:
        candidate = _from_hsl(hue, saturation, lightness)
        if readable(candidate):
            return candidate
        lightness -= LIGHTNESS_STEP
    return _from_hsl(hue, saturation, 0)


def accent_check(value: object) -> dict:
    """{farbe, ok, schrift: weiss|dunkel, problem: None|zu-hell|mittelton, meldung, vorschlag} for an own colour."""
    checked = colour(value)
    on = "weiss" if text_on(checked) == WHITE else "dunkel"
    if readable(checked):
        return {"farbe": checked, "ok": True, "schrift": on, "problem": None, "meldung": "", "vorschlag": None}
    problem = "zu-hell" if contrast(checked, PAPER) < MIN_PAPER else "mittelton"
    return {"farbe": checked, "ok": False, "schrift": on, "problem": problem,
            "meldung": TOO_LIGHT if problem == "zu-hell" else MID_TONE, "vorschlag": darker(checked)}


def svg_problem(text: str) -> str | None:
    """Why an SVG may not be the logo, or None: no script and nothing loaded from outside."""
    if SVG_ACTIVE.search(text):
        return SVG_SCRIPT
    if SVG_OUTSIDE.search(text):
        return SVG_REMOTE
    return None


def variant(value: object) -> str:
    chosen = FITTING if value in (None, "") else value
    if chosen not in VARIANTS:
        raise ValueError(BAD_VARIANT.format(value=value))
    return chosen


def stored_accent(value: object) -> str:
    """`passend` or a readable colour; a colour that fails the rules is refused, never stored."""
    if value in (None, "", FITTING):
        return FITTING
    check = accent_check(value)
    if not check["ok"]:
        raise ValueError(f"{check['meldung']} Vorschlag {check['vorschlag']}.")
    return check["farbe"]


def accent_for(basics: dict, cover_design: str) -> str:
    """The accent colour of the whole dossier: the chosen one, otherwise the main colour of the cover's design."""
    chosen = stored_accent(basics.get("x-akzent"))
    return MAIN_COLOURS.get(cover_design, MAIN_COLOURS["dossier-siegel"]) if chosen == FITTING else chosen


def logo_file(basics: dict, base: pathlib.Path) -> pathlib.Path | None:
    """The logo cv.yaml names, inside the folder of cv.yaml and of a known format; None when it is missing."""
    name = basics.get("x-logo")
    if not isinstance(name, str) or not name:
        return None
    root = base.resolve()
    path = (root / name).resolve()
    if not path.is_relative_to(root) or path.suffix.lower() not in LOGO_SUFFIXES or not path.is_file():
        return None
    if path.suffix.lower() == ".svg" and svg_problem(path.read_text(encoding="utf-8", errors="replace")):
        return None  # refused on upload; a file changed by hand later is not drawn either
    return path


def settings(basics: dict, base: pathlib.Path, monogram: str) -> dict:
    """What the designs draw: {variant, logo (path or None), logo-missing}. A chosen logo that is gone falls back to
    the mark of each design, and the check says so; „Verschränkt“ without exactly two letters does the same."""
    chosen = variant(basics.get("x-zeichen"))
    if chosen == LOGO:
        logo = logo_file(basics, base)
        return {"variant": FITTING if logo is None else LOGO, "logo": logo, "logo-missing": logo is None}
    if chosen == TWO_LETTERS_ONLY and len(monogram) != 2:
        chosen = FITTING
    return {"variant": chosen, "logo": None, "logo-missing": False}
