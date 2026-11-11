"""No nearly empty last page (G49, #236): choose how dense a part is set before the PDF is written.

Every part (CV, letter) leaves markers (themes/page-fill.typ): its first page, and where its content ends within the
page's content area. When a part runs over more than one page and its last page is less than a third full, the build
tries both fixes within the design and takes the smaller change: tighter (spacing, leading, body size never below
9 pt) until the content fits on one page fewer, or wider spacing until the last page is full enough. No content is
removed; when neither works, the part stays as the design draws it.
"""
import dataclasses
import functools
import json
from collections.abc import Callable

import typst

MIN_FILL = 1 / 3
# The build aims a little higher than the rule: what a reader sees as the page ends at the last line, not at the
# margin, so a fill just above a third here can measure just below it in the PDF
AIM = 0.4
TIGHTER = (1, 2, 3, 4, 5)
WIDER = (-1, -2, -3, -4, -5)
SELECTOR = "<page-fill>"


@dataclasses.dataclass(frozen=True)
class Fill:
    pages: int
    last: float  # share of the last page's content area that holds content, 0 to 1

    def fills(self, minimum: float) -> bool:
        return self.pages <= 1 or self.last >= minimum

    @property
    def enough(self) -> bool:
        return self.fills(MIN_FILL)


def measure(markers: list[dict], part: str) -> Fill:
    """Pages and fill of the last page of one part, from the markers of a whole document."""
    starts = [m["page"] for m in markers if m.get("part") == part and m.get("edge") == "start"]
    ends = [m for m in markers if m.get("part") == part and m.get("edge") == "end"]
    if not starts or not ends:
        raise ValueError(f"Das Design setzt keine Marken für die Seitenfüllung ({part})")
    last_page = max(m["page"] for m in ends)
    end = max((m for m in ends if m["page"] == last_page), key=lambda m: m["y"])
    area = end["height"] - end["top"] - end["bottom"]
    return Fill(pages=last_page - min(starts) + 1, last=max(0.0, (end["y"] - end["top"]) / area))


def choose(probe: Callable[[int], Fill]) -> int:
    """The density level of a part: 0 when the design fits, otherwise the smaller of the two fixes that works.

    Both fixes are tried step by step from the smallest change, so the first that works is the smaller one; at the
    same step tightening goes first, because a page fewer is the shorter document. A fix that reaches the aim goes
    before one that only reaches the rule; a design that already meets the rule stays when no fix reaches the aim."""
    probe = functools.cache(probe)
    drawn = probe(0)
    if drawn.fills(AIM):
        return 0
    found = _smallest_fix(probe, drawn, AIM)
    if found is None and not drawn.enough:
        found = _smallest_fix(probe, drawn, MIN_FILL)
    return found or 0


def _smallest_fix(probe: Callable[[int], Fill], drawn: Fill, minimum: float) -> int | None:
    for tighter, wider in zip(TIGHTER, WIDER):
        fill = probe(tighter)
        if fill.pages < drawn.pages and fill.fills(minimum):
            return tighter
        fill = probe(wider)
        if fill.pages == drawn.pages and fill.fills(minimum):
            return wider
    return None


def markers(entry: str, root: str, font_paths: list[str], sys_inputs: dict) -> list[dict]:
    """The page-fill markers of one document, without writing it."""
    try:
        found = typst.query(entry, SELECTOR, field="value", root=root, font_paths=font_paths, sys_inputs=sys_inputs)
    except typst.TypstError:
        raise
    except RuntimeError as error:
        # The query raises a bare RuntimeError where compile raises TypstError; callers catch the latter
        raise typst.TypstError(str(error)) from error
    return json.loads(found)


def levels(query: Callable[[dict], list[dict]], sys_inputs: dict, parts: tuple[str, ...]) -> dict:
    """sys_inputs with each part's density, chosen one part after the other (the letter before the CV)."""
    chosen = dict(sys_inputs)
    for part in parts:
        def probe(level: int, part: str = part) -> Fill:
            return measure(query({**chosen, f"density-{part}": str(level)}), part)
        chosen[f"density-{part}"] = str(choose(probe))
    return chosen
