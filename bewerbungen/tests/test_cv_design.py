"""The design the app builds the CV with, chosen on „Lebenslauf und Dateien“ with „Aussehen wählen“ (G61, #280)."""
import json

import pytest

import cv_design
import inhalte
import unterlagen
from register import Register, pruefe_bewerbung
from sample_folder import BRIEF_ID
from test_app import get, post, server  # noqa: F401  (server is a fixture)

ROUTE = "/api/dateien/aussehen"


def spy_on_builds(monkeypatch) -> list[list[str]]:
    """Every CV build goes through lebenslauf/build.py; record its arguments and build for real."""
    calls = []
    real = unterlagen.lebenslauf_modul.main

    def recording(argv):
        calls.append(list(argv))
        return real(argv)

    monkeypatch.setattr(unterlagen.lebenslauf_modul, "main", recording)
    return calls


def theme_of(argv: list[str]) -> str | None:
    return argv[argv.index("--theme") + 1] if "--theme" in argv else None


def test_without_a_choice_the_cv_is_two_columns(datenordner):
    assert cv_design.load(datenordner) == "zweispaltig"
    assert cv_design.for_application(datenordner, Register(datenordner).hole(BRIEF_ID)) == "zweispaltig"


def test_the_page_reads_the_choice_and_the_designs(server):  # noqa: F811
    status, _, body = get(server, ROUTE)

    assert status == 200
    answer = json.loads(body)
    assert answer["design"] == "zweispaltig"
    assert answer["designs"] == ["zweispaltig", "einspaltig"]


def test_the_choice_is_stored_with_drafts_before_and_after(server):  # noqa: F811
    daten = server.kontext.daten
    post(server, ROUTE, {"design": "zweispaltig"})

    status, answer = post(server, ROUTE, {"design": "einspaltig"})

    assert status == 200 and answer["design"] == "einspaltig"
    assert cv_design.load(daten) == "einspaltig"
    assert len(server.kontext.ablage.liste(daten / cv_design.FILE)) >= 2


@pytest.mark.parametrize("wrong", ["dossier-siegel", "../cv", "", None, 3])
def test_an_unknown_design_is_refused_and_nothing_is_stored(server, wrong):  # noqa: F811
    status, answer = post(server, ROUTE, {"design": wrong})

    assert status == 400
    assert "Zweispaltig" in answer["fehler"] and "Einspaltig" in answer["fehler"]
    assert not (server.kontext.daten / cv_design.FILE).exists()


def test_a_stored_design_the_app_does_not_know_falls_back_to_the_preset(datenordner):
    (datenordner / cv_design.FILE).write_text("lebenslauf: barock\n", encoding="utf-8")

    assert cv_design.load(datenordner) == "zweispaltig"


def test_a_new_cv_build_uses_the_chosen_design(datenordner, tmp_path, monkeypatch):
    calls = spy_on_builds(monkeypatch)
    cv_design.save(datenordner, "einspaltig")

    built = unterlagen.baue(datenordner, Register(datenordner).hole(BRIEF_ID), tmp_path / "build")

    assert [theme_of(argv) for argv in calls] == ["einspaltig"]
    assert built["lebenslauf"].is_file()


def test_the_whole_cv_without_variants_uses_the_chosen_design(datenordner, tmp_path, monkeypatch):
    (datenordner / "varianten.yaml").unlink()
    calls = spy_on_builds(monkeypatch)
    cv_design.save(datenordner, "einspaltig")
    entry = {key: value for key, value in Register(datenordner).hole(BRIEF_ID).items() if key != "variante"}

    unterlagen.baue(datenordner, entry, tmp_path / "build")

    assert [theme_of(argv) for argv in calls] == ["einspaltig"]


def test_choosing_a_design_leaves_existing_versions_unchanged(server, tmp_path):  # noqa: F811
    daten = server.kontext.daten
    entry = Register(daten).hole(BRIEF_ID)
    built = unterlagen.baue(daten, entry, tmp_path / "build")
    before = {kind: path.read_bytes() for kind, path in built.items()}
    drafts = {draft.id for draft in server.kontext.ablage.liste()}

    assert post(server, ROUTE, {"design": "einspaltig"})[0] == 200

    assert {kind: path.read_bytes() for kind, path in built.items()} == before
    new_drafts = [draft for draft in server.kontext.ablage.liste() if draft.id not in drafts]
    assert {draft.datei for draft in new_drafts} == {cv_design.FILE}


def test_one_application_keeps_a_design_of_its_own(datenordner, tmp_path, monkeypatch):
    calls = spy_on_builds(monkeypatch)
    cv_design.save(datenordner, "einspaltig")
    entry = Register(datenordner).speichere({**Register(datenordner).hole(BRIEF_ID), "lebenslauf_design": "zweispaltig"})

    unterlagen.baue(datenordner, entry, tmp_path / "build")

    assert [theme_of(argv) for argv in calls] == ["zweispaltig"]


def test_the_register_only_takes_designs_the_app_knows():
    entry = {"id": "beispiel-ag", "firma": "Beispiel AG", "stelle": "Tester"}

    assert pruefe_bewerbung({**entry, "lebenslauf_design": "einspaltig"})["lebenslauf_design"] == "einspaltig"
    assert "lebenslauf_design" not in pruefe_bewerbung({**entry, "lebenslauf_design": ""})
    with pytest.raises(ValueError, match="lebenslauf_design"):
        pruefe_bewerbung({**entry, "lebenslauf_design": "barock"})


def test_the_preview_of_the_cv_shows_the_chosen_design(datenordner, tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(inhalte.lebenslauf_modul, "main", lambda argv: calls.append(list(argv)))
    cv_design.save(datenordner, "einspaltig")

    inhalte.pruefe_inhalt(datenordner, "cv.yaml", (datenordner / "cv.yaml").read_text(encoding="utf-8"),
                          tmp_path / "build")

    assert [theme_of(argv) for argv in calls] == ["einspaltig"]
