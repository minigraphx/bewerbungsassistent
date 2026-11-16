"""The live preview in „Lebenslauf erstellen“ (G76, #294): the CV as the app builds it, from the choice not yet taken.

The preview is built into a temporary folder and kept in memory; it never writes to the data folder, nothing of it
goes to the AI, and a failed build answers with a message instead of an old preview.
"""
import io
import json
import struct

import pypdf
import pytest

import cv_creation
import cv_preview
import routes_ai
import unterlagen
from register import Register
from sample_folder import BRIEF_ID
from test_app import get, post, server  # noqa: F401  (server is a fixture)

ROUTE = "/api/lebenslauf/erstellen"
PREVIEW = f"{ROUTE}/vorschau"
PNG = b"\x89PNG\r\n\x1a\n"
SMALL_WIDTH_PX = 600  # 300 pt at 144 ppi: sharp beside the choices on a retina screen
LARGE_WIDTH_PX = 1190  # A4 width (595 pt) at 144 ppi for «Gross ansehen»


def form(s) -> dict:
    status, _, body = get(s, ROUTE, id=BRIEF_ID)
    assert status == 200, body
    return json.loads(body)


def choice(answer: dict, **changes) -> dict:
    return {"id": BRIEF_ID, "stand": answer["stand"], "stationen": {"work": [1, 0], "education": [0]},
            "berufsbezeichnung": "Data Engineer", "kurzprofil": "Baut Datenpipelines.",
            "design": "einspaltig", "bezeichnung": "Daten, Beispiel AG", **changes}


def preview(s, body: dict) -> dict:
    status, answer = post(s, PREVIEW, body)
    assert status == 200, answer
    return answer


def preview_pdf(s, key: str) -> bytes:
    status, kind, body = get(s, f"{PREVIEW}/pdf", id=BRIEF_ID, schluessel=key)
    assert (status, kind) == (200, "application/pdf"), body
    return body


def pdf_text(data: bytes) -> str:
    return " ".join(page.extract_text() for page in pypdf.PdfReader(io.BytesIO(data)).pages)


def png_width(data: bytes) -> int:
    return struct.unpack(">II", data[16:24])[0]


def files(folder) -> dict[str, tuple[int, int]]:
    return {str(path.relative_to(folder)): (path.stat().st_mtime_ns, path.stat().st_size)
            for path in sorted(folder.rglob("*")) if path.is_file()}


def test_the_preview_is_the_cv_of_the_choice_with_its_page_count(server):  # noqa: F811
    answer = preview(server, choice(form(server)))

    assert answer["seiten"] >= 1 and answer["schluessel"]
    built = preview_pdf(server, answer["schluessel"])
    assert len(pypdf.PdfReader(io.BytesIO(built)).pages) == answer["seiten"]
    text = pdf_text(built)
    assert "Data Engineer" in text and "Baut Datenpipelines." in text


def test_the_preview_follows_every_change_of_content_and_looks(server):  # noqa: F811
    opened = form(server)
    first = preview(server, choice(opened))
    fewer = preview(server, choice(opened, stationen={"work": [0], "education": [0]}, kurzprofil="Kurz."))
    other_look = preview(server, choice(opened, design="zweispaltig"))

    assert len({first["schluessel"], fewer["schluessel"], other_look["schluessel"]}) == 3
    text = pdf_text(preview_pdf(server, fewer["schluessel"]))
    assert "Muster GmbH" not in text and "Kurz." in text
    assert "Muster GmbH" in pdf_text(preview_pdf(server, first["schluessel"]))


def test_the_pages_come_as_png_small_beside_the_choice_and_large_for_a_closer_look(server):  # noqa: F811
    answer = preview(server, choice(form(server)))

    status, kind, small = get(server, f"{PREVIEW}/seite", id=BRIEF_ID, schluessel=answer["schluessel"], seite="1")
    assert (status, kind) == (200, "image/png") and small.startswith(PNG)
    assert png_width(small) == SMALL_WIDTH_PX
    for page in range(1, answer["seiten"] + 1):
        status, kind, large = get(server, f"{PREVIEW}/seite", id=BRIEF_ID, schluessel=answer["schluessel"],
                                  seite=str(page), groesse="gross")
        assert (status, kind) == (200, "image/png") and png_width(large) == LARGE_WIDTH_PX, page


@pytest.mark.parametrize("parameters", [
    {"schluessel": "unbekannt", "seite": "1"},
    {"seite": "99"},
    {"seite": "0"},
])
def test_an_unknown_preview_or_page_is_not_found(server, parameters):  # noqa: F811
    answer = preview(server, choice(form(server)))
    asked = {"id": BRIEF_ID, "schluessel": answer["schluessel"], **parameters}

    assert get(server, f"{PREVIEW}/seite", **asked)[0] in (400, 404)


def test_building_the_preview_writes_nothing_into_the_data_folder_and_leaves_no_temporary_files(server):  # noqa: F811
    daten, build = server.kontext.daten, server.kontext.build
    opened = form(server)
    before = files(daten)

    preview(server, choice(opened))

    assert files(daten) == before
    assert not unterlagen.pdf_pfade(daten, BRIEF_ID)["lebenslauf"].exists()
    assert Register(daten).hole(BRIEF_ID)["variante"] == "daten"
    assert not [path for path in build.rglob("*") if "vorschau" in path.name]


def test_nothing_goes_to_the_ai_for_the_preview(server, monkeypatch):  # noqa: F811
    created = []

    def refuse():
        created.append(True)
        raise AssertionError("an AI client was created")

    monkeypatch.setattr(routes_ai, "new_client", refuse)

    preview(server, choice(form(server)))

    assert created == []


def test_a_failed_build_points_to_meine_angaben_with_the_details_and_leaves_nothing_behind(server):  # noqa: F811
    daten, build = server.kontext.daten, server.kontext.build
    cv = daten / "cv.yaml"
    cv.write_text(cv.read_text(encoding="utf-8").replace("basics:\n", "basics:\n  x-image: {spiegel: ja}\n", 1),
                  encoding="utf-8")

    status, answer = post(server, PREVIEW, choice(form(server)))

    assert status == 400
    assert answer["aktion"] == cv_preview.CHECK_DATA, "the page names Meine Angaben and shows the details"
    assert "x-image" in answer["fehler"], "the details under «Genauer»"
    assert not [path for path in build.rglob("*") if "vorschau" in path.name]


def test_a_build_that_breaks_inside_points_to_meine_angaben_without_its_internals(server, monkeypatch):  # noqa: F811
    def broken(argv):
        raise OSError("disk full")

    monkeypatch.setattr(unterlagen.lebenslauf_modul, "main", broken)

    status, answer = post(server, PREVIEW, choice(form(server)))

    assert status == 400 and answer["aktion"] == cv_preview.CHECK_DATA
    assert "disk full" not in answer["fehler"]


def test_meine_angaben_that_cannot_be_read_point_there_too(server):  # noqa: F811
    opened = form(server)
    (server.kontext.daten / "cv.yaml").write_text("basics: [kaputt\n", encoding="utf-8")

    status, answer = post(server, PREVIEW, choice(opened))

    assert status == 400 and answer["aktion"] == cv_preview.CHECK_DATA


def test_meine_angaben_changed_elsewhere_asks_to_open_the_panel_again(server):  # noqa: F811
    status, answer = post(server, PREVIEW, choice(form(server), stand="anders"))

    assert status == 400 and answer["aktion"] == cv_preview.REOPEN
    assert answer["fehler"] == cv_creation.CHANGED


def test_the_sentences_that_name_the_panel_quote_it_with_guillemets():
    for sentence in (cv_creation.CHANGED, cv_creation.WRONG_STATION):
        assert "«Lebenslauf erstellen»" in sentence and "„" not in sentence


@pytest.mark.parametrize("changes", [
    {"stationen": {"work": [], "education": []}},
    {"design": "dossier-siegel"},
])
def test_a_choice_that_cannot_be_built_is_refused_with_its_reason(server, changes):  # noqa: F811
    status, answer = post(server, PREVIEW, choice(form(server), **changes))

    assert status == 400 and answer["fehler"]


def test_only_the_last_previews_are_kept(server):  # noqa: F811
    opened = form(server)
    keys = [preview(server, choice(opened, kurzprofil=f"Fassung {number}."))["schluessel"] for number in range(5)]

    assert get(server, f"{PREVIEW}/pdf", id=BRIEF_ID, schluessel=keys[0])[0] == 404
    assert get(server, f"{PREVIEW}/pdf", id=BRIEF_ID, schluessel=keys[-1])[0] == 200


def test_a_sent_application_gets_no_preview(server):  # noqa: F811
    daten = server.kontext.daten
    opened = form(server)
    register = Register(daten)
    register.speichere({**register.hole(BRIEF_ID), "versand": {"datum": "2026-10-20", "art": "elektronisch"}})

    status, refused = post(server, PREVIEW, choice(opened))

    assert status == 400 and refused["fehler"] == unterlagen.SENT_STAYS
