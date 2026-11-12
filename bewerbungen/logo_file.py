"""The person's own logo for the dossier (G18, docs/design/monogramm.md): checked on upload, never changed in its pixels.

PNG and JPG lose their metadata like a photo (photo_file.py); an SVG must carry no script and load nothing from
outside. A plain SVG DOCTYPE from an older editor is taken off before the check, so a stored logo never has one (#243). To see shape, transparency and colours, Typst renders a small PNG of the logo, which this file decodes;
no image library is needed. The logo stays on the computer: nothing here goes to the AI.
"""
import collections
import pathlib
import struct
import tempfile
import zlib

import typst

import pfade  # noqa: F401  (makes the module lebenslauf importable)
import mark
import photo_file
import svg_check

MAX_BYTES = 5_000_000
GOOD_WIDTH = 1000  # pixels; below that a hint, no refusal
WIDE = 4.0  # width : height from which the logo gets small on the cover
HIGH = 1.5  # height : width
PROBE_PX = 64
SATURATED = 0.25
WHITE_LEVEL = 245

FORMAT = "Diese Datei ist kein Bild in PNG, JPG oder SVG."
TOO_LARGE = "Die Datei ist grösser als 5 MB. Bitte ein kleineres Bild wählen."
UNREADABLE = "Das Bild liess sich nicht lesen. Bitte ein anderes Bild in PNG, JPG oder SVG wählen."
VERY_WIDE = "Sehr breit: Auf dem Deckblatt wird das Logo nur etwa 7 mm hoch. Ein kompakteres Zeichen wirkt besser."
VERY_HIGH = "Sehr hoch: Das Logo wird auf dem Deckblatt schmal und wirkt klein. Eine quere Fassung passt besser."
FEW_PIXELS = ("Das Bild hat nur {w} × {h} Pixel und wird im Druck unscharf. Besser mindestens 1000 Pixel breit.")
WHITE_BACKGROUND = ("Das Logo hat einen weissen Hintergrund. Auf dem Papier fällt das kaum auf; in Raster steht es "
                    "ohnehin auf einer weissen Fläche.")


def kind(data: bytes) -> str:
    """png, jpg or svg by the content, whatever the file was called."""
    try:
        return photo_file.extension(data)
    except ValueError:
        pass
    head = data[:2048].lstrip(b"\xef\xbb\xbf \t\r\n").lower()
    starts = (b"<svg", b"<?xml", b"<!--", b"<!doctype")
    if head.startswith(starts) and b"<svg" in data[:65536].lower():
        return "svg"
    raise ValueError(FORMAT)


def cleaned(data: bytes) -> tuple[str, bytes]:
    """The extension and the file to store; ValueError with the reason for the person otherwise."""
    if len(data) > MAX_BYTES:
        raise ValueError(TOO_LARGE)
    found = kind(data)
    if found == "svg":
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValueError(UNREADABLE) from error
        text = svg_check.without_doctype(text)
        problem = mark.svg_problem(text)
        if problem:
            raise ValueError(problem)
        return found, text.encode("utf-8")
    return photo_file.without_metadata(data)


def pixels(extension: str, data: bytes) -> tuple[int, int] | None:
    """Width and height of a PNG or JPG; None for an SVG, which has no pixels."""
    if extension == "png":
        return struct.unpack(">II", data[16:24])
    if extension == "jpg":
        position = 2
        while position + 9 < len(data):
            if data[position] != 0xFF:
                position += 1
                continue
            marker = data[position + 1]
            length = struct.unpack(">H", data[position + 2:position + 4])[0]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                height, width = struct.unpack(">HH", data[position + 5:position + 9])
                return width, height
            position += 2 + length
    return None


def render(extension: str, data: bytes, build: pathlib.Path) -> bytes:
    """A small PNG of the whole logo with its transparency and shape, from Typst, which also has to read it for the dossier."""
    build.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=build) as folder:
        name = f"logo.{extension}"
        (pathlib.Path(folder) / name).write_bytes(data)
        document = pathlib.Path(folder) / "probe.typ"
        document.write_text('#set page(width: auto, height: auto, margin: 0pt, fill: none)\n'
                            f'#image("{name}", width: {PROBE_PX}pt)\n', encoding="utf-8")
        try:
            return typst.compile(str(document), root=folder, format="png", ppi=72)
        except typst.TypstError as error:
            raise ValueError(UNREADABLE) from error


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    return a if pa <= pb and pa <= pc else b if pb <= pc else c


def decode_rgba(png: bytes) -> tuple[int, int, list[tuple[int, int, int, int]]]:
    """The pixels of an 8-bit RGBA PNG without interlacing, as Typst writes it."""
    width, height, depth, colour_type = struct.unpack(">IIBB", png[16:26])
    if depth != 8 or colour_type != 6:
        raise ValueError(UNREADABLE)
    position, stream = 8, b""
    while position < len(png):
        length = struct.unpack(">I", png[position:position + 4])[0]
        if png[position + 4:position + 8] == b"IDAT":
            stream += png[position + 8:position + 8 + length]
        position += 12 + length
    raw, stride, previous, rows = zlib.decompress(stream), width * 4, bytes(width * 4), []
    for y in range(height):
        start = y * (stride + 1)
        kind_of, line = raw[start], bytearray(raw[start + 1:start + 1 + stride])
        for x in range(stride):
            left = line[x - 4] if x >= 4 else 0
            up, corner = previous[x], previous[x - 4] if x >= 4 else 0
            line[x] = (line[x] + (0, left, up, (left + up) // 2, _paeth(left, up, corner))[kind_of]) & 0xFF
        rows.append(bytes(line))
        previous = line
    return width, height, [tuple(row[i:i + 4]) for row in rows for i in range(0, stride, 4)]


def _saturation(r: int, g: int, b: int) -> float:
    high, low = max(r, g, b) / 255, min(r, g, b) / 255
    lightness = (high + low) / 2
    if high == low:
        return 0.0
    return (high - low) / (2 - high - low) if lightness > 0.5 else (high - low) / (high + low)


def strongest_colour(rgba: list[tuple[int, int, int, int]]) -> str | None:
    """The most frequent saturated colour, made dark enough for the rules; None for a logo in greys only."""
    counts = collections.Counter((r >> 4, g >> 4, b >> 4) for r, g, b, a in rgba if a > 200 and _saturation(r, g, b) > SATURATED)
    if not counts:
        return None
    bucket = counts.most_common(1)[0][0]
    members = [(r, g, b) for r, g, b, a in rgba if a > 200 and (r >> 4, g >> 4, b >> 4) == bucket]
    average = "#" + "".join(f"{round(sum(p[i] for p in members) / len(members)):02x}" for i in range(3))
    return average if mark.readable(average) else mark.darker(average)


def inspect(extension: str, data: bytes, build: pathlib.Path) -> dict:
    """What the page says about a logo: pixels, transparency, hints and the colour „Aus dem Logo“."""
    width, height, rgba = decode_rgba(render(extension, data, build))  # as wide as the probe, as high as its shape
    if not any(a for *_, a in rgba):
        raise ValueError(UNREADABLE)
    size = pixels(extension, data)
    corners = [rgba[i] for i in (0, width - 1, (height - 1) * width, height * width - 1)]
    transparent = any(a < 128 for *_, a in rgba)
    white = not transparent and all(min(r, g, b) >= WHITE_LEVEL for r, g, b, _ in corners)
    hints = [*([VERY_WIDE] if width / height > WIDE else []), *([VERY_HIGH] if height / width > HIGH else []),
             *([FEW_PIXELS.format(w=size[0], h=size[1])] if size and size[0] < GOOD_WIDTH else []),
             *([WHITE_BACKGROUND] if white else [])]
    return {"breite": size[0] if size else None, "hoehe": size[1] if size else None, "vektor": size is None,
            "durchsichtig": transparent, "hinweise": hints, "farbe": strongest_colour(rgba)}
