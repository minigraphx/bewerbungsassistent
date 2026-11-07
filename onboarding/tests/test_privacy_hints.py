"""Where name and contact details are entered, the form says what the app replaces before text goes to the AI (G14)."""
import re

import build_template

SIE_FORM = re.compile(r"\b(Sie|Ihr|Ihre|Ihrem|Ihren|Ihrer|Ihnen)\b")
DU_FORM = re.compile(r"\b(du|dein|deine|deinem|deinen|deiner|dir|dich)\b", re.IGNORECASE)


def _person(form):
    return next(section for section in form["sections"] if section["id"] == "person")


def _field(form, field_id):
    return next(field for field in _person(form)["fields"] if field["id"] == field_id)


def test_the_person_intro_names_what_is_replaced_and_what_stays_in_both_forms(form):
    intro = _person(form)["intro"]
    for track in ("job", "apprenticeship"):
        text = intro[track]
        assert "Platzhalter" in text and "KI" in text
        for replaced in ("Name", "Strasse", "PLZ", "Telefon", "E-Mail", "Geburtsdatum"):
            assert replaced in text, (track, replaced)
        assert "Jahreszahlen" in text and "bleiben" in text
        assert "richtig eingetragen" in text
    assert SIE_FORM.search(intro["job"]) and not DU_FORM.search(intro["job"])
    assert DU_FORM.search(intro["apprenticeship"]) and not SIE_FORM.search(intro["apprenticeship"])


def test_the_apprenticeship_intro_says_schools_are_replaced(form):
    assert "Schulen" in _person(form)["intro"]["apprenticeship"]


def test_the_name_hint_asks_for_the_exact_spelling_in_both_forms(form):
    hint = _field(form, "name")["hint"]
    assert hint["job"].startswith("Schreiben Sie den Namen genau wie im Lebenslauf")
    assert hint["apprenticeship"].startswith("Schreib deinen Namen genau wie im Lebenslauf")
    for text in hint.values():
        assert "ersetzt die App" in text and "KI" in text


def test_the_built_pages_carry_the_hint():
    page = build_template.build()
    assert "Schreiben Sie den Namen genau wie im Lebenslauf" in page
    assert "Schreib deinen Namen genau wie im Lebenslauf" in page
