"""An existing cv.yaml the form's rules do not accept still loads and saves on Meine Angaben (#167, G23).

Values written by hand or by an older version (a fluency outside the list, full dates, long texts, more entries than
the form allows, a station shown by its display only, two-language values) block nothing as long as they stay as they
are. All data is invented.
"""
import copy
import datetime
import difflib
import json

import pytest
import yaml

import cv_read
import import_bundle
import validation
from form_cases import ROOT, base_bundle

TODAY = datetime.date(2026, 11, 9)
FORM = json.loads((ROOT / "form.json").read_text(encoding="utf-8"))
LANGUAGES = "".join(f"  - language: Sprache {n}\n    fluency: Gut (B2)\n" for n in range(1, 8))
HIGHLIGHTS = "".join(f"      - Punkt {n}\n" for n in range(1, 9))
LONG = "Sehr lange Funktionsbezeichnung " * 4

EXISTING_CV = f"""\
# Lebenslauf von Hand (frei erfunden)
basics:
  name: Erika Beispiel
  email: erika@example.ch
  phone: 079 000 00 00
  location:
    city: Bern
  summary:
    de: Software-Entwicklerin mit zehn Jahren Praxis.
    en: Software developer with ten years of experience.

work:
  - position: {{de: Software-Entwicklerin, en: Software developer}}
    name: Beispiel AG
    startDate: 2022-06-01
    endDate: 2023-01-15
    highlights:
      - {{de: Aufbau von Datenpipelines, en: Built data pipelines}}
      - text: {{de: Schulungen intern, en: Internal training}}
        tags: [bildung]
      - Wartung der Plattform
  - position: {LONG.strip()}
    name: Muster GmbH
    x-display: 2010 bis 2014
  - position: Praktikantin
    name: Beispiel Verlag
    startDate: 2009
    highlights:
{HIGHLIGHTS}
languages:
  - language: Deutsch
    fluency: Muttersprache
  - language: Englisch
    fluency: fliessend
{LANGUAGES}"""


def write_cv(folder, text: str = EXISTING_CV):
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "cv.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def bundle_from(path, change=None) -> dict:
    """The answers of the page after opening it on this cv.yaml, with the other steps from the base example."""
    data = cv_read.form_data(yaml.safe_load(path.read_text(encoding="utf-8")))
    if change:
        data = copy.deepcopy(data)
        change(data)
    base = base_bundle("job")
    cv_sections = {s["id"] for s in FORM["sections"] if s.get("cv")}
    others = {key: value for key, value in base["data"].items() if key not in cv_sections}
    return {**base, "data": {**others, **{key: value for key, value in data.items() if value}}}


def save(folder, bundle) -> import_bundle.ImportResult:
    return import_bundle.import_answers(folder, bundle, TODAY, force=True)


def changed_lines(before: str, after: str) -> list[str]:
    return [line for line in difflib.ndiff(before.splitlines(), after.splitlines()) if line[:2] in ("- ", "+ ")]


def test_since_g30_the_rules_of_the_form_take_the_file_even_when_typed_anew(tmp_path):
    bundle = bundle_from(write_cv(tmp_path))

    assert validation.validate_bundle(FORM, bundle) == []


def test_the_answers_read_from_the_file_pass_against_the_file(tmp_path):
    path = write_cv(tmp_path)
    loaded = cv_read.read_form_data(tmp_path)

    assert validation.validate_bundle(FORM, bundle_from(path), loaded=loaded) == []


def test_two_language_values_are_shown_as_they_are(tmp_path):
    data = cv_read.read_form_data(write_cv(tmp_path).parent)

    assert data["summary"] == {"summary": {"de": "Software-Entwicklerin mit zehn Jahren Praxis.",
                                           "en": "Software developer with ten years of experience."}}
    first = data["work"][0]
    assert first["position"] == {"de": "Software-Entwicklerin", "en": "Software developer"}
    assert first["startDate"] == "2022-06-01"
    assert first["highlights"] == [{"de": "Aufbau von Datenpipelines", "en": "Built data pipelines"},
                                   {"text": {"de": "Schulungen intern", "en": "Internal training"}, "tags": ["bildung"]},
                                   "Wartung der Plattform"]


def test_saving_without_a_change_keeps_the_file_byte_for_byte(tmp_path):
    path = write_cv(tmp_path)

    result = save(tmp_path, bundle_from(path))

    assert "cv.yaml" in result.written
    assert path.read_text(encoding="utf-8") == EXISTING_CV


def test_changing_one_unrelated_field_saves_and_changes_only_its_line(tmp_path):
    path = write_cv(tmp_path)

    def new_phone(data):
        data["person"]["phone"] = "079 111 11 11"

    save(tmp_path, bundle_from(path, change=new_phone))

    after = path.read_text(encoding="utf-8")
    assert changed_lines(EXISTING_CV, after) == ["-   phone: 079 000 00 00", "+   phone: 079 111 11 11"]


def test_an_edited_entry_keeps_its_untouched_values(tmp_path):
    path = write_cv(tmp_path)

    def edit(data):
        data["work"][0]["name"] = "Beispiel Software AG"

    save(tmp_path, bundle_from(path, change=edit))

    after = path.read_text(encoding="utf-8")
    assert changed_lines(EXISTING_CV, after) == ["-     name: Beispiel AG", "+     name: Beispiel Software AG"]


def test_a_two_language_value_is_replaced_only_when_edited(tmp_path):
    path = write_cv(tmp_path)

    def edit(data):
        data["work"][0]["position"] = "Senior-Entwicklerin"

    save(tmp_path, bundle_from(path, change=edit))

    cv = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert cv["work"][0]["position"] == "Senior-Entwicklerin"
    assert cv["basics"]["summary"]["en"] == "Software developer with ten years of experience."
    assert cv["work"][0]["highlights"][0] == {"de": "Aufbau von Datenpipelines", "en": "Built data pipelines"}


@pytest.mark.parametrize("change, message", [
    (lambda data: data["work"][2].update(startDate="2009-13-01"), "Ungültiges Format"),
    (lambda data: data["work"][2].update(position="Prakti-\nkantin"), "ohne Zeilenumbruch"),
    (lambda data: data["work"][2].update(startDate="", endDate=""), "Bitte ausfüllen"),
])
def test_values_typed_on_the_page_still_follow_the_rules(tmp_path, change, message):
    path = write_cv(tmp_path)

    with pytest.raises(import_bundle.ImportRejected) as rejected:
        save(tmp_path, bundle_from(path, change=change))

    assert any(message in text for text in rejected.value.messages)
    assert path.read_text(encoding="utf-8") == EXISTING_CV
