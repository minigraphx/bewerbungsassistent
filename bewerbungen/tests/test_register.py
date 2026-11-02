"""Tests für das Bewerbungsregister: Daten pro Bewerbung, Job-Room-Angaben, Import aus der Jobliste (MIN-306)."""
import datetime

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
        ({"rav_zuweisung": "ja"}, "rav_zuweisung"),
        ({"jobroom": "Zug"}, "jobroom"),
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


def test_jobroom_angaben_aus_der_bewerbung():
    b = {"id": "x", "firma": "Beispiel AG", "stelle": "Data Engineer", "pensum": "80–100%", "status": "Beworben",
         "beworben_am": "2026-09-23", "adresse": "Musterweg 1, 3000 Bern", "kontaktperson": "Frau Meier",
         "kontakt": "jobs@beispiel.ch", "versand": {"datum": "2026-09-23", "art": "schriftlich"}}

    j = register.jobroom_angaben(b)

    assert j == {"datum": "2026-09-23", "arbeitgeber": "Beispiel AG", "adresse": "Musterweg 1, 3000 Bern",
                 "kontaktperson": "Frau Meier", "kontakt": "jobs@beispiel.ch", "stelle": "Data Engineer",
                 "pensum": "Teilzeit", "art": "schriftlich", "ergebnis": "offen", "rav_zuweisung": False}


@pytest.mark.parametrize(
    "angaben, ergebnis",
    [
        ({"status": "Beworben"}, "offen"),
        ({"status": "Absage"}, "Absage"),
        ({"status": "Beworben", "absage_am": "2026-11-02"}, "Absage"),
        ({"status": "Gespräch", "absage_am": "2026-11-02"}, "Absage"),
        ({"status": "Gespräch"}, "Vorstellungsgespräch"),
        ({"status": "Beworben", "gespraech_am": "2026-11-05"}, "Vorstellungsgespräch"),
        ({"status": "Zusage"}, "Anstellung"),
    ],
)
def test_jobroom_ergebnis(angaben, ergebnis):
    assert register.jobroom_angaben({"id": "x", "firma": "F", "stelle": "S", **angaben})["ergebnis"] == ergebnis


@pytest.mark.parametrize("pensum, erwartet", [("100%", "Vollzeit"), ("80–100%", "Teilzeit"), ("Vollzeit", "Vollzeit"),
                                              ("Teilzeit", "Teilzeit"), ("", None)])
def test_jobroom_pensum(pensum, erwartet):
    assert register.jobroom_angaben({"id": "x", "firma": "F", "stelle": "S", "pensum": pensum}).get("pensum") == erwartet


def test_jobroom_art_ohne_versand_elektronisch():
    assert register.jobroom_angaben({"id": "x", "firma": "F", "stelle": "S"})["art"] == "elektronisch"


def test_fruehere_jobroom_angaben_werden_uebernommen():
    b = register.pruefe_bewerbung({
        "id": "x", "firma": "F", "stelle": "S", "status": "Absage", "kontakt": "neu@f.ch",
        "jobroom": {"adresse": "Musterweg 1, 3000 Bern", "kontaktperson": "Frau Meier", "kontakt": "alt@f.ch",
                    "pensum": "Vollzeit", "rav_zuweisung": True, "ergebnis": "offen", "erfasst_am": "2026-10-26"},
    })

    assert "jobroom" not in b
    assert b["adresse"] == "Musterweg 1, 3000 Bern"
    assert b["kontaktperson"] == "Frau Meier"
    assert b["kontakt"] == "neu@f.ch"
    assert b["pensum"] == "Vollzeit"
    assert b["rav_zuweisung"] is True
    assert register.jobroom_angaben(b)["ergebnis"] == "Absage"


def test_rav_zuweisung_nein_entfaellt():
    assert "rav_zuweisung" not in register.pruefe_bewerbung({"id": "x", "firma": "F", "stelle": "S", "rav_zuweisung": False})


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


# Eingetragen am und Passung


@pytest.mark.parametrize("wert, erwartet", [(6, 6), ("5.5", 5.5), ("4,5", 4.5), (1, 1), ("3", 3)])
def test_passung_als_schweizer_note(wert, erwartet):
    b = register.pruefe_bewerbung({"id": "a-b", "firma": "A", "stelle": "B", "passung": wert})

    assert b["passung"] == erwartet


@pytest.mark.parametrize("wert", [0, 7, "5.3", "gut", True])
def test_passung_ungueltig(wert):
    with pytest.raises(ValueError, match="passung"):
        register.pruefe_bewerbung({"id": "a-b", "firma": "A", "stelle": "B", "passung": wert})


def test_eingetragen_am_ist_ein_datum():
    b = register.pruefe_bewerbung({"id": "a-b", "firma": "A", "stelle": "B", "eingetragen_am": "26.10.2026"})

    assert b["eingetragen_am"] == "2026-10-26"


def test_neu_setzt_eingetragen_am_auf_heute(reg):
    b = reg.neu(firma="Alpha AG", stelle="Tester")

    assert b["eingetragen_am"] == datetime.date.today().isoformat()


def test_neu_behaelt_angegebenes_datum(reg):
    b = reg.neu(firma="Alpha AG", stelle="Tester", eingetragen_am="2026-10-01")

    assert b["eingetragen_am"] == "2026-10-01"


def test_zusatzspalten_fuer_jobliste(reg):
    b = reg.neu(firma="Alpha AG", stelle="Tester", eingetragen_am="2026-10-01", passung=4.5)

    assert register.ZUSATZ_SPALTEN == ["Eingetragen am", "Passung"]
    assert register.zusatzspalten(b) == ["01.10.2026", 4.5]
    assert register.zusatzspalten({"firma": "A", "stelle": "B"}) == ["", ""]


def test_import_liest_zusatzspalten():
    zeile = ["alpha", "Alpha AG", "Tester", "", "", "", "", "", "Gemerkt", "", "", "", "", "01.10.2026", "5,5"]

    (b,) = register.aus_jobliste([KOPF + register.ZUSATZ_SPALTEN, zeile])

    assert b["eingetragen_am"] == "2026-10-01"
    assert b["passung"] == 5.5
