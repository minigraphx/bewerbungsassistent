"""Projects, teaching, free texts and the website on Meine Angaben (#162, G25, tags per G24).

All data is invented.
"""
import copy
import datetime
import json

import pytest
import yaml

import convert
import cv_read
import import_bundle
import known_tags
import prefill
import validation
from form_cases import ROOT, base_bundle

TODAY = datetime.date(2026, 11, 8)
FORM = json.loads((ROOT / "form.json").read_text(encoding="utf-8"))

CV = """\
# Lebenslauf mit Projekten und Lehre (frei erfunden)
basics:
  name: Erika Beispiel
  email: erika@example.ch
  url: www.example.ch  # eigene Seite
  location:
    city: Bern

work:
  - position: Software-Entwicklerin
    name: Beispiel AG
    startDate: "2019-03"
    x-display: seit 2019

projects:
  - name: datenatlas
    description: Visualisierung offener Verkehrsdaten
    url: https://example.ch/datenatlas
    tags: [daten]
  - name: Kleines Spiel
    group: more
  - name: Altes Projekt
    group: archiv

teaching:
  - position: Kursleiterin Programmieren
    name: Volkshochschule Beispiel
    startDate: 2020
    x-display: seit 2020
    highlights:
      - Einführung in Python
      - text: Datenanalyse mit pandas
        tags: [daten]
    tags: [bildung]
  - position: Mentorin
    name: Verein Beispiel
    x-display: gelegentlich

education:
  - studyType: Bachelor
    institution: Beispiel-Hochschule
    startDate: 2011
    endDate: 2015
    text: Bachelor of Science in Informatik, Beispiel-Hochschule
  - text: Matura, Gymnasium Beispiel, 2010

certificates:
  - name: Scrum Master
    date: "2022"
  - text: Kurs in Projektleitung, 2021
"""


def write_cv(folder, text: str = CV):
    path = folder / "cv.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def for_track(data: dict, track: str) -> dict:
    """What the page sends for a track: like model.js cleanData, only the sections and fields of that track."""
    shown = {}
    for section in FORM["sections"]:
        if section["id"] not in data or track not in section.get("tracks", [track]):
            continue
        fields = {f["id"] for f in section["fields"] if track in f.get("tracks", [track])}
        pick = lambda item: {key: value for key, value in item.items() if key in fields}  # noqa: E731
        value = data[section["id"]]
        shown[section["id"]] = [pick(item) for item in value] if isinstance(value, list) else pick(value)
    return shown


def bundle_from(path, change=None, track: str = "job") -> dict:
    """What the page sends after opening on this cv.yaml: the CV sections from the file, empty ones included, the rest
    from the example."""
    data = copy.deepcopy(cv_read.form_data(yaml.safe_load(path.read_text(encoding="utf-8"))))
    if change:
        change(data)
    base = base_bundle(track)
    cv_sections = {s["id"] for s in FORM["sections"] if s.get("cv")}
    others = {key: value for key, value in base["data"].items() if key not in cv_sections}
    return {**base, "data": for_track({**others, **data}, track)}


def save(folder, bundle) -> str:
    errors = validation.validate_bundle(FORM, bundle, known=frozenset(known_tags.known_tags(folder, FORM)))
    assert errors == []
    import_bundle.import_answers(folder, bundle, TODAY, force=True)
    return (folder / "cv.yaml").read_text(encoding="utf-8")


def fields_of(section_id: str) -> dict:
    section = next(s for s in FORM["sections"] if s["id"] == section_id)
    return {f["id"]: f for f in section["fields"]}


def test_the_form_has_projects_and_teaching_with_tags_like_work():
    projects, teaching, work = fields_of("projects"), fields_of("teaching"), fields_of("work")

    assert list(projects) == ["name", "description", "group", "tags"]
    assert projects["group"]["type"] == "select" and projects["group"]["options"] == ["main", "more"]
    assert projects["tags"] == work["tags"] == teaching["tags"]
    assert teaching["highlights"]["tags"] is True
    assert set(teaching) == {*work, "x-display"} - {"evidence"}


def test_education_and_certificates_have_a_free_text_and_the_person_a_website():
    assert fields_of("education")["text"]["type"] == "text"
    assert fields_of("certificates")["text"]["type"] == "text"
    url = fields_of("person")["url"]
    assert url["format"] == "url" and url["tracks"] == ["job"]


def test_projects_teaching_texts_and_website_are_read_into_the_form():
    data = cv_read.form_data(yaml.safe_load(CV))

    assert data["person"]["url"] == "www.example.ch"
    assert data["projects"] == [
        {"name": "datenatlas", "description": "Visualisierung offener Verkehrsdaten", "tags": ["daten"]},
        {"name": "Kleines Spiel", "group": "more"},
        {"name": "Altes Projekt"},
    ]
    assert data["teaching"] == [
        {"position": "Kursleiterin Programmieren", "name": "Volkshochschule Beispiel", "startDate": "2020",
         "x-display": "seit 2020", "highlights": ["Einführung in Python",
                                                  {"text": "Datenanalyse mit pandas", "tags": ["daten"]}],
         "tags": ["bildung"]},
        {"position": "Mentorin", "name": "Verein Beispiel", "x-display": "gelegentlich"},
    ]
    assert data["education"][0]["text"] == "Bachelor of Science in Informatik, Beispiel-Hochschule"
    assert data["education"][1] == {"text": "Matura, Gymnasium Beispiel, 2010"}
    assert data["certificates"][1] == {"text": "Kurs in Projektleitung, 2021"}
    assert "x-display" not in data["work"][0]


def test_saving_without_a_change_keeps_the_file_byte_for_byte(tmp_path):
    path = write_cv(tmp_path)

    assert save(tmp_path, bundle_from(path)) == CV


def test_the_apprenticeship_track_keeps_projects_teaching_and_the_website(tmp_path):
    path = write_cv(tmp_path)

    after = save(tmp_path, bundle_from(path, track="apprenticeship"))

    # the apprenticeship track adds its own headings at the end; everything above stays
    assert after.startswith(CV) and yaml.safe_load(after[len(CV):]) == {"x-beschriftungen": convert.APPRENTICESHIP_HEADINGS}


def test_answers_from_before_g25_keep_projects_teaching_and_website_byte_for_byte(tmp_path):
    path = write_cv(tmp_path)

    def before_g25(data):
        del data["person"]["url"], data["projects"], data["teaching"]

    assert save(tmp_path, bundle_from(path, before_g25)) == CV


def test_answers_from_before_g25_keep_them_while_other_answers_change(tmp_path):
    path = write_cv(tmp_path)

    def before_g25(data):
        del data["person"]["url"], data["projects"], data["teaching"]
        data["person"]["email"] = "erika.beispiel@example.ch"

    after = save(tmp_path, bundle_from(path, before_g25))

    assert after == CV.replace("email: erika@example.ch", "email: erika.beispiel@example.ch")


def test_an_empty_list_and_an_empty_website_remove_them(tmp_path):
    path = write_cv(tmp_path)

    def clear(data):
        data["person"]["url"] = ""
        data["projects"] = []
        data["teaching"] = []

    cv = yaml.safe_load(save(tmp_path, bundle_from(path, clear)))

    assert "projects" not in cv and "teaching" not in cv and "url" not in cv["basics"]


def test_removing_a_project_on_the_page_removes_it(tmp_path):
    path = write_cv(tmp_path)

    def remove(data):
        del data["projects"][0]

    cv = yaml.safe_load(save(tmp_path, bundle_from(path, remove)))

    assert [p["name"] for p in cv["projects"]] == ["Kleines Spiel", "Altes Projekt"]
    assert cv["projects"][1]["group"] == "archiv"


def test_empty_answers_write_no_empty_keys(tmp_path):
    bundle = base_bundle("job")
    bundle["data"]["person"]["url"] = ""
    bundle["data"]["projects"] = []
    bundle["data"]["teaching"] = []

    new = yaml.safe_load(save(tmp_path, bundle))
    assert "projects" not in new and "teaching" not in new and "url" not in new["basics"]

    write_cv(tmp_path, "basics:\n  name: Erika Beispiel\n")
    merged = yaml.safe_load(save(tmp_path, bundle))
    assert "projects" not in merged and "teaching" not in merged and "url" not in merged["basics"]


def test_edits_change_only_what_the_form_shows(tmp_path):
    path = write_cv(tmp_path)

    def edit(data):
        data["person"]["url"] = "https://www.example.ch/erika"
        data["projects"][0]["description"] = "Karten offener Verkehrsdaten"
        data["projects"][1]["name"] = "Kleines Spiel in Godot"
        data["teaching"][0]["x-display"] = "2020 bis heute"
        data["teaching"][0]["highlights"][0] = {"text": "Einführung in Python", "tags": ["bildung"]}
        data["education"][0]["text"] = "BSc Informatik, Beispiel-Hochschule"

    cv = yaml.safe_load(save(tmp_path, bundle_from(path, edit)))

    assert cv["basics"]["url"] == "https://www.example.ch/erika"
    assert cv["projects"][0] == {"name": "datenatlas", "description": "Karten offener Verkehrsdaten",
                                 "url": "https://example.ch/datenatlas", "tags": ["daten"]}
    assert cv["projects"][1] == {"name": "Kleines Spiel in Godot", "group": "more"}
    assert cv["projects"][2] == {"name": "Altes Projekt", "group": "archiv"}
    assert cv["teaching"][0]["x-display"] == "2020 bis heute" and cv["teaching"][0]["startDate"] == 2020
    assert cv["teaching"][0]["highlights"][0] == {"text": "Einführung in Python", "tags": ["bildung"]}
    assert cv["education"][0]["text"] == "BSc Informatik, Beispiel-Hochschule"
    assert cv["work"][0]["x-display"] == "seit 2019"


def test_a_change_of_group_and_a_removed_website_are_written(tmp_path):
    path = write_cv(tmp_path)

    def edit(data):
        data["person"]["url"] = ""  # what the page sends for a cleared field
        data["projects"][0]["group"] = "more"
        data["projects"][1]["group"] = "main"

    cv = yaml.safe_load(save(tmp_path, bundle_from(path, edit)))

    assert "url" not in cv["basics"]
    assert cv["projects"][0]["group"] == "more" and cv["projects"][1]["group"] == "main"


def test_new_entries_come_in_with_their_shape_and_removed_ones_go(tmp_path):
    path = write_cv(tmp_path)

    def edit(data):
        data["projects"].append({"name": "kurs-tools", "description": "Werkzeuge für Kurse", "group": "more",
                                 "tags": ["web", "bildung"]})
        del data["teaching"][1]
        data["teaching"].append({"position": "Tutorin", "name": "Beispiel-Hochschule", "startDate": "2013",
                                 "endDate": "2015", "highlights": [{"text": "Übungen in Statistik", "tags": []}],
                                 "tags": []})
        data["certificates"].append({"text": "Erste-Hilfe-Kurs, 2024"})

    after = save(tmp_path, bundle_from(path, edit))
    cv = yaml.safe_load(after)

    assert cv["projects"][3] == {"name": "kurs-tools", "description": "Werkzeuge für Kurse", "group": "more",
                                 "tags": ["web", "bildung"]}
    assert "tags: [web, bildung]" in after
    assert [t["position"] for t in cv["teaching"]] == ["Kursleiterin Programmieren", "Tutorin"]
    assert cv["teaching"][1] == {"position": "Tutorin", "name": "Beispiel-Hochschule", "startDate": "2013",
                                 "endDate": "2015", "highlights": ["Übungen in Statistik"]}
    assert cv["certificates"][2] == {"text": "Erste-Hilfe-Kurs, 2024"}


def test_a_new_cv_gets_projects_teaching_texts_and_website(tmp_path):
    bundle = base_bundle("job")
    bundle["data"]["person"]["url"] = "www.example.ch"
    bundle["data"]["projects"] = [{"name": "datenatlas", "tags": ["daten"]}, {"name": "Spiel", "group": "more"}]
    bundle["data"]["teaching"] = [{"position": "Kursleiterin", "name": "Volkshochschule Beispiel",
                                   "x-display": "seit 2020", "highlights": ["Python für Erwachsene"]}]
    bundle["data"]["education"][0]["text"] = "Bachelor in Informatik"

    cv = yaml.safe_load(save(tmp_path, bundle))

    assert cv["basics"]["url"] == "www.example.ch"
    assert cv["projects"] == [{"name": "datenatlas", "tags": ["daten"]}, {"name": "Spiel", "group": "more"}]
    assert cv["teaching"] == [{"position": "Kursleiterin", "name": "Volkshochschule Beispiel",
                               "x-display": "seit 2020", "highlights": ["Python für Erwachsene"]}]
    assert cv["education"][0]["text"] == "Bachelor in Informatik"


def test_tags_of_projects_and_teaching_are_suggested(tmp_path):
    write_cv(tmp_path)

    assert {"daten", "bildung"} <= set(known_tags.known_tags(tmp_path, FORM))


@pytest.mark.parametrize("section, field", [("education", "text"), ("certificates", "text")])
def test_the_ai_is_not_asked_for_free_texts(section, field):
    guide = prefill.field_guide(FORM, "job")
    line = next(line for line in guide.splitlines() if line.startswith(f"- {section} "))
    assert field not in [name.split(" (")[0] for name in line.split(": ", 1)[1].split(", ")]


def test_the_website_is_replaced_before_text_goes_to_the_ai():
    data = {"person": {"name": "Erika Beispiel", "url": "www.example.ch"}}

    secrets = prefill._person_secrets(data, "job")

    assert any(s.value == "www.example.ch" for s in secrets)
