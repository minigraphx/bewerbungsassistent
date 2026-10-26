"""Tests für die Themes: Fortsetzung auf Folgeseiten, englische Fassung, Foto-Optionen."""
import pytest

import build
from conftest import beispiel, lang


def test_fortsetzung_auf_seite_2(baue):
    seiten = baue(lang(beispiel()))

    assert len(seiten) >= 2
    assert "FORTSETZUNG" not in seiten[0]
    assert "BERUFSERFAHRUNG (FORTSETZUNG)" in seiten[1]


@pytest.mark.parametrize("faktor", [2, 3, 8])
def test_fortsetzung_der_hauptspalte_beginnt_links(baue, faktor):
    """Gedruckt liest man nach Seite 1 unten rechts oben links weiter: dort steht die Berufserfahrung."""
    cv = lang(beispiel(), faktor)
    seiten = baue(cv)

    assert seiten[1].lstrip().startswith("BERUFSERFAHRUNG (FORTSETZUNG)")
    alles = "".join(seiten)
    for station in cv["work"]:
        assert alles.count(station["position"] + "\n") == 1, station["position"]


def test_keine_fortsetzung_bei_einer_seite(baue):
    kurz = {k: v for k, v in beispiel().items() if k not in ("teaching", "interests", "projects")}
    seiten = baue(kurz)

    assert len(seiten) == 1
    assert "FORTSETZUNG" not in seiten[0]


def test_ganzer_abschnitt_auf_neuer_seite_ohne_fortsetzung(baue):
    seiten = baue(beispiel())

    assert len(seiten) == 2
    assert seiten[1].lstrip().startswith("INTERESSEN")
    assert "FORTSETZUNG" not in "".join(seiten)


@pytest.mark.parametrize(
    "label, zeile1, zeile2",
    [
        ("Senior-Entwickler – Qualitätssicherung und KI-Systeme", "SENIOR-ENTWICKLER –", "QUALITÄTSSICHERUNG UND KI-SYSTEME"),
        ("Software-Entwickler – KI-Anwendungen und Qualitätssicherung", "SOFTWARE-ENTWICKLER –", "KI-ANWENDUNGEN UND QUALITÄTSSICHERUNG"),
    ],
)
def test_label_umbruch_nach_gedankenstrich(baue, label, zeile1, zeile2):
    cv = beispiel()
    cv["basics"]["label"] = label

    zeilen = [z.strip() for z in baue(cv)[0].splitlines()]

    assert zeilen[zeilen.index(zeile1) + 1] == zeile2


def test_englische_beschriftungen(baue):
    seiten = baue(lang(beispiel()), "--lang", "en")

    assert "EXPERIENCE" in seiten[0]
    assert "March 2019 – present" in seiten[0]
    assert "EXPERIENCE (CONTINUED)" in seiten[1]
    assert "BERUFSERFAHRUNG" not in "".join(seiten)


@pytest.mark.parametrize("theme", ["zweispaltig", "einspaltig"])
def test_englisch_in_beiden_themes(baue, theme):
    text = "".join(baue(beispiel(), "--lang", "en", "--theme", theme))

    assert "present" in text
    assert "heute" not in text


def test_foto_optionen(baue, mit_foto):
    seiten = baue(mit_foto(beispiel(), mirror=True, zoom=1.5, x=0.3, y=0.2))

    assert "Erika" in seiten[0]


def test_foto_ohne_optionen(baue, mit_foto):
    seiten = baue(mit_foto(beispiel()))

    assert "Erika" in seiten[0]


@pytest.mark.parametrize(
    "optionen, meldung",
    [
        ({"mirror": "ja"}, "mirror"),
        ({"zoom": 0.5}, "zoom"),
        ({"zoom": 5}, "zoom"),
        ({"x": 1.5}, "x"),
        ({"y": -0.1}, "y"),
        ({"spiegeln": True}, "spiegeln"),
    ],
)
def test_ungueltige_foto_optionen(optionen, meldung):
    with pytest.raises(ValueError, match=meldung):
        build.pruefe_foto_optionen(optionen)


def test_gueltige_foto_optionen():
    assert build.pruefe_foto_optionen({"mirror": True, "zoom": 1, "x": 0, "y": 1}) == {
        "mirror": True,
        "zoom": 1,
        "x": 0,
        "y": 1,
    }
