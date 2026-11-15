"""Page 1 of a document as a small PNG for the step «Unterlagen erstellen und prüfen» (#321).

Typst reads PDFs as images since 0.14, so the thumbnail needs no PDF renderer of its own. A broken own PDF gives a
message instead; the page then shows the alt text.
"""
import pathlib
import tempfile

import typst

WIDTH_PT = 144
PPI = 144  # 288 px wide: sharp at 72 to 144 CSS pixels on a retina screen
SOURCE = ('#set page(width: auto, height: auto, margin: 0pt)\n'
          f'#image("dokument.pdf", page: 1, width: {WIDTH_PT}pt)\n')
UNREADABLE = "Vorschau nicht möglich: Das PDF lässt sich nicht lesen. Es lässt sich trotzdem als PDF öffnen."


def render(pdf: pathlib.Path, build: pathlib.Path) -> bytes:
    build.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=build) as folder:
        root = pathlib.Path(folder)
        (root / "dokument.pdf").write_bytes(pdf.read_bytes())
        (root / "miniatur.typ").write_text(SOURCE, encoding="utf-8")
        try:
            return typst.compile(str(root / "miniatur.typ"), root=folder, format="png", ppi=PPI)
        except typst.TypstError as error:
            raise ValueError(UNREADABLE) from error


def cached(cache: dict, pdf: pathlib.Path, build: pathlib.Path) -> bytes:
    """The pages ask again after every load; a file that did not change is not rendered again."""
    stat = pdf.stat()
    key = ("pdf-miniatur", str(pdf), stat.st_mtime_ns, stat.st_size)
    if key not in cache:
        stale = [old for old in cache if isinstance(old, tuple) and old[:2] == key[:2]]
        for old in stale:
            cache.pop(old)
        cache[key] = render(pdf, build)
    return cache[key]
