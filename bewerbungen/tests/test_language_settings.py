"""Languages (G10, G12, #94): the language of the app and the languages the person applies in, in the data folder.

Without a choice the app speaks German and suggests the application languages from `languages` in cv.yaml; the
person confirms the suggestion. All CVs here are invented.
"""
import pathlib

import pytest
import yaml

import language_settings
from test_app import get, post, server  # noqa: F401  (server is a fixture)

DESKTOP = pathlib.Path(__file__).resolve().parents[2] / "desktop"


def _cv(folder: pathlib.Path, languages) -> None:
    cv = {"basics": {"name": "Erika Beispiel"}}
    if languages is not None:
        cv = {**cv, "languages": languages}
    (folder / "cv.yaml").write_text(yaml.safe_dump(cv, allow_unicode=True), encoding="utf-8")


def test_without_a_choice_the_app_is_german_and_german_is_suggested_from_a_cv_with_only_german(tmp_path):
    _cv(tmp_path, [{"language": "Deutsch", "fluency": "Muttersprache"}, {"language": "Englisch", "fluency": "Grundkenntnisse"}])

    settings = language_settings.load(tmp_path)

    assert settings.as_dict() == {
        "app": "de", "app_gewaehlt": False, "bewerbung": ["de"], "bewerbung_gewaehlt": False,
        "vorschlag": [{"sprache": "de", "stufe": "Muttersprache"}],
    }


def test_the_suggestion_takes_every_language_the_cv_names_at_c1_or_better(tmp_path):
    _cv(tmp_path, [{"language": "Schweizerdeutsch", "fluency": "Muttersprache"},
                   {"language": {"de": "Englisch", "en": "English"}, "fluency": {"de": "Fliessend", "en": "Fluent"}},
                   {"language": "Französisch", "fluency": "gut (B2)"},
                   {"language": "Italienisch", "fluency": "C1"}])

    settings = language_settings.load(tmp_path)

    assert settings.applications == ("de", "en") and settings.applications_chosen is False
    assert settings.as_dict()["vorschlag"] == [{"sprache": "de", "stufe": "Muttersprache"},
                                               {"sprache": "en", "stufe": "Fliessend"}]


def test_a_level_only_in_x_level_still_counts(tmp_path):
    _cv(tmp_path, [{"language": "Französisch", "x-level": "C2"}])

    assert language_settings.load(tmp_path).as_dict()["vorschlag"] == [{"sprache": "fr", "stufe": "C2"}]


@pytest.mark.parametrize("languages", [None, [], [{"language": "Englisch", "fluency": "A2"}], "Deutsch", [{"fluency": "C2"}]])
def test_a_cv_without_usable_languages_falls_back_to_german(tmp_path, languages):
    _cv(tmp_path, languages)

    settings = language_settings.load(tmp_path)

    assert settings.applications == ("de",) and settings.as_dict()["vorschlag"] == []


def test_a_missing_or_broken_cv_falls_back_to_german(tmp_path):
    assert language_settings.load(tmp_path).applications == ("de",)
    (tmp_path / "cv.yaml").write_text("languages: [kaputt", encoding="utf-8")
    assert language_settings.load(tmp_path).applications == ("de",)


def test_a_stored_choice_wins_over_the_suggestion(tmp_path):
    _cv(tmp_path, [{"language": "Englisch", "fluency": "Fliessend"}])
    (tmp_path / language_settings.FILE).write_text("app: fr\nbewerbung: [fr, de]\n", encoding="utf-8")

    settings = language_settings.load(tmp_path)

    assert (settings.app, settings.app_chosen, settings.applications, settings.applications_chosen) == ("fr", True, ("de", "fr"), True)
    assert settings.as_dict()["vorschlag"] == [{"sprache": "en", "stufe": "Fliessend"}]


def test_a_broken_or_strange_file_falls_back_to_the_defaults(tmp_path):
    (tmp_path / language_settings.FILE).write_text("app: [kaputt", encoding="utf-8")
    assert language_settings.load(tmp_path).as_dict()["app_gewaehlt"] is False
    (tmp_path / language_settings.FILE).write_text("app: it\nbewerbung: []\n", encoding="utf-8")
    settings = language_settings.load(tmp_path)
    assert (settings.app, settings.app_chosen, settings.applications, settings.applications_chosen) == ("de", False, ("de",), False)


@pytest.mark.parametrize("values, message", [
    ({"app": "it"}, language_settings.BAD_APP),
    ({"app": ["de"]}, language_settings.BAD_APP),
    ({"bewerbung": []}, language_settings.BAD_APPLICATIONS),
    ({"bewerbung": ["de", "es"]}, language_settings.BAD_APPLICATIONS),
    ({"bewerbung": "de"}, language_settings.BAD_APPLICATIONS),
    ({"bewerbung": ["de", "de"]}, language_settings.BAD_APPLICATIONS),
    ({}, language_settings.BAD_VALUES),
    ({"sprache": "de"}, language_settings.BAD_VALUES),
    ("de", language_settings.BAD_VALUES),
])
def test_a_bad_value_is_refused_in_german(values, message):
    with pytest.raises(ValueError, match=message):
        language_settings.parse(values)


def test_the_page_stores_both_settings_with_drafts_and_reads_them_back(server):  # noqa: F811
    folder = server.kontext.daten
    status, answer = post(server, "/api/sprachen", {"app": "en"})

    assert status == 200 and answer["app"] == "en" and answer["app_gewaehlt"] is True
    assert answer["bewerbung_gewaehlt"] is False
    status, answer = post(server, "/api/sprachen", {"bewerbung": ["fr", "de"]})
    assert status == 200 and answer["bewerbung"] == ["de", "fr"] and answer["app"] == "en"
    assert yaml.safe_load((folder / language_settings.FILE).read_text(encoding="utf-8")) == {"app": "en", "bewerbung": ["de", "fr"]}
    status, _, body = get(server, "/api/sprachen")
    assert status == 200 and yaml.safe_load(body)["bewerbung"] == ["de", "fr"]
    assert len(server.kontext.ablage.liste(folder / language_settings.FILE)) >= 2


def test_the_page_gets_a_german_error_for_a_bad_value_and_nothing_is_written(server):  # noqa: F811
    status, answer = post(server, "/api/sprachen", {"app": "it"})
    assert status == 400 and answer["fehler"] == language_settings.BAD_APP
    status, answer = post(server, "/api/sprachen", {"bewerbung": []})
    assert status == 400 and answer["fehler"] == language_settings.BAD_APPLICATIONS
    assert not (server.kontext.daten / language_settings.FILE).exists()


def test_neither_the_extension_nor_claude_reach_the_setting():
    for name in ("native_host.py", "mcp_tools.py"):
        assert "/api/sprachen" not in (DESKTOP / name).read_text(encoding="utf-8")
