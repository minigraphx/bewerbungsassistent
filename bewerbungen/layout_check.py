"""What the check before sending measures in a generated PDF (G52, #237), beside the page count of pruefung.py.

- Fill of the last page (G49): a part over more than one page fills its last page to at least a third. Measured like
  lebenslauf/tests/page_fill_samples.py: header and footer (the same text at the same height on several pages) do
  not count, the content area runs from the highest content line on a following page to the lowest on a full one.
- Lone headings (G50): a section heading with nothing under it in its column on the same page.
- Text outside the type area: text in a margin of the design, as the build passed it beside the PDF for each page
  (lebenslauf/type_area.py, #304). The footer, and a band at the foot a design declares, sit in the bottom margin on
  purpose; shapes and images reaching into the margins (bands, backgrounds) are not text and do not count. Text that
  reaches closer to the edge of the page than SAFE_MARGIN, or past it, counts always, also without known margins.
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
import pfade  # noqa: F401  (makes the module lebenslauf importable)
import type_area
from ui_message import T

MIN_FILL = 1 / 3
SAFE_MARGIN = 20.0  # pt, about 7 mm
CAP_HEIGHT = 0.7  # of the font size: the height of capitals above the baseline
MIN_OVERLAP = 1.0  # pt in both directions; less is rounding
MARGIN_TOLERANCE = 1.0  # pt: text set flush with a margin ends on it, give or take rounding
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
    reason: str  # a T, said in the app language by the route


def check(pdf: pathlib.Path, part: str, headings: Iterable[str] = ()) -> list[Breach]:
    """Every breach in one generated PDF; `headings` adds the CV's own section headings to the known ones."""
    pages = pdf_boxes.read(pdf)
    areas = type_area.read(pdf) or {}
    found = []
    if part in FILLED_PARTS:
        found += _fill(pages)
    if part in HEADED_PARTS:
        found += _lone_headings(pages, {_folded(h) for h in (*HEADINGS, *headings)})
    for page in pages:
        found += _outside(page, areas.get(page.number)) + _overlaps(page)
    return found


def lines_beyond(pdf: pathlib.Path, limit: int) -> int:
    """About how many lines a document has on the pages beyond `limit` (G92): the content lines there, header and
    footer aside, one per baseline; text at the same height, side by side in two columns, counts once. With the type
    area the build stored, header and footer are what lies outside it; without, the text that recurs (_content), which
    can also take out list lines alike but for their digits."""
    pages = pdf_boxes.read(pdf)
    areas = type_area.read(pdf)
    if areas:
        content = [box for page in pages if page.number > limit for box in page.text
                   if page.number in areas and _in_area(box, areas[page.number])]
    else:
        content = [box for box in _content(pages) if box.page > limit]
    baselines = sorted({(box.page, round(box.baseline)) for box in content})
    lines, last = 0, None
    for page, baseline in baselines:
        if last is None or page != last[0] or baseline - last[1] > POSITION_TOLERANCE:
            lines += 1
        last = (page, baseline)
    return lines


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


# Why a rule is broken, as T (#427): German as before, said in the app language by the route; the text quoted from the
# PDF stays as it is.


def fill_reason(share: float) -> T:
    return T("nur zu {prozent} % gefüllt, verlangt ist mindestens ein Drittel.", prozent=round(max(share, 0) * 100))


def lone_heading_reason(text: str) -> T:
    return T("Die Überschrift «{text}» steht allein am Ende der Seite.", text=_shown(text))


def edge_reason(text: str) -> T:
    return T("Text reicht bis an den Rand der Seite oder darüber hinaus («{text}»).", text=_shown(text))


def margin_reason(text: str) -> T:
    return T("Text ragt in den Rand des Designs hinein («{text}»).", text=_shown(text))


def overlap_reason(first: str, second: str) -> T:
    return T("Text liegt über anderem Text («{erster}» und «{zweiter}»).", erster=_shown(first), zweiter=_shown(second))


def image_edge_reason(text: str) -> T:
    return T("Text läuft über den Rand eines Bildes («{text}»).", text=_shown(text))


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
    return [Breach(last, "fuellung", fill_reason(share))]


def _lone_headings(pages: list[pdf_boxes.Page], headings: set[str]) -> list[Breach]:
    content = _content(pages)
    found = []
    for box in content:
        if _folded(box.text) not in headings:
            continue
        below = [o for o in content if o.page == box.page and o.baseline > box.baseline + MIN_OVERLAP
                 and min(o.right, box.right) - max(o.left, box.left) > 0]
        if not below:
            found.append(Breach(box.page, "ueberschrift", lone_heading_reason(box.text)))
    return found


def _outside(page: pdf_boxes.Page, area: dict | None) -> list[Breach]:
    found = []
    for box in page.text:
        if _at_edge(page, box):
            found.append(Breach(page.number, "rand", edge_reason(box.text)))
        elif area is not None and _in_margin(box, area):
            found.append(Breach(page.number, "rand", margin_reason(box.text)))
    return found


def _at_edge(page: pdf_boxes.Page, box: pdf_boxes.Box) -> bool:
    return (box.left < SAFE_MARGIN or box.top < SAFE_MARGIN
            or box.right > page.width - SAFE_MARGIN or box.bottom > page.height - SAFE_MARGIN)


def _in_margin(box: pdf_boxes.Box, area: dict) -> bool:
    """Text past one of the four margins of its page. Measured on the cap height like an overlap: the first line
    stands with its capitals, not with its font box, on the top margin."""
    left, top, right, bottom = _core(box)
    content_bottom = area["height"] - area["bottom"]
    in_footer = area["footer"] is not None and top >= area["footer"] - MARGIN_TOLERANCE
    return (left < area["left"] - MARGIN_TOLERANCE or right > area["width"] - area["right"] + MARGIN_TOLERANCE
            or top < area["top"] - MARGIN_TOLERANCE
            or (bottom > content_bottom + MARGIN_TOLERANCE and not in_footer))


def _in_area(box: pdf_boxes.Box, area: dict) -> bool:
    """Whether the baseline of `box` lies in the content area of its page, above the footer."""
    bottom = area["height"] - area["bottom"]
    if area["footer"] is not None:
        bottom = min(bottom, area["footer"])
    return area["top"] - MARGIN_TOLERANCE <= box.baseline <= bottom + MARGIN_TOLERANCE


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
                found.append(Breach(page.number, "ueberlappung", overlap_reason(a.text, b.text)))
    for image in page.images:
        frame = _core(image)
        for box, core in text:
            if _overlap(core, frame) and not _inside(core, frame):
                found.append(Breach(page.number, "ueberlappung", image_edge_reason(box.text)))
    return found
