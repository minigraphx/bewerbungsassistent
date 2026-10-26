"""Tests für mehrsprachige Inhalte (MIN-300): Texte als {de: ..., en: ...}, gewählt über --lang."""
import pytest

import build
from conftest import beispiel


def test_waehlt_sprache_ueberall():
    daten = {"summary": {"de": "Hallo", "en": "Hello"},
             "work": [{"highlights": [{"de": "eins", "en": "one"}, "immer gleich"]}]}

    assert build.waehle_sprache(daten, "en") == {"summary": "Hello", "work": [{"highlights": ["one", "immer gleich"]}]}


def test_fehlende_sprache_faellt_auf_deutsch_zurueck():
    assert build.waehle_sprache({"t": {"de": "Hallo"}}, "en") == {"t": "Hallo"}


def test_andere_zuordnungen_bleiben():
    ort = {"location": {"city": "Bern", "postalCode": "3000"}}

    assert build.waehle_sprache(ort, "en") == ort


def test_englische_inhalte_im_pdf(baue):
    cv = beispiel()
    cv["basics"]["summary"] = {"de": "Deutsches Profil.", "en": "English profile."}
    cv["work"][0]["highlights"][0] = {"de": "Deutscher Stichpunkt", "en": "English bullet point"}

    text = "".join(baue(cv, "--lang", "en"))

    assert "English profile." in text
    assert "English bullet point" in text
    assert "Deutsches Profil." not in text


def test_mehrsprachiger_stichpunkt_mit_tags(baue):
    cv = beispiel()
    cv["work"][0]["highlights"] = [{"text": {"de": "Mit Tag", "en": "With tag"}, "tags": ["daten"]}]

    assert "With tag" in "".join(baue(cv, "--lang", "en"))


def test_unbekannte_sprache(baue):
    with pytest.raises(SystemExit):
        baue(beispiel(), "--lang", "fr")
