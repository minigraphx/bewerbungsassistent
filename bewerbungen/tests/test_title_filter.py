"""How a title filter term matches a job title (G104): also as the start or end of a compound word, never in its
middle; short terms and terms marked «(ganzes Wort)» only as whole words. Invented titles and terms only."""
import pathlib

import pytest

import search_plan
import title_filter
from ai import term_review

ROOT = pathlib.Path(__file__).resolve().parents[2]

PROFILE = """# Suchprofil

## Keywords
- Kernliste: Kursleiter

## Titelfilter
- Positiv: Software, Kurs, Applikation, KI
- Ausschluss: Pflege, Intern/Trainee (ganzes Wort), Sales (Ganzes  Wort), Head of
"""


@pytest.mark.parametrize("title, term", [
    ("Softwareentwickler:in (80–100 %)", "Software"),
    ("Kursleiter-in für Erwachsene", "Kurs"),
    ("Applikationsentwickler/in", "Applikation"),
    ("Fachperson Erwachsenenbildung", "Bildung"),
    ("Bildungsberaterin", "Bildung"),
    ("Senior SOFTWARE Engineer", "software"),
])
def test_a_term_matches_as_the_start_or_end_of_a_word(title, term):
    assert title_filter.matches(title, term)


@pytest.mark.parametrize("title, term", [
    ("Fachperson Weiterbildungsangebote", "Bildung"),  # in the middle of the word
    ("Netzwerkspezialist", "Werk"),
    ("Projektleiter Bau", "Software"),
])
def test_a_term_never_matches_in_the_middle_of_a_word(title, term):
    assert not title_filter.matches(title, term)


@pytest.mark.parametrize("title, term", [
    ("International Sales", "Intern (ganzes Wort)"),
    ("Salesforce-Entwickler", "Sales (ganzes Wort)"),
    ("Kitaleiterin", "KI"),
    ("Qualitätsmanager QAS", "QA"),
])
def test_short_and_marked_terms_match_only_as_whole_words(title, term):
    assert not title_filter.matches(title, term)


@pytest.mark.parametrize("title, term", [
    ("Praktikum Intern 2027", "Intern (ganzes Wort)"),
    ("KI-Trainer", "KI"),
    ("Sales Manager B2B", "Sales (ganzes Wort)"),
])
def test_a_whole_word_still_matches(title, term):
    assert title_filter.matches(title, term)


def test_the_rule_counts_letters_and_digits_of_the_term():
    assert title_filter.whole_word("KI") and title_filter.whole_word("SAP") and title_filter.whole_word(".NET")
    assert not title_filter.whole_word("Kurs")
    assert title_filter.whole_word("Kurs (ganzes Wort)")


def test_the_marker_is_read_in_any_case_and_written_one_way():
    assert title_filter.bare("Sales (Ganzes  Wort)") == "Sales"
    assert title_filter.marked("sales (ganzes wort)")
    assert title_filter.with_marker("Sales") == "Sales (ganzes Wort)"


def test_the_plan_marks_every_alternative_of_a_slash_group():
    plan = search_plan.parse(PROFILE)
    assert plan.title_exclude == ("Pflege", "Intern (ganzes Wort)", "Trainee (ganzes Wort)", "Sales (ganzes Wort)", "Head of")
    assert plan.title_positive == ("Software", "Kurs", "Applikation", "KI")


def test_the_term_review_and_the_skill_state_the_rule():
    assert "als ganzes Wort, sonst" not in term_review.INSTRUCTIONS
    assert "Anfang oder Ende eines Worts" in term_review.INSTRUCTIONS
    assert "«Sales (ganzes Wort)»" in term_review.INSTRUCTIONS
    assert "höchstens drei Buchstaben" in term_review.INSTRUCTIONS
    skill = (ROOT / "skills" / "jobsuche" / "SKILL.md").read_text(encoding="utf-8")
    assert "(ganzes Wort)" in skill and "Anfang oder Ende" in skill


def test_matches_name_every_term_and_the_first_one_in_order():
    terms = ("Entwickler", "Software", "Sales (ganzes Wort)")
    assert title_filter.all_matches("Softwareentwickler", terms) == ("Entwickler", "Software")
    assert title_filter.first_match("Softwareentwickler", terms) == "Entwickler"
    assert title_filter.first_match("Salesforce-Admin", terms) is None
