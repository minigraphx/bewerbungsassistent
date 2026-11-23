"""The AI writes to the person in the language of the app (G11, #97); ads, portals and search terms keep theirs.

Every request is built with a simulated API or without a client at all: nothing goes to the real AI. The app's
language comes from `sprachen.yaml` (#94); letters and form answers follow the application language (#98), not this.
"""
import json

import pytest

import routes_ai
import routes_rate_all
from ai import career, chat, cv_suggestions, exclusion_reasons, prompts, tasks, term_review
from test_ai_exclusions import Client as ExclusionsClient
from test_ai_exclusions import job_search, propose  # noqa: F401  (job_search is a fixture)
from test_ai_tasks import AD, ADS, ENTRY, FakeClient, PackageClient, daten, gateway_for, rating_entry  # noqa: F401
from test_app import server  # noqa: F401  (server is a fixture)
from test_cv_suggestions import FIRST, ROUTE as CV_ROUTE, connected, with_ad  # noqa: F401  (fixtures)
from test_app import get
from sample_folder import BRIEF_ID

SWISS_GERMAN = "Antworte auf Deutsch, Schweizer Schreibweise (ss statt ß)."
NAMES = {"fr": "Französisch", "en": "Englisch"}
FOREIGN = ("fr", "en")
LETTER_IN_GERMAN = "Nennt die Aufgabe keine Sprache dafür, schreibst du sie auf Deutsch"
# A part of the German ad without personal data (the sample person is called Beispiel), so masking leaves it as it is.
AD_START = "AG in Bern. Python, Airflow, SQL. Deutsch fliessend."


def choose_app_language(folder, language: str) -> None:
    (folder / "sprachen.yaml").write_text(f"app: {language}\n", encoding="utf-8")


def system_of(client) -> str:
    return "\n".join(block["text"] for block in client.messages.calls[-1]["system"])


def content_of(client) -> str:
    return client.messages.calls[-1]["messages"][0]["content"]


# The rules


@pytest.mark.parametrize("address", ["sie", "du"])
def test_german_keeps_the_rules_word_for_word(address):
    assert prompts.rules(address, "de") == prompts.rules(address)
    assert prompts.rules(address).startswith(prompts.RULES)
    assert SWISS_GERMAN in prompts.rules(address)
    assert not any(name in prompts.rules(address) for name in NAMES.values())


@pytest.mark.parametrize("language", FOREIGN)
@pytest.mark.parametrize("address", ["sie", "du"])
def test_another_app_language_says_which_language_to_write_to_the_person_in(language, address):
    text = prompts.rules(address, language)
    assert f"auf {NAMES[language]}" in text
    assert "auch wenn Inserat, Lebenslauf und Suchprofil deutsch sind" in text
    assert SWISS_GERMAN not in text
    for rule in prompts.RULES.split("\n")[2:]:  # the rules of every task stay
        assert rule in text


@pytest.mark.parametrize("language", FOREIGN)
def test_quotes_and_search_terms_keep_their_original_language(language):
    text = prompts.rules("sie", language)
    assert "Originalsprache" in text
    for kept in ("Zitate aus Inseraten, Seiten und Portalen", "Suchbegriffe", "Berufsnamen", "feste Werte"):
        assert kept in text


@pytest.mark.parametrize("language", FOREIGN)
def test_letters_and_form_answers_still_speak_to_the_firm_in_german_unless_the_task_says_otherwise(language):
    text = prompts.rules("sie", language)
    assert "Anschreiben und Antworten in Formularen richten sich an die Firma" in text
    assert LETTER_IN_GERMAN in text
    assert LETTER_IN_GERMAN not in prompts.rules("sie", "de")


@pytest.mark.parametrize("language, address, word", [
    ("fr", "sie", "vous"), ("fr", "du", "tu"), ("en", "sie", "höflich"), ("en", "du", "locker"),
])
def test_the_form_of_address_fits_the_language(language, address, word):
    text = prompts.rules(address, language)
    assert word in text and "du, dein und dir klein" not in text


def test_a_language_the_app_does_not_offer_falls_back_to_german():
    assert prompts.rules("sie", "it") == prompts.rules("sie")


# The material of the person


def test_without_a_choice_the_ai_writes_german(daten):  # noqa: F811
    assert tasks.load_material(daten).language == "de"


@pytest.mark.parametrize("language", FOREIGN)
def test_the_material_carries_the_language_of_the_app(daten, language):  # noqa: F811
    choose_app_language(daten, language)
    material = tasks.load_material(daten)
    assert material.language == language
    assert material.rules == prompts.rules(material.address, language)


def test_a_broken_language_file_means_german(daten):  # noqa: F811
    (daten / "sprachen.yaml").write_text("app: [kaputt\n", encoding="utf-8")
    assert tasks.load_material(daten).language == "de"


# Each task that writes to the person


@pytest.mark.parametrize("language", FOREIGN)
def test_a_package_rating_of_a_german_ad_answers_in_the_app_language(daten, language):  # noqa: F811
    choose_app_language(daten, language)
    client = PackageClient(lambda labels: [rating_entry(label, 4) for label in labels])
    gateway, material = gateway_for(daten, client)
    tasks.rate_package(gateway, material, ADS[:1])
    assert f"auf {NAMES[language]}" in system_of(client)
    assert SWISS_GERMAN not in system_of(client)


@pytest.mark.parametrize("language", FOREIGN)
def test_a_single_rating_answers_in_the_app_language_and_quotes_the_ad_as_it_is(daten, language):  # noqa: F811
    choose_app_language(daten, language)
    client = FakeClient(reply={"grade": 4, "summary": "s", "fits": [], "hooks": [], "new_gaps": [], "suspicious_lines": []})
    gateway, material = gateway_for(daten, client)
    tasks.rate_match(gateway, material, AD)
    assert f"auf {NAMES[language]}" in system_of(client)
    assert AD_START in content_of(client)


@pytest.mark.parametrize("language", FOREIGN)
def test_the_review_answers_in_the_app_language(daten, language):  # noqa: F811
    choose_app_language(daten, language)
    client = FakeClient(reply={"requirements": [], "unsupported": [], "new_gaps": [], "suspicious_lines": []})
    gateway, material = gateway_for(daten, client, ENTRY)
    tasks.review_content(gateway, material, AD, "Sehr geehrte Damen und Herren")
    assert f"auf {NAMES[language]}" in system_of(client)


def test_the_draft_of_a_letter_keeps_german_for_the_firm(daten):  # noqa: F811
    choose_app_language(daten, "fr")
    client = FakeClient(reply={"subject": "Betreff", "salutation": "Guten Tag", "paragraphs": ["Text."],
                               "closing": "Freundliche Grüsse", "claims": [], "gaps_named": [], "suspicious_lines": []})
    gateway, material = gateway_for(daten, client, ENTRY)
    tasks.draft_letter(gateway, material, ENTRY, AD)
    assert LETTER_IN_GERMAN in system_of(client)


@pytest.mark.parametrize("language", FOREIGN)
def test_the_questions_page_answers_in_the_app_language(daten, language):  # noqa: F811
    choose_app_language(daten, language)
    client = FakeClient(reply="Réponse.")
    gateway, material = gateway_for(daten, client)
    chat.answer(gateway, material, "Wie bereite ich mich vor?", [])
    assert f"auf {NAMES[language]}" in system_of(client)


@pytest.mark.parametrize("language", FOREIGN)
def test_career_suggestions_answer_in_the_app_language(daten, language):  # noqa: F811
    choose_app_language(daten, language)
    client = FakeClient(reply={"recommendations": [
        {"profession": "Büroassistenz", "why": "x", "daily": "x", "check": "x"}]})
    gateway, material = gateway_for(daten, client)
    career.recommend(gateway, material, {"interests": "Ordnung", "strengths": "genau", "avoid": ""}, "stelle")
    assert f"auf {NAMES[language]}" in system_of(client)
    assert "Berufsnamen" in system_of(client)


@pytest.mark.parametrize("language", FOREIGN)
def test_the_term_review_answers_in_the_app_language(daten, language):  # noqa: F811
    choose_app_language(daten, language)
    request = term_review.request(tasks.load_material(daten), "Was die Suche jetzt sucht")
    assert f"auf {NAMES[language]}" in request.rules and "Suchbegriffe" in request.rules


@pytest.mark.parametrize("language", FOREIGN)
def test_cv_suggestions_give_their_reasons_in_the_app_language(language):
    labels, by_label = cv_suggestions.labelled([], FIRST)
    request = cv_suggestions.request("Inserat", labels, by_label, language)
    assert f"auf {NAMES[language]}" in request.rules
    assert "Antworte auf Deutsch" not in request.rules
    assert cv_suggestions.request("Inserat", labels, by_label).rules == cv_suggestions.RULES


@pytest.mark.parametrize("language", FOREIGN)
def test_exclusion_reasons_answer_in_the_app_language_and_keep_the_words_of_the_titles(language):
    request = exclusion_reasons.request({}, language)
    assert f"auf {NAMES[language]}" in request.rules and "Ausschlüsse für die Suche" in request.rules
    assert "Antworte auf Deutsch" not in request.rules
    assert exclusion_reasons.request({}).rules == exclusion_reasons.RULES


# The routes read the language of the app


def test_the_text_for_cv_suggestions_follows_the_app_language(with_ad, connected):  # noqa: F811
    choose_app_language(with_ad.kontext.daten, "en")
    status, _, body = get(with_ad, f"{CV_ROUTE}/text", id=BRIEF_ID)
    assert status == 200
    assert "auf Englisch" in json.loads(body)["text"]


def test_exclusion_reasons_from_the_page_follow_the_app_language(job_search, monkeypatch):  # noqa: F811
    choose_app_language(job_search.kontext.daten, "fr")
    client = ExclusionsClient()
    monkeypatch.setattr(routes_ai, "new_client", lambda: client)
    propose(job_search)
    assert "auf Französisch" in system_of(client)


def test_the_estimate_counts_the_rules_in_the_app_language(daten):  # noqa: F811
    k = type("K", (), {"daten": daten})()
    german = routes_rate_all._context_chars(k)
    choose_app_language(daten, "fr")
    assert routes_rate_all._context_chars(k) - german == len(prompts.rules("sie", "fr")) - len(prompts.rules("sie"))
