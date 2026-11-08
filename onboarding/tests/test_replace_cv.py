"""Replacing the basics must not lose CV content the form cannot show (#159); all data is invented."""
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


@pytest.mark.parametrize("change", [
    ("    highlights: [Erster Punkt]\n", "    tags: [daten]\n    highlights: [Erster Punkt]\n"),
    ("    highlights: [Erster Punkt]\n", "    highlights: [{text: Erster Punkt, tags: [daten]}]\n"),
    ("    highlights: [Erster Punkt]\n", "    x-display: seit 2010\n    highlights: [Erster Punkt]\n"),
    ("    highlights: [Erster Punkt]\n", "    summary: Ein Satz, den das Formular nicht kennt\n"),
    ("x-farbe: blau\n", "education:\n  - text: Matura, Beispiel-Gymnasium\n"),
    ("  url: https://beispiel.example\n", "  location: {city: Bern, countryCode: CH}\n"),
    ("  url: https://beispiel.example\n", "  profiles: [{network: GitHub, username: beispiel}]\n"),
])
def test_entries_with_fields_the_form_would_drop_leave_the_cv_as_it_was(tmp_path, change):
    text = EXTRAS_ONLY.replace(*change)
    assert text != EXTRAS_ONLY
    path = existing_cv(tmp_path, text)

    replace(tmp_path)

    assert path.read_bytes() == text.encode("utf-8")


def test_tagged_work_keeps_the_cv_byte_for_byte_and_writes_the_rest(tmp_path):
    path = existing_cv(tmp_path, TAGGED)
    before = path.read_bytes()

    result = replace(tmp_path)

    assert path.read_bytes() == before
    assert result.kept_files == ("cv.yaml",)
    assert "cv.yaml" not in result.written
    assert set(result.written) == {"suchprofil.md", "anschreiben/stil.md", "anschreiben/bausteine.md"}
    assert all((tmp_path / rel).is_file() for rel in result.written)


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
