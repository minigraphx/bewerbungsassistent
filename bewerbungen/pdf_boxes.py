"""Where the text and the images of a PDF sit on its pages (G52, #237).

The check before sending measures the PDFs the app builds with Typst. pypdf reads the file but gives no width for a
piece of text, and pdftotext is not part of the app, so this module walks the content streams itself: the graphics
state (q, Q, cm), the text state (Tf, Tm, Td, TD, T*, Tc, Tw, Tz, TL) and the shown strings, with the widths from
each font. That covers what Typst writes (Type0 fonts with Identity-H, Type3 for bitmap glyphs, images and forms);
a font it cannot measure counts as 500 units per glyph, so a foreign PDF yields rough boxes instead of an error.

Coordinates are in pt from the top left corner of the page, like a reader sees it.
"""
import dataclasses
import pathlib
import re

from pypdf import PdfReader
from pypdf.generic import ContentStream, DictionaryObject, IndirectObject

IDENTITY = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
DEFAULT_WIDTH = 500.0  # units per 1000 em for a glyph without a known width
DEFAULT_ASCENT, DEFAULT_DESCENT = 800.0, -200.0
MAX_FORM_DEPTH = 8  # nested forms deeper than this are not drawn by any design
HEX = re.compile(rb"<([0-9A-Fa-f]+)>")


@dataclasses.dataclass(frozen=True)
class Box:
    page: int
    left: float
    top: float
    right: float
    bottom: float
    text: str = ""  # empty for an image
    baseline: float = 0.0  # where the letters stand; the bottom of an image
    size: float = 0.0  # the font size as printed, in pt; 0 for an image

    @property
    def height(self) -> float:
        return self.bottom - self.top

    @property
    def is_image(self) -> bool:
        return not self.text


@dataclasses.dataclass(frozen=True)
class Page:
    number: int
    width: float
    height: float
    boxes: tuple[Box, ...]

    @property
    def text(self) -> tuple[Box, ...]:
        return tuple(b for b in self.boxes if not b.is_image)

    @property
    def images(self) -> tuple[Box, ...]:
        return tuple(b for b in self.boxes if b.is_image)


def multiply(m: tuple, n: tuple) -> tuple:
    """m × n for PDF matrices (a b c d e f): first m, then n."""
    a, b, c, d, e, f = m
    p, q, r, s, t, u = n
    return (a * p + b * r, a * q + b * s, c * p + d * r, c * q + d * s, e * p + f * r + t, e * q + f * s + u)


def apply(m: tuple, x: float, y: float) -> tuple[float, float]:
    a, b, c, d, e, f = m
    return a * x + c * y + e, b * x + d * y + f


def _resolve(obj):
    return obj.get_object() if isinstance(obj, IndirectObject) else obj


def _unicode_map(font: DictionaryObject) -> dict[int, str]:
    """Character codes to text from the font's ToUnicode CMap (bfchar and bfrange)."""
    stream = _resolve(font.get("/ToUnicode"))
    if stream is None:
        return {}
    try:
        data = stream.get_data()
    except (ValueError, OSError):
        return {}
    found: dict[int, str] = {}
    for block in re.findall(rb"beginbfchar(.*?)endbfchar", data, re.S):
        values = HEX.findall(block)
        for code, text in zip(values[::2], values[1::2]):
            found[int(code, 16)] = _utf16(text)
    for block in re.findall(rb"beginbfrange(.*?)endbfrange", data, re.S):
        for line in block.splitlines():
            values = HEX.findall(line)
            if len(values) < 3:
                continue
            first, last = int(values[0], 16), int(values[1], 16)
            if b"[" in line:
                for offset, text in enumerate(values[2:]):
                    found[first + offset] = _utf16(text)
            else:
                start = int(values[2], 16)
                for offset in range(last - first + 1):
                    found[first + offset] = chr(start + offset) if start + offset < 0x110000 else ""
    return found


def _raw(part) -> bytes:
    """The bytes of a shown string; pypdf hands some of them over already decoded."""
    if isinstance(part, bytes):
        return part
    original = getattr(part, "original_bytes", None)
    return original if isinstance(original, bytes) else part.encode("latin-1", "replace")


def _utf16(hex_text: bytes) -> str:
    try:
        return bytes.fromhex(hex_text.decode("ascii")).decode("utf-16-be")
    except (ValueError, UnicodeDecodeError):
        return ""


def _cid_widths(descendant: DictionaryObject) -> dict[int, float]:
    """The /W array of a CID font: `c [w1 w2 …]` or `first last w`."""
    widths: dict[int, float] = {}
    items = [_resolve(x) for x in (_resolve(descendant.get("/W")) or [])]
    i = 0
    while i < len(items):
        first = int(items[i])
        following = items[i + 1] if i + 1 < len(items) else None
        if isinstance(following, list):
            for offset, width in enumerate(following):
                widths[first + offset] = float(_resolve(width))
            i += 2
        elif i + 2 < len(items):
            for code in range(first, int(following) + 1):
                widths[code] = float(items[i + 2])
            i += 3
        else:
            break
    return widths


@dataclasses.dataclass(frozen=True)
class Font:
    two_bytes: bool
    widths: dict
    default_width: float
    scale: float  # glyph units to text space: 1/1000, or the FontMatrix of a Type3 font
    ascent: float  # above the baseline, in em
    descent: float  # below it, negative, in em
    to_text: dict

    def codes(self, data: bytes) -> list[int]:
        if self.two_bytes:
            return [int.from_bytes(data[i:i + 2], "big") for i in range(0, len(data) - 1, 2)]
        return list(data)

    def width(self, code: int) -> float:
        return self.widths.get(code, self.default_width) * self.scale

    def text(self, codes: list[int]) -> str:
        if self.to_text:
            return "".join(self.to_text.get(code, "") for code in codes)
        return "".join(chr(code) for code in codes if 32 <= code < 127)


def _descriptor_metrics(descriptor) -> tuple[float, float]:
    descriptor = _resolve(descriptor)
    if not isinstance(descriptor, DictionaryObject):
        return DEFAULT_ASCENT / 1000, DEFAULT_DESCENT / 1000
    ascent = float(descriptor.get("/Ascent", DEFAULT_ASCENT)) or DEFAULT_ASCENT
    descent = float(descriptor.get("/Descent", DEFAULT_DESCENT))
    return ascent / 1000, descent / 1000


def font_of(font: DictionaryObject) -> Font:
    subtype = font.get("/Subtype")
    to_text = _unicode_map(font)
    if subtype == "/Type0":
        descendant = _resolve(font["/DescendantFonts"][0])
        ascent, descent = _descriptor_metrics(descendant.get("/FontDescriptor"))
        return Font(True, _cid_widths(descendant), float(descendant.get("/DW", 1000)), 1 / 1000, ascent, descent,
                    to_text)
    first = int(font.get("/FirstChar", 0))
    widths = {first + i: float(_resolve(w)) for i, w in enumerate(_resolve(font.get("/Widths")) or [])}
    if subtype == "/Type3":
        matrix = [float(x) for x in _resolve(font.get("/FontMatrix", [0.001, 0, 0, 0.001, 0, 0]))]
        bbox = [float(x) for x in _resolve(font.get("/FontBBox", [0, -200, 1000, 800]))]
        return Font(False, widths, DEFAULT_WIDTH, matrix[0], bbox[3] * matrix[3], bbox[1] * matrix[3], to_text)
    ascent, descent = _descriptor_metrics(font.get("/FontDescriptor"))
    descriptor = _resolve(font.get("/FontDescriptor"))
    missing = float(descriptor.get("/MissingWidth", DEFAULT_WIDTH)) if isinstance(descriptor, DictionaryObject) \
        else DEFAULT_WIDTH
    return Font(False, widths, missing, 1 / 1000, ascent, descent, to_text)


@dataclasses.dataclass
class _TextState:
    font: Font | None = None
    size: float = 0.0
    char_spacing: float = 0.0
    word_spacing: float = 0.0
    horizontal: float = 1.0
    leading: float = 0.0
    matrix: tuple = IDENTITY
    line: tuple = IDENTITY


class _Walker:
    """Reads one page: every shown string and every image as a box in device space."""

    def __init__(self, page_top: float):
        self.page_top = page_top
        self.found: list[tuple[float, float, float, float, str]] = []
        self.fonts: dict[int, Font] = {}

    def walk(self, content, resources: DictionaryObject, ctm: tuple, reader: PdfReader, depth: int = 0) -> None:
        if content is None or depth > MAX_FORM_DEPTH:
            return
        stack: list[tuple] = []
        text = _TextState()
        fonts = _resolve(resources.get("/Font")) or {}
        xobjects = _resolve(resources.get("/XObject")) or {}
        for args, op in ContentStream(content, reader, "bytes").operations:
            if op == b"q":
                stack.append(ctm)
            elif op == b"Q":
                ctm = stack.pop() if stack else ctm
            elif op == b"cm":
                ctm = multiply(tuple(float(a) for a in args), ctm)
            elif op == b"BT":
                text.matrix = text.line = IDENTITY
            elif op == b"Tf":
                text.font = self._font(fonts.get(args[0]))
                text.size = float(args[1])
            elif op in (b"Tc", b"Tw", b"Tz", b"TL"):
                self._text_parameter(text, op, float(args[0]))
            elif op in (b"Td", b"TD"):
                if op == b"TD":
                    text.leading = -float(args[1])
                self._move(text, float(args[0]), float(args[1]))
            elif op == b"T*":
                self._move(text, 0.0, -text.leading)
            elif op == b"Tm":
                text.matrix = text.line = tuple(float(a) for a in args)
            elif op in (b"Tj", b"TJ", b"'", b'"'):
                self._show(text, op, args, ctm)
            elif op == b"Do":
                self._draw(xobjects.get(args[0]), ctm, reader, depth)
            elif op == b"INLINE IMAGE":
                self._image(ctm)

    def _font(self, reference) -> Font | None:
        font = _resolve(reference)
        if not isinstance(font, DictionaryObject):
            return None
        key = id(font)
        if key not in self.fonts:
            try:
                self.fonts[key] = font_of(font)
            except (KeyError, IndexError, TypeError, ValueError):
                self.fonts[key] = Font(False, {}, DEFAULT_WIDTH, 1 / 1000, DEFAULT_ASCENT / 1000,
                                       DEFAULT_DESCENT / 1000, {})
        return self.fonts[key]

    @staticmethod
    def _text_parameter(text: _TextState, op: bytes, value: float) -> None:
        if op == b"Tc":
            text.char_spacing = value
        elif op == b"Tw":
            text.word_spacing = value
        elif op == b"Tz":
            text.horizontal = value / 100
        else:
            text.leading = value

    @staticmethod
    def _move(text: _TextState, x: float, y: float) -> None:
        text.line = multiply((1.0, 0.0, 0.0, 1.0, x, y), text.line)
        text.matrix = text.line

    def _show(self, text: _TextState, op: bytes, args: list, ctm: tuple) -> None:
        if op in (b"'", b'"'):
            if op == b'"':
                text.word_spacing, text.char_spacing = float(args[0]), float(args[1])
            self._move(text, 0.0, -text.leading)
        parts = args[0] if op == b"TJ" else [args[-1]]
        if text.font is None:
            return
        start = text.matrix
        advance, codes, visible = 0.0, [], []
        for part in parts:
            if isinstance(part, (bytes, str)):
                for code in text.font.codes(_raw(part)):
                    space = text.word_spacing if not text.font.two_bytes and code == 32 else 0.0
                    before = advance
                    advance += (text.font.width(code) * text.size + text.char_spacing + space) * text.horizontal
                    codes.append(code)
                    if text.font.text([code]).strip():
                        visible.append((before, advance))
            else:
                advance -= float(part) / 1000 * text.size * text.horizontal
        text.matrix = multiply((1.0, 0.0, 0.0, 1.0, advance, 0.0), text.matrix)
        if visible:  # spaces at either end take room but show nothing
            low = (visible[0][0], text.font.descent * text.size)
            high = (visible[-1][1], text.font.ascent * text.size)
            matrix = multiply(start, ctm)
            self._add(matrix, low, high, text.font.text(codes).strip(), _baseline(matrix, self.page_top),
                      text.size * abs(matrix[3]))

    def _draw(self, reference, ctm: tuple, reader: PdfReader, depth: int) -> None:
        xobject = _resolve(reference)
        if xobject is None:
            return
        subtype = xobject.get("/Subtype")
        if subtype == "/Image":
            self._image(ctm)
        elif subtype == "/Form":
            matrix = tuple(float(a) for a in xobject.get("/Matrix", IDENTITY))
            resources = _resolve(xobject.get("/Resources")) or DictionaryObject()
            self.walk(xobject, resources, multiply(matrix, ctm), reader, depth + 1)

    def _image(self, ctm: tuple) -> None:
        self._add(ctm, (0.0, 0.0), (1.0, 1.0), "")

    def _add(self, matrix: tuple, low: tuple, high: tuple, text: str, baseline: float | None = None,
             size: float = 0.0) -> None:
        corners = [apply(matrix, x, y) for x in (low[0], high[0]) for y in (low[1], high[1])]
        xs = [x for x, _ in corners]
        ys = [self.page_top - y for _, y in corners]
        self.found.append((min(xs), min(ys), max(xs), max(ys), text, max(ys) if baseline is None else baseline, size))


def _baseline(matrix: tuple, page_top: float) -> float:
    return page_top - apply(matrix, 0.0, 0.0)[1]


def read(pdf: pathlib.Path) -> list[Page]:
    """Every page with the boxes of its text and images, in the order the PDF draws them."""
    reader = PdfReader(pdf)
    pages = []
    for number, page in enumerate(reader.pages, 1):
        box = page.mediabox
        walker = _Walker(float(box.top))
        contents = page.get_contents()
        resources = _resolve(page.get("/Resources")) or DictionaryObject()
        walker.walk(contents, resources, (1.0, 0.0, 0.0, 1.0, -float(box.left), 0.0), reader)
        boxes = tuple(Box(number, *found) for found in walker.found)
        pages.append(Page(number, float(box.width), float(box.height), boxes))
    return pages
