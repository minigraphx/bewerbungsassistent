"""Tests für Lebenslauf-Varianten: Tags zum Wiederfinden und Vorschlag passender Varianten zur Stelle (MIN-307)."""
import pytest

import varianten
from varianten import Varianten

KI = {"id": "ki", "quelle": "jobs/ki.yaml", "beschreibung": "Entwicklung mit KI-Schwerpunkt",
      "tags": ["ki", "fullstack"], "stichworte": ["Python", "LLM", "Prompt Engineering", "RAG"]}
BILDUNG = {"id": "bildung", "quelle": "jobs/bildung.yaml", "beschreibung": "Berufsbildung und Kurse",
           "tags": ["bildung"], "stichworte": ["Berufsbildner", "Lernende", "Erwachsenenbildung", "Python"]}
CANVA = {"id": "canva-fullstack", "extern": "Google Drive: Fullstack 2026.pdf", "beschreibung": "Canva-Fassung",
         "tags": ["fullstack"], "stichworte": ["PHP", "TypeScript"]}


@pytest.fixture
def var(tmp_path):
    v = Varianten(tmp_path)
    for d in (KI, BILDUNG, CANVA):
        v.speichere(d)
    return v


@pytest.mark.parametrize(
    "aenderung, meldung",
    [
        ({"id": "Mit Leerzeichen"}, "id"),
        ({"tags": "ki"}, "tags"),
        ({"quelle": None, "extern": None}, "quelle"),
        ({"extern": "zusätzlich"}, "nur eine"),
        ({"quelle": "../ausserhalb.yaml"}, "quelle"),
        ({"art": "zeugnis"}, "art"),
        ({"farbe": "blau"}, "farbe"),
    ],
)
def test_ungueltig(aenderung, meldung):
    with pytest.raises(ValueError, match=meldung):
        varianten.pruefe_variante({**KI, **aenderung})


def test_standardwerte():
    v = varianten.pruefe_variante({"id": "x", "quelle": "jobs/x.yaml"})

    assert v["art"] == "lebenslauf"
    assert v["tags"] == []
    assert v["sprache"] == "de"


def test_speichern_lesen_ersetzen(var, tmp_path):
    var.speichere({**KI, "beschreibung": "neu"})

    assert [v["id"] for v in Varianten(tmp_path).alle()] == ["ki", "bildung", "canva-fullstack"]
    assert var.hole("ki")["beschreibung"] == "neu"


def test_finde_nach_tags(var):
    assert [v["id"] for v in var.finde(["fullstack"])] == ["ki", "canva-fullstack"]
    assert [v["id"] for v in var.finde(["fullstack", "ki"])] == ["ki"]


def test_vorschlag_ki_stelle(var):
    stelle = "Wir suchen einen AI Engineer mit Python, Erfahrung mit LLM und RAG. Lernende betreuen ist ein Plus."

    vorschlaege = varianten.vorschlagen(stelle, var.alle())

    besten = vorschlaege[0]
    assert besten["id"] == "ki"
    assert besten["treffer"] == ["LLM", "Python", "RAG"]
    assert besten["fehlt"] == ["Lernende"]
    assert [v["id"] for v in vorschlaege] == ["ki", "bildung"]


def test_vorschlag_ganze_woerter(var):
    vorschlaege = varianten.vorschlagen("Wir nutzen Pythonic Tools und LLMs", var.alle())

    assert vorschlaege == []


def test_vorschlag_mit_bindestrichen_und_gross_klein(var):
    vorschlaege = varianten.vorschlagen("BERUFSBILDNER/in ICT und prompt engineering", var.alle())

    assert {v["id"] for v in vorschlaege} == {"ki", "bildung"}


def test_unbekannte_sprache():
    with pytest.raises(ValueError, match="sprache"):
        varianten.pruefe_variante({**KI, "sprache": "fr"})
