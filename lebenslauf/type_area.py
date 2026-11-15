"""The type area of a built PDF (G51, #304): the margins each page of the design has, written beside the PDF.

Every design leaves a marker on every page (themes/type-area.typ) with its page size, its four margins and where its
footer begins. The build reads them from the same sources and inputs the PDF was written with and stores them next to
it, with the fingerprint of the PDF, so the check before sending measures text against the design's own margins and
knows when the file beside a PDF belongs to an older build.
"""
import hashlib
import json
import pathlib

import typst

SELECTOR = "<type-area>"
SUFFIX = ".type-area.json"
FIELDS = ("width", "height", "left", "right", "top", "bottom")


def path_for(pdf: pathlib.Path) -> pathlib.Path:
    """Where the type area of a PDF lies: beside it, `lebenslauf.pdf` → `lebenslauf.type-area.json`."""
    return pdf.with_name(pdf.stem + SUFFIX)


def fingerprint(pdf: pathlib.Path) -> str:
    return hashlib.sha256(pdf.read_bytes()).hexdigest()


def pages(entry: str, root: str, font_paths: list[str], sys_inputs: dict) -> list[dict]:
    """The markers of one document, one per page, in page order."""
    try:
        found = json.loads(typst.query(entry, SELECTOR, field="value", root=root, font_paths=font_paths,
                                       sys_inputs=sys_inputs))
    except RuntimeError as error:
        # The query raises a bare RuntimeError where compile raises TypstError; callers catch the latter
        raise typst.TypstError(str(error)) from error
    return sorted(found, key=lambda marker: marker["page"])


def write(pdf: pathlib.Path, markers: list[dict]) -> pathlib.Path:
    """Store the type area beside the PDF that was just written."""
    target = path_for(pdf)
    content = {"pdf": fingerprint(pdf), "pages": [_page(marker) for marker in markers]}
    target.write_text(json.dumps(content, indent=1), encoding="utf-8")
    return target


def record(pdf: pathlib.Path, entry: str, root: str, font_paths: list[str], sys_inputs: dict) -> pathlib.Path:
    """Read the markers with the inputs the PDF was built with and store them beside it."""
    return write(pdf, pages(entry, root, font_paths, sys_inputs))


def _page(marker: dict) -> dict:
    if not isinstance(marker, dict):
        raise ValueError("Das Design gibt den Satzspiegel nicht an")
    missing = [name for name in ("page", *FIELDS) if not isinstance(marker.get(name), (int, float))]
    if missing:
        raise ValueError(f"Das Design gibt den Satzspiegel unvollständig an ({', '.join(missing)})")
    footer = marker.get("footer")
    return {"page": int(marker["page"]), **{name: float(marker[name]) for name in FIELDS},
            "footer": float(footer) if isinstance(footer, (int, float)) else None}


def read(pdf: pathlib.Path) -> dict[int, dict] | None:
    """The type area per page number, as the build stored it for exactly this PDF; None without one, or when the
    file beside it belongs to another build (then nobody knows the margins, and only the page edge counts)."""
    target = path_for(pdf)
    try:
        content = json.loads(target.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    if not isinstance(content, dict) or content.get("pdf") != fingerprint(pdf):
        return None
    return {page["page"]: page for page in map(_page, content.get("pages") or [])}
