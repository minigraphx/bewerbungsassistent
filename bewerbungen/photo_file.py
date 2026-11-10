"""A photo for the CV, uploaded on the page Foto (#128): JPG or PNG, stored without metadata.

Camera, place and time in a photo say more about a person than the CV needs, so only the pixels stay. A JPEG keeps
its orientation (a fresh EXIF block with that one entry), otherwise a portrait taken upright would lie on its side.
No image library: the segments and chunks are copied as they are, the pixels are never decoded or re-encoded here.
"""
import struct
import zlib

FORMAT = "Bitte ein Foto als JPG oder PNG wählen."
UNREADABLE = "Das Bild liess sich nicht lesen. Bitte ein anderes Foto als JPG oder PNG wählen."

JPEG_START = b"\xff\xd8"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
EXIF_HEADER = b"Exif\x00\x00"
ICC_HEADER = b"ICC_PROFILE\x00"
ORIENTATION_TAG = 0x0112
ORIENTATIONS = range(1, 9)

APP0, APP1, APP2, APP14, SOS, EOI, COM = 0xE0, 0xE1, 0xE2, 0xEE, 0xDA, 0xD9, 0xFE
RESTARTS = range(0xD0, 0xD8)
STANDALONE = {0x01, *RESTARTS}  # TEM and RST0..7 carry no length
KEPT_APP = {APP0, APP14}  # JFIF and Adobe (colour transform); APP2 only as an ICC profile
PNG_KEPT = {b"IHDR", b"PLTE", b"IDAT", b"IEND", b"tRNS", b"gAMA", b"cHRM", b"sRGB", b"iCCP", b"sBIT", b"pHYs"}


def extension(data: bytes) -> str:
    """`jpg` or `png` by the first bytes, whatever the file was called."""
    if data.startswith(JPEG_START + b"\xff"):
        return "jpg"
    if data.startswith(PNG_SIGNATURE):
        return "png"
    raise ValueError(FORMAT)


def without_metadata(data: bytes) -> tuple[str, bytes]:
    """The extension and the image without metadata; ValueError with a message for the person otherwise."""
    kind = extension(data)
    try:
        return kind, (_jpeg(data) if kind == "jpg" else _png(data))
    except (IndexError, struct.error) as error:
        raise ValueError(UNREADABLE) from error


# JPEG


def _entropy_end(data: bytes, position: int) -> int:
    """Where the coded data after a start of scan ends: at the next marker that is not a stuffed byte or a restart."""
    while True:
        found = data.find(b"\xff", position)
        if found < 0 or found + 1 >= len(data):
            raise ValueError(UNREADABLE)
        following = data[found + 1]
        if following != 0x00 and following not in RESTARTS:
            return found
        position = found + 2


def _segments(data: bytes):
    """(marker, bytes) of each segment up to the end of image; a scan carries its coded data. What follows the end
    of image (some phones append a video there) is left out."""
    position = len(JPEG_START)
    while True:
        if data[position] != 0xFF:
            raise ValueError(UNREADABLE)
        while data[position + 1] == 0xFF:  # fill bytes before a marker
            position += 1
        marker = data[position + 1]
        if marker == EOI:
            yield marker, data[position:position + 2]
            return
        if marker in STANDALONE:
            yield marker, data[position:position + 2]
            position += 2
            continue
        (length,) = struct.unpack(">H", data[position + 2:position + 4])
        end = position + 2 + length
        if length < 2 or end > len(data):
            raise ValueError(UNREADABLE)
        if marker == SOS:
            end = _entropy_end(data, end)
        yield marker, data[position:end]
        position = end


def _orientation(segment: bytes) -> int | None:
    """The orientation from an EXIF segment, or None when it has none or does not read; the rest is left out anyway."""
    try:
        return _read_orientation(segment[4:])
    except (IndexError, struct.error):
        return None


def _read_orientation(body: bytes) -> int | None:
    if not body.startswith(EXIF_HEADER):
        return None
    tiff = body[len(EXIF_HEADER):]
    order = {b"II": "<", b"MM": ">"}.get(tiff[:2])
    if order is None:
        return None
    (ifd,) = struct.unpack(order + "I", tiff[4:8])
    (count,) = struct.unpack(order + "H", tiff[ifd:ifd + 2])
    for index in range(count):
        entry = tiff[ifd + 2 + 12 * index:ifd + 14 + 12 * index]
        tag, kind, _, value = struct.unpack(order + "HHIH", entry[:10])
        if tag == ORIENTATION_TAG and kind == 3:
            return value if value in ORIENTATIONS else None
    return None


def _orientation_segment(orientation: int) -> bytes:
    """An APP1 segment whose EXIF holds the orientation and nothing else."""
    entry = struct.pack(">HHIHH", ORIENTATION_TAG, 3, 1, orientation, 0)
    tiff = b"MM\x00\x2a" + struct.pack(">I", 8) + struct.pack(">H", 1) + entry + struct.pack(">I", 0)
    body = EXIF_HEADER + tiff
    return struct.pack(">BBH", 0xFF, APP1, len(body) + 2) + body


def _kept(marker: int, segment: bytes) -> bool:
    if marker in KEPT_APP:
        return True
    if marker == APP2:
        return segment[4:].startswith(ICC_HEADER)
    return not (0xE0 <= marker <= 0xEF or marker == COM)


def _jpeg(data: bytes) -> bytes:
    parts, orientation, markers = [JPEG_START], None, set()
    for marker, segment in _segments(data):
        markers.add(marker)
        if marker == APP1:
            orientation = orientation or _orientation(segment)
        elif _kept(marker, segment):
            parts.append(segment)
    if SOS not in markers:
        raise ValueError(UNREADABLE)
    if orientation and orientation != 1:
        after_jfif = 2 if len(parts) > 1 and parts[1][1] == APP0 else 1  # JFIF stays right after the start
        parts.insert(after_jfif, _orientation_segment(orientation))
    return b"".join(parts)


# PNG


def _chunks(data: bytes):
    position = len(PNG_SIGNATURE)
    while position < len(data):
        (length,) = struct.unpack(">I", data[position:position + 4])
        kind = data[position + 4:position + 8]
        end = position + 12 + length
        if end > len(data):
            raise ValueError(UNREADABLE)
        (crc,) = struct.unpack(">I", data[end - 4:end])
        if zlib.crc32(data[position + 4:end - 4]) != crc:
            raise ValueError(UNREADABLE)
        yield kind, data[position:end]
        position = end
        if kind == b"IEND":
            return
    raise ValueError(UNREADABLE)


def _png(data: bytes) -> bytes:
    chunks = list(_chunks(data))
    kinds = [kind for kind, _ in chunks]
    if kinds[0] != b"IHDR" or b"IDAT" not in kinds:
        raise ValueError(UNREADABLE)
    return PNG_SIGNATURE + b"".join(chunk for kind, chunk in chunks if kind in PNG_KEPT)
