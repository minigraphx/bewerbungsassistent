"""Meine Angaben edits and adds every value an existing cv.yaml holds (#181, G30).

The values #167 only let pass unchanged (two-language values, full dates, long texts, more entries than the old
limits, a station shown by its display only, a fluency outside the suggestions) can now be changed and added anew,
and the saved cv.yaml holds exactly the edit. A data folder from 0.2.14 still loads, saves unchanged byte for byte
and builds the same CV. All data is invented.
"""
import copy
import datetime
import difflib
import json

import pypdf
import pytest
import yaml

import build
import convert
import cv_read
import import_bundle
import validation
from form_cases import ROOT, base_bundle

TODAY = datetime.date(2026, 11, 13)
FORM = json.loads((ROOT / "form.json").read_text(encoding="utf-8"))
LONG = "Sehr lange Funktionsbezeichnung " * 4
LANGUAGES = "".join(f"  - language: Sprache {n}\n    fluency: Gut (B2)\n" for n in range(1, 8))
HIGHLIGHTS = "".join(f"      - Punkt {n}\n" for n in range(1, 9))

EXISTING_CV = f"""\
# Lebenslauf von Hand (frei erfunden)
basics:
  name: Erika Beispiel
  email: erika@example.ch
  location:
    city: Bern
  summary:
    de: Software-Entwicklerin mit zehn Jahren Praxis.
    en: Software developer with ten years of experience.

work:
  - position: {{de: Software-Entwicklerin, en: Software developer}}
    name: Beispiel AG
    startDate: '2022-06-01'
    endDate: '2023-01-15'
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

# What the import of version 0.2.14 wrote for the base example of cases.json, unchanged.
CV_0_2_14 = """\
# Erstellt mit der Einstiegsvorlage am 1.11.2026. Format: lebenslauf/README.md
basics:
  name: Erika Beispiel
  email: erika@example.ch
  phone: 079 000 00 00
  location:
    address: Musterweg 1
    postalCode: '3000'
    city: Bern
  summary: Software-Entwicklerin mit zehn Jahren Praxis.
  profiles:
  - network: GitHub
    url: https://github.com/example
work:
- position: Software-Entwicklerin
  name: Beispiel AG
  location: Bern
  startDate: 2019-03
  endDate: null
  highlights:
  - Plattform für Kundendaten
  - Datenpipelines
- position: Junior-Entwicklerin
  name: Muster GmbH
  startDate: '2015'
  endDate: '2019'
education:
- studyType: Bachelor
  area: Informatik
  institution: Beispiel-Hochschule, Bern
  startDate: '2011'
  endDate: '2015'
certificates:
- name: Machine Learning Grundlagen
  issuer: Online-Kurs
  date: 2023-05
languages:
- language: Deutsch
  fluency: Muttersprache
- language: Englisch
  fluency: Sehr gut (C1)
skills:
- name: Programme
  keywords:
  - Python
  - SQL
interests:
- name: Wandern
"""


def write_cv(folder, text: str = EXISTING_CV):
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "cv.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def bundle_from(path, change=None) -> dict:
    """The answers of the page after opening it on this cv.yaml and the edit, with the other steps from the base."""
    data = cv_read.form_data(yaml.safe_load(path.read_text(encoding="utf-8")))
    if change:
        data = copy.deepcopy(data)
        change(data)
    base = base_bundle("job")
    cv_sections = {s["id"] for s in FORM["sections"] if s.get("cv")}
    others = {key: value for key, value in base["data"].items() if key not in cv_sections}
    return {**base, "data": {**others, **{key: value for key, value in data.items() if value}}}


def save(folder, change=None) -> dict:
    """Save the page after the edit; the cv.yaml as written."""
    path = folder / "cv.yaml"
    import_bundle.import_answers(folder, bundle_from(path, change), TODAY, force=True)
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def changed_lines(before: str, after: str) -> list[str]:
    return [line for line in difflib.ndiff(before.splitlines(), after.splitlines()) if line[:2] in ("- ", "+ ")]


def errors_of(path, change) -> list[str]:
    bundle = bundle_from(path, change)
    return [f"{e.path}|{e.code}" for e in validation.validate_bundle(FORM, bundle, loaded=cv_read.read_form_data(path.parent))]


# Two-language values


def test_both_languages_of_a_field_are_edited_and_saved_as_de_en(tmp_path):
    path = write_cv(tmp_path)

    def edit(data):
        data["work"][0]["position"] = {"de": "Senior-Entwicklerin", "en": "Senior developer"}

    cv = save(tmp_path, edit)

    assert cv["work"][0]["position"] == {"de": "Senior-Entwicklerin", "en": "Senior developer"}
    assert changed_lines(EXISTING_CV, path.read_text(encoding="utf-8")) == [
        "-   - position: {de: Software-Entwicklerin, en: Software developer}",
        "+   - position: {de: Senior-Entwicklerin, en: Senior developer}",
    ]


def test_a_two_language_text_in_block_form_keeps_its_form(tmp_path):
    path = write_cv(tmp_path)

    def edit(data):
        data["summary"]["summary"] = {"de": "Entwicklerin mit Praxis.", "en": "Software developer with ten years of experience."}

    save(tmp_path, edit)

    assert changed_lines(EXISTING_CV, path.read_text(encoding="utf-8")) == [
        "-     de: Software-Entwicklerin mit zehn Jahren Praxis.", "+     de: Entwicklerin mit Praxis."]


def test_a_two_language_highlight_is_edited_and_keeps_its_tags(tmp_path):
    write_cv(tmp_path)

    def edit(data):
        data["work"][0]["highlights"][1] = {"text": {"de": "Schulungen für das Team", "en": "Team training"},
                                            "tags": ["bildung"]}

    cv = save(tmp_path, edit)

    assert cv["work"][0]["highlights"][1] == {"text": {"de": "Schulungen für das Team", "en": "Team training"},
                                              "tags": ["bildung"]}
    assert cv["work"][0]["highlights"][0] == {"de": "Aufbau von Datenpipelines", "en": "Built data pipelines"}


def test_new_two_language_values_are_added(tmp_path):
    write_cv(tmp_path)

    def add(data):
        data["work"].append({"position": {"de": "Teamleiterin", "en": "Team lead"}, "name": "Neu AG",
                             "startDate": "2024-02-01",
                             "highlights": [{"de": "Team aufgebaut", "en": "Built the team"}, "Budget geführt"]})
        data["work"][1]["highlights"] = [{"de": "Kurse gegeben", "en": "Gave courses"}]
        data["person"]["label"] = {"de": "Entwicklerin", "en": "Developer"}

    cv = save(tmp_path, add)

    added = cv["work"][3]
    assert added["position"] == {"de": "Teamleiterin", "en": "Team lead"}
    assert added["highlights"] == [{"de": "Team aufgebaut", "en": "Built the team"}, "Budget geführt"]
    assert added["startDate"] == "2024-02-01"
    assert cv["work"][1]["highlights"] == [{"de": "Kurse gegeben", "en": "Gave courses"}]
    assert cv["basics"]["label"] == {"de": "Entwicklerin", "en": "Developer"}


def test_a_two_language_value_can_become_one_language_and_be_removed(tmp_path):
    write_cv(tmp_path)

    def edit(data):
        data["work"][0]["position"] = "Entwicklerin"
        del data["summary"]["summary"]

    cv = save(tmp_path, edit)

    assert cv["work"][0]["position"] == "Entwicklerin"
    assert "summary" not in cv["basics"]


def test_two_language_values_typed_anew_follow_the_rules(tmp_path):
    path = write_cv(tmp_path)

    def edit(data):
        data["work"][0]["position"] = {"de": "Zeile\nmit Umbruch", "en": "Developer"}
        data["languages"][0]["fluency"] = {"de": "", "en": ""}
        data["person"]["email"] = {"de": "erika@example.ch", "en": "erika@example.ch"}

    assert sorted(errors_of(path, edit)) == ["languages.0.fluency|required", "person.email|type",
                                            "work.0.position|newline"]


# Full dates


def test_a_full_date_is_edited_and_added_as_full_date(tmp_path):
    path = write_cv(tmp_path)

    def edit(data):
        data["work"][0]["startDate"] = "2022-07-15"
        data["work"].append({"position": "Beraterin", "name": "Neu AG", "startDate": "2024-03-01",
                             "endDate": "2024-03-31"})

    assert errors_of(path, edit) == []
    cv = save(tmp_path, edit)

    assert cv["work"][0]["startDate"] == "2022-07-15"
    assert (cv["work"][3]["startDate"], cv["work"][3]["endDate"]) == ("2024-03-01", "2024-03-31")


@pytest.mark.parametrize("start, end, codes", [
    ("2022-06-15", "2022-06", []),  # same month: not before the start
    ("2022-06-15", "2022-06-14", ["work.0.endDate|notBefore"]),
    ("2022-06-15", "2021", ["work.0.endDate|notBefore"]),
    ("2022-13-01", "", ["work.0.startDate|format"]),
    ("2022-06-32", "", ["work.0.startDate|format"]),
])
def test_full_dates_keep_their_order_and_format(tmp_path, start, end, codes):
    path = write_cv(tmp_path)

    def edit(data):
        data["work"][0].update(startDate=start, endDate=end)

    assert errors_of(path, edit) == codes


# Long texts and more entries


def test_texts_longer_than_the_old_limits_are_edited_and_added(tmp_path):
    path = write_cv(tmp_path)
    longer = "Leitende Entwicklerin für Datenplattformen " * 5

    def edit(data):
        data["work"][1]["position"] = longer.strip()
        data["work"][2]["highlights"][0] = "Punkt " * 60
        data["person"]["name"] = "Erika " * 20
        data["summary"]["summary"] = {"de": "Satz. " * 200, "en": "Sentence. " * 200}

    assert errors_of(path, edit) == []
    cv = save(tmp_path, edit)
    assert cv["work"][1]["position"] == longer.strip()


def test_more_entries_than_the_old_limits_are_added(tmp_path):
    path = write_cv(tmp_path)

    def add(data):
        data["languages"] += [{"language": f"Neue Sprache {n}", "fluency": "Mittel (B1)"} for n in range(1, 4)]
        data["work"][2]["highlights"] += [f"Neuer Punkt {n}" for n in range(1, 4)]
        data["work"] += [{"position": f"Station {n}", "name": "Firma", "startDate": "2000"} for n in range(25)]
        data["person"]["profiles"] = [f"https://example.ch/profil-{n}" for n in range(8)]

    assert errors_of(path, add) == []
    cv = save(tmp_path, add)
    assert len(cv["languages"]) == 12
    assert len(cv["work"][2]["highlights"]) == 11
    assert len(cv["work"]) == 28


# A station shown by its display only


def test_a_station_with_a_display_and_no_start_is_shown_edited_and_added(tmp_path):
    path = write_cv(tmp_path)
    assert cv_read.read_form_data(tmp_path)["work"][1]["x-display"] == "2010 bis 2014"

    def edit(data):
        data["work"][1]["x-display"] = "2010 bis 2015"
        data["work"].append({"position": "Mentorin", "name": "Verein Beispiel", "x-display": "seit 2020"})

    assert errors_of(path, edit) == []
    cv = save(tmp_path, edit)

    assert cv["work"][1]["x-display"] == "2010 bis 2015"
    assert cv["work"][3] == {"position": "Mentorin", "name": "Verein Beispiel", "x-display": "seit 2020"}


def test_a_new_station_still_needs_a_start_or_a_display(tmp_path):
    path = write_cv(tmp_path)

    def add(data):
        data["work"].append({"position": "Mentorin", "name": "Verein Beispiel"})

    assert errors_of(path, add) == ["work.3.startDate|required"]


# A fluency outside the suggestions


def test_a_fluency_in_own_words_is_edited_and_added(tmp_path):
    path = write_cv(tmp_path)

    def edit(data):
        data["languages"][1]["fluency"] = "verhandlungssicher in Wort und Schrift"
        data["languages"].append({"language": "Italienisch", "fluency": "Ferienkenntnisse"})
        data["languages"].append({"language": "Französisch", "fluency": {"de": "Gut", "en": "Good"}})

    assert errors_of(path, edit) == []
    cv = save(tmp_path, edit)

    assert cv["languages"][1]["fluency"] == "verhandlungssicher in Wort und Schrift"
    assert cv["languages"][9:] == [{"language": "Italienisch", "fluency": "Ferienkenntnisse"},
                                   {"language": "Französisch", "fluency": {"de": "Gut", "en": "Good"}}]


# Older data folders


def test_a_cv_from_0_2_14_loads_and_saves_unchanged_byte_for_byte(tmp_path):
    path = write_cv(tmp_path, CV_0_2_14)

    assert errors_of(path, None) == []
    save(tmp_path)

    assert path.read_text(encoding="utf-8") == CV_0_2_14


def test_an_existing_cv_saves_unchanged_byte_for_byte(tmp_path):
    path = write_cv(tmp_path)

    save(tmp_path)

    assert path.read_text(encoding="utf-8") == EXISTING_CV


def pdf_text(cv_path, out, lang: str = "de") -> str:
    pdf = build.main([str(cv_path), "--build-dir", str(out / "build"), "-o", str(out / f"cv-{lang}.pdf"), "--lang", lang])
    return " ".join(" ".join(page.extract_text().split()) for page in pypdf.PdfReader(pdf).pages)


def test_a_cv_from_0_2_14_builds_the_same_cv_after_saving(tmp_path):
    path = write_cv(tmp_path / "daten", CV_0_2_14)
    before = pdf_text(path, tmp_path / "vorher")

    save(tmp_path / "daten")

    assert pdf_text(path, tmp_path / "nachher") == before


def test_lebenslauf_renders_every_new_form(tmp_path):
    path = write_cv(tmp_path / "daten")

    def edit(data):
        data["work"][0]["startDate"] = "2022-07-15"
        data["work"][0]["position"] = {"de": "Senior-Entwicklerin", "en": "Senior developer"}
        data["work"].append({"position": "Mentorin", "name": "Verein Beispiel", "x-display": {"de": "seit 2020", "en": "since 2020"}})
        data["languages"][1]["fluency"] = {"de": "verhandlungssicher", "en": "business fluent"}

    save(tmp_path / "daten", edit)
    german = pdf_text(path, tmp_path / "de")
    english = pdf_text(path, tmp_path / "en", "en")

    assert "Senior-Entwicklerin" in german and "Juli 2022" in german and "seit 2020" in german
    assert "verhandlungssicher" in german
    assert "Senior developer" in english and "July 2022" in english and "since 2020" in english
    assert "business fluent" in english


def test_lebenslauf_renders_a_full_date_written_without_quotes(tmp_path):
    path = write_cv(tmp_path, EXISTING_CV.replace("'2022-06-01'", "2022-06-01"))

    assert "Juni 2022" in pdf_text(path, tmp_path)


def test_the_building_blocks_take_the_german_text_of_two_languages():
    bundle = base_bundle("job")
    bundle["data"]["work"][0]["position"] = {"de": "Senior-Entwicklerin", "en": "Senior developer"}
    bundle["data"]["work"][0]["highlights"] = [{"de": "Team aufgebaut", "en": "Built the team"}]

    blocks = convert.convert_bundle(FORM, bundle, TODAY)["anschreiben/bausteine.md"]

    assert "Senior-Entwicklerin" in blocks and "Team aufgebaut" in blocks and "Senior developer" not in blocks
