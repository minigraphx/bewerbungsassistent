"""Page limits of the documents (G51): the switch under Einstellungen > Erweitert allows a three-page CV.

The setting lives in the data folder, goes to every build of the CV and sets the bar of the check before sending.
Over the limit, the check names what could be cut; nothing is cut without the person.
"""
import json

import pytest
import yaml

import page_fill
import page_limit
import pruefung
import unterlagen
from register import Register
from sample_folder import BRIEF_ID
from test_app import get, post, server  # noqa: F401  (server is a fixture)

TODAY = __import__("datetime").date(2026, 10, 25)


def test_without_a_choice_the_cv_has_at_most_two_pages(tmp_path):
    assert page_limit.load(tmp_path) == 2


def test_a_broken_or_strange_file_falls_back_to_two_pages(tmp_path):
    (tmp_path / page_limit.FILE).write_text("lebenslauf_seiten: [kaputt", encoding="utf-8")
    assert page_limit.load(tmp_path) == 2
    (tmp_path / page_limit.FILE).write_text("lebenslauf_seiten: 7\n", encoding="utf-8")
    assert page_limit.load(tmp_path) == 2


@pytest.mark.parametrize("values", [{"lebenslauf_seiten": 4}, {"lebenslauf_seiten": "3"}, {}, "3",
                                    {"lebenslauf_seiten": True}])
def test_only_two_or_three_pages_can_be_chosen(values):
    with pytest.raises(ValueError, match=page_limit.BAD_PAGES):
        page_limit.parse(values)


def test_the_page_stores_three_pages_with_drafts_and_reads_them_back(server):  # noqa: F811
    folder = server.kontext.daten
    status, answer = post(server, "/api/unterlagen/seitengrenze", {"lebenslauf_seiten": 3})

    assert status == 200 and answer == {"lebenslauf_seiten": 3}
    assert yaml.safe_load((folder / page_limit.FILE).read_text(encoding="utf-8")) == {"lebenslauf_seiten": 3}
    status, _, body = get(server, "/api/unterlagen/seitengrenze")
    assert status == 200 and json.loads(body) == {"lebenslauf_seiten": 3}
    post(server, "/api/unterlagen/seitengrenze", {"lebenslauf_seiten": 2})
    assert page_limit.load(folder) == 2
    assert len(server.kontext.ablage.liste(folder / page_limit.FILE)) >= 2


def test_a_bad_value_gets_a_german_error(server):  # noqa: F811
    status, answer = post(server, "/api/unterlagen/seitengrenze", {"lebenslauf_seiten": 5})

    assert status == 400 and answer["fehler"] == page_limit.BAD_PAGES


def test_neither_the_extension_nor_claude_reach_the_setting():
    import pathlib
    desktop = pathlib.Path(__file__).resolve().parents[2] / "desktop"
    for name in ("native_host.py", "mcp_tools.py"):
        assert "/api/unterlagen/seitengrenze" not in (desktop / name).read_text(encoding="utf-8")


# The builds take the setting


def _asked_limits(monkeypatch) -> list[dict]:
    asked = []
    original = page_fill.levels

    def levels(query, inputs, parts, limits=page_fill.LIMITS):
        asked.append(dict(limits))
        return original(query, inputs, parts, limits)

    monkeypatch.setattr(page_fill, "levels", levels)
    return asked


@pytest.mark.parametrize("pages", [2, 3])
def test_the_cv_of_an_application_is_built_with_the_chosen_pages(datenordner, tmp_path, monkeypatch, pages):
    (datenordner / page_limit.FILE).write_text(f"lebenslauf_seiten: {pages}\n", encoding="utf-8")
    asked = _asked_limits(monkeypatch)

    unterlagen.baue(datenordner, Register(datenordner).hole(BRIEF_ID), tmp_path / "build")

    assert {"cv": pages, "letter": 1} in asked
    assert all(limits["letter"] == 1 for limits in asked)


def test_the_dossier_is_built_with_the_chosen_pages(datenordner, tmp_path, monkeypatch):
    (datenordner / page_limit.FILE).write_text("lebenslauf_seiten: 3\n", encoding="utf-8")
    register = Register(datenordner)
    register.speichere({**register.hole(BRIEF_ID), "unterlagen": "dossier"})
    asked = _asked_limits(monkeypatch)

    unterlagen.baue(datenordner, Register(datenordner).hole(BRIEF_ID), tmp_path / "build")

    assert asked and all(limits == {"cv": 3, "letter": 1} for limits in asked)


# The check before sending


def test_a_built_cv_over_two_pages_is_named_with_what_could_be_cut(datenordner, tmp_path, monkeypatch):
    entry = Register(datenordner).hole(BRIEF_ID)
    unterlagen.baue(datenordner, entry, tmp_path / "build")
    monkeypatch.setattr(pruefung, "_seiten", lambda pdf: ["Text " * 100] * (3 if pdf.name == "lebenslauf.pdf" else 1))

    found = [f for f in pruefung.pruefe(datenordner, entry, TODAY) if "erlaubt sind höchstens 2" in f.text]

    assert len(found) == 1, [f.text for f in pruefung.pruefe(datenordner, entry, TODAY)]
    assert found[0].text.startswith("Lebenslauf: 3 Seiten, erlaubt sind höchstens 2. Auch enger gesetzt passt er nicht.")
    assert "Kürzen lässt sich: Stichpunkte bei «Software-Entwicklerin, Beispiel AG» (" in found[0].text
    assert "«Einstellungen», «Erweitert»" in found[0].text


def test_with_three_pages_allowed_a_three_page_cv_is_fine(datenordner, tmp_path, monkeypatch):
    (datenordner / page_limit.FILE).write_text("lebenslauf_seiten: 3\n", encoding="utf-8")
    entry = Register(datenordner).hole(BRIEF_ID)
    unterlagen.baue(datenordner, entry, tmp_path / "build")
    monkeypatch.setattr(pruefung, "_seiten", lambda pdf: ["Text " * 100] * (3 if pdf.name == "lebenslauf.pdf" else 1))

    found = pruefung.pruefe(datenordner, entry, TODAY)

    assert not [f for f in found if "Lebenslauf" in f.text and "Seiten," in f.text], [f.text for f in found]


def test_a_cover_letter_over_one_page_names_its_longest_paragraph(datenordner, tmp_path, monkeypatch):
    entry = Register(datenordner).hole(BRIEF_ID)
    unterlagen.baue(datenordner, entry, tmp_path / "build")
    monkeypatch.setattr(pruefung, "_seiten", lambda pdf: ["Text " * 100] * (2 if pdf.name == "anschreiben.pdf" else 1))

    found = [f for f in pruefung.pruefe(datenordner, entry, TODAY) if f.text.startswith("Anschreiben: 2 Seiten")]

    assert len(found) == 1 and found[0].stufe == "fehler"
    assert "erlaubt ist eine. Auch enger gesetzt passt es nicht. Kürzen lässt sich: der längste Absatz («" in found[0].text
