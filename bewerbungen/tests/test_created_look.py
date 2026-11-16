"""Photo, colour and mark of one CV in „Lebenslauf erstellen“ (G77, #295).

Under «Aussehen» the person also chooses whether this CV carries a photo, and its colour and mark. The defaults are
those of „Lebenslauf und Dateien“ (G61, G62); the choice is saved with the created variant and used when it is built
and in the preview (G76); other CVs stay as they are. All data is invented.
"""
import json
import pathlib
import shutil

import pytest
import yaml

import build
import created_look
import unterlagen
from register import Register
from sample_folder import BRIEF_ID
from test_app import get, post, server  # noqa: F401  (server is a fixture)

ROUTE = "/api/lebenslauf/erstellen"
PREVIEW = f"{ROUTE}/vorschau"
WINE = "#7a2e3a"
CHOSEN = {"foto": False, "zeichen": "ring", "akzent": WINE}


def form(s) -> dict:
    status, _, body = get(s, ROUTE, id=BRIEF_ID)
    assert status == 200, body
    return json.loads(body)


def choice(answer: dict, **changes) -> dict:
    return {"id": BRIEF_ID, "stand": answer["stand"], "stationen": {"work": [1, 0], "education": [0]},
            "berufsbezeichnung": "Data Engineer", "kurzprofil": "Baut Datenpipelines.", "design": "zweispaltig",
            "bezeichnung": "Daten, Beispiel AG", **changes}


def entry(s) -> dict:
    return Register(s.kontext.daten).hole(BRIEF_ID)


def built_cv(s, tmp_path: pathlib.Path) -> dict:
    folder = tmp_path / "bau"
    unterlagen.baue(s.kontext.daten, entry(s), folder)
    return json.loads((folder / "cv.json").read_text(encoding="utf-8"))


def job(s) -> dict:
    return yaml.safe_load((s.kontext.daten / "jobs" / f"{BRIEF_ID}.yaml").read_text(encoding="utf-8"))


def add_logo(s) -> None:
    daten = s.kontext.daten
    (daten / "logos").mkdir()
    shutil.copy(build.ROOT / "tests" / "halbe.png", daten / "logos" / "logo.png")
    cv = daten / "cv.yaml"
    cv.write_text(cv.read_text(encoding="utf-8").replace("basics:\n", "basics:\n  x-logo: logos/logo.png\n", 1),
                  encoding="utf-8")


# What the panel offers


def test_the_defaults_are_those_of_lebenslauf_und_dateien(server):  # noqa: F811
    answer = form(server)

    assert answer["aussehen"] == {"foto": True, "zeichen": "passend", "akzent": "passend"}
    assert answer["aussehen_angebot"] == {"foto_vorhanden": True, "initialen": "EB", "logo": False}


def test_with_the_photo_turned_off_there_the_cv_starts_without_it(server):  # noqa: F811
    post(server, "/api/foto/zeigen", {"zeigen": False})

    assert form(server)["aussehen"]["foto"] is False


def test_a_logo_of_the_person_is_offered_as_mark(server):  # noqa: F811
    add_logo(server)

    assert form(server)["aussehen_angebot"]["logo"] is True


# Saved with the variant


def test_the_choice_is_saved_with_the_created_variant_and_shown_again(server):  # noqa: F811
    status, answer = post(server, ROUTE, choice(form(server), aussehen=CHOSEN))

    assert status == 200, answer
    assert job(server)[created_look.KEY] == CHOSEN
    assert form(server)["aussehen"] == CHOSEN


def test_without_a_choice_from_the_page_the_defaults_are_saved(server):  # noqa: F811
    post(server, ROUTE, choice(form(server)))

    assert job(server)[created_look.KEY] == {"foto": True, "zeichen": "passend", "akzent": "passend"}


@pytest.mark.parametrize("look, message", [
    ({**CHOSEN, "foto": "nein"}, created_look.BAD_PHOTO),
    ({**CHOSEN, "zeichen": "stern"}, "Unbekanntes Zeichen"),
    ({**CHOSEN, "akzent": "#f0f0f0"}, "Zu hell"),
    ({**CHOSEN, "zeichen": "logo"}, created_look.NO_LOGO),
    ("schlicht", created_look.BAD_LOOK),
])
def test_a_choice_that_cannot_be_drawn_is_refused_before_anything_is_written(server, look, message):  # noqa: F811
    status, answer = post(server, ROUTE, choice(form(server), aussehen=look))

    assert status == 400 and message in answer["fehler"]
    assert not (server.kontext.daten / "jobs" / f"{BRIEF_ID}.yaml").exists()


def test_the_interlaced_mark_needs_two_initials(server):  # noqa: F811
    cv = server.kontext.daten / "cv.yaml"
    cv.write_text(cv.read_text(encoding="utf-8").replace("basics:\n", "basics:\n  x-monogramm: EBX\n", 1),
                  encoding="utf-8")

    status, answer = post(server, ROUTE, choice(form(server), aussehen={**CHOSEN, "zeichen": "verschraenkt"}))

    assert status == 400 and answer["fehler"] == created_look.NEEDS_TWO


# Used when it is built


def test_the_built_cv_follows_the_choice(server, tmp_path):  # noqa: F811
    post(server, ROUTE, choice(form(server), aussehen=CHOSEN))

    cv = built_cv(server, tmp_path)

    assert "image" not in cv["basics"]
    assert cv["x-aussehen"]["akzent"] == WINE and cv["x-aussehen"]["zeichen"]["variant"] == "ring"


def test_the_photo_of_this_cv_goes_before_the_switch_on_lebenslauf_und_dateien(server, tmp_path):  # noqa: F811
    post(server, "/api/foto/zeigen", {"zeigen": False})
    post(server, ROUTE, choice(form(server), aussehen={**CHOSEN, "foto": True}))

    assert built_cv(server, tmp_path)["basics"]["image"].endswith("foto.png")


def test_the_own_logo_becomes_the_mark_of_this_cv(server, tmp_path):  # noqa: F811
    add_logo(server)
    post(server, ROUTE, choice(form(server), aussehen={**CHOSEN, "zeichen": "logo"}))

    assert built_cv(server, tmp_path)["x-aussehen"]["zeichen"]["variant"] == "logo"


def test_a_dossier_takes_the_photo_of_this_cv_and_keeps_its_own_colour_and_mark(server, tmp_path):  # noqa: F811
    post(server, ROUTE, choice(form(server), aussehen=CHOSEN))
    register = Register(server.kontext.daten)
    register.speichere({**register.hole(BRIEF_ID), "unterlagen": "dossier"})
    folder = tmp_path / "bau"

    unterlagen.baue(server.kontext.daten, entry(server), folder)

    dossier = json.loads((folder / "dossier.json").read_text(encoding="utf-8"))
    assert dossier["person"]["photo"] is None
    assert dossier["style"]["farbe-akzent"] != WINE and dossier["person"]["mark"]["variant"] == "passend"


# Other CVs stay as they are


def test_a_variant_of_claude_builds_as_before(server, tmp_path):  # noqa: F811
    register = Register(server.kontext.daten)
    register.speichere({**register.hole(BRIEF_ID), "variante": "daten"})

    cv = built_cv(server, tmp_path)

    assert "x-aussehen" not in cv and cv["basics"]["image"].endswith("foto.png")


def test_the_whole_cv_without_variant_builds_as_before(server, tmp_path):  # noqa: F811
    register = Register(server.kontext.daten)
    register.speichere({**register.hole(BRIEF_ID), "variante": None})
    (server.kontext.daten / "varianten.yaml").write_text("[]\n", encoding="utf-8")

    assert "x-aussehen" not in built_cv(server, tmp_path)


def test_the_dossier_choice_of_mark_and_colour_does_not_reach_a_created_cv(server, tmp_path):  # noqa: F811
    post(server, "/api/dossier/zeichen", {"zeichen": "block", "akzent": WINE})
    post(server, ROUTE, choice(form(server)))

    assert "x-aussehen" not in built_cv(server, tmp_path)


# The preview follows


def preview(s, body: dict) -> str:
    status, answer = post(s, PREVIEW, body)
    assert status == 200, answer
    return answer["schluessel"]


def test_the_preview_follows_photo_colour_and_mark(server):  # noqa: F811
    opened = form(server)
    plain = choice(opened, aussehen={"foto": True, "zeichen": "passend", "akzent": "passend"})

    keys = {preview(server, plain), preview(server, {**plain, "aussehen": {**plain["aussehen"], "foto": False}}),
            preview(server, {**plain, "aussehen": {**plain["aussehen"], "zeichen": "ring"}}),
            preview(server, {**plain, "aussehen": {**plain["aussehen"], "akzent": WINE}})}

    assert len(keys) == 4


def test_a_preview_with_a_choice_that_cannot_be_drawn_says_why(server):  # noqa: F811
    status, answer = post(server, PREVIEW, choice(form(server), aussehen={**CHOSEN, "zeichen": "logo"}))

    assert status == 400 and answer["fehler"] == created_look.NO_LOGO
