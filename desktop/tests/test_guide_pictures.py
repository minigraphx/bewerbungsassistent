"""The pictures of the guide are sharp on retina screens (#228, #232).

The website shows them in a lightbox and as WebP with srcset, converted from these JPGs at build time. Taken at
1280 px CSS width with device pixel ratio 2, each picture the guide, the page on the own subscription or a README shows is at least 2200 px wide.
"""
import pathlib
import re
import struct

ROOT = pathlib.Path(__file__).resolve().parents[2]
PICTURES = ROOT / "docs" / "bilder"
PAGES = {ROOT / "docs" / "installation.md": "bilder/", ROOT / "README.md": "docs/bilder/",
         ROOT / "docs" / "eigenes-abo.md": "bilder/", ROOT / "bewerbungen" / "README.md": "../docs/bilder/"}
MIN_WIDTH = 2200
MAX_WIDTH = 2560
# Start-of-frame markers carry the size; DHT (C4), JPG (C8) and DAC (CC) share the range but do not.
FRAME_MARKERS = set(range(0xC0, 0xD0)) - {0xC4, 0xC8, 0xCC}


def referenced() -> set[str]:
    names = set()
    for page, prefix in PAGES.items():
        pattern = re.compile(r"!\[[^\]]*\]\(" + re.escape(prefix) + r"([^)\s]+)\)")
        names.update(pattern.findall(page.read_text(encoding="utf-8")))
    return names


def jpeg_size(data: bytes) -> tuple[int, int]:
    """(width, height) from the first start-of-frame segment."""
    assert data[:2] == b"\xff\xd8", "kein JPG"
    pos = 2
    while pos + 4 <= len(data):
        if data[pos] != 0xFF:
            raise AssertionError(f"kaputtes JPG bei Byte {pos}")
        marker = data[pos + 1]
        length = struct.unpack(">H", data[pos + 2:pos + 4])[0]
        if marker in FRAME_MARKERS:
            height, width = struct.unpack(">HH", data[pos + 5:pos + 9])
            return width, height
        pos += 2 + length
    raise AssertionError("keine Bildgrösse im JPG")


def test_the_guide_shows_pictures():
    assert len(referenced()) >= 10
    assert {"einstellungen-claude.jpg", "fragen.jpg"} <= referenced()


def test_every_shown_picture_exists_as_jpg():
    missing = sorted(name for name in referenced() if not (PICTURES / name).is_file())
    assert not missing, f"fehlen: {missing}"
    assert all(name.endswith(".jpg") for name in referenced())


def test_every_shown_picture_is_taken_at_double_resolution():
    widths = {name: jpeg_size((PICTURES / name).read_bytes())[0] for name in sorted(referenced())}
    too_small = {name: width for name, width in widths.items() if not MIN_WIDTH <= width <= MAX_WIDTH}
    assert not too_small, f"nicht {MIN_WIDTH} bis {MAX_WIDTH} px breit: {too_small}"


def test_pictures_carry_no_metadata():
    """No EXIF (APP1) or other application segments beyond JFIF (APP0): no camera, place or time, no program name."""
    carrying = []
    for name in sorted(referenced()):
        data = (PICTURES / name).read_bytes()
        pos = 2
        while pos + 4 <= len(data) and data[pos] == 0xFF:
            marker = data[pos + 1]
            if marker == 0xDA:
                break
            if 0xE1 <= marker <= 0xEF or marker == 0xFE:
                carrying.append(name)
                break
            pos += 2 + struct.unpack(">H", data[pos + 2:pos + 4])[0]
    assert not carrying, f"mit Metadaten: {carrying}"


def test_reading_the_size_finds_the_frame():
    frame = b"\xff\xd8" + b"\xff\xe0\x00\x04ab" + b"\xff\xc4\x00\x04cd" + b"\xff\xc0\x00\x0b\x08\x01\x2c\x0a\x00\x03xx"
    assert jpeg_size(frame) == (2560, 300)
