"""Meine Angaben reads an existing cv.yaml into the form and merges the answers back (#160, G23).

All data is invented.
"""
import copy
import datetime
import difflib
import json
import shutil

import pytest
import yaml
from pypdf import PdfReader

import build
import cv_read
import import_bundle
import validation
from form_cases import ROOT, base_bundle

TODAY = datetime.date(2026, 11, 8)
PHOTO = build.ROOT / "tests" / "foto.jpg"
FORM = json.loads((ROOT / "form.json").read_text(encoding="utf-8"))

FULL_CV = """\
# Stamm-Lebenslauf (frei erfunden)
basics:
  name: Erika Beispiel
  label: Software-Entwicklerin – Web und Daten
  email: erika@example.ch
  phone: 079 000 00 00
  url: www.example.ch
  image: foto.jpg
  x-image: {mirror: true, zoom: 1.3, x: 0.5, y: 0.2}
  location:
    address: Musterweg 1
    postalCode: "3000"
    city: Bern
    countryCode: CH
  details: ["geboren 1. Mai 1990", "Schweiz", "Führerausweis B"]
  summary: >-
    Software-Entwicklerin mit zehn Jahren Praxis in Python und TypeScript. Baut Webanwendungen
    und Datenpipelines.
  profiles:
    - network: GitHub
      url: https://github.com/example
    - network: LinkedIn
      url: www.linkedin.com/in/example
    - network: Mastodon
      username: beispiel

# Projekte zeigt das Formular nicht
projects:
  - name: datenatlas
    description: Visualisierung offener Verkehrsdaten
    tags: [daten]
  - name: Kleines Spiel
    group: more

skills:
  - name: Sprachen
    keywords: [Python, TypeScript, SQL]
  - name: Daten
    keywords: [pandas, PostgreSQL]
    tags: [daten]

work:
  - position: Software-Entwicklerin
    name: Beispiel AG
    location: Bern
    startDate: "2019-03"
    endDate: null
    tags: [web, daten]
    highlights:
      - Entwicklung einer Plattform für Kundendaten  # wichtigster Punkt
      - text: Aufbau von Datenpipelines mit Airflow
        tags: [daten]
  - position: Junior-Entwicklerin
    name: Muster GmbH
    location: Zürich
    startDate: 2015
    endDate: 2019
    x-display: 2015 bis 2019
    highlights:
      - Wartung von Webshops

teaching:
  - position: Kursleiterin Programmieren
    name: Volkshochschule Beispiel
    startDate: 2020
    x-display: seit 2020
    tags: [bildung]

languages:
  - language: Deutsch
    fluency: Muttersprache
  - language: Englisch
    fluency: Sehr gut (C1)

interests:
  - name: Wandern
  - name: Fotografie
    keywords: [Analog]

education:
  - studyType: Bachelor
    area: Informatik
    institution: Beispiel-Hochschule
    startDate: 2011
    endDate: 2015
    text: Bachelor of Science in Informatik, Beispiel-Hochschule

certificates:
  - name: Machine Learning Grundlagen
    issuer: Online-Kurs
    date: "2023-05"
    tags: [daten]

x-beschriftungen: {erfahrung: Berufserfahrung}
"""

JOB = "tags: [daten]\n"


def write_cv(folder, text: str = FULL_CV):
    folder.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(PHOTO, folder / "foto.jpg")
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


def bundle_from(path, track: str = "job", change=None) -> dict:
    """The answers of the page after opening it on this cv.yaml, with the other steps from the base example."""
    data = cv_read.form_data(yaml.safe_load(path.read_text(encoding="utf-8")))
    if change:
        data = copy.deepcopy(data)
        change(data)
    base = base_bundle(track)
    cv_sections = {s["id"] for s in FORM["sections"] if s.get("cv")}
    others = {key: value for key, value in base["data"].items() if key not in cv_sections}
    return {**base, "data": for_track({**others, **data}, track)}


def save(folder, bundle) -> import_bundle.ImportResult:
    assert validation.validate_bundle(FORM, bundle) == []
    return import_bundle.import_answers(folder, bundle, TODAY, force=True)


def pdf(path, tmp_path, name: str) -> tuple[int, list[str]]:
    job = tmp_path / "stelle.yaml"
    job.write_text(JOB, encoding="utf-8")
    out = tmp_path / f"{name}.pdf"
    build.main([str(path), "--job", str(job), "--build-dir", str(tmp_path / f"build-{name}"), "-o", str(out)])
    pages = PdfReader(out).pages
    return len(pages), [page.extract_text() for page in pages]


def changed_lines(before: str, after: str) -> list[str]:
    return [line for line in difflib.ndiff(before.splitlines(), after.splitlines()) if line[:2] in ("- ", "+ ")]


def test_the_form_is_filled_from_the_cv():
    data = cv_read.form_data(yaml.safe_load(FULL_CV))

    assert data["person"] == {
        "name": "Erika Beispiel", "label": "Software-Entwicklerin – Web und Daten", "email": "erika@example.ch",
        "phone": "079 000 00 00", "address": "Musterweg 1", "postalCode": "3000", "city": "Bern",
        "birthDate": "1. Mai 1990", "nationality": "Schweiz",
        "profiles": ["https://github.com/example", "www.linkedin.com/in/example"],
    }
    assert data["summary"] == {"summary": "Software-Entwicklerin mit zehn Jahren Praxis in Python und TypeScript. "
                                          "Baut Webanwendungen und Datenpipelines."}
    assert data["work"] == [
        {"position": "Software-Entwicklerin", "name": "Beispiel AG", "location": "Bern", "startDate": "2019-03",
         "highlights": ["Entwicklung einer Plattform für Kundendaten", "Aufbau von Datenpipelines mit Airflow"]},
        {"position": "Junior-Entwicklerin", "name": "Muster GmbH", "location": "Zürich", "startDate": "2015",
         "endDate": "2019", "highlights": ["Wartung von Webshops"]},
    ]
    assert data["education"] == [{"studyType": "Bachelor", "area": "Informatik", "institution": "Beispiel-Hochschule",
                                  "startDate": "2011", "endDate": "2015"}]
    assert data["certificates"] == [{"name": "Machine Learning Grundlagen", "issuer": "Online-Kurs", "date": "2023-05"}]
    assert data["languages"][1] == {"language": "Englisch", "fluency": "Sehr gut (C1)"}
    assert data["skills"][0] == {"name": "Sprachen", "keywords": ["Python", "TypeScript", "SQL"]}
    assert data["interests"] == {"interests": ["Wandern", "Fotografie"]}


def test_every_cv_section_of_the_form_is_filled_even_when_empty():
    data = cv_read.form_data({"basics": {"name": "Erika Beispiel"}})

    assert set(data) == {s["id"] for s in FORM["sections"] if s.get("cv")}
    assert data["work"] == [] and data["interests"] == {}


def test_a_cv_folder_without_a_readable_cv_fills_nothing(tmp_path):
    assert cv_read.read_form_data(tmp_path) is None
    (tmp_path / "cv.yaml").write_text("basics: [nicht: lesbar\n", encoding="utf-8")
    assert cv_read.read_form_data(tmp_path) is None
    (tmp_path / "cv.yaml").write_text("- eine Liste\n", encoding="utf-8")
    assert cv_read.read_form_data(tmp_path) is None


def test_saving_without_a_change_keeps_the_file_byte_for_byte(tmp_path):
    path = write_cv(tmp_path)

    result = save(tmp_path, bundle_from(path))

    assert "cv.yaml" in result.written and result.kept_files == ()
    assert path.read_text(encoding="utf-8") == FULL_CV


def test_saving_without_a_change_builds_the_same_pdf(tmp_path):
    path = write_cv(tmp_path / "daten")
    before = pdf(path, tmp_path, "vorher")

    save(path.parent, bundle_from(path))

    assert pdf(path, tmp_path, "nachher") == before
    assert before[0] >= 1 and "Beispiel AG" in "".join(before[1])


def test_a_change_rewrites_only_its_line_and_keeps_comments_and_order(tmp_path):
    path = write_cv(tmp_path)

    def new_phone(data):
        data["person"]["phone"] = "079 111 11 11"

    save(tmp_path, bundle_from(path, change=new_phone))

    after = path.read_text(encoding="utf-8")
    assert changed_lines(FULL_CV, after) == ["- " + "  phone: 079 000 00 00", "+ " + "  phone: 079 111 11 11"]


def test_fields_the_form_does_not_know_stay_on_their_entries(tmp_path):
    path = write_cv(tmp_path)

    def edit(data):
        data["work"][0]["position"] = "Senior-Entwicklerin"
        data["work"][0]["highlights"][1] = "Aufbau von Datenpipelines mit Airflow und dbt"
        data["work"][1]["name"] = "Muster AG"

    save(tmp_path, bundle_from(path, change=edit))

    work = yaml.safe_load(path.read_text(encoding="utf-8"))["work"]
    assert work[0]["position"] == "Senior-Entwicklerin" and work[0]["tags"] == ["web", "daten"]
    assert work[0]["highlights"][1] == {"text": "Aufbau von Datenpipelines mit Airflow und dbt", "tags": ["daten"]}
    assert work[1]["name"] == "Muster AG" and work[1]["x-display"] == "2015 bis 2019"
    assert work[1]["startDate"] == 2015


def test_removing_an_entry_keeps_the_fields_of_the_others(tmp_path):
    path = write_cv(tmp_path)

    def drop_first(data):
        del data["work"][0]
        del data["skills"][0]

    save(tmp_path, bundle_from(path, change=drop_first))

    cv = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert [w["name"] for w in cv["work"]] == ["Muster GmbH"] and cv["work"][0]["x-display"] == "2015 bis 2019"
    assert cv["skills"] == [{"name": "Daten", "keywords": ["pandas", "PostgreSQL"], "tags": ["daten"]}]


def test_a_new_entry_comes_in_and_a_cleared_field_goes(tmp_path):
    path = write_cv(tmp_path)

    def edit(data):
        data["certificates"].append({"name": "Scrum Master", "date": "2024"})
        del data["person"]["birthDate"]
        del data["work"][0]["location"]

    save(tmp_path, bundle_from(path, change=edit))

    cv = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert cv["certificates"][1] == {"name": "Scrum Master", "date": "2024"}
    assert cv["certificates"][0]["tags"] == ["daten"]
    assert cv["basics"]["details"] == ["Schweiz", "Führerausweis B"]
    assert "location" not in cv["work"][0] and cv["work"][0]["tags"] == ["web", "daten"]


def test_the_photo_and_what_the_form_never_writes_stay_as_they_were(tmp_path):
    path = write_cv(tmp_path)
    old = yaml.safe_load(FULL_CV)

    def edit(data):
        data["person"]["name"] = "Erika Muster"
        data["person"]["profiles"] = ["https://gitlab.com/example"]

    save(tmp_path, bundle_from(path, change=edit))

    cv = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert cv["basics"]["name"] == "Erika Muster"
    for key in ("image", "x-image", "url"):
        assert cv["basics"][key] == old["basics"][key]
    assert cv["basics"]["location"]["countryCode"] == "CH"
    assert cv["basics"]["profiles"] == [{"network": "GitLab", "url": "https://gitlab.com/example"},
                                        {"network": "Mastodon", "username": "beispiel"}]
    for key in ("projects", "teaching", "x-beschriftungen"):
        assert cv[key] == old[key]


def test_the_apprenticeship_track_keeps_what_only_the_job_track_shows(tmp_path):
    path = write_cv(tmp_path)
    old = yaml.safe_load(FULL_CV)

    save(tmp_path, bundle_from(path, track="apprenticeship"))

    cv = yaml.safe_load(path.read_text(encoding="utf-8"))
    for key in ("label", "summary", "profiles"):
        assert cv["basics"][key] == old["basics"][key]
    assert cv["education"][0]["area"] == "Informatik"
    assert cv["x-beschriftungen"] == old["x-beschriftungen"]


@pytest.mark.parametrize("text", [FULL_CV.replace("  - network: Mastodon\n      username: beispiel\n", ""),
                                  FULL_CV.replace('"geboren 1. Mai 1990", ', "")])
def test_variants_round_trip_as_well(tmp_path, text):
    path = write_cv(tmp_path, text)

    save(tmp_path, bundle_from(path))

    assert path.read_text(encoding="utf-8") == text
