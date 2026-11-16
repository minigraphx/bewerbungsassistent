"""The step «Unterlagen erstellen und prüfen» (#321, G40, G41): page 1 of each document as a thumbnail, the old name gone."""
import struct

import unterlagen
from routes_apply import CONFIRM_FIRST
from sample_folder import BRIEF_ID
from test_app import get, post, server  # noqa: F401  (server is a fixture)

PNG = b"\x89PNG\r\n\x1a\n"
THUMB_WIDTH_PX = 288  # 144 pt at 144 ppi: sharp at 72 to 144 CSS pixels on a retina screen


def png_size(data: bytes) -> tuple[int, int]:
    return struct.unpack(">II", data[16:24])


def test_the_thumbnail_is_page_one_of_the_built_cv_as_png(server):
    post(server, "/api/unterlagen", {}, id=BRIEF_ID)

    status, kind, body = get(server, "/api/pdf/miniatur", id=BRIEF_ID, art="lebenslauf")

    assert (status, kind) == (200, "image/png") and body.startswith(PNG)
    width, height = png_size(body)
    assert width == THUMB_WIDTH_PX and height > width, "A4 upright"


def test_the_letter_and_the_chosen_dossier_have_thumbnails_too(server):
    post(server, "/api/bewerbung", {"id": BRIEF_ID, "unterlagen": "dossier"})
    post(server, "/api/unterlagen", {}, id=BRIEF_ID)

    for art in ("anschreiben", "dossier"):
        status, kind, body = get(server, "/api/pdf/miniatur", id=BRIEF_ID, art=art)
        assert (status, kind) == (200, "image/png") and body.startswith(PNG), art


def test_no_thumbnail_before_building_or_for_an_unknown_or_unchosen_document(server):
    assert get(server, "/api/pdf/miniatur", id=BRIEF_ID, art="lebenslauf")[0] == 404
    post(server, "/api/unterlagen", {}, id=BRIEF_ID)
    assert get(server, "/api/pdf/miniatur", id=BRIEF_ID, art="cv")[0] == 400
    assert get(server, "/api/pdf/miniatur", id=BRIEF_ID, art="dossier")[0] == 400


def test_an_own_pdf_that_cannot_be_read_gets_a_message_not_a_crash(server):
    own = server.kontext.daten / unterlagen.OWN_CV
    own.parent.mkdir(parents=True, exist_ok=True)
    own.write_bytes(b"%PDF-1.4\n" + b"x" * 300)
    post(server, "/api/bewerbung", {"id": BRIEF_ID, "variante": ""})

    status, kind, body = get(server, "/api/pdf/miniatur", id=BRIEF_ID, art="lebenslauf")

    assert status == 400 and "Vorschau" in body.decode("utf-8")


def test_the_form_stays_closed_with_the_name_of_the_new_step():
    assert CONFIRM_FIRST == "Bitte zuerst unter «Unterlagen erstellen und prüfen» ansehen und mit «So lassen» bestätigen."


def test_the_page_loads_the_logic_of_the_step(server):
    _, _, page = get(server, "/bewerbung", id=BRIEF_ID)
    script = get(server, "/unterlagen-ergebnis.js")

    assert script[0] == 200
    assert page.decode("utf-8").index("/unterlagen-ergebnis.js") < page.decode("utf-8").index("/bewerbung.js")
