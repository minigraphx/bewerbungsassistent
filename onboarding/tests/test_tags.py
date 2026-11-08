"""Tags on Meine Angaben (#161, G24): read from cv.yaml, suggested from the data folder, written back.

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
import markdown_files
import prefill
import validation
from form_cases import ROOT, base_bundle

TODAY = datetime.date(2026, 11, 8)
FORM = json.loads((ROOT / "form.json").read_text(encoding="utf-8"))

CV = """\
# Lebenslauf mit Tags (frei erfunden)
basics:
  name: Erika Beispiel
  email: erika@example.ch
  location:
    city: Bern
work:
  - position: Software-Entwicklerin
    name: Beispiel AG
    startDate: "2019-03"
    tags: [web, daten]
    highlights:
      - Plattform für Kundendaten  # wichtig
      - text: Datenpipelines mit Airflow
        tags: [daten]
  - position: Junior-Entwicklerin
    name: Muster GmbH
    startDate: "2015"
    endDate: "2019"
    highlights:
      - Wartung von Webshops
skills:
  - name: Daten
    keywords: [pandas]
    tags: [daten]
  - name: Programme
    keywords: [Python]
certificates:
  - name: Machine Learning Grundlagen
    tags:
      - ki
projects:
  - name: datenatlas
    tags: [daten, offen]
"""


def write_cv(folder, text: str = CV):
    path = folder / "cv.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def bundle_from(path, change=None, track: str = "job") -> dict:
    """What the page sends after opening on this cv.yaml: the CV sections from the file, the rest from the example."""
    data = copy.deepcopy(cv_read.form_data(yaml.safe_load(path.read_text(encoding="utf-8"))))
    if change:
        change(data)
    base = base_bundle(track)
    cv_sections = {s["id"] for s in FORM["sections"] if s.get("cv")}
    others = {key: value for key, value in base["data"].items() if key not in cv_sections}
    return {**base, "data": {**others, **{key: value for key, value in data.items() if value}}}


def save(folder, bundle) -> str:
    assert validation.validate_bundle(FORM, bundle) == []
    import_bundle.import_answers(folder, bundle, TODAY, force=True)
    return (folder / "cv.yaml").read_text(encoding="utf-8")


def test_tags_of_entries_and_highlights_are_read_into_the_form():
    data = cv_read.form_data(yaml.safe_load(CV))

    assert data["work"][0]["tags"] == ["web", "daten"]
    assert data["work"][0]["highlights"] == ["Plattform für Kundendaten",
                                             {"text": "Datenpipelines mit Airflow", "tags": ["daten"]}]
    assert "tags" not in data["work"][1]
    assert data["skills"][0] == {"name": "Daten", "keywords": ["pandas"], "tags": ["daten"]}
    assert data["certificates"] == [{"name": "Machine Learning Grundlagen", "tags": ["ki"]}]


def test_tags_the_form_cannot_show_are_left_out_of_it():
    text = CV.replace("tags: [web, daten]", "tags: web").replace("        tags: [daten]\n", "        tags: daten\n")
    data = cv_read.form_data(yaml.safe_load(text))

    assert "tags" not in data["work"][0]
    assert data["work"][0]["highlights"][1] == "Datenpipelines mit Airflow"


def test_the_tags_fields_are_in_the_form_where_the_cv_has_tags():
    fields = {s["id"]: {f["id"]: f for f in s["fields"]} for s in FORM["sections"]}

    for section in ("work", "skills", "certificates"):
        assert fields[section]["tags"]["type"] == "tags"
    assert fields["work"]["highlights"]["tags"] is True
    assert "tags" not in fields["languages"] and "tags" not in fields["education"]


def test_saving_without_a_change_keeps_a_tagged_cv_byte_for_byte(tmp_path):
    path = write_cv(tmp_path)

    assert save(tmp_path, bundle_from(path)) == CV


def test_saving_without_a_change_keeps_tags_the_form_cannot_show(tmp_path):
    text = CV.replace("tags: [web, daten]", "tags: web").replace("        tags: [daten]\n", "        tags: daten\n")
    path = write_cv(tmp_path, text)

    assert save(tmp_path, bundle_from(path)) == text

    def edit(data):
        data["work"][0]["position"] = "Senior-Entwicklerin"

    work = yaml.safe_load(save(tmp_path, bundle_from(path, edit)))["work"]
    assert work[0]["tags"] == "web" and work[0]["highlights"][1] == {"text": "Datenpipelines mit Airflow", "tags": "daten"}


def test_a_new_tag_on_an_entry_is_written_as_a_short_list(tmp_path):
    path = write_cv(tmp_path)

    def edit(data):
        data["skills"][1]["tags"] = ["web", "neu"]

    after = save(tmp_path, bundle_from(path, edit))

    assert yaml.safe_load(after)["skills"][1] == {"name": "Programme", "keywords": ["Python"], "tags": ["web", "neu"]}
    assert "    tags: [web, neu]\n" in after


def test_changing_the_tags_of_an_entry_changes_only_its_tags(tmp_path):
    path = write_cv(tmp_path)

    def edit(data):
        data["work"][0]["tags"] = ["web", "ki"]

    after = save(tmp_path, bundle_from(path, edit))

    assert yaml.safe_load(after)["work"][0]["tags"] == ["web", "ki"]
    assert after == CV.replace("tags: [web, daten]", "tags: [web, ki]")


def test_removing_all_tags_of_an_entry_removes_the_key(tmp_path):
    path = write_cv(tmp_path)

    def edit(data):
        data["certificates"][0]["tags"] = []

    cv = yaml.safe_load(save(tmp_path, bundle_from(path, edit)))

    assert cv["certificates"] == [{"name": "Machine Learning Grundlagen"}]
    assert cv["projects"][0]["tags"] == ["daten", "offen"]


def test_a_tag_on_a_plain_highlight_makes_it_text_and_tags(tmp_path):
    path = write_cv(tmp_path)

    def edit(data):
        data["work"][0]["highlights"][0] = {"text": "Plattform für Kundendaten", "tags": ["web"]}

    after = save(tmp_path, bundle_from(path, edit))

    highlights = yaml.safe_load(after)["work"][0]["highlights"]
    assert highlights[0] == {"text": "Plattform für Kundendaten", "tags": ["web"]}
    assert highlights[1] == {"text": "Datenpipelines mit Airflow", "tags": ["daten"]}
    assert "tags: [web]" in after


def test_a_highlight_without_tags_is_written_as_plain_text(tmp_path):
    path = write_cv(tmp_path)

    def edit(data):
        data["work"][0]["highlights"][1] = {"text": "Datenpipelines mit Airflow", "tags": []}

    highlights = yaml.safe_load(save(tmp_path, bundle_from(path, edit)))["work"][0]["highlights"]

    assert highlights == ["Plattform für Kundendaten", "Datenpipelines mit Airflow"]


def test_editing_the_text_of_a_tagged_highlight_keeps_it_with_its_tags(tmp_path):
    path = write_cv(tmp_path)

    def edit(data):
        data["work"][0]["highlights"][1] = {"text": "Datenpipelines mit Airflow und dbt", "tags": ["daten"]}

    after = save(tmp_path, bundle_from(path, edit))

    assert yaml.safe_load(after)["work"][0]["highlights"][1] == {"text": "Datenpipelines mit Airflow und dbt",
                                                                 "tags": ["daten"]}
    assert "Plattform für Kundendaten  # wichtig" in after


def test_a_highlight_keeps_its_other_fields_when_its_tags_go(tmp_path):
    path = write_cv(tmp_path, CV.replace("        tags: [daten]\n", "        tags: [daten]\n        prio: 1\n"))

    def edit(data):
        data["work"][0]["highlights"][1] = {"text": "Datenpipelines mit Airflow", "tags": []}

    highlights = yaml.safe_load(save(tmp_path, bundle_from(path, edit)))["work"][0]["highlights"]

    assert highlights[1] == {"text": "Datenpipelines mit Airflow", "prio": 1}


def without_tags(data: dict) -> None:
    """An answer from before G24: no tags key anywhere, highlights as plain text."""
    for section in ("work", "skills", "certificates"):
        for entry in data[section]:
            entry.pop("tags", None)
            if "highlights" in entry:
                entry["highlights"] = [line["text"] if isinstance(line, dict) else line for line in entry["highlights"]]


def test_an_old_bundle_without_tags_keeps_them_byte_for_byte(tmp_path):
    path = write_cv(tmp_path)

    assert save(tmp_path, bundle_from(path, without_tags)) == CV


def test_an_old_bundle_with_a_change_keeps_the_tags_of_matching_entries(tmp_path):
    path = write_cv(tmp_path)

    def edit(data):
        without_tags(data)
        data["work"][0]["position"] = "Senior-Entwicklerin"
        data["work"][0]["highlights"][1] = "Datenpipelines mit Airflow und dbt"
        data["skills"].reverse()

    cv = yaml.safe_load(save(tmp_path, bundle_from(path, edit)))

    assert cv["work"][0]["position"] == "Senior-Entwicklerin" and cv["work"][0]["tags"] == ["web", "daten"]
    assert cv["work"][0]["highlights"][1] == {"text": "Datenpipelines mit Airflow und dbt", "tags": ["daten"]}
    assert {s["name"]: s.get("tags") for s in cv["skills"]} == {"Daten": ["daten"], "Programme": None}
    assert cv["certificates"][0]["tags"] == ["ki"]


def test_an_explicit_empty_list_removes_the_tags(tmp_path):
    path = write_cv(tmp_path)

    def edit(data):
        without_tags(data)
        data["work"][0]["tags"] = []
        data["work"][0]["highlights"][1] = {"text": "Datenpipelines mit Airflow", "tags": []}

    cv = yaml.safe_load(save(tmp_path, bundle_from(path, edit)))

    assert "tags" not in cv["work"][0]
    assert cv["work"][0]["highlights"] == ["Plattform für Kundendaten", "Datenpipelines mit Airflow"]
    assert cv["skills"][0]["tags"] == ["daten"] and cv["certificates"][0]["tags"] == ["ki"]


def test_what_the_page_sends_after_removing_a_tag_removes_it(tmp_path):
    path = write_cv(tmp_path)

    def removed_on_the_page(data):
        # what model.js collectBundle sends after the person cleared the tags (tags.test.cjs checks that shape)
        data["certificates"][0]["tags"] = []
        data["work"][0]["highlights"][1] = {"text": "Datenpipelines mit Airflow", "tags": []}
        data["work"][1]["highlights"][0] = {"text": "Wartung von Webshops", "tags": []}

    after = save(tmp_path, bundle_from(path, removed_on_the_page))

    cv = yaml.safe_load(after)
    assert "tags" not in cv["certificates"][0] and cv["work"][0]["highlights"][1] == "Datenpipelines mit Airflow"
    assert cv["work"][1]["highlights"] == ["Wartung von Webshops"] and "tags: []" not in after


def test_a_new_entry_with_an_empty_list_of_tags_has_none(tmp_path):
    path = write_cv(tmp_path)

    def edit(data):
        data["certificates"].append({"name": "Scrum Master", "tags": []})
        data["work"][1]["highlights"].append({"text": "Shop-Migration", "tags": []})

    after = save(tmp_path, bundle_from(path, edit))

    cv = yaml.safe_load(after)
    assert cv["certificates"][1] == {"name": "Scrum Master"}
    assert cv["work"][1]["highlights"] == ["Wartung von Webshops", "Shop-Migration"]


def test_an_empty_cv_file_gets_no_empty_tags(tmp_path):
    write_cv(tmp_path, "")
    bundle = base_bundle("job")
    bundle["data"]["work"][0]["tags"] = []
    bundle["data"]["work"][0]["highlights"][0] = {"text": "Plattform", "tags": []}

    after = save(tmp_path, bundle)

    assert "tags" not in after and yaml.safe_load(after)["work"][0]["highlights"][0] == "Plattform"


def test_a_new_tagged_highlight_and_entry_come_in(tmp_path):
    path = write_cv(tmp_path)

    def edit(data):
        data["work"][1]["highlights"].append({"text": "Shop-Migration", "tags": ["web"]})
        data["certificates"].append({"name": "Scrum Master", "tags": ["agil"]})

    after = save(tmp_path, bundle_from(path, edit))

    cv = yaml.safe_load(after)
    assert cv["work"][1]["highlights"] == ["Wartung von Webshops", {"text": "Shop-Migration", "tags": ["web"]}]
    assert cv["certificates"][1] == {"name": "Scrum Master", "tags": ["agil"]}
    assert "tags: [agil]" in after


def test_a_new_cv_gets_the_tags_of_the_answers():
    bundle = base_bundle("job")
    bundle["data"]["work"][0]["tags"] = [" web ", "daten"]
    bundle["data"]["work"][0]["highlights"] = ["Plattform", {"text": " Datenpipelines ", "tags": ["daten"]},
                                               {"text": "Ohne Tags", "tags": [" "]}]
    bundle["data"]["skills"][0]["tags"] = ["daten"]
    bundle["data"]["certificates"][0]["tags"] = ["ki"]

    cv = convert.build_cv(bundle["data"], "job")

    assert cv["work"][0]["tags"] == ["web", "daten"]
    assert cv["work"][0]["highlights"] == ["Plattform", {"text": "Datenpipelines", "tags": ["daten"]}, "Ohne Tags"]
    assert cv["skills"][0]["tags"] == ["daten"] and cv["certificates"][0]["tags"] == ["ki"]
    assert "tags" not in cv["work"][1]


def test_the_building_blocks_keep_the_text_of_tagged_highlights():
    bundle = base_bundle("job")
    bundle["data"]["work"][0]["highlights"] = ["Plattform", {"text": "Datenpipelines", "tags": ["daten"]}]

    blocks = markdown_files.building_blocks(bundle["data"], "job", "Notiz")

    assert "Plattform; Datenpipelines" in blocks and "daten" not in blocks.split("Datenpipelines")[1].split("\n")[0]


def test_the_ai_is_not_asked_for_tags():
    guide = prefill.field_guide(FORM, "job")

    assert "tags" not in guide


def test_messages_about_tags_name_the_tag_and_its_limits():
    long_tag = validation.describe(FORM, "job", validation.ValidationError("work.0.tags.2", "max"))
    bad_line_tag = validation.describe(FORM, "job", validation.ValidationError("work.0.highlights.1.tags.0", "format"))
    many = validation.describe(FORM, "job", validation.ValidationError("work.0.highlights.1.tags", "maxItems"))

    assert long_tag == "Berufliche Stationen, Station 1, Tags, Tag 3: Zu lang (höchstens 40 Zeichen)."
    assert bad_line_tag.startswith("Berufliche Stationen, Station 1, Tätigkeiten und Erfolge, Zeile 2, Tags, Tag 1: ")
    assert bad_line_tag.endswith("daten.")
    assert many.endswith("Zu viele Einträge (höchstens 10).")


def write(folder, rel: str, text: str) -> None:
    path = folder / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_suggestions_are_the_tags_of_the_cv_the_variants_and_the_jobs(tmp_path):
    write_cv(tmp_path)
    write(tmp_path, "varianten.yaml", "- id: daten\n  quelle: jobs/daten.yaml\n  tags: [Daten, fullstack]\n")
    write(tmp_path, "jobs/daten.yaml", "tags: [daten, ki]\nmax_highlights: 4\n")
    write(tmp_path, "jobs/lehre.yaml", "# Zuschnitt\ntags: [bildung]\n")

    assert known_tags.known_tags(tmp_path, FORM) == ["bildung", "Daten", "daten", "fullstack", "ki", "offen", "web"]


@pytest.mark.parametrize("text, expected", [
    ("tags: [zwei Wörter, gut]\n", ["gut"]), ("tags: [gut, 5, null, true, {a: 1}, [x]]\n", ["gut"]),
    ("tags: [gut, " + "x" * 41 + "]\n", ["gut"]), ("tags: [gut, 'a,b']\n", ["gut"]), ("tags: gut\n", []),
])
def test_suggestions_leave_out_what_is_no_valid_tag(tmp_path, text, expected):
    write(tmp_path, "jobs/a.yaml", text)

    assert known_tags.known_tags(tmp_path, FORM) == expected


def test_suggestions_skip_files_that_cannot_be_read(tmp_path):
    write(tmp_path, "cv.yaml", "work: [nicht: lesbar\n")
    write(tmp_path, "varianten.yaml", "- eine\n- {tags: [daten]}\n")
    write(tmp_path, "jobs/kaputt.yaml", "tags: [\n")
    (tmp_path / "jobs" / "binär.yaml").write_bytes(b"\xff\xfe\x00")
    write(tmp_path, "jobs/gut.yaml", "tags: [ki]\n")
    write(tmp_path, "jobs/notiz.md", "tags: [md]\n")

    assert known_tags.known_tags(tmp_path, FORM) == ["daten", "ki"]


def test_an_empty_folder_suggests_nothing(tmp_path):
    assert known_tags.known_tags(tmp_path, FORM) == []


def test_suggestions_are_limited(tmp_path):
    write(tmp_path, "jobs/viele.yaml", "tags: [" + ", ".join(f"t{i:04d}" for i in range(known_tags.MAX_TAGS + 50)) + "]\n")

    assert len(known_tags.known_tags(tmp_path, FORM)) == known_tags.MAX_TAGS
