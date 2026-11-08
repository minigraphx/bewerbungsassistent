"""Replacing the basics must not lose CV content the form cannot show (#159, #160); all data is invented."""
import datetime

import pytest
import yaml

import import_bundle
from form_cases import base_bundle

TODAY = datetime.date(2026, 11, 8)

EXTRAS_ONLY = """\
# Von Hand ergänzt
basics:
  name: Alt Beispiel
  phone: 079 111 11 11
  image: foto.jpg
  x-image: {mirror: true, zoom: 1.3, x: 0.5, y: 0.2}
  url: https://beispiel.example
work:
  - position: Alte Stelle
    name: Alt AG
    startDate: "2010"
    endDate: "2012"
    highlights: [Erster Punkt]
projects:
  - name: Beispielprojekt
    group: more
    highlights: [Prototyp gebaut]
teaching:
  - position: Kursleiterin
    name: Beispiel-Schule
    startDate: "2020"
x-farbe: blau
x-beschriftungen: {erfahrung: Berufserfahrung}
"""

TAGGED = EXTRAS_ONLY.replace(
    "    highlights: [Erster Punkt]\n",
    "    tags: [daten]\n"
    "    x-display: seit 2010\n"
    "    highlights:\n"
    "      - Erster Punkt\n"
    "      - {text: Zweiter Punkt, tags: [daten]}\n",
)


def existing_cv(tmp_path, text: str):
    path = tmp_path / "cv.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def replace(tmp_path, track: str = "job") -> import_bundle.ImportResult:
    return import_bundle.import_answers(tmp_path, base_bundle(track), TODAY, force=True)


def test_replacing_carries_over_what_the_form_does_not_write(tmp_path):
    path = existing_cv(tmp_path, EXTRAS_ONLY)
    old = yaml.safe_load(EXTRAS_ONLY)

    result = replace(tmp_path)

    cv = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert "cv.yaml" in result.written and result.kept_files == ()
    assert cv["basics"]["name"] == "Erika Beispiel"
    assert "phone" in cv["basics"] and cv["basics"]["phone"] != "079 111 11 11"
    for key in ("image", "x-image", "url"):
        assert cv["basics"][key] == old["basics"][key]
    for key in ("projects", "teaching", "x-farbe", "x-beschriftungen"):
        assert cv[key] == old[key]
    assert cv["work"][0]["name"] == "Beispiel AG"


def test_basics_the_person_cleared_in_the_form_stay_cleared(tmp_path):
    path = existing_cv(tmp_path, EXTRAS_ONLY)
    bundle = base_bundle("job")
    del bundle["data"]["person"]["phone"]

    import_bundle.import_answers(tmp_path, bundle, TODAY, force=True)

    assert "phone" not in yaml.safe_load(path.read_text(encoding="utf-8"))["basics"]


MATCHING = EXTRAS_ONLY.replace("  - position: Alte Stelle\n    name: Alt AG\n    startDate: \"2010\"\n    endDate: \"2012\"\n",
                               "  - position: Software-Entwicklerin\n    name: Beispiel AG\n    startDate: \"2019-03\"\n")


@pytest.mark.parametrize("change, kept", [
    (("    highlights: [Erster Punkt]\n", "    tags: daten\n    highlights: [Erster Punkt]\n"),
     lambda cv: cv["work"][0]["tags"] == "daten"),
    (("    highlights: [Erster Punkt]\n", "    highlights: [{text: Plattform für Kundendaten, tags: daten}]\n"),
     lambda cv: cv["work"][0]["highlights"][0] == {"text": "Plattform für Kundendaten", "tags": "daten"}),
    (("    highlights: [Erster Punkt]\n", "    x-display: seit 2019\n    highlights: [Erster Punkt]\n"),
     lambda cv: cv["work"][0]["x-display"] == "seit 2019"),
    (("    highlights: [Erster Punkt]\n", "    summary: Ein Satz, den das Formular nicht kennt\n"),
     lambda cv: cv["work"][0]["summary"] == "Ein Satz, den das Formular nicht kennt"),
    (("x-farbe: blau\n", "education:\n  - text: Matura, Beispiel-Gymnasium\n"),
     lambda cv: cv["education"][0] == {"text": "Matura, Beispiel-Gymnasium"} and len(cv["education"]) == 2),
    (("  url: https://beispiel.example\n", "  location: {city: Bern, countryCode: CH}\n"),
     lambda cv: cv["basics"]["location"]["countryCode"] == "CH"),
    (("  url: https://beispiel.example\n", "  profiles: [{network: GitHub, username: beispiel}]\n"),
     lambda cv: {"network": "GitHub", "username": "beispiel"} in cv["basics"]["profiles"]),
])
def test_fields_the_form_does_not_know_stay_when_replacing(tmp_path, change, kept):
    text = MATCHING.replace(*change)
    assert text != MATCHING
    path = existing_cv(tmp_path, text)

    result = replace(tmp_path)

    cv = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert "cv.yaml" in result.written and result.kept_files == ()
    assert kept(cv)
    assert cv["basics"]["name"] == "Erika Beispiel"


TAGGED_MATCH = MATCHING.replace("    highlights: [Erster Punkt]\n",
                                "    tags: [daten]\n    highlights: [{text: Plattform für Kundendaten, tags: [daten]}]\n")


def test_tags_are_answers_since_the_form_shows_them(tmp_path):
    path = existing_cv(tmp_path, TAGGED_MATCH)
    bundle = base_bundle("job")
    bundle["data"]["work"][0]["tags"] = ["daten"]
    bundle["data"]["work"][0]["highlights"][0] = {"text": "Plattform für Kundendaten", "tags": ["daten"]}

    import_bundle.import_answers(tmp_path, bundle, TODAY, force=True)

    work = yaml.safe_load(path.read_text(encoding="utf-8"))["work"][0]
    assert work["tags"] == ["daten"]
    assert work["highlights"] == [{"text": "Plattform für Kundendaten", "tags": ["daten"]}, "Datenpipelines"]


def test_answers_without_tags_take_them_away(tmp_path):
    path = existing_cv(tmp_path, TAGGED_MATCH)

    replace(tmp_path)

    work = yaml.safe_load(path.read_text(encoding="utf-8"))["work"][0]
    assert "tags" not in work and work["highlights"] == ["Plattform für Kundendaten", "Datenpipelines"]


def test_an_entry_the_answers_no_longer_hold_goes_with_its_fields(tmp_path):
    path = existing_cv(tmp_path, TAGGED)

    result = replace(tmp_path)

    cv = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert result.kept_files == () and "cv.yaml" in result.written
    assert [w["name"] for w in cv["work"]] == ["Beispiel AG", "Muster GmbH"]
    assert all("tags" not in w and "x-display" not in w for w in cv["work"])
    assert set(result.written) == {"cv.yaml", "suchprofil.md", "anschreiben/stil.md", "anschreiben/bausteine.md"}


def test_a_cv_that_cannot_be_read_is_left_as_it_was(tmp_path):
    path = existing_cv(tmp_path, "basics: [nicht: lesbar\n")

    result = replace(tmp_path)

    assert path.read_text(encoding="utf-8") == "basics: [nicht: lesbar\n"
    assert result.kept_files == ("cv.yaml",)


def test_headings_the_form_made_follow_the_track(tmp_path):
    replace(tmp_path, "apprenticeship")
    assert "x-beschriftungen" in yaml.safe_load((tmp_path / "cv.yaml").read_text(encoding="utf-8"))

    replace(tmp_path, "job")

    assert "x-beschriftungen" not in yaml.safe_load((tmp_path / "cv.yaml").read_text(encoding="utf-8"))


def test_a_cv_the_form_wrote_is_replaced_as_before(tmp_path):
    replace(tmp_path)
    bundle = base_bundle("job")
    bundle["data"]["person"]["name"] = "Neu Beispiel"

    result = import_bundle.import_answers(tmp_path, bundle, TODAY, force=True)

    assert result.kept_files == ()
    assert yaml.safe_load((tmp_path / "cv.yaml").read_text(encoding="utf-8"))["basics"]["name"] == "Neu Beispiel"
