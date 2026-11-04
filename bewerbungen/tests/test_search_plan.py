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


def apprenticeship_template() -> str:
    return (VORLAGEN / "suchprofil-lehrstelle.md").read_text(encoding="utf-8")


def test_apprenticeship_profile_searches_lena_and_yousty_for_the_professions():
    plan = search_plan.parse(apprenticeship_template())
    assert plan.kind == search_plan.KIND_APPRENTICESHIP
    assert plan.portals == ("LENA", "yousty")
    assert plan.keywords == ("Fachfrau Gesundheit EFZ", "Fachfrau Betreuung EFZ, Fachrichtung Kinder",
                             "Assistentin Gesundheit und Soziales EBA")
    assert plan.places == ("Bern",)
    assert plan.cantons == ("BE",)
    assert plan.radius_km == 25
    assert plan.start_years == (2027,)
    assert plan.hints == ()


def test_job_profile_is_of_kind_job():
    assert search_plan.parse(GENERATED, postal_code="3600").kind == search_plan.KIND_JOB


@pytest.mark.parametrize("line, years", [("August 2027", (2027,)), ("2027 oder 2028", (2027, 2028)),
                                         ("noch offen", ()), ("2028, 2027, 2028", (2027, 2028))])
def test_start_of_apprenticeship_gives_the_years(line, years):
    text = apprenticeship_template().replace("- August 2027", f"- {line}")
    assert search_plan.parse(text).start_years == years


def test_radius_comes_from_the_profile_within_limits():
    text = apprenticeship_template().replace("- Kantone: BE", "- Kantone: BE\n- Umkreis: 10 km")
    assert search_plan.parse(text).radius_km == 10
    too_far = text.replace("10 km", "9000 km")
    assert search_plan.parse(too_far).radius_km == search_plan.MAX_RADIUS_KM
    unreadable = text.replace("10 km", "nicht so weit")
    assert search_plan.parse(unreadable).radius_km == search_plan.DEFAULT_RADIUS_KM


def test_remark_in_brackets_goes_but_a_specialisation_stays():
    text = apprenticeship_template().replace("Fachfrau Gesundheit EFZ (Priorität 1)", "Fachfrau Betreuung (Kinder) EFZ")
    assert search_plan.parse(text).keywords[0] == "Fachfrau Betreuung (Kinder) EFZ"


def test_apprenticeship_without_home_searches_the_cantons():
    plan = search_plan.parse(apprenticeship_template().replace("- Wohnort: Bern\n", ""))
    assert plan.places == ()
    assert plan.cantons == ("BE",)
    assert plan.portals == ("LENA", "yousty")


def test_apprenticeship_without_region_is_refused():
    text = apprenticeship_template().replace("- Wohnort: Bern\n", "").replace("- Kantone: BE\n", "")
    with pytest.raises(ValueError, match="Wohnort"):
        search_plan.parse(text)


def test_apprenticeship_without_professions_is_refused():
    text = apprenticeship_template()
    start, end = text.index("1. Fachfrau Gesundheit"), text.index("## Region")
    with pytest.raises(ValueError, match="Berufe"):
        search_plan.parse(text[:start] + text[end:])


def test_several_cantons_next_to_a_home_are_named_in_a_hint():
    plan = search_plan.parse(apprenticeship_template().replace("- Kantone: BE", "- Kantone: BE, LU"))
    assert plan.places == ("Bern",)
    assert any("BE, LU" in hint and "25 km" in hint for hint in plan.hints)


def test_portal_set_to_aus_also_works_for_apprenticeships():
    text = apprenticeship_template() + "\n## Portale und Rhythmus\n| Portal | Modus |\n|---|---|\n| yousty | aus |\n"
    assert search_plan.parse(text).portals == ("LENA",)


def test_as_dict_of_an_apprenticeship_plan():
    data = search_plan.parse(apprenticeship_template()).as_dict()
    assert data["art"] == "lehrstelle"
    assert data["umkreis_km"] == 25
    assert data["lehrbeginn_jahre"] == [2027]
    assert data["max_seiten"] == search_plan.MAX_APPRENTICESHIP_PAGES
    assert data["stichworte"][0] == "Fachfrau Gesundheit EFZ"


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


def test_kind_of_folder_needs_no_complete_profile(tmp_path):
    assert search_plan.kind_of_folder(tmp_path) == search_plan.KIND_JOB
    (tmp_path / "suchprofil.md").write_text("## Lehrbeginn\n- 2027\n", encoding="utf-8")
    assert search_plan.kind_of_folder(tmp_path) == search_plan.KIND_APPRENTICESHIP


@pytest.mark.parametrize("line, offers", [
    ("- Lehrstellen", ("lehrstelle",)),
    ("- Schnupperlehren", ("schnupperlehre",)),
    ("- Lehrstellen und Schnupperlehren", ("lehrstelle", "schnupperlehre")),
    ("- beides", ("lehrstelle", "schnupperlehre")),
])
def test_the_profile_says_what_is_searched(line, offers):
    text = apprenticeship_template().replace("## Lehrbeginn", f"## Gesucht\n{line}\n\n## Lehrbeginn", 1)

    plan = search_plan.parse(text)

    assert plan.offers == offers
    assert plan.as_dict()["angebote"] == list(offers)


def test_a_profile_without_the_wish_searches_apprenticeships():
    assert search_plan.parse(apprenticeship_template().replace("## Gesucht", "## Anderes")).offers == ("lehrstelle",)


def test_past_trial_apprenticeships_in_the_profile_are_no_wish():
    text = apprenticeship_template().replace("## Gesucht", "## Anderes")
    assert "## Schnupperlehren" in text

    assert search_plan.parse(text).offers == ("lehrstelle",)


def test_a_job_profile_has_no_offers():
    assert search_plan.parse(GENERATED, postal_code="3600").as_dict()["angebote"] == []


@pytest.mark.parametrize("choice, offers", [("schnupperlehre", ("schnupperlehre",)), ("beides", ("lehrstelle", "schnupperlehre")),
                                            ("lehrstelle", ("lehrstelle",))])
def test_changing_the_wish_keeps_the_rest_of_the_profile(choice, offers):
    once = search_plan.with_offers(apprenticeship_template(), choice)
    twice = search_plan.with_offers(once, choice)

    assert twice == once and once.count("## Gesucht") == 1
    assert search_plan.parse(once).offers == offers
    assert search_plan.parse(once).keywords == search_plan.parse(apprenticeship_template()).keywords
    assert "## Eignungstests" in once and "Multicheck" in once


def test_changing_the_wish_replaces_the_old_one():
    first = search_plan.with_offers(apprenticeship_template(), "beides")

    assert search_plan.parse(search_plan.with_offers(first, "schnupperlehre")).offers == ("schnupperlehre",)


def test_an_unknown_wish_is_refused():
    with pytest.raises(ValueError):
        search_plan.with_offers(apprenticeship_template(), "ferienjob")


def test_a_job_profile_cannot_get_the_wish():
    with pytest.raises(ValueError):
        search_plan.with_offers(GENERATED, "beides")


def test_the_wish_at_the_end_of_a_file_without_a_line_break_is_replaced():
    text = apprenticeship_template().split("## Gesucht")[1].split("\n", 2)[2] + "\n## Gesucht\n- beides"
    changed = search_plan.with_offers(text, "schnupperlehre")

    assert changed.count("## Gesucht") == 1 and search_plan.parse(changed).offers == ("schnupperlehre",)


def test_a_similar_heading_stays():
    text = "## Gesuchte Stellen\n- A\n\n" + apprenticeship_template()

    assert "## Gesuchte Stellen\n- A" in search_plan.with_offers(text, "beides")
