"""The cover letter goes to the firm in the language of the documents, whatever the app language (#98, G12).

The app language (#97, G11) decides what the person reads; the letter's `sprache` decides what the firm reads. Every
request goes to a simulated API: nothing reaches the real AI.
"""
import pytest
import yaml

from ai import prompts, tasks
from sample_folder import BRIEF_ID
from test_ai_tasks import AD, DRAFT, ENTRY, FakeClient, daten, gateway_for  # noqa: F401  (daten is a fixture)
from test_app import post, server  # noqa: F401  (server is a fixture)
from test_routes_ai import ki, use  # noqa: F401  (ki is a fixture)

SWISS_GERMAN = "Antworte auf Deutsch, Schweizer Schreibweise (ss statt ß)."
LETTER_IN = {"de": "Schreibe das Anschreiben auf Deutsch", "fr": "Schreibe das Anschreiben auf Französisch",
             "en": "Schreibe das Anschreiben auf Englisch"}
# The sample application has no contact person, so the route's draft greets without a placeholder
ROUTE_DRAFT = {**DRAFT, "salutation": "Madame, Monsieur"}
TO_THE_PERSON = {"fr": "Schreibe alles, was die Person liest, auf Französisch",
                 "en": "Schreibe alles, was die Person liest, auf Englisch"}


def choose_app_language(folder, language: str) -> None:
    (folder / "sprachen.yaml").write_text(f"app: {language}\n", encoding="utf-8")


def system_of(client) -> str:
    return "\n".join(block["text"] for block in client.messages.calls[-1]["system"])


def content_of(client) -> str:
    return client.messages.calls[-1]["messages"][0]["content"]


def draft_in(folder, app: str, letter: str | None) -> FakeClient:
    choose_app_language(folder, app)
    client = FakeClient(reply=DRAFT)
    gateway, material = gateway_for(folder, client, ENTRY)
    if letter is None:
        tasks.draft_letter(gateway, material, ENTRY, AD)
    else:
        tasks.draft_letter(gateway, material, ENTRY, AD, language=letter)
    return client


@pytest.mark.parametrize("app, letter", [("de", "fr"), ("fr", "de"), ("fr", "fr"), ("en", "fr"), ("de", "en"),
                                         ("fr", "en")])
def test_the_letter_is_drafted_in_the_language_of_the_documents(daten, app, letter):  # noqa: F811
    client = draft_in(daten, app, letter)
    prompt = content_of(client)
    assert LETTER_IN[letter] in prompt
    assert not [other for code, other in LETTER_IN.items() if code != letter and other in prompt]


@pytest.mark.parametrize("app", ["fr", "en"])
def test_what_the_person_reads_still_follows_the_app_language(daten, app):  # noqa: F811
    client = draft_in(daten, app, "de")
    assert TO_THE_PERSON[app] in system_of(client)
    assert LETTER_IN["de"] in content_of(client)


def test_a_french_letter_from_a_german_app_keeps_the_german_rules(daten):  # noqa: F811
    client = draft_in(daten, "de", "fr")
    assert SWISS_GERMAN in system_of(client)
    assert LETTER_IN["fr"] in content_of(client)


@pytest.mark.parametrize("letter", [None, "de"])
def test_a_german_letter_in_a_german_app_is_asked_for_as_before(daten, letter):  # noqa: F811
    client = draft_in(daten, "de", letter)
    assert not any(line in content_of(client) for line in LETTER_IN.values())


def test_the_trial_request_follows_the_language_of_the_documents_too(daten):  # noqa: F811
    choose_app_language(daten, "de")
    client = FakeClient(reply=DRAFT)
    gateway, material = gateway_for(daten, client, ENTRY)
    tasks.draft_letter(gateway, material, {**ENTRY, "art": "Schnupperlehre"}, AD, language="fr")
    assert LETTER_IN["fr"] in content_of(client)


def test_the_dossier_texts_can_be_french():
    assert "auf Französisch" in prompts.dossier_texts_prompt("Inserat", {"Firma": "Beispiel AG"}, "", "fr")


# The route reads the language from the letter


def test_the_route_drafts_in_the_language_of_the_letter_and_keeps_it(ki, monkeypatch):  # noqa: F811
    choose_app_language(ki.kontext.daten, "de")
    path = ki.kontext.daten / "bewerbungen" / BRIEF_ID / "anschreiben.yaml"
    letter = yaml.safe_load(path.read_text(encoding="utf-8"))
    path.write_text(yaml.safe_dump({**letter, "sprache": "fr"}, allow_unicode=True), encoding="utf-8")
    client = use(monkeypatch, FakeClient(reply=ROUTE_DRAFT))

    status, answer = post(ki, "/api/ki/anschreiben", {}, id=BRIEF_ID)

    assert status == 200, answer
    assert LETTER_IN["fr"] in content_of(client)
    assert yaml.safe_load(path.read_text(encoding="utf-8"))["sprache"] == "fr"


def test_the_route_drafts_german_for_a_letter_without_language_in_a_french_app(ki, monkeypatch):  # noqa: F811
    choose_app_language(ki.kontext.daten, "fr")
    client = use(monkeypatch, FakeClient(reply=ROUTE_DRAFT))

    status, answer = post(ki, "/api/ki/anschreiben", {}, id=BRIEF_ID)

    assert status == 200, answer
    assert LETTER_IN["de"] in content_of(client)
    assert TO_THE_PERSON["fr"] in system_of(client)
