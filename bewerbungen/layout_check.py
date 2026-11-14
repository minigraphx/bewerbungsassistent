"""What the check before sending measures in a generated PDF (G52, #237), beside the page count of pruefung.py.

- Fill of the last page (G49): a part over more than one page fills its last page to at least a third. Measured like
  lebenslauf/tests/page_fill_samples.py: header and footer (the same text at the same height on several pages) do
  not count, the content area runs from the highest content line on a following page to the lowest on a full one.
- Lone headings (G50): a section heading with nothing under it in its column on the same page.
- Text outside the type area: text that reaches closer to the edge of the page than SAFE_MARGIN, or past it. The
  designs keep 27 pt or more; the PDF does not say where a design's own margins are, so this is the line no design
  crosses on purpose.
- Overlapping elements: text printed over other text, or text that runs across the edge of an image. Text wholly on
  an image (a label on a picture) is left alone. Overlap is measured on the cap height above the baseline, because
  the font boxes of tightly set lines touch without any letters touching.

The builds already avoid all of this (lebenslauf/page_fill.py); the check is the net for what slips through.
"""
import dataclasses
import pathlib
import re
from collections.abc import Iterable

import pdf_boxes

MIN_FILL = 1 / 3
SAFE_MARGIN = 20.0  # pt, about 7 mm
CAP_HEIGHT = 0.7  # of the font size: the height of capitals above the baseline
MIN_OVERLAP = 1.0  # pt in both directions; less is rounding
POSITION_TOLERANCE = 2.0  # pt: a footer line sits at the same height on every page
SHOWN_CHARACTERS = 40
DIGITS = re.compile(r"\d+")
# The section headings of lebenslauf/themes/common.typ (de and en) and of the Register design
HEADINGS = ("Profil", "Berufserfahrung", "Projekte", "Weitere Projekte", "Fähigkeiten", "Lehre & Training",
            "Sprachen", "Interessen", "Bildung & Weiterbildung", "Referenzen",
            "Profile", "Experience", "Projects", "Further projects", "Skills", "Teaching & training", "Languages",
            "Interests", "Education & training")
CONTINUED = ("(Fortsetzung)", "(continued)")
FILLED_PARTS = ("lebenslauf", "anschreiben")  # the dossier is measured as its two parts, built beside it
HEADED_PARTS = ("lebenslauf", "dossier")


@dataclasses.dataclass(frozen=True)
class Breach:
    page: int
    rule: str  # fuellung | ueberschrift | rand | ueberlappung
    reason: str


def check(pdf: pathlib.Path, part: str, headings: Iterable[str] = ()) -> list[Breach]:
    """Every breach in one generated PDF; `headings` adds the CV's own section headings to the known ones."""
    pages = pdf_boxes.read(pdf)
    found = []
    if part in FILLED_PARTS:
        found += _fill(pages)
    if part in HEADED_PARTS:
        found += _lone_headings(pages, {_folded(h) for h in (*HEADINGS, *headings)})
    for page in pages:
        found += _outside(page) + _overlaps(page)
    return found


def _shown(text: str) -> str:
    text = " ".join(text.split())
    return text if len(text) <= SHOWN_CHARACTERS else text[:SHOWN_CHARACTERS - 1] + "…"


def _folded(text: str) -> str:
    text = " ".join(text.split())
    for suffix in CONTINUED:
        text = text.removesuffix(suffix).strip()
    return text.casefold()


def _content(pages: list[pdf_boxes.Page]) -> list[pdf_boxes.Box]:
    """The text of all pages without header and footer: the same text, digits aside, at the same height on more
    than one page."""
    boxes = [box for page in pages for box in page.text]
    by_text: dict[str, list[pdf_boxes.Box]] = {}
    for box in boxes:
        by_text.setdefault(DIGITS.sub("#", box.text), []).append(box)
    recurring = {id(box) for same in by_text.values() for box in same
                 if any(o.page != box.page and abs(o.top - box.top) <= POSITION_TOLERANCE for o in same)}
    return [box for box in boxes if id(box) not in recurring]


def _fill(pages: list[pdf_boxes.Page]) -> list[Breach]:
    content = _content(pages)
    if not content:
        return []
    first, last = min(box.page for box in content), max(box.page for box in content)
    if last == first:
        return []
    following = [box.top for box in content if box.page > first]
    full = [box.bottom for box in content if box.page < last]
    top, bottom = min(following), max(full)
    on_last = max(box.bottom for box in content if box.page == last)
    share = (on_last - top) / (bottom - top) if bottom > top else 1.0
    if share >= MIN_FILL:
        return []
    return [Breach(last, "fuellung", f"nur zu {round(max(share, 0) * 100)} % gefüllt, verlangt ist mindestens ein Drittel.")]


def _lone_headings(pages: list[pdf_boxes.Page], headings: set[str]) -> list[Breach]:
    content = _content(pages)
    found = []
    for box in content:
        if _folded(box.text) not in headings:
            continue
        below = [o for o in content if o.page == box.page and o.baseline > box.baseline + MIN_OVERLAP
                 and min(o.right, box.right) - max(o.left, box.left) > 0]
        if not below:
            found.append(Breach(box.page, "ueberschrift",
                                f"Die Überschrift «{_shown(box.text)}» steht allein am Ende der Seite."))
    return found


def _outside(page: pdf_boxes.Page) -> list[Breach]:
    outside = [box for box in page.text if box.left < SAFE_MARGIN or box.top < SAFE_MARGIN
               or box.right > page.width - SAFE_MARGIN or box.bottom > page.height - SAFE_MARGIN]
    return [Breach(page.number, "rand",
                   f"Text reicht bis an den Rand der Seite oder darüber hinaus («{_shown(box.text)}»).")
            for box in outside]


def _core(box: pdf_boxes.Box) -> tuple[float, float, float, float]:
    if box.is_image:
        return box.left, box.top, box.right, box.bottom
    return box.left, box.baseline - CAP_HEIGHT * box.size, box.right, box.baseline


def _overlap(a: tuple, b: tuple) -> bool:
    return (min(a[2], b[2]) - max(a[0], b[0]) > MIN_OVERLAP
            and min(a[3], b[3]) - max(a[1], b[1]) > MIN_OVERLAP)


def _inside(inner: tuple, outer: tuple) -> bool:
    return inner[0] >= outer[0] and inner[1] >= outer[1] and inner[2] <= outer[2] and inner[3] <= outer[3]


def _overlaps(page: pdf_boxes.Page) -> list[Breach]:
    found = []
    text = [(box, _core(box)) for box in page.text]
    for i, (a, core_a) in enumerate(text):
        for b, core_b in text[i + 1:]:
            if _overlap(core_a, core_b):
                found.append(Breach(page.number, "ueberlappung",
                                    f"Text liegt über anderem Text («{_shown(a.text)}» und «{_shown(b.text)}»)."))
    for image in page.images:
        frame = _core(image)
        for box, core in text:
            if _overlap(core, frame) and not _inside(core, frame):
                found.append(Breach(page.number, "ueberlappung",
                                    f"Text läuft über den Rand eines Bildes («{_shown(box.text)}»)."))
    return found
