"""The hints on what the app replaces before sending to the AI (G14, #127) name everything personal.py replaces,
in the versions for jobs and for apprenticeships alike: the consent text (texte.js) and the intro of „Person und
Kontakt“ in the form (onboarding/form.json)."""
import json
import pathlib
import re

import pytest

from ai.personal import secrets_from_cv

ROOT = pathlib.Path(__file__).resolve().parents[2]
TEXTS_JS = ROOT / "bewerbungen" / "seiten" / "texte.js"
FORM = ROOT / "onboarding" / "form.json"
CONSENT_KEY = "einwilligung.ersetzt"
# Invented values; every field personal.py reads is filled, so every kind of placeholder shows up.
SAMPLE_CV = {
    "basics": {"name": "Lena Beispiel", "email": "lena@example.ch", "phone": "079 000 00 00",
               "url": "https://www.example.ch", "details": ["geboren am 3.4.2010"],
               "location": {"address": "Musterweg 1", "postalCode": "3000", "city": "Bern"},
               "profiles": [{"network": "LinkedIn", "url": "https://www.linkedin.com/in/lena-beispiel"}]},
    "references": [{"name": "Hans Muster"}],
    "education": [{"institution": "Oberstufe Muster, Bern"}],
}
# Words a hint uses for each kind of placeholder; one of them must appear.
WORDS = {
    "NAME": ("Name",), "EMAIL": ("E-Mail",), "PHONE": ("Telefon",), "ADDRESS": ("Adresse", "Strasse"),
    "POSTAL_CODE": ("Adresse", "PLZ"), "WEBSITE": ("Links",), "PROFILE_USER": ("Links",), "PROFILE": ("Links",),
    "BIRTH_DATE": ("Geburtsdatum",), "REFERENCE": ("Referenzen",), "SCHOOL": ("Schulen",),
}
# References are entered in the section „Rahmen“, so the intro of „Person und Kontakt“ need not name them.
NOT_IN_PERSON_SECTION = {"REFERENCE"}


def kind(secret_name: str) -> str:
    for key in sorted(WORDS, key=len, reverse=True):
        if secret_name.startswith(key):
            return key
    raise AssertionError(f"personal.py replaces {secret_name}, which no hint names; add its words to WORDS")


def replaced(minor: bool) -> set[str]:
    return {kind(secret.field) for secret in secrets_from_cv(SAMPLE_CV, minor=minor)}


def unnamed(text: str, kinds: set[str]) -> set[str]:
    return {k for k in kinds if not any(word in text for word in WORDS[k])}


def consent_texts() -> dict[str, str]:
    source = TEXTS_JS.read_text(encoding="utf-8")
    block = re.search(rf'"{re.escape(CONSENT_KEY)}": \{{(.*?)\n    \}}', source, re.DOTALL)
    assert block, f"{CONSENT_KEY} not found in texte.js"
    return dict(re.findall(r'(sie|du|lehrstelle): "([^"]*)"', block.group(1)))


def person_intro() -> dict[str, str]:
    sections = json.loads(FORM.read_text(encoding="utf-8"))["sections"]
    return next(section for section in sections if section["id"] == "person")["intro"]


def test_the_sample_covers_links_and_schools():
    assert {"WEBSITE", "PROFILE", "SCHOOL"} <= replaced(minor=True)
    assert "SCHOOL" not in replaced(minor=False)


@pytest.mark.parametrize("version, minor", [("sie", False), ("du", False), ("lehrstelle", True)])
def test_the_consent_text_names_what_is_replaced(version, minor):
    assert unnamed(consent_texts()[version], replaced(minor)) == set()


@pytest.mark.parametrize("track, minor", [("job", False), ("apprenticeship", True)])
def test_the_form_names_what_is_replaced(track, minor):
    assert unnamed(person_intro()[track], replaced(minor) - NOT_IN_PERSON_SECTION) == set()
