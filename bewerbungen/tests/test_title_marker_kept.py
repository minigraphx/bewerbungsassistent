"""«(ganzes Wort)» stays wherever the title filter is written or read (G104): the cards of Suche einstellen, term
changes, word proposals from dismissed hits, «Künftig nicht zeigen» and the exclusion reasons of the AI. Invented data."""
import dismissed_words
import rating_exclusion
import search_frame
import search_plan
import search_terms
import term_changes
import term_evidence
from ai import exclusion_reasons

PROFILE = """# Suchprofil

## Suchrichtungen
1. Erwachsenenbildung (Priorität 1)

## Keywords
- Kernliste: Kursleiter, Lernbegleiter

## Titelfilter
- Positiv: Kurs, Bildung, KI
- Ausschluss: Intern/Trainee (ganzes Wort), Sales (ganzes Wort), Pflege
"""


def dismissed(number: int, title: str, state: str = "verworfen") -> dict:
    return {"id": f"jobs-ch-m{number}", "portal": "jobs.ch", "stelle": title, "firma": f"Muster {number} AG",
            "ort": "Bern", "pensum": "80%", "zustand": state}


# The cards of Suche einstellen

def test_the_cards_keep_the_marker_as_written_and_a_save_writes_it_back():
    values = search_frame.values(PROFILE)
    assert values["titel_ausschluss"] == ["Intern/Trainee (ganzes Wort)", "Sales (ganzes Wort)", "Pflege"]
    saved = search_frame.with_values(PROFILE, {"titel_ausschluss": [*values["titel_ausschluss"], "Praktikum (ganzes Wort)"]})
    assert search_plan.title_terms(saved, "ausschluss")[-1] == "Praktikum (ganzes Wort)"
    assert "Intern (ganzes Wort)" in search_plan.title_terms(saved, "ausschluss")


def test_the_card_was_nicht_shows_each_alternative_with_its_marker():
    assert search_plan.frame(PROFILE)["titel_ausschluss"] == ["Intern (ganzes Wort)", "Trainee (ganzes Wort)",
                                                             "Sales (ganzes Wort)", "Pflege"]


# Term changes (#210)

def test_a_term_is_the_same_with_or_without_the_marker():
    text = search_terms.with_title_term(PROFILE, "ausschluss", "sales")
    assert text == PROFILE


def test_one_alternative_of_a_marked_group_goes_and_the_other_keeps_the_marker():
    text = search_terms.without_title_term(PROFILE, "ausschluss", "Intern (ganzes Wort)")
    assert "- Ausschluss: Trainee (ganzes Wort), Sales (ganzes Wort), Pflege" in text


def test_the_ai_may_remove_a_marked_term_by_its_plain_name_and_add_a_marked_one():
    current = term_changes.terms_of(PROFILE)
    raw = [{"area": "exclude", "remove": ["Sales"], "add": ["Pflegehelfer (Ganzes Wort)"], "reason": "Genauer."}]
    [change] = term_changes.cleaned_changes(raw, current, ())
    assert change.remove == ("Sales (ganzes Wort)",)
    assert change.add == ("Pflegehelfer (ganzes Wort)",)
    after = term_changes.applied(PROFILE, (change,))
    assert search_plan.title_terms(after, "ausschluss") == ("Intern (ganzes Wort)", "Trainee (ganzes Wort)", "Pflege",
                                                           "Pflegehelfer (ganzes Wort)")


def test_the_evidence_counts_a_title_as_the_search_screens_it():
    assert term_evidence.matching("Kursleiterin Erwachsenenbildung", ("Kurs", "Bildung", "KI")) == ("Kurs", "Bildung")


# Word proposals from dismissed hits (#225) and the exclusion reasons of the AI (#319)

def test_a_word_proposal_counts_hits_as_the_marked_exclusion_screens_them():
    hits = [dismissed(n, f"International Marketing {n}") for n in range(3)]
    positive, excluded = search_plan.title_terms(PROFILE, "positiv"), search_plan.title_terms(PROFILE, "ausschluss")
    words = [proposal.word for proposal in dismissed_words.proposals(hits, positive, excluded, {})]
    assert "International" in words, "«Intern (ganzes Wort)» does not catch International"
    assert "ganzes" not in dismissed_words.blocked(positive, excluded)


def test_the_ai_gets_dismissed_hits_a_marked_exclusion_does_not_catch():
    hits = [dismissed(1, "International Sales Lead"), dismissed(2, "Intern Kommunikation"), dismissed(3, "Salesforce Admin")]
    sent = exclusion_reasons.dismissed(hits, search_plan.title_terms(PROFILE, "ausschluss"))
    assert [hit["stelle"] for hit in sent] == ["Salesforce Admin"]


def test_an_ai_title_word_may_carry_the_marker():
    hits = [dismissed(n, f"Teamleiter Logistik {n}") for n in range(3)]
    by_label = exclusion_reasons.labelled(hits)
    frame = exclusion_reasons.Frame(positive=("Kurs",), titles=search_plan.title_terms(PROFILE, "ausschluss"), ads=(), chars=80)
    raw = {"proposals": [{"category": "titel", "value": "Teamleiter (ganzes Wort)", "reason": "Alle führen ein Team.",
                          "hits": list(by_label)}]}
    [proposal] = exclusion_reasons.cleaned(raw, by_label, frame)
    assert (proposal.value, len(proposal.ids)) == ("Teamleiter (ganzes Wort)", 3)


# «Künftig nicht zeigen» (#224)

def test_a_point_is_excluded_by_a_marked_entry_without_the_marker():
    entries = search_frame.values(PROFILE)["titel_ausschluss"]
    assert rating_exclusion.is_excluded("Sales-Erfahrung wird erwartet; Sales im Fokus", entries)
    assert not rating_exclusion.is_excluded("Viel Salesforce", entries)


def test_a_point_word_already_excluded_with_the_marker_is_not_proposed_again():
    found = rating_exclusion.propose("Sales im Aussendienst", "Sales Aussendienst", ("Kurs",),
                                     search_plan.title_terms(PROFILE, "ausschluss"), 80)
    assert (found.kind, found.value) == (rating_exclusion.TITLE, "Aussendienst")
