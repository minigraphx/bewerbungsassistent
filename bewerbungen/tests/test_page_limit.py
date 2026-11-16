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
from varianten import Varianten
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
    # the stand-in pages carry no layout to count lines in, so the finding names no number
    assert found[0].text == ("Lebenslauf: 3 Seiten, erlaubt sind höchstens 2. Auch so eng wie möglich gesetzt passt er "
                             "nicht.")
    assert found[0].kuerzen["optionen"][0]["text"].endswith("bei «Software-Entwicklerin, Beispiel AG» (2019–heute)")
    assert found[0].kuerzen["drei_seiten"] is True  # G92: for this application, not under «Erweitert»


def test_a_finished_file_variant_over_two_pages_claims_no_tightening(datenordner, tmp_path, monkeypatch):
    # the app copies a finished file as it is, so the finding must not say it was set tighter (#349)
    (datenordner / "fertig.pdf").write_bytes(b"%PDF-1.4 kein echtes PDF")
    Varianten(datenordner).speichere({"id": "fertig", "datei": "fertig.pdf", "beschreibung": "Fertiges PDF"})
    register = Register(datenordner)
    register.speichere({**register.hole(BRIEF_ID), "variante": "fertig"})
    entry = register.hole(BRIEF_ID)
    unterlagen.baue(datenordner, entry, tmp_path / "build")
    monkeypatch.setattr(pruefung, "_seiten", lambda pdf: ["Text " * 100] * (3 if pdf.name == "lebenslauf.pdf" else 1))

    found = [f for f in pruefung.pruefe(datenordner, entry, TODAY) if "erlaubt sind höchstens 2" in f.text]

    assert [f.text for f in found] == [
        "Lebenslauf: 3 Seiten, erlaubt sind höchstens 2. Eine fertige Datei setzt die App nicht neu; kürzer wird er "
        "mit einer anderen Variante unter «Lebenslauf» oder einer kürzeren Datei unter «Lebenslauf und Dateien»."]
    assert found[0].kuerzen is None and found[0].cv_over is None


def test_with_three_pages_allowed_a_three_page_cv_is_fine(datenordner, tmp_path, monkeypatch):
    (datenordner / page_limit.FILE).write_text("lebenslauf_seiten: 3\n", encoding="utf-8")
    entry = Register(datenordner).hole(BRIEF_ID)
    unterlagen.baue(datenordner, entry, tmp_path / "build")
    monkeypatch.setattr(pruefung, "_seiten", lambda pdf: ["Text " * 100] * (3 if pdf.name == "lebenslauf.pdf" else 1))

    found = pruefung.pruefe(datenordner, entry, TODAY)

    assert not [f for f in found if "Lebenslauf" in f.text and "Seiten," in f.text], [f.text for f in found]


# A letter over one page (G94): set as tight as possible, the lines over named, cut in the letter or left as it is

LETTER_SENTENCE = ("In meiner letzten Stelle habe ich Auswertungen für mehrere Bereiche aufgebaut und die Zahlen so "
                   "aufbereitet, dass das Team sie ohne Rückfragen nutzen konnte. ")
LONGEST = 5  # the place of the longest paragraph in the long letter, counted from 0


def _long_letter(daten):
    """The sample letter with eleven more invented paragraphs, too long for one page in every design."""
    source = unterlagen.letter_source(daten, BRIEF_ID)
    letter = yaml.safe_load(source.read_text(encoding="utf-8"))
    first = len(letter["text"].split("\n\n"))
    extra = [LETTER_SENTENCE * (5 if first + number == LONGEST else 3) for number in range(11)]
    letter["text"] = letter["text"].rstrip() + "".join(f"\n\n{paragraph}" for paragraph in extra)
    source.write_text(yaml.safe_dump(letter, allow_unicode=True), encoding="utf-8")


def _letter_over(findings: list[dict]) -> list[dict]:
    return [f for f in findings if f["letter_cut"]]


def _checked(server) -> list[dict]:  # noqa: F811
    status, _, body = get(server, "/api/pruefung", id=BRIEF_ID)
    assert status == 200
    return json.loads(body)["befunde"]


def test_a_letter_over_one_page_names_the_lines_over_and_its_longest_paragraph(datenordner, tmp_path):
    _long_letter(datenordner)
    entry = Register(datenordner).hole(BRIEF_ID)
    unterlagen.baue(datenordner, entry, tmp_path / "build")

    found = pruefung.pruefe(datenordner, entry, TODAY)
    [over] = [f for f in found if f.text.startswith("Anschreiben: 2 Seiten")]

    lines = over.letter_cut["lines"]
    assert over.stufe == "fehler" and over.schluessel and not over.bestaetigt
    assert lines > 0
    assert over.text.startswith("Anschreiben: 2 Seiten, erlaubt ist eine. Auch so eng wie möglich gesetzt sind es "
                                f"etwa {lines} Zeilen zu viel. Am meisten bringt der längste Absatz («In meiner ")
    assert over.text.endswith("»).")
    assert over.letter_cut["paragraph"] == LONGEST and over.letter_cut["pages"] == 2
    # the second page is short on purpose: its fill is no finding of its own while the letter is over
    assert not [f for f in found if f.text.startswith("Anschreiben, Seite 2") and "gefüllt" in f.text]


def test_so_lassen_confirms_a_letter_over_one_page_as_it_is(server):  # noqa: F811
    _long_letter(server.kontext.daten)
    post(server, "/api/unterlagen", {}, id=BRIEF_ID)
    [over] = _letter_over(_checked(server))

    status, answer = post(server, "/api/pruefung/bestaetigen", {"id": BRIEF_ID, "schluessel": over["schluessel"]})

    assert status == 200, answer
    [confirmed] = _letter_over(answer["befunde"])
    assert confirmed["bestaetigt"] and confirmed["stufe"] == "hinweis", "confirmed, it no longer stops a form"
    assert _letter_over(_checked(server)) == [confirmed]


def test_the_tile_of_a_letter_over_one_page_says_it_is_set_as_tight_as_possible(server):  # noqa: F811
    _long_letter(server.kontext.daten)
    post(server, "/api/unterlagen", {}, id=BRIEF_ID)

    status, _, body = get(server, "/api/bewerbung", id=BRIEF_ID)

    assert status == 200
    assert json.loads(body)["seiten"]["anschreiben"] == {"seiten": 2, "ausgleich": {"letter": "tightest"}}


def test_in_a_dossier_the_letter_over_one_page_is_as_tight_and_offers_the_same(server):  # noqa: F811
    _long_letter(server.kontext.daten)
    post(server, "/api/bewerbung", {"id": BRIEF_ID, "unterlagen": "dossier"})
    post(server, "/api/unterlagen", {}, id=BRIEF_ID)

    status, _, body = get(server, "/api/bewerbung", id=BRIEF_ID)

    assert json.loads(body)["seiten"]["dossier"]["ausgleich"]["letter"] == "tightest"
    [over] = _letter_over(_checked(server))
    assert over["stufe"] == "fehler" and over["letter_cut"]["paragraph"] == LONGEST
