"""Levels for skills, languages and programs on Meine Angaben (#123, G20): set, cleared, absent.

A keyword with a level is {name, level} in cv.yaml, a language has `x-level` (lebenslauf/dossier_data.py reads both).
On the page a keyword line with a level is {text, level}; an empty level clears it, a plain line leaves it to the file.
All data is invented.
"""
import copy
import json

import yaml

import convert
import cv_read
from form_cases import ROOT
from test_tags import TODAY, bundle_from, save, write_cv  # noqa: F401  (TODAY keeps the import of the helpers honest)

FORM = json.loads((ROOT / "form.json").read_text(encoding="utf-8"))
FIELDS = {s["id"]: {f["id"]: f for f in s["fields"]} for s in FORM["sections"]}

CV = """\
# Lebenslauf mit Stufen (frei erfunden)
basics:
  name: Erika Beispiel
  email: erika@example.ch
  location:
    city: Bern
languages:
  - language: Deutsch
    fluency: Muttersprache
    x-level: C2
  - language: Englisch
    fluency: Sehr gut (C1)
skills:
  - name: Programme
    keywords:
      - name: Python  # am liebsten
        level: 5
      - SQL
      - name: Excel
        level: B2
"""


def cv_after(tmp_path, change) -> dict:
    path = write_cv(tmp_path, CV)
    return yaml.safe_load(save(tmp_path, bundle_from(path, change)))


# The form


def test_keywords_and_languages_offer_an_optional_level_with_a_short_note():
    keywords, level = FIELDS["skills"]["keywords"], FIELDS["languages"]["x-level"]

    assert keywords["levels"] is True and not level.get("required")
    assert level["type"] == "select" and level["options"] == ["A1", "A2", "B1", "B2", "C1", "C2"]
    for field in (keywords, level):
        hint = field["hint"] if isinstance(field["hint"], str) else field["hint"]["job"]
        assert "freiwillig" in hint.lower() and "neutral" in hint and "keine Grafik" in hint


# Reading cv.yaml into the form


def test_levels_are_read_into_the_form():
    data = cv_read.form_data(yaml.safe_load(CV))

    assert data["skills"][0]["keywords"] == [{"text": "Python", "level": "5"}, "SQL", {"text": "Excel", "level": "4"}]
    assert data["languages"] == [{"language": "Deutsch", "fluency": "Muttersprache", "x-level": "C2"},
                                 {"language": "Englisch", "fluency": "Sehr gut (C1)"}]


def test_a_level_the_form_cannot_show_leaves_the_keyword_as_text():
    data = cv_read.form_data(yaml.safe_load(CV.replace("level: 5", "level: 9")))

    assert data["skills"][0]["keywords"][0] == "Python"


# Writing a new cv.yaml


def test_a_new_cv_gets_levels_only_where_they_are_set():
    data = {"skills": [{"name": "Programme", "keywords": [{"text": " Python ", "level": "4"}, "SQL",
                                                          {"text": "Git", "level": ""}]}],
            "languages": [{"language": "Deutsch", "fluency": "Muttersprache", "x-level": "C2"},
                          {"language": "Englisch", "fluency": "Gut (B2)", "x-level": ""}]}

    cv = convert.build_cv(data, "job")

    assert cv["skills"][0]["keywords"] == [{"name": "Python", "level": 4}, "SQL", "Git"]
    assert cv["languages"] == [{"language": "Deutsch", "fluency": "Muttersprache", "x-level": "C2"},
                               {"language": "Englisch", "fluency": "Gut (B2)"}]


# Saving into an existing cv.yaml


def test_saving_without_a_change_keeps_the_levels_byte_for_byte(tmp_path):
    path = write_cv(tmp_path, CV)

    assert save(tmp_path, bundle_from(path)) == CV


def test_a_level_is_set_on_a_keyword_and_a_language(tmp_path):
    def change(data):
        data["skills"][0]["keywords"][1] = {"text": "SQL", "level": "3"}
        data["languages"][1]["x-level"] = "C1"

    cv = cv_after(tmp_path, change)

    assert cv["skills"][0]["keywords"][1] == {"name": "SQL", "level": 3}
    assert cv["languages"][1]["x-level"] == "C1"


def test_clearing_a_level_leaves_no_trace(tmp_path):
    def change(data):
        data["skills"][0]["keywords"][0] = {"text": "Python", "level": ""}
        data["languages"][0]["x-level"] = ""

    text = save(tmp_path, bundle_from(write_cv(tmp_path, CV), change))
    cv = yaml.safe_load(text)

    assert cv["skills"][0]["keywords"][0] == "Python"
    assert "x-level" not in cv["languages"][0]
    assert "level: 5" not in text and "x-level: C2" not in text


def test_a_changed_level_keeps_the_comment_and_the_rest(tmp_path):
    def change(data):
        data["skills"][0]["keywords"][0] = {"text": "Python", "level": "6"}

    text = save(tmp_path, bundle_from(write_cv(tmp_path, CV), change))

    assert "level: 6" in text and "# am liebsten" in text and "level: B2" in text


def test_a_plain_line_leaves_the_level_to_the_file(tmp_path):
    """Answers from before #123 send keywords as text; they must not drop a level."""
    def change(data):
        data["skills"][0]["keywords"] = ["Python", "SQL", "Excel"]

    cv = cv_after(tmp_path, change)

    assert cv["skills"][0]["keywords"] == [{"name": "Python", "level": 5}, "SQL", {"name": "Excel", "level": "B2"}]


def test_a_level_the_form_cannot_show_stays_when_the_line_is_cleared(tmp_path):
    path = write_cv(tmp_path, CV.replace("level: 5", "level: 9"))

    def change(data):
        data["skills"][0]["keywords"][0] = {"text": "Python", "level": ""}

    text = save(tmp_path, bundle_from(path, change))

    assert "level: 9" in text


def test_a_renamed_keyword_keeps_its_level(tmp_path):
    def change(data):
        data["skills"][0]["keywords"][0] = {"text": "Python 3", "level": "5"}

    cv = cv_after(tmp_path, change)

    assert cv["skills"][0]["keywords"][0] == {"name": "Python 3", "level": 5}


def test_a_new_skill_group_with_levels_is_written_in_the_file_format(tmp_path):
    def change(data):
        data["skills"] = [*copy.deepcopy(data["skills"]),
                          {"name": "Werkzeuge", "keywords": [{"text": "Bohrmaschine", "level": "2"},
                                                             {"text": "Säge", "level": ""}]}]

    cv = cv_after(tmp_path, change)

    assert cv["skills"][1]["keywords"] == [{"name": "Bohrmaschine", "level": 2}, "Säge"]
