"""Search plan for the browser extension (MIN-339): read from suchprofil.md, with fallbacks for short profiles."""
import pathlib

import pytest

import search_plan

VORLAGEN = pathlib.Path(__file__).resolve().parents[2] / "vorlagen"

GENERATED = """# Suchprofil

Aus der Einstiegsvorlage. Wird vom Skill `jobsuche` gelesen; ergänzen in der App oder von Hand.

## Person
- Name: Erika Beispiel

## Suchrichtungen
1. Sachbearbeiterin Buchhaltung
2. Kaufmännische Angestellte (Priorität 2)
- Ausschluss: Verkauf

## Region
- Wohnort: Thun
- Pendelgrenze: 45 Minuten
- Kantone (job-room): BE, LU
- Remote: teilweise

## Titelfilter
- Ausschluss: Praktikum, Lehrstelle
"""


def test_template_profile_gives_all_portal_queries():
    plan = search_plan.parse((VORLAGEN / "suchprofil.md").read_text(encoding="utf-8"))
    assert plan.keywords == ("Python", "TypeScript", "Softwareentwickler", "Data Engineer", "E-Learning")
    assert plan.niche_keywords == ("EdTech", "Remote Python")
    assert plan.cantons == ("BE", "SO")
    assert plan.places == ("Bern", "Solothurn")
    assert plan.postal_codes == ("3000", "4500")
    assert plan.regions == ("grossraum-bern", "solothurn")
    assert plan.title_exclude == ("Praktikum", "Lehrstelle", "Werkstudent", "PhD", "Sales", "Head of")
    assert plan.portals == ("job-room", "jobs.ch", "jobscout24", "ictjobs")


def test_generated_profile_falls_back_to_directions_home_and_cantons():
    plan = search_plan.parse(GENERATED, postal_code="3600")
    assert plan.keywords == ("Sachbearbeiterin Buchhaltung", "Kaufmännische Angestellte")
    assert plan.places == ("Thun",)
    assert plan.postal_codes == ("3600",)
    assert plan.regions == ("grossraum-bern", "zentralschweiz")
    assert plan.title_exclude == ("Praktikum", "Lehrstelle")


def test_portal_set_to_aus_is_skipped_and_mit_nutzer_still_runs():
    text = GENERATED + "\n## Portale und Rhythmus\n| Portal | Modus |\n|---|---|\n| jobs.ch | aus |\n| ictjobs | mit Nutzer |\n"
    assert search_plan.parse(text, postal_code="3600").portals == ("job-room", "jobscout24", "ictjobs")


def test_missing_postal_code_skips_jobscout24_with_a_hint():
    plan = search_plan.parse(GENERATED)
    assert "jobscout24" not in plan.portals
    assert any("jobscout24" in hint for hint in plan.hints)


def test_profile_without_keywords_or_directions_is_refused():
    with pytest.raises(ValueError, match="Stichworte"):
        search_plan.parse("# Suchprofil\n\n## Region\n- Wohnort: Bern\n")


def test_apprenticeship_profile_is_refused_for_now():
    text = (VORLAGEN / "suchprofil-lehrstelle.md").read_text(encoding="utf-8")
    with pytest.raises(ValueError, match="Lehrstellen"):
        search_plan.parse(text)


def test_values_are_trimmed_bounded_and_deduplicated():
    text = "# Suchprofil\n\n## Keywords\n- Kernliste: Python, python , " + ", ".join(f"K{i}" for i in range(40)) + "\n"
    plan = search_plan.parse(text)
    assert plan.keywords[0] == "Python"
    assert "python" not in plan.keywords
    assert len(plan.keywords) == search_plan.MAX_KEYWORDS


def test_unknown_canton_codes_are_ignored():
    text = GENERATED.replace("BE, LU", "BE, XX, be")
    assert search_plan.parse(text, postal_code="3600").cantons == ("BE",)


def test_as_dict_is_what_the_extension_receives():
    data = search_plan.parse(GENERATED, postal_code="3600").as_dict()
    assert data["stichworte"] == ["Sachbearbeiterin Buchhaltung", "Kaufmännische Angestellte"]
    assert data["max_seiten"] == search_plan.MAX_PAGES
    assert data["max_abfragen"] == search_plan.MAX_QUERIES
    assert data["max_alter_tage"] == search_plan.MAX_AGE_DAYS
    assert set(data) >= {"portale", "kantone", "orte", "plz", "regionen", "nischen", "hinweise"}


def test_for_folder_reads_profile_and_postal_code_from_cv(tmp_path):
    (tmp_path / "suchprofil.md").write_text(GENERATED, encoding="utf-8")
    (tmp_path / "cv.yaml").write_text("basics:\n  location:\n    postalCode: '3600'\n", encoding="utf-8")
    assert search_plan.for_folder(tmp_path).postal_codes == ("3600",)


def test_for_folder_without_profile_explains_the_einstieg(tmp_path):
    with pytest.raises(ValueError, match="Einstieg"):
        search_plan.for_folder(tmp_path)
