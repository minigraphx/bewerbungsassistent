"""The FAQ docs/fragen.md (#108): every statement the tests can reach matches the code, and the app links to it.

The website renders the same file with the GitHub slugs as heading ids, so an anchor the app uses must be the slug
of a heading. All personal values here are invented.
"""
import pathlib
import re

import pytest

import search_plan
from ai import personal, pseudonym
from ai.personal import secrets_from_cv
from ai.pseudonym import Pseudonymizer, PseudonymError

ROOT = pathlib.Path(__file__).resolve().parents[2]
FAQ = ROOT / "docs" / "fragen.md"
PAGES = ROOT / "bewerbungen" / "seiten"
FAQ_URL = "https://github.com/minigraphx/bewerbungsassistent/blob/main/docs/fragen.md"
ANCHOR_IN_CALL = re.compile(r"fragenLink\(\s*\"([^\"]+)\"")
ANCHOR_IN_URL = re.compile(r"docs/fragen\.md#([^\"'\s)>]+)")

PERSON = {"basics": {"name": "Léa Müller-Brändli", "email": "lea@example.ch", "phone": "079 123 45 67",
                     "url": "https://www.lea-beispiel.ch", "details": ["geboren am 3.3.1994"],
                     "location": {"address": "Musterweg 5", "postalCode": "3000", "city": "Bern"}}}
RECOGNIZED = ["Müller-Brändlis Lebenslauf", "Brändli Léa", "Müller Brändli", "Mueller-Braendli", "Lea Muller-Brandli",
              "0791234567", "+41 79 123 45 67", "+41 (0)79 123 45 67", "0041 79 123 45 67", "079.123.45.67", "079/123 45 67",
              "3.3.1994", "03.03.94", "1994-03-03", "3. März 1994", "3. Mär. 1994", "lea-beispiel.ch", "http://lea-beispiel.ch/"]
NOT_RECOGNIZED = ["Lele", "Müler", "03/03/1994", "März 1994", "Peter Meier"]
COMPUTING_TERMS = ["Software-Entwickler", "Data Engineer", "Informatiker"]
OTHER_TERMS = ["Administration", "Datenschutz", "Systemgastronomie", "Testfahrer"]


def faq() -> str:
    return FAQ.read_text(encoding="utf-8")


def headings() -> list[str]:
    return [line.lstrip("#").strip() for line in faq().splitlines() if re.match(r"#{1,6}\s", line)]


def github_slug(heading: str) -> str:
    """The id GitHub gives a plain heading: lower case, punctuation dropped, each space a hyphen."""
    return re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-")


def anchors_in(path: pathlib.Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    return ANCHOR_IN_CALL.findall(text) + ANCHOR_IN_URL.findall(text)


def person() -> Pseudonymizer:
    return Pseudonymizer(secrets_from_cv(PERSON))


def test_headings_are_plain_and_unique():
    found = headings()
    assert all(re.fullmatch(r"[\w ,?.-]+", heading) for heading in found), found
    assert len({github_slug(h) for h in found}) == len(found)


def test_the_app_links_the_faq_at_the_consent_and_where_to_search():
    assert ANCHOR_IN_CALL.search((PAGES / "einwilligung.js").read_text(encoding="utf-8"))
    assert ANCHOR_IN_CALL.search((PAGES / "portal-wahl.js").read_text(encoding="utf-8"))
    assert FAQ_URL in (PAGES / "app.js").read_text(encoding="utf-8")


def test_every_anchor_the_app_links_to_is_the_slug_of_a_heading():
    slugs = {github_slug(h) for h in headings()}
    used = {anchor for path in [*PAGES.glob("*.js"), *PAGES.glob("*.html")] for anchor in anchors_in(path)}
    assert used and used <= slugs, used - slugs


def test_the_table_of_contents_points_to_headings():
    slugs = {github_slug(h) for h in headings()}
    assert set(re.findall(r"\]\(#([^)]+)\)", faq())) <= slugs


@pytest.mark.parametrize("example", RECOGNIZED)
def test_every_spelling_named_as_recognized_is_replaced(example):
    assert f"«{example}»" in faq()
    masked = person().mask(example)
    assert "{{" in masked and not re.search(r"Müller|Brändli|Mueller|Muller|Braendli|Brandli|123|1994|beispiel", masked)


@pytest.mark.parametrize("example", NOT_RECOGNIZED)
def test_every_form_named_as_not_recognized_stays(example):
    assert f"«{example}»" in faq()
    assert person().mask(example) == example


def test_the_initial_stays_and_the_last_name_goes():
    assert "«L. Müller-Brändli»" in faq()
    assert person().mask("L. Müller-Brändli") == "L. {{NAME_LAST}}"


def test_short_name_parts_stay_alone_but_go_within_the_name():
    assert personal.MIN_TOKEN_CHARS == 3 and "unter drei Buchstaben" in faq() and "«Li»" in faq()
    masked = Pseudonymizer(secrets_from_cv({"basics": {"name": "Li Wang"}})).mask("Li Wang, Li")
    assert masked == "{{NAME}}, Li"


def test_postal_codes_that_look_like_years_stay():
    assert personal.YEAR_RANGE == range(1900, 2100) and "Postleitzahlen von 1900 bis 2099" in faq()
    looks_like_a_year = {"basics": {"name": "Anna Beispiel", "location": {"postalCode": "1950"}}}
    assert Pseudonymizer(secrets_from_cv(looks_like_a_year)).mask("1950 Sion") == "1950 Sion"
    assert person().mask("3000") == "{{POSTAL_CODE}}"


def test_the_last_check_stops_with_the_message_quoted_in_the_faq():
    with pytest.raises(PseudonymError) as stopped:
        person().check_clean("LeaMuellerBraendli schreibt an x@example.org")
    assert f"> {stopped.value}" in faq()


def test_the_last_check_finds_joined_values_from_ten_letters():
    assert pseudonym.MIN_FOLDED_CHARS == 10 and "mindestens zehn Buchstaben" in faq() and "«LeaMuellerBraendli»" in faq()
    with pytest.raises(PseudonymError):
        person().check_clean("LeaMuellerBraendli")


def test_names_in_an_ad_are_found_after_frau_or_herr_and_in_personal_mailboxes():
    ad = "Kontakt: Frau Petra Meier, petra.meier@firma.example, 031 123 45 67. Bewerbungen an jobs@firma.example."
    masked = person().extended(personal.secrets_found_in([ad])).mask(ad)
    assert "Petra" not in masked and "031" not in masked and "@" not in masked
    assert "«Frau Petra Meier»" in faq() and "info@ oder jobs@" in faq()
    assert {"info", "jobs"} <= personal.GENERIC_MAILBOXES


@pytest.mark.parametrize("term", COMPUTING_TERMS)
def test_terms_named_as_computing_switch_ictjobs_on(term):
    assert f"«{term}»" in faq()
    plan = search_plan.SearchPlan(keywords=(term,))
    assert "ictjobs" in search_plan.chosen(plan, None).portals


@pytest.mark.parametrize("term", OTHER_TERMS)
def test_terms_named_as_not_computing_leave_ictjobs_off(term):
    assert f"«{term}»" in faq()
    plan = search_plan.SearchPlan(keywords=(term,))
    assert "ictjobs" not in search_plan.chosen(plan, None).portals


def test_without_terms_ictjobs_is_on_and_a_choice_wins():
    assert "Ohne Suchbegriffe ist ictjobs an" in faq()
    assert "ictjobs" in search_plan.chosen(search_plan.SearchPlan(keywords=()), None).portals
    chosen = search_plan.chosen(search_plan.SearchPlan(keywords=("Informatiker",)), ["ictjobs"])
    assert "ictjobs" not in chosen.portals


def test_at_least_one_portal_stays_on_and_apprenticeships_have_no_ictjobs():
    assert "Mindestens ein Portal bleibt an" in faq()
    with pytest.raises(ValueError):
        search_plan.checked_choice(list(search_plan.PORTALS), search_plan.KIND_JOB)
    assert "ictjobs" not in search_plan.APPRENTICESHIP_PORTALS
    assert "LENA und yousty" in faq() and set(search_plan.APPRENTICESHIP_PORTALS) == {"LENA", "yousty"}


def test_schools_are_replaced_only_for_apprenticeships():
    cv = {"basics": {"name": "Anna Beispiel"}, "education": [{"institution": "Schulhaus Musterberg"}]}
    assert "Schulhaus Musterberg" not in Pseudonymizer(secrets_from_cv(cv, minor=True)).mask("Schulhaus Musterberg")
    assert Pseudonymizer(secrets_from_cv(cv)).mask("Schulhaus Musterberg") == "Schulhaus Musterberg"
    assert "auch die Namen deiner Schulen" in faq()


def test_initials_and_the_logo_file_name_are_replaced_as_the_faq_says():
    cv = {"basics": {"name": "Léa Müller", "x-monogramm": "LMB", "x-logo": "logos/lea-zeichen.svg"}}
    masked = Pseudonymizer(secrets_from_cv(cv)).mask("x-monogramm: LMB\nx-logo: logos/lea-zeichen.svg\nLMB-Team bleibt")
    assert masked == "x-monogramm: {{MONOGRAM}}\nx-logo: {{LOGO}}\nLMB-Team bleibt"
    assert ("die eigenen Initialen fürs Dossier aus dem Feld dafür (gleiche Buchstaben anderswo, etwa IT oder HR, "
            "bleiben stehen) und den Dateinamen Ihres Logos") in faq()
