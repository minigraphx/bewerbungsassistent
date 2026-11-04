"""Changing what is searched from the page (MIN-375): the profile stays as written, except for the term."""
import pytest

import search_plan
import search_terms

KERN = "# Suchprofil\n\n## Region\n- Wohnort: Bern\n\n## Keywords\n- Kernliste: `Daten`, Python\n- Nischen: dbt\n\n## Rahmen\n- Pensum: 80\n"
DIRECTIONS = ("## Suchrichtungen\n1. Administration, Empfang (Priorität 1)\n2. Bildung (Priorität 2, auch mit Lücken)\n"
              "   - Nur mit IT-Bezug\n3. Logistik (Priorität 3)\n\n## Region\n- Wohnort: Bern\n")
LEHRE = ("## Berufe (mit Priorität)\n1. Koch/Köchin EFZ (Priorität 1)\n2. Fachfrau Betreuung EFZ, Fachrichtung Kinder (Priorität 2)\n"
         "3. Maler/in EFZ (Ersatz)\n\n## Lehrbeginn\n- 2027\n")


def test_current_follows_what_the_search_uses():
    assert search_terms.current(KERN) == ("Daten", "Python")
    assert search_terms.current(DIRECTIONS) == ("Administration", "Empfang", "Bildung", "Logistik")
    assert search_terms.current(LEHRE)[0] == "Koch/Köchin EFZ"
    assert search_terms.current("# Suchprofil\n") == ()


def test_current_is_what_the_plan_searches():
    assert search_plan.parse(KERN).keywords == search_terms.current(KERN)
    assert search_plan.parse(DIRECTIONS).keywords == search_terms.current(DIRECTIONS)


def test_adding_to_the_core_list_keeps_the_rest():
    changed = search_terms.added(KERN, "Sachbearbeitung Administration")
    assert search_terms.current(changed) == ("Daten", "Python", "Sachbearbeitung Administration")
    assert changed.replace(", Sachbearbeitung Administration", "") == KERN


def test_adding_to_directions_comes_last():
    changed = search_terms.added(DIRECTIONS, "Büroassistenz")
    assert search_terms.current(changed)[-1] == "Büroassistenz"
    assert "4. Büroassistenz\n" in changed and "   - Nur mit IT-Bezug\n" in changed


def test_adding_to_a_profile_without_terms_makes_it_searchable():
    text = "# Suchprofil\n\n## Region\n- Wohnort: Bern\n- Kantone (job-room): BE\n"
    with pytest.raises(ValueError, match="Welche Stellen passen zu Ihnen"):
        search_plan.parse(text)
    assert search_plan.parse(search_terms.added(text, "Empfang")).keywords == ("Empfang",)
    assert search_terms.current(search_terms.added("# Suchprofil\n", "Empfang")) == ("Empfang",)


def test_adding_what_is_there_changes_nothing():
    assert search_terms.added(DIRECTIONS, "empfang") == DIRECTIONS


def test_adding_stops_at_what_the_search_uses():
    terms = ", ".join(f"Begriff{i}" for i in range(search_plan.MAX_KEYWORDS))
    with pytest.raises(ValueError, match="Entfernen"):
        search_terms.added(f"## Keywords\n- Kernliste: {terms}\n", "Empfang")


def test_removing_from_the_core_list():
    changed = search_terms.removed(KERN, "Daten")
    assert search_terms.current(changed) == ("Python",)
    assert "- Nischen: dbt\n" in changed and "## Rahmen\n- Pensum: 80\n" in changed


def test_removing_one_term_of_a_direction_keeps_the_other_and_the_remark():
    changed = search_terms.removed(DIRECTIONS, "Empfang")
    assert "1. Administration (Priorität 1)\n" in changed
    assert search_terms.current(changed) == ("Administration", "Bildung", "Logistik")


def test_removing_a_direction_takes_its_bullets_and_numbers_the_rest():
    changed = search_terms.removed(DIRECTIONS, "Bildung")
    assert "IT-Bezug" not in changed
    assert "2. Logistik (Priorität 2)\n" in changed
    assert changed.endswith("\n\n## Region\n- Wohnort: Bern\n")


def test_removing_a_profession_numbers_the_rest():
    changed = search_terms.removed(LEHRE, "Koch/Köchin EFZ")
    assert search_terms.current(changed) == ("Fachfrau Betreuung EFZ, Fachrichtung Kinder", "Maler/in EFZ")
    assert changed.startswith("## Berufe (mit Priorität)\n1. Fachfrau Betreuung EFZ, Fachrichtung Kinder (Priorität 1)\n2. Maler/in EFZ (Ersatz)\n\n## Lehrbeginn")


def test_removing_the_last_profession_leaves_a_profile_that_can_get_a_new_one():
    text = "## Berufe (mit Priorität)\n1. Koch EFZ\n\n## Lehrbeginn\n- 2027\n"
    empty = search_terms.removed(text, "Koch EFZ")
    assert search_terms.current(empty) == ()
    assert search_terms.current(search_terms.added(empty, "Maler EFZ")) == ("Maler EFZ",)


@pytest.mark.parametrize("text", [KERN, DIRECTIONS, LEHRE])
def test_removing_what_is_not_there_changes_nothing(text):
    assert search_terms.removed(text, "Astronaut") == text


def test_removing_another_form_of_the_name_finds_it():
    assert "Koch" not in search_terms.removed(LEHRE, "Koch EFZ")


def test_removing_leaves_hand_written_priorities_alone():
    text = "## Suchrichtungen\n1. Alpha (Priorität 2)\n2. Beta (Priorität 1)\n5. Gamma (Priorität 1)\n\n## Region\n- Wohnort: Bern\n"
    assert search_terms.removed(text, "Astronaut") == text
    changed = search_terms.removed(text, "Alpha")
    assert "1. Beta (Priorität 1)\n" in changed and "4. Gamma (Priorität 1)\n" in changed


def test_an_indented_core_list_is_the_one_that_is_changed():
    text = "## Keywords\n  - Kernliste: Python, Java\n\n## Region\n- Wohnort: Bern\n"
    assert search_terms.current(search_terms.added(text, "Empfang")) == ("Python", "Java", "Empfang")
    changed = search_terms.removed(text, "Python")
    assert search_terms.current(changed) == ("Java",) and "  - Kernliste: Java\n" in changed


def test_an_empty_first_core_list_counts_as_none_like_in_the_plan():
    text = "## Keywords\n- Kernliste:\n- Kernliste (alt): x\n\n## Suchrichtungen\n1. Empfang\n"
    assert search_terms.current(text) == ("Empfang",)
    assert search_terms.current(search_terms.added(text, "Büroassistenz")) == ("Empfang", "Büroassistenz")


@pytest.mark.parametrize("template", ["## Suchrichtungen\n1. {long} (Priorität 1)\n2. Empfang\n", "## Keywords\n- Kernliste: {long}, Empfang\n",
                                      "## Berufe (mit Priorität)\n1. {long} EFZ\n2. Empfang EFZ\n\n## Lehrbeginn\n- 2027\n"])
def test_a_long_entry_can_be_removed_by_what_the_page_shows(template):
    text = template.format(long="Softwareentwicklung im Bereich Datenanalyse und Machine Learning für KMU in der Region Bern")
    shown = search_terms.current(text)[0]
    assert len(shown) == search_plan.MAX_VALUE
    assert search_terms.current(search_terms.removed(text, shown))[0].startswith("Empfang")


def test_a_core_list_without_the_term_stays_exactly_as_written():
    text = "## Keywords\n- Kernliste: a,b ,  `c`\n"
    assert search_terms.removed(text, "Astronaut") == text


def test_the_section_before_is_found_by_its_whole_line():
    text = "### Region der Eltern\n\n## Region\n- Wohnort: Bern\n"
    assert search_terms.added(text, "Empfang").startswith("### Region der Eltern\n\n## Suchrichtungen\n1. Empfang\n")


def test_keys_are_the_same_for_two_forms_of_a_name():
    assert search_terms.key("Fachfrau/Fachmann Gesundheit EFZ") == search_terms.key("Fachfrau Gesundheit EFZ")


def test_replacing_keeps_what_was_added_on_the_page():
    new = "## Berufe (mit Priorität)\n1. Koch/Köchin EFZ (Priorität 1)\n\n## Lehrbeginn\n- 2027\n"
    old = "## Berufe (mit Priorität)\n1. Koch EFZ\n2. Maler/in EFZ\n\n## Lehrbeginn\n- 2028\n"
    text, kept = search_terms.kept_on_replace(old, new)
    assert kept == ("Maler/in EFZ",)
    assert search_terms.current(text) == ("Koch/Köchin EFZ", "Maler/in EFZ")
    assert "- 2027\n" in text and "- 2028\n" not in text


def test_replacing_with_nothing_new_changes_nothing():
    assert search_terms.kept_on_replace(LEHRE, LEHRE) == (LEHRE, ())


def test_replacing_keeps_job_terms_in_what_the_new_profile_searches():
    new = "## Suchrichtungen\n1. Empfang (Priorität 1)\n\n## Region\n- Wohnort: Bern\n"
    text, kept = search_terms.kept_on_replace(KERN, new)
    assert kept == ("Daten", "Python")
    assert search_terms.current(text) == ("Empfang", "Daten", "Python")


def test_changing_the_kind_of_search_keeps_nothing():
    assert search_terms.kept_on_replace(KERN, LEHRE) == (LEHRE, ())


def test_replacing_stops_at_what_the_search_uses():
    names = "".join(f"{i}. Beruf{i} EFZ\n" for i in range(1, search_plan.MAX_PROFESSIONS + 1))
    old = f"## Berufe (mit Priorität)\n{names}\n## Lehrbeginn\n- 2027\n"
    text, kept = search_terms.kept_on_replace(old, "## Berufe (mit Priorität)\n1. Koch EFZ\n\n## Lehrbeginn\n- 2027\n")
    assert len(kept) == search_plan.MAX_PROFESSIONS - 1 and len(search_terms.current(text)) == search_plan.MAX_PROFESSIONS


def test_replacing_keeps_the_choice_of_offers_if_the_form_has_none():
    old = "## Gesucht\n- Schnupperlehren\n\n## Lehrbeginn\n- 2027\n"
    text, _ = search_terms.kept_on_replace(old, "## Lehrbeginn\n- 2028\n")
    assert search_plan.OFFERS_SECTION in text and "- Schnupperlehren\n" in text
    chosen = "## Gesucht\n- Lehrstellen\n\n## Lehrbeginn\n- 2028\n"
    assert search_terms.kept_on_replace(old, chosen)[0] == chosen
