"""Profile values with a remark in brackets or several terms joined by a slash (#176)."""
import hits
import search_plan
import search_terms

PROFILE = """# Suchprofil

## Region
- Kantone (job-room): BE
- Orte (jobs.ch): Bern, Biel (kleine Gemeinden liefern 0 Treffer)

## Keywords
- Kernliste: Python, Backend/Frontend

## Titelfilter
- Ausschluss: Java/.NET/C#/C++, Verkauf/Sales, Head of/Director, Embedded (nur Hardware)
"""


def test_a_remark_in_brackets_is_not_part_of_the_place():
    assert search_plan.parse(PROFILE).places == ("Bern", "Biel")


def test_a_slash_splits_keywords_into_single_terms():
    assert search_plan.parse(PROFILE).keywords == ("Python", "Backend", "Frontend")


def test_a_slash_splits_title_excludes_and_the_remark_goes():
    expected = ("Java", ".NET", "C#", "C++", "Verkauf", "Sales", "Head of", "Director", "Embedded")
    assert search_plan.parse(PROFILE).title_exclude == expected


def test_title_excludes_from_slash_values_filter_titles():
    exclude = search_plan.parse(PROFILE).title_exclude
    assert hits._title_match("Senior Java Developer", exclude) == "Java"
    assert hits._title_match("Software Engineer .NET", exclude) == ".NET"
    assert hits._title_match("Key Account Manager Sales", exclude) == "Sales"
    assert hits._title_match("Embedded Software Engineer", exclude) == "Embedded"
    assert hits._title_match("Python Developer", exclude) is None


def test_a_gender_form_after_the_slash_stays_one_term():
    expected = ("Sachbearbeiter/in", "Kaufmann/-frau", "Koch/Köchin EFZ", "Fachfrau/Fachmann Betreuung")
    text = PROFILE.replace("Python, Backend/Frontend", ", ".join(expected))
    assert search_plan.parse(text).keywords == expected


def test_one_term_of_a_slash_value_can_be_removed_as_the_page_shows_it():
    changed = search_terms.removed(PROFILE, "Frontend")
    assert search_plan.parse(changed).keywords == ("Python", "Backend")
