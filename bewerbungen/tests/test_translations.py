"""Translations per field (MIN-309): which ones were checked against which text, so only changed ones are checked again."""
import datetime
import json

import pytest
import yaml

import translations

TODAY = datetime.date(2026, 11, 4)


def write_cv(folder, summary):
    (folder / "cv.yaml").write_text(yaml.safe_dump({"basics": {"name": "Erika Beispiel", "summary": summary}, "work": [
        {"name": "Muster GmbH", "highlights": [{"de": "Aufbau", "en": "Built"}, "immer gleich", {"text": {"de": "Kurse", "en": "Courses"}, "tags": ["x"]}]},
    ]}, allow_unicode=True), encoding="utf-8")


@pytest.fixture
def folder(tmp_path):
    write_cv(tmp_path, {"de": "Hallo", "en": "Hello"})
    return tmp_path


def by_field(found):
    return {entry["feld"]: entry for entry in found}


def test_every_multilingual_field_is_open_with_its_place_and_texts(folder):
    found = by_field(translations.open_fields(folder))
    assert set(found) == {"basics.summary", "work[0].highlights[0]", "work[0].highlights[2].text"}
    entry = found["basics.summary"]
    assert (entry["datei"], entry["sprache"], entry["de"], entry["uebersetzung"], entry["stand"]) == ("cv.yaml", "en", "Hallo", "Hello", "ungeprüft")
    assert entry["hash"]


def test_a_checked_field_is_not_open_again(folder):
    wanted = by_field(translations.open_fields(folder))["basics.summary"]["hash"]
    translations.mark_checked(folder, [wanted], TODAY)
    assert "basics.summary" not in by_field(translations.open_fields(folder))
    assert len(translations.open_fields(folder)) == 2


def test_a_changed_german_text_is_open_again(folder):
    translations.mark_checked(folder, [e["hash"] for e in translations.open_fields(folder)], TODAY)
    assert translations.open_fields(folder) == []
    write_cv(folder, {"de": "Guten Tag", "en": "Hello"})
    assert [e["feld"] for e in translations.open_fields(folder)] == ["basics.summary"]


def test_a_changed_translation_is_open_again(folder):
    translations.mark_checked(folder, [e["hash"] for e in translations.open_fields(folder)], TODAY)
    write_cv(folder, {"de": "Hallo", "en": "Hi there"})
    assert [e["feld"] for e in translations.open_fields(folder)] == ["basics.summary"]


def test_a_moved_field_stays_checked(folder):
    translations.mark_checked(folder, [e["hash"] for e in translations.open_fields(folder)], TODAY)
    (folder / "cv.yaml").write_text(yaml.safe_dump({"neu": [{"de": "Kurse", "en": "Courses"}, {"de": "Hallo", "en": "Hello"}, {"de": "Aufbau", "en": "Built"}]}), encoding="utf-8")
    assert translations.open_fields(folder) == []


def test_a_field_without_translation_is_open_and_cannot_be_checked(folder):
    write_cv(folder, {"de": "Hallo"})
    entry = by_field(translations.open_fields(folder))["basics.summary"]
    assert (entry["stand"], entry["uebersetzung"], entry["hash"]) == ("fehlt", None, None)


def test_what_build_does_not_read_as_multilingual_is_ignored(tmp_path):
    (tmp_path / "cv.yaml").write_text(yaml.safe_dump({"location": {"city": "Bern"}, "y": {"de": "a", "en": 5}}), encoding="utf-8")
    assert translations.open_fields(tmp_path) == []


def test_tailored_variants_count_too(folder):
    (folder / "jobs").mkdir()
    (folder / "jobs" / "daten.yaml").write_text(yaml.safe_dump({"basics": {"label": {"de": "Datenfachfrau", "en": "Data specialist"}}}, allow_unicode=True), encoding="utf-8")
    assert "jobs/daten.yaml" in {e["datei"] for e in translations.open_fields(folder)}


def test_marking_a_text_that_has_changed_stores_nothing(folder):
    old = by_field(translations.open_fields(folder))["basics.summary"]["hash"]
    other = by_field(translations.open_fields(folder))["work[0].highlights[0]"]["hash"]
    write_cv(folder, {"de": "Guten Tag", "en": "Hello"})
    with pytest.raises(ValueError, match="1 Prüfung"):
        translations.mark_checked(folder, [other, old], TODAY)
    assert not (folder / translations.RECORD).exists()


def test_the_record_holds_only_hashes_and_forgets_what_is_gone(folder):
    translations.mark_checked(folder, [e["hash"] for e in translations.open_fields(folder)], TODAY)
    write_cv(folder, {"de": "Guten Tag", "en": "Good day"})
    new = by_field(translations.open_fields(folder))["basics.summary"]["hash"]
    translations.mark_checked(folder, [new], TODAY)
    text = (folder / translations.RECORD).read_text(encoding="utf-8")
    assert "Guten Tag" not in text and "Good day" not in text
    assert len(yaml.safe_load(text)["geprueft"]) == 3
    assert translations.open_fields(folder) == []


def test_a_broken_record_is_reported_not_overwritten(folder):
    (folder / translations.RECORD).write_text("- keine\n- zuordnung\n", encoding="utf-8")
    with pytest.raises(ValueError, match=translations.RECORD):
        translations.open_fields(folder)


def test_no_cv_means_nothing_open(tmp_path):
    assert translations.open_fields(tmp_path) == []


def test_the_command_lists_and_marks(folder, capsys):
    translations.main(["open", str(folder)])
    found = json.loads(capsys.readouterr().out)
    assert len(found) == 3
    translations.main(["checked", str(folder), *[e["hash"] for e in found]])
    assert json.loads(capsys.readouterr().out) == {"geprueft": 3}
    translations.main(["open", str(folder)])
    assert json.loads(capsys.readouterr().out) == []


def test_the_command_fails_clearly(folder, capsys):
    with pytest.raises(SystemExit) as stop:
        translations.main(["checked", str(folder), "abc"])
    assert stop.value.code != 0
    assert "Prüfung" in capsys.readouterr().err


def test_a_field_only_in_another_language_is_reported(tmp_path):
    (tmp_path / "cv.yaml").write_text(yaml.safe_dump({"a": {"en": "only english"}, "b": {"de": ""}}), encoding="utf-8")
    found = translations.open_fields(tmp_path)
    assert [(entry["feld"], entry["stand"], entry["hash"]) for entry in found] == [("a", "deutsch fehlt", None)]


def test_a_folder_that_does_not_exist_is_no_empty_result(tmp_path):
    with pytest.raises(ValueError, match="Datenordner"):
        translations.open_fields(tmp_path / "gibt-es-nicht")


@pytest.mark.parametrize("name", [translations.RECORD, "cv.yaml"])
def test_broken_yaml_is_reported_in_plain_words(folder, name):
    (folder / name).write_text("a: [unterbrochen\n", encoding="utf-8")
    with pytest.raises(ValueError, match="lässt sich nicht lesen"):
        translations.open_fields(folder)
