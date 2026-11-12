"""Invented CVs and letters of several lengths, and how full a PDF's pages are (G49, G50, #236).

Imported by name, not from conftest (#93). The fill of a page is read with pdftotext -bbox-layout: lines that recur
at the same height on several pages (running header, footer, page number) are not content. The content area is
measured on the document itself: from the highest content line on a following page to the lowest on a full page.
"""
import copy
import dataclasses
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET

import yaml
from pypdf import PdfReader

import build

DATA = build.ROOT / "data"
NS = {"x": "http://www.w3.org/1999/xhtml"}
DIGITS = re.compile(r"\d+")
POSITION_TOLERANCE = 2.0  # pt: a footer line sits at the same height on every page
# The German section headings of themes/common.typ and the Register design
HEADINGS = {h.casefold() for h in ("Profil", "Berufserfahrung", "Projekte", "Weitere Projekte", "Fähigkeiten",
                                   "Lehre & Training", "Sprachen", "Interessen", "Bildung & Weiterbildung",
                                   "Referenzen")}
CONTINUED = "Fortsetzung"
MIN_FILL_RULE = 1 / 3  # G49, measured in the PDF; page_fill.MIN_FILL is the same rule inside the build
MIN_BODY_SIZE = 10.0  # pt, G53: body text never smaller, also when page fill tightens
CV_BODY = "Aufbau und Betrieb einer Auswertung"  # the invented highlights of station()
LETTER_BODY = "In meiner letzten Stelle"  # the invented paragraphs of letter_of_length()


@dataclasses.dataclass(frozen=True)
class Line:
    page: int
    top: float
    bottom: float
    text: str


def example_cv() -> dict:
    return yaml.safe_load((DATA / "beispiel.yaml").read_text(encoding="utf-8"))


def example_letter() -> dict:
    return yaml.safe_load((DATA / "anschreiben-beispiel.yaml").read_text(encoding="utf-8"))


def station(number: int, highlights: int) -> dict:
    """An invented station; every highlight takes about one line."""
    return {"position": f"Projektleiterin Daten {number}", "name": f"Muster Informatik {number} AG", "location": "Bern",
            "startDate": f"{2000 + number % 20}-01", "endDate": f"{2001 + number % 20}-12",
            "highlights": [f"Aufbau und Betrieb einer Auswertung für den Bereich {number}.{k}, mit Berichten fürs Team"
                           for k in range(highlights)]}


def cv_of_length(units: int) -> dict:
    """The example CV with `units` more lines of experience: a station per four units, the rest as highlights."""
    cv = copy.deepcopy(example_cv())
    stations = [station(number, 3) for number in range(units // 4)]
    if units % 4:
        stations.append(station(99, units % 4))
    cv["work"] = cv["work"] + stations
    return cv


def letter_of_length(paragraphs: int) -> dict:
    """The example letter with more paragraphs of invented text."""
    letter = copy.deepcopy(example_letter())
    sentence = ("In meiner letzten Stelle habe ich Auswertungen für mehrere Bereiche aufgebaut und die Zahlen so "
                "aufbereitet, dass das Team sie ohne Rückfragen nutzen konnte. ")
    letter["text"] = letter["text"].rstrip() + "".join("\n\n" + sentence * 3 for _ in range(paragraphs))
    return letter


def lines(pdf) -> list[Line]:
    tool = shutil.which("pdftotext")
    assert tool, "pdftotext (poppler) is needed to measure the pages"
    xhtml = subprocess.run([tool, "-bbox-layout", "-enc", "UTF-8", str(pdf), "-"], capture_output=True, text=True,
                           check=True).stdout
    root = ET.fromstring(xhtml)
    found = []
    for number, page in enumerate(root.iter("{http://www.w3.org/1999/xhtml}page"), 1):
        for line in page.iter("{http://www.w3.org/1999/xhtml}line"):
            words = [w.text or "" for w in line.iter("{http://www.w3.org/1999/xhtml}word")]
            found.append(Line(number, float(line.get("yMin")), float(line.get("yMax")), " ".join(words)))
    return found


def _recurring(all_lines: list[Line]) -> set[Line]:
    """Lines at the same height with the same text, digits aside, on more than one page: header and footer."""
    def key(line: Line) -> str:
        return DIGITS.sub("#", line.text)
    pages = {}
    for line in all_lines:
        pages.setdefault(key(line), []).append(line)
    result = set()
    for same in pages.values():
        for line in same:
            if any(o.page != line.page and abs(o.top - line.top) <= POSITION_TOLERANCE for o in same):
                result.add(line)
    return result


def content_lines(pdf, first_page: int = 1, last_page: int | None = None) -> list[Line]:
    """The lines of pages first_page to last_page (a part inside the dossier) without header and footer, in page
    and height order."""
    every = lines(pdf)
    last = last_page or max(line.page for line in every)
    chosen = [line for line in every if first_page <= line.page <= last]
    recurring = _recurring(chosen)
    return sorted((line for line in chosen if line not in recurring), key=lambda line: (line.page, line.top))


def last_page_fill(pdf, first_page: int = 1, last_page: int | None = None) -> float | None:
    """How much of the last page's content area holds content, 0 to 1; None for a single page."""
    content = content_lines(pdf, first_page, last_page)
    last = max(line.page for line in content)
    if last == first_page:
        return None
    following = [line.top for line in content if line.page > first_page]
    full = [line.bottom for line in content if line.page < last]
    top, bottom = min(following), max(full)
    on_last = [line.bottom for line in content if line.page == last]
    return (max(on_last) - top) / (bottom - top) if on_last else 0.0


def text_sizes(pdf, marker: str, first_page: int = 1, last_page: int | None = None) -> list[float]:
    """The font sizes in pt, as printed, of the text runs that start with marker on pages first_page to last_page."""
    pages = PdfReader(pdf).pages
    sizes = []

    def visit(text, cm, tm, font, size):
        if text.strip().startswith(marker):
            sizes.append(round(size * abs(tm[3] * cm[3]), 2))

    for page in pages[first_page - 1:last_page or len(pages)]:
        page.extract_text(visitor_text=visit)
    return sizes


def page_count(pdf) -> int:
    return max(line.page for line in lines(pdf))


def is_heading(line: Line) -> bool:
    """A section heading as the themes write it, also in capitals or continued."""
    text = line.text.removesuffix(f"({CONTINUED})").strip().casefold()
    return text in HEADINGS


def lone_headings(content: list[Line]) -> list[Line]:
    """Headings that are the last line of their page: their first entry went to the next page."""
    last_of_page = {}
    for line in content:
        last_of_page[line.page] = line
    return [line for line in last_of_page.values() if is_heading(line)]


def section_pages(content: list[Line], heading: str) -> set[int]:
    """The pages a section spans in a one-column layout: from its heading to the next heading."""
    start = next((i for i, line in enumerate(content) if is_heading(line) and line.text.casefold() == heading.casefold()),
                 None)
    if start is None:
        return set()
    end = next((i for i in range(start + 1, len(content)) if is_heading(content[i])), len(content))
    return {line.page for line in content[start:end]}


def thin_continuations(content: list[Line]) -> list[Line]:
    """Continued headings followed by fewer than two lines on their page."""
    thin = []
    for i, line in enumerate(content):
        if not line.text.endswith(f"({CONTINUED})"):
            continue
        after = [o for o in content[i + 1:] if o.page == line.page]
        until = next((k for k, o in enumerate(after) if is_heading(o)), len(after))
        if until < 2:
            thin.append(line)
    return thin
