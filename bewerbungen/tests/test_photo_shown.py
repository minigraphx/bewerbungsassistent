"""„Im Lebenslauf zeigen“ with the active photo on „Lebenslauf und Dateien“ (G62, #281).

On by default once a photo exists; off builds new CVs and dossiers without the photo. What is built or sent stays.
"""
import json
import pathlib

import pytest
import yaml

import inhalte
import page_limit
import photo_shown
import unterlagen
from register import Register
from sample_folder import BRIEF_ID
from test_app import get, post, server  # noqa: F401  (server is a fixture)

ROUTE = "/api/foto/zeigen"


def _listing(s) -> dict:
    status, _, body = get(s, "/api/foto/liste")
    assert status == 200, body
    return json.loads(body)


def _built_basics(build: pathlib.Path) -> dict:
    return json.loads((build / "cv.json").read_text(encoding="utf-8"))["basics"]


def _entry(s) -> dict:
    return Register(s.kontext.daten).hole(BRIEF_ID)


def test_without_a_choice_the_photo_is_shown(tmp_path):
    assert photo_shown.load(tmp_path) is True


def test_a_broken_or_strange_file_shows_the_photo(tmp_path):
    (tmp_path / photo_shown.FILE).write_text("foto_im_lebenslauf: [kaputt", encoding="utf-8")
    assert photo_shown.load(tmp_path) is True
    (tmp_path / photo_shown.FILE).write_text("foto_im_lebenslauf: vielleicht\n", encoding="utf-8")
    assert photo_shown.load(tmp_path) is True


@pytest.mark.parametrize("values", [{"zeigen": "nein"}, {"zeigen": 0}, {}, "aus", None])
def test_only_on_or_off_can_be_chosen(values):
    with pytest.raises(ValueError, match=photo_shown.BAD_VALUE):
        photo_shown.parse(values)


def test_the_list_of_photos_says_the_photo_is_shown_by_default(server):  # noqa: F811
    assert _listing(server)["zeigen"] is True


def test_turning_it_off_is_stored_with_drafts_and_read_back(server):  # noqa: F811
    folder = server.kontext.daten

    status, answer = post(server, ROUTE, {"zeigen": False})

    assert status == 200 and answer == {"zeigen": False}
    assert yaml.safe_load((folder / photo_shown.FILE).read_text(encoding="utf-8"))["foto_im_lebenslauf"] is False
    assert _listing(server)["zeigen"] is False
    post(server, ROUTE, {"zeigen": True})
    assert photo_shown.load(folder) is True
    assert len(server.kontext.ablage.liste(folder / photo_shown.FILE)) >= 2


def test_a_bad_value_gets_a_german_error(server):  # noqa: F811
    status, answer = post(server, ROUTE, {"zeigen": "ja"})

    assert status == 400 and answer["fehler"] == photo_shown.BAD_VALUE


def test_the_switch_and_the_page_limit_share_their_file_without_losing_each_other(server):  # noqa: F811
    folder = server.kontext.daten
    post(server, "/api/unterlagen/seitengrenze", {"lebenslauf_seiten": 3})

    post(server, ROUTE, {"zeigen": False})
    post(server, "/api/unterlagen/seitengrenze", {"lebenslauf_seiten": 3})

    assert page_limit.load(folder) == 3 and photo_shown.load(folder) is False


def test_turning_it_off_keeps_the_photo_active_and_the_cv_file_unchanged(server):  # noqa: F811
    cv = server.kontext.daten / "cv.yaml"
    before = cv.read_text(encoding="utf-8")

    post(server, ROUTE, {"zeigen": False})

    assert cv.read_text(encoding="utf-8") == before
    assert [p["aktiv"] for p in _listing(server)["fotos"]] == [True]


def test_neither_the_extension_nor_claude_reach_the_switch():
    desktop = pathlib.Path(__file__).resolve().parents[2] / "desktop"
    for name in ("native_host.py", "mcp_tools.py"):
        assert ROUTE not in (desktop / name).read_text(encoding="utf-8")


# Builds


def test_by_default_a_new_cv_carries_the_active_photo(server, tmp_path):  # noqa: F811
    build = tmp_path / "bau"

    unterlagen.baue(server.kontext.daten, _entry(server), build)

    assert _built_basics(build)["image"].endswith("foto.png")


def test_switched_off_a_new_cv_has_no_photo(server, tmp_path):  # noqa: F811
    post(server, ROUTE, {"zeigen": False})
    build = tmp_path / "bau"

    unterlagen.baue(server.kontext.daten, _entry(server), build)

    assert "image" not in _built_basics(build) and "x-image" not in _built_basics(build)


def test_switched_off_the_whole_cv_without_variant_has_no_photo(server, tmp_path):  # noqa: F811
    register = Register(server.kontext.daten)
    register.speichere({**register.hole(BRIEF_ID), "variante": None})
    (server.kontext.daten / "varianten.yaml").write_text("[]\n", encoding="utf-8")
    post(server, ROUTE, {"zeigen": False})
    build = tmp_path / "bau"

    unterlagen.baue(server.kontext.daten, _entry(server), build)

    assert "image" not in _built_basics(build)


def test_switched_off_a_new_dossier_has_no_photo(server, tmp_path):  # noqa: F811
    register = Register(server.kontext.daten)
    register.speichere({**register.hole(BRIEF_ID), "unterlagen": "dossier"})
    post(server, ROUTE, {"zeigen": False})
    build = tmp_path / "bau"

    unterlagen.baue(server.kontext.daten, _entry(server), build)

    assert json.loads((build / "dossier.json").read_text(encoding="utf-8"))["person"]["photo"] is None


def test_switched_on_a_new_dossier_carries_the_photo(server, tmp_path):  # noqa: F811
    register = Register(server.kontext.daten)
    register.speichere({**register.hole(BRIEF_ID), "unterlagen": "dossier"})
    build = tmp_path / "bau"

    unterlagen.baue(server.kontext.daten, _entry(server), build)

    assert json.loads((build / "dossier.json").read_text(encoding="utf-8"))["person"]["photo"].endswith("foto.png")


def test_switched_off_the_preview_of_the_cv_has_no_photo(server, tmp_path):  # noqa: F811
    folder = server.kontext.daten
    post(server, ROUTE, {"zeigen": False})
    build = tmp_path / "bau"

    inhalte.pruefe_inhalt(folder, "cv.yaml", (folder / "cv.yaml").read_text(encoding="utf-8"), build)

    assert "image" not in _built_basics(build)


def test_documents_built_before_stay_as_they_are(server, tmp_path):  # noqa: F811
    folder = server.kontext.daten
    built = unterlagen.baue(folder, _entry(server), tmp_path / "bau")
    before = built["lebenslauf"].read_bytes()

    post(server, ROUTE, {"zeigen": False})

    assert built["lebenslauf"].read_bytes() == before
    assert unterlagen.wirksame_pdfs(folder, _entry(server))["lebenslauf"] == built["lebenslauf"]
