"""Upload a photo on the page Foto when none was given at the start (#128). Test images are generated here."""
import base64
import io
import json

import pypdf
import pytest
import yaml
from PIL import Image, PngImagePlugin

import build
import photo_file
import routen_foto
from test_app import get, post, server  # noqa: F401  (server is a fixture)

ORIENTATION = 0x0112
MAKE = 0x010F
GPS_IFD = 0x8825


@pytest.fixture
def without_photo(server):
    """The sample folder of the tests has a photo; this one has none, as after a start without photo."""
    cv = server.kontext.daten / "cv.yaml"
    cv.write_text(cv.read_text(encoding="utf-8").replace("  image: foto.png\n", "", 1), encoding="utf-8")
    (server.kontext.daten / "foto.png").unlink()
    return server


def jpeg_with_metadata(orientation: int = 6) -> bytes:
    image = Image.new("RGB", (120, 80), (200, 120, 90))
    exif = Image.Exif()
    exif[ORIENTATION] = orientation
    exif[MAKE] = "Erfundene Kamera"
    exif.get_ifd(GPS_IFD)[2] = (47.0, 22.0, 0.0)  # latitude, invented
    out = io.BytesIO()
    image.save(out, "JPEG", exif=exif.tobytes())
    return out.getvalue()


def png_with_text() -> bytes:
    info = PngImagePlugin.PngInfo()
    info.add_text("Author", "Erfundene Person")
    out = io.BytesIO()
    Image.new("RGB", (60, 90), (40, 80, 160)).save(out, "PNG", pnginfo=info)
    return out.getvalue()


def upload(s, data: bytes, name: str = "bild.jpg"):
    return post(s, "/api/foto/hochladen", {"name": name, "daten": base64.b64encode(data).decode("ascii")})


def present(s) -> bool:
    return json.loads(get(s, "/api/foto/vorhanden")[2])["vorhanden"]


def test_a_jpeg_without_metadata_becomes_the_photo_of_the_cv(without_photo):
    assert not present(without_photo)

    status, answer = upload(without_photo, jpeg_with_metadata())

    assert status == 200, answer
    assert answer == {"mirror": False, "zoom": 1, "x": 0.5, "y": 0.5}
    assert present(without_photo)
    daten = without_photo.kontext.daten
    cv = yaml.safe_load((daten / "cv.yaml").read_text(encoding="utf-8"))
    assert cv["basics"]["image"] == "foto.jpg"
    stored = Image.open(daten / "foto.jpg")
    exif = stored.getexif()
    assert dict(exif) == {ORIENTATION: 6}  # turned as taken, nothing else about camera or place
    assert not exif.get_ifd(GPS_IFD)
    assert b"Erfundene Kamera" not in (daten / "foto.jpg").read_bytes()
    assert get(without_photo, "/api/foto/bild")[0] == 200


def test_a_png_keeps_its_pixels_and_loses_its_text(without_photo):
    data = png_with_text()

    status, _ = upload(without_photo, data, "portrait.PNG")

    assert status == 200
    stored = without_photo.kontext.daten / "foto.png"
    assert b"Erfundene Person" not in stored.read_bytes()
    assert Image.open(stored).tobytes() == Image.open(io.BytesIO(data)).tobytes()


def test_the_cv_uses_the_uploaded_photo(without_photo, tmp_path):
    daten = without_photo.kontext.daten
    before = build.main([str(daten / "cv.yaml"), "--build-dir", str(tmp_path / "b1"), "-o", str(tmp_path / "ohne.pdf")])
    upload(without_photo, jpeg_with_metadata())

    after = build.main([str(daten / "cv.yaml"), "--build-dir", str(tmp_path / "b2"), "-o", str(tmp_path / "mit.pdf")])

    def images(pdf) -> int:
        return sum(len(page.images) for page in pypdf.PdfReader(pdf).pages)
    assert images(before) == 0 and images(after) == 1


def test_the_upload_keeps_drafts_of_the_cv(without_photo):
    upload(without_photo, jpeg_with_metadata())

    notes = [e.beschreibung for e in without_photo.kontext.ablage.liste()]

    assert "Foto hochgeladen" in notes and "Stand vor: Foto hochgeladen" in notes


def test_a_second_photo_does_not_replace_the_first(without_photo):
    upload(without_photo, jpeg_with_metadata(orientation=1))
    first = (without_photo.kontext.daten / "foto.jpg").read_bytes()
    upload(without_photo, jpeg_with_metadata(orientation=3))

    drafts = without_photo.kontext.ablage.liste(without_photo.kontext.daten / "foto.jpg")

    assert (without_photo.kontext.daten / "foto.jpg").read_bytes() == first  # several photos since #129
    assert len(drafts) == 1


@pytest.mark.parametrize("data, message", [
    (b"kein Bild, nur Text", "Bitte ein Foto als JPG oder PNG"),
    (b"GIF89a" + b"\x00" * 40, "Bitte ein Foto als JPG oder PNG"),
    (jpeg_with_metadata()[:200], "liess sich nicht lesen"),
    (b"\x89PNG\r\n\x1a\n" + b"\x00" * 30, "liess sich nicht lesen"),
], ids=["text", "gif", "cut-jpeg", "empty-png"])
def test_an_invalid_image_gets_a_clear_message(without_photo, data, message):
    status, answer = upload(without_photo, data)

    assert status == 400
    assert message in answer["fehler"]
    assert not present(without_photo)
    assert not (without_photo.kontext.daten / "foto.jpg").exists()


def test_a_photo_above_the_limit_is_refused(without_photo, monkeypatch):
    monkeypatch.setattr(routen_foto, "MAX_PHOTO_BYTES", 1000)

    status, answer = upload(without_photo, jpeg_with_metadata() + b"\x00" * 1000)

    assert status == 400 and "zu gross" in answer["fehler"]


def test_without_a_cv_the_upload_asks_for_the_details_first(without_photo):
    (without_photo.kontext.daten / "cv.yaml").unlink()

    status, answer = upload(without_photo, jpeg_with_metadata())

    assert status == 400 and "Angaben" in answer["fehler"]


def test_the_page_offers_the_upload_without_a_photo(server):
    html = get(server, "/foto")[2].decode("utf-8")
    script = get(server, "/foto.js")[2].decode("utf-8")

    assert 'id="hochladen"' in html and 'type="file"' in html and 'accept="image/jpeg,image/png"' in html
    assert "/api/foto/hochladen" in script


def test_a_progressive_jpeg_loses_what_a_phone_appended(tmp_path):
    from PIL import ImageCms
    profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    out = io.BytesIO()
    Image.new("RGB", (64, 48), (10, 200, 30)).save(out, "JPEG", progressive=True, icc_profile=profile,
                                                   comment=b"Erfundener Kommentar")
    data = out.getvalue() + b"ftypmp42 erfundenes Video"

    kind, clean = photo_file.without_metadata(data)

    assert kind == "jpg"
    assert b"Video" not in clean and b"Erfundener Kommentar" not in clean
    stored = Image.open(io.BytesIO(clean))
    assert stored.info.get("icc_profile") == profile  # colours stay as they were
    assert stored.tobytes() == Image.open(io.BytesIO(data)).tobytes()
    assert not stored.getexif()  # upright already: no EXIF at all


def test_a_png_with_a_broken_checksum_does_not_read():
    data = bytearray(png_with_text())
    data[20] ^= 0xFF  # inside IHDR

    with pytest.raises(ValueError, match="liess sich nicht lesen"):
        photo_file.without_metadata(bytes(data))
