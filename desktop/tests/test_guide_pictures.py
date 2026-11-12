"""The pictures of the guide are sharp on retina screens (#228, #232).

The website shows them in a lightbox and as WebP with srcset, converted from these JPGs at build time. Taken at
1280 px CSS width with device pixel ratio 2, each picture the guide, the page on the own subscription or a README shows is at least 2200 px wide.
"""
import pathlib
import re
import struct

import pytest
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parents[2]
PICTURES = ROOT / "docs" / "bilder"
PAGES = {ROOT / "docs" / "installation.md": "bilder/", ROOT / "README.md": "docs/bilder/",
         ROOT / "docs" / "eigenes-abo.md": "bilder/", ROOT / "bewerbungen" / "README.md": "../docs/bilder/"}
MIN_WIDTH = 2200
MAX_WIDTH = 2560
# Start-of-frame markers carry the size; DHT (C4), JPG (C8) and DAC (CC) share the range but do not.
FRAME_MARKERS = set(range(0xC0, 0xD0)) - {0xC4, 0xC8, 0xCC}
# The first picture on the website's start page (#246): no empty band below the content
CROPPED = ("uebersicht.jpg",)
MAX_EMPTY_BOTTOM = 0.05  # of the height
CONTENT_CONTRAST = 24  # grey levels from the page background, above JPEG noise
# Taken by the website at the release tag, shown on no page of this repo (#267): first pages of lebenslauf.pdf
# and anschreiben.pdf from `lebenslauf/dossier.py lebenslauf/data/dossier-beispiel.yaml`, invented data
WEBSITE_ONLY = ("beispiel-unterlagen.jpg",)


def referenced() -> set[str]:
    names = set()
    for page, prefix in PAGES.items():
        pattern = re.compile(r"!\[[^\]]*\]\(" + re.escape(prefix) + r"([^)\s]+)\)")
        names.update(pattern.findall(page.read_text(encoding="utf-8")))
    return names


def checked() -> set[str]:
    return referenced() | set(WEBSITE_ONLY)


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
    missing = sorted(name for name in checked() if not (PICTURES / name).is_file())
    assert not missing, f"fehlen: {missing}"
    assert all(name.endswith(".jpg") for name in checked())


def test_every_shown_picture_is_taken_at_double_resolution():
    widths = {name: jpeg_size((PICTURES / name).read_bytes())[0] for name in sorted(checked())}
    too_small = {name: width for name, width in widths.items() if not MIN_WIDTH <= width <= MAX_WIDTH}
    assert not too_small, f"nicht {MIN_WIDTH} bis {MAX_WIDTH} px breit: {too_small}"


def test_pictures_carry_no_metadata():
    """No EXIF (APP1) or other application segments beyond JFIF (APP0): no camera, place or time, no program name."""
    carrying = []
    for name in sorted(checked()):
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


def lowest_content_row(picture: Image.Image) -> int:
    """The lowest row that differs from the page background, taken from the bottom row."""
    grey = picture.convert("L")
    width, height = grey.size
    bottom = [grey.getpixel((x, height - 1)) for x in range(width)]
    background = max(set(bottom), key=bottom.count)
    for y in range(height - 1, -1, -1):
        if any(abs(grey.getpixel((x, y)) - background) > CONTENT_CONTRAST for x in range(0, width, 2)):
            return y
    return 0


@pytest.mark.parametrize("name", CROPPED)
def test_a_cropped_picture_ends_where_its_content_ends(name):
    with Image.open(PICTURES / name) as picture:
        empty = (picture.height - 1 - lowest_content_row(picture)) / picture.height
    assert empty <= MAX_EMPTY_BOTTOM, f"{name}: {empty:.0%} empty at the bottom"


def test_finding_the_content_sees_a_line_above_an_empty_band():
    picture = Image.new("L", (40, 100), 250)
    picture.paste(40, (5, 30, 35, 32))
    assert lowest_content_row(picture) == 31


def test_reading_the_size_finds_the_frame():
    frame = b"\xff\xd8" + b"\xff\xe0\x00\x04ab" + b"\xff\xc4\x00\x04cd" + b"\xff\xc0\x00\x0b\x08\x01\x2c\x0a\x00\x03xx"
    assert jpeg_size(frame) == (2560, 300)
