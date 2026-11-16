"""What the page fill did to a built PDF (G93, #324): the density level of each part, written beside the PDF.

The build chooses a level per part before it writes the PDF (page_fill.py). It returns the levels and stores them next
to the PDF with its fingerprint, like the type area (type_area.py), so the check names how the pages were balanced
for exactly this file. A record that does not fit the PDF, or that cannot be read, counts as none.
"""
import dataclasses
import json
import pathlib

import page_fill
from type_area import fingerprint

SUFFIX = ".page-fill.json"
PARTS = ("letter", "cv")
LEVELS = frozenset((*page_fill.WIDER, 0, *page_fill.TIGHTER))


@dataclasses.dataclass(frozen=True)
class Built:
    """A built PDF and the density level each of its parts got."""
    pdf: pathlib.Path
    levels: dict[str, int]


def levels_of(inputs: dict) -> dict[str, int]:
    """The level of each part in the sys_inputs a PDF was compiled with."""
    return {part: int(inputs[f"density-{part}"]) for part in PARTS if f"density-{part}" in inputs}


def path_for(pdf: pathlib.Path) -> pathlib.Path:
    """Where the record of a PDF lies: beside it, `lebenslauf.pdf` → `lebenslauf.page-fill.json`."""
    return pdf.with_name(pdf.stem + SUFFIX)


def write(pdf: pathlib.Path, levels: dict[str, int]) -> Built:
    """Store the levels beside the PDF that was just written."""
    content = {"pdf": fingerprint(pdf), "levels": dict(levels)}
    path_for(pdf).write_text(json.dumps(content, indent=1), encoding="utf-8")
    return Built(pdf=pdf, levels=dict(levels))


def read(pdf: pathlib.Path, built_as: pathlib.Path | None = None) -> dict[str, int] | None:
    """The levels the build stored for exactly this PDF; None without a fitting record. A sent copy has none beside it,
    so `built_as` names the file it was built as."""
    try:
        content = json.loads(path_for(built_as or pdf).read_text(encoding="utf-8"))
        own = fingerprint(pdf)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(content, dict) or content.get("pdf") != own:
        return None
    return _checked(content.get("levels"))


def _checked(levels) -> dict[str, int] | None:
    if not isinstance(levels, dict):
        return None
    valid = all(part in PARTS and type(level) is int and level in LEVELS for part, level in levels.items())
    return dict(levels) if valid else None
