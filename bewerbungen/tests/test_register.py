"""Tests für das Bewerbungsregister: Daten pro Bewerbung, Job-Room-Angaben, Import aus der Jobliste (MIN-306)."""
import pytest

import register
from register import Register

KOPF = ["Firmen-Schlüssel", "Arbeitgeber", "Stelle", "Ort", "Pensum", "Inserent / Vermittler", "Portal(e)",
        "Link", "Status", "Beworben am", "Frist", "Notiz", "Duplikat-Check"]


@pytest.fixture
def reg(tmp_path):
    return Register(tmp_path)


# Prüfen


def test_minimal():
    b = register.pruefe_bewerbung({"id": "beispiel-data-engineer", "firma": "Beispiel AG", "stelle": "Data Engineer"})

    assert b["status"] == "Gemerkt"
    assert b["firma"] == "Beispiel AG"


@pytest.mark.parametrize(
    "aenderung, meldung",
    [
        ({"firma": ""}, "firma"),
        ({"stelle": None}, "stelle"),
        ({"status": "Vielleicht"}, "status"),
        ({"beworben_am": "gestern"}, "beworben_am"),
        ({"absage_am": "2026-13-01"}, "absage_am"),
        ({"link": "javascript:alert(1)"}, "link"),
        ({"id": "Mit Leerzeichen"}, "id"),
        ({"unbekannt": 1}, "unbekannt"),
        ({"jobroom": {"art": "Brieftaube"}}, "art"),
        ({"jobroom": {"farbe": "rot"}}, "farbe"),
    ],
)
def test_ungueltig(aenderung, meldung):
    with pytest.raises(ValueError, match=meldung):
        register.pruefe_bewerbung({"id": "x", "firma": "F", "stelle": "S", **aenderung})


def test_datum_im_schweizer_format_wird_umgewandelt():
    b = register.pruefe_bewerbung({"id": "x", "firma": "F", "stelle": "S", "beworben_am": "23.09.2026"})

    assert b["beworben_am"] == "2026-09-23"


def test_leere_felder_entfallen():
    b = register.pruefe_bewerbung({"id": "x", "firma": "F", "stelle": "S", "ort": "", "jobroom": {}})

    assert "ort" not in b
    assert "jobroom" not in b


# IDs


def test_id_aus_firma_und_stelle():
    assert register.erzeuge_id("a&b AG", "Senior Data Engineer mit Flair für AI", set()) == "a-b-ag-senior-data-engineer-mit-flair-fur-ai"


def test_id_eindeutig():
    assert register.erzeuge_id("Beispiel", "Tester", {"beispiel-tester"}) == "beispiel-tester-2"


# Register


def test_neu_speichern_und_lesen(reg):
    b = reg.neu(firma="Beispiel AG", stelle="Data Engineer", ort="Bern")

    assert reg.hole(b["id"])["ort"] == "Bern"
    assert Register(reg.ordner).alle() == [b]


def test_speichern_ersetzt_nach_id(reg):
    b = reg.neu(firma="Beispiel AG", stelle="Data Engineer")

    reg.speichere({**b, "status": "Beworben", "beworben_am": "2026-10-24"})

    assert len(reg.alle()) == 1
    assert reg.hole(b["id"])["status"] == "Beworben"


def test_unbekannte_id(reg):
    with pytest.raises(KeyError):
        reg.hole("gibt-es-nicht")


def test_ungueltig_wird_nicht_gespeichert(reg):
    b = reg.neu(firma="Beispiel AG", stelle="Data Engineer")

    with pytest.raises(ValueError):
        reg.speichere({**b, "status": "Kaputt"})
    assert reg.hole(b["id"])["status"] == "Gemerkt"


# Job-Room


def test_jobroom_vorschlag():
    b = {"id": "x", "firma": "Beispiel AG", "stelle": "Data Engineer", "pensum": "80–100%",
         "status": "Absage", "beworben_am": "2026-09-23"}

    j = register.jobroom_vorschlag(b)

    assert j["datum"] == "2026-09-23"
    assert j["arbeitgeber"] == "Beispiel AG"
    assert j["stelle"] == "Data Engineer"
    assert j["pensum"] == "Teilzeit"
    assert j["art"] == "elektronisch"
    assert j["ergebnis"] == "Absage"


def test_jobroom_vorschlag_behaelt_erfasste_werte():
    b = {"id": "x", "firma": "F", "stelle": "S", "pensum": "100%", "jobroom": {"art": "schriftlich", "kontaktperson": "Frau Meier"}}

    j = register.jobroom_vorschlag(b)

    assert j["art"] == "schriftlich"
    assert j["kontaktperson"] == "Frau Meier"
    assert j["pensum"] == "Vollzeit"


# Import aus der Jobliste


def test_import_aus_jobliste():
    zeilen = [
        KOPF,
        ["alpha", "Alpha AG", "Software Developer Logistik", "Bern", "", "direkt", "LinkedIn", "",
         "Absage", "15.09.2026", "", "Über LinkedIn beworben; Absage 23.09.2026"],
        [],
        ["beta", "Beta & Co AG", "AI Engineer", "Bern", "", "direkt", "Beta Karriereseite", "https://example.org/ai",
         "Beworben", "24.10.2026", "", "Online-Formular", "Firma mehrfach – prüfen"],
        ["gamma", "Gamma Stiftung", "Jobcoach", "Solothurn", "", "direkt", "LinkedIn", "",
         "Verworfen (kein IT-Bezug)", "ca. Sept. 2026", "", "Coaching-Profil"],
    ]

    bewerbungen = register.aus_jobliste(zeilen)

    alpha, beta, gamma = bewerbungen
    assert alpha["id"] == "alpha-software-developer-logistik"
    assert alpha["beworben_am"] == "2026-09-15"
    assert alpha["absage_am"] == "2026-09-23"
    assert beta["link"] == "https://example.org/ai"
    assert beta["vermittler"] == "direkt"
    assert "Firma mehrfach – prüfen" in beta["notiz"]
    assert gamma["status"] == "Verworfen"
    assert "kein IT-Bezug" in gamma["notiz"]
    assert "ca. Sept. 2026" in gamma["notiz"]
    assert "beworben_am" not in gamma


def test_import_mehrfach_gleiche_firma_und_stelle():
    zeile = ["beta", "Beta & Co AG", "AI Engineer", "", "", "", "", "", "Gemerkt", "", "", ""]

    ids = [b["id"] for b in register.aus_jobliste([KOPF, zeile, zeile])]

    assert ids == ["beta-ai-engineer", "beta-ai-engineer-2"]


def test_zusammenfuehren_behaelt_vorhandene(reg):
    b = reg.neu(firma="Alpha AG", stelle="Software Developer Logistik", id="alpha-software-developer-logistik")
    reg.speichere({**b, "notiz": "lokal ergänzt"})
    importiert = register.aus_jobliste([KOPF, ["alpha", "Alpha AG", "Software Developer Logistik", "", "",
                                              "", "", "", "Absage", "15.09.2026", "", ""],
                                        ["neu", "Neu AG", "Tester", "", "", "", "", "", "Gemerkt", "", "", ""]])

    neu = reg.fuehre_zusammen(importiert)

    assert [b["id"] for b in neu] == ["neu-tester"]
    assert reg.hole("alpha-software-developer-logistik")["notiz"] == "lokal ergänzt"


def test_export_fuer_jobliste(reg):
    reg.neu(firma="Beispiel AG", stelle="Tester", firma_schluessel="beispiel", status="Beworben", beworben_am="2026-10-24")

    zeilen = register.als_jobliste(reg.alle())

    assert zeilen[0] == KOPF[:12]
    assert zeilen[1][:3] == ["beispiel", "Beispiel AG", "Tester"]
    assert zeilen[1][8:10] == ["Beworben", "24.10.2026"]


def test_lange_id_endet_an_wortgrenze():
    neu = register.erzeuge_id("beispiel", "Spontanbewerbung Software Engineer (Inserat nicht mehr publiziert)", set())

    assert neu == "beispiel-spontanbewerbung-software-engineer-inserat-nicht-mehr"
    assert len(neu) <= 70


def test_id_ohne_zeilenumbruch():
    with pytest.raises(ValueError, match="id"):
        register.pruefe_bewerbung({"id": "abc\n", "firma": "F", "stelle": "S"})
