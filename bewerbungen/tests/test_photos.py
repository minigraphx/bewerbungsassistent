"""Several photos on the page Foto, one of them active (#129, G21). Test images are generated here."""
import io
import json

import pypdf
import yaml
from PIL import Image

import build
from test_app import get, post, server  # noqa: F401  (server is a fixture)
from test_photo_upload import upload

FIRST = "foto.png"  # the photo of the sample folder in the fixture, as a folder from before #129 has it


def jpeg(width: int, height: int, colour=(90, 140, 200)) -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (width, height), colour).save(out, "JPEG")
    return out.getvalue()


def photos(s) -> list[dict]:
    status, _, body = get(s, "/api/foto/liste")
    assert status == 200, body
    return json.loads(body)["fotos"]


def active(s) -> str:
    return next(p["datei"] for p in photos(s) if p["aktiv"])


def cv(s) -> dict:
    return yaml.safe_load((s.kontext.daten / "cv.yaml").read_text(encoding="utf-8"))


def test_a_folder_with_one_photo_has_it_as_the_first_active_photo_without_a_step(server):
    assert photos(server) == [{"datei": FIRST, "aktiv": True}]
    assert not (server.kontext.daten / "fotos.yaml").exists()


def test_a_second_upload_adds_a_photo_and_keeps_the_first(server):
    before = (server.kontext.daten / FIRST).read_bytes()

    status, answer = upload(server, jpeg(80, 120))

    assert status == 200, answer
    listed = photos(server)
    assert [p["datei"] for p in listed][0] == FIRST and len(listed) == 2
    assert (server.kontext.daten / FIRST).read_bytes() == before
    new = active(server)
    assert new != FIRST and new.startswith("fotos/") and (server.kontext.daten / new).is_file()
    assert cv(server)["basics"]["image"] == new


def test_each_photo_keeps_its_own_crop(server):
    post(server, "/api/foto/speichern", {"mirror": True, "zoom": 1.5, "x": 0.4, "y": 0.2})
    upload(server, jpeg(80, 120))
    second = active(server)
    post(server, "/api/foto/speichern", {"mirror": False, "zoom": 2, "x": 0.6, "y": 0.7})

    status, answer = post(server, "/api/foto/aktiv", {"datei": FIRST})

    assert status == 200, answer
    assert cv(server)["basics"]["image"] == FIRST
    assert cv(server)["basics"]["x-image"] == {"mirror": True, "zoom": 1.5, "x": 0.4, "y": 0.2}
    post(server, "/api/foto/aktiv", {"datei": second})
    assert cv(server)["basics"]["x-image"] == {"mirror": False, "zoom": 2, "x": 0.6, "y": 0.7}


def test_switching_keeps_drafts_of_the_cv(server):
    upload(server, jpeg(80, 120))

    post(server, "/api/foto/aktiv", {"datei": FIRST})

    drafts = server.kontext.ablage.liste(server.kontext.daten / "cv.yaml")
    # the state before is the one the upload saved; the drafts keep each content once
    assert [d.beschreibung for d in drafts][:2] == ["Aktives Foto gewechselt", "Foto hochgeladen"]
    assert yaml.safe_load(server.kontext.ablage.inhalt(drafts[1].id))["basics"]["image"].startswith("fotos/")


def test_a_new_cv_uses_the_active_photo(server, tmp_path):
    upload(server, jpeg(80, 120))
    cv_file = server.kontext.daten / "cv.yaml"

    def image_size(name: str) -> tuple[int, int]:
        pdf = build.main([str(cv_file), "--build-dir", str(tmp_path / name), "-o", str(tmp_path / f"{name}.pdf")])
        image = next(img for page in pypdf.PdfReader(pdf).pages for img in page.images)
        return image.image.size

    assert image_size("neu") == (80, 120)
    post(server, "/api/foto/aktiv", {"datei": FIRST})
    assert image_size("alt") == Image.open(server.kontext.daten / FIRST).size


def test_a_photo_that_is_not_active_can_be_deleted_and_stays_in_the_drafts(server):
    before = (server.kontext.daten / FIRST).read_bytes()
    upload(server, jpeg(80, 120))

    status, answer = post(server, "/api/foto/loeschen", {"datei": FIRST})

    assert status == 200, answer
    assert [p["datei"] for p in photos(server)] == [active(server)]
    assert not (server.kontext.daten / FIRST).exists()
    drafts = server.kontext.ablage.liste(server.kontext.daten / FIRST)
    assert any(server.kontext.ablage.inhalt(d.id) == before for d in drafts)


def test_the_active_photo_cannot_be_deleted(server):
    status, answer = post(server, "/api/foto/loeschen", {"datei": FIRST})

    assert status == 400 and "aktiv" in answer["fehler"]
    assert (server.kontext.daten / FIRST).is_file()


def test_an_old_version_keeps_its_photo(server):
    old_photo = (server.kontext.daten / FIRST).read_bytes()
    upload(server, jpeg(80, 120))
    post(server, "/api/foto/loeschen", {"datei": FIRST})

    ablage = server.kontext.ablage
    old_cvs = [yaml.safe_load(ablage.inhalt(d.id)) for d in ablage.liste(server.kontext.daten / "cv.yaml")
               if d.beschreibung == "Stand vor: Foto hochgeladen"]
    assert [c["basics"]["image"] for c in old_cvs] == [FIRST]
    assert any(ablage.inhalt(d.id) == old_photo for d in ablage.liste(server.kontext.daten / FIRST))


def test_only_listed_photos_can_be_chosen_or_deleted(server):
    (server.kontext.daten / "anderes.png").write_bytes((server.kontext.daten / FIRST).read_bytes())

    for route in ("/api/foto/aktiv", "/api/foto/loeschen"):
        for name in ("anderes.png", "../ausserhalb.png", "cv.yaml"):
            status, _ = post(server, route, {"datei": name})
            assert status in (400, 404), (route, name)
    assert (server.kontext.daten / "anderes.png").is_file() and cv(server)["basics"]["image"] == FIRST


def test_the_same_photo_uploaded_twice_is_listed_once(server):
    data = jpeg(80, 120)
    upload(server, data)
    upload(server, data)

    assert len(photos(server)) == 2


def test_each_photo_can_be_shown(server):
    upload(server, jpeg(80, 120))

    for photo in photos(server):
        status, kind, body = get(server, "/api/foto/bild", datei=photo["datei"])
        assert status == 200 and kind.startswith("image/") and body


def test_the_page_lists_the_photos_with_choose_and_delete(server):
    html = get(server, "/foto")[2].decode("utf-8")
    script = get(server, "/foto.js")[2].decode("utf-8")

    assert 'id="fotos"' in html
    for route in ("/api/foto/liste", "/api/foto/aktiv", "/api/foto/loeschen"):
        assert route in script
