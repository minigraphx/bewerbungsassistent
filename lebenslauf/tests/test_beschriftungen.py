"""Eigene Überschriften pro Lebenslauf (MIN-335), z.B. für Schülerlebensläufe."""
import pytest

import build
from cv_samples import beispiel, lang

SCHUELER = {"erfahrung": "Schnupperlehren & Erfahrungen", "bildung": "Schule & Eignungstests"}


@pytest.mark.parametrize("theme", ["zweispaltig", "einspaltig"])
def test_eigene_ueberschriften(baue, theme):
    cv = {**beispiel(), "x-beschriftungen": SCHUELER}

    text = "".join(baue(cv, "--theme", theme))

    assert "SCHNUPPERLEHREN & ERFAHRUNGEN" in text
    assert "SCHULE & EIGNUNGSTESTS" in text
    assert "BERUFSERFAHRUNG" not in text
    assert "BILDUNG & WEITERBILDUNG" not in text
    assert "SPRACHEN" in text  # nicht überschriebene bleiben


def test_eigene_ueberschrift_auch_in_der_fortsetzung(baue):
    cv = {**lang(beispiel()), "x-beschriftungen": SCHUELER}

    seiten = baue(cv)

    assert seiten[1].lstrip().startswith("SCHNUPPERLEHREN & ERFAHRUNGEN (FORTSETZUNG)")


def test_eigene_ueberschriften_mehrsprachig(baue):
    cv = {**beispiel(), "x-beschriftungen": {"erfahrung": {"de": "Erfahrungen", "en": "Work experience"}}}

    assert "WORK EXPERIENCE" in "".join(baue(cv, "--lang", "en"))
    assert "ERFAHRUNGEN" in "".join(baue(cv, "--lang", "de"))


@pytest.mark.parametrize(
    "wert, meldung",
    [
        ("Schule", "Zuordnung"),
        ({"berufserfahrung": "X"}, "erfahrung"),
        ({"erfahrung": ""}, "erfahrung"),
        ({"erfahrung": 3}, "erfahrung"),
        ({"erfahrung": "x" * (build.MAX_BESCHRIFTUNG + 1)}, "höchstens"),
    ],
)
def test_ungueltige_ueberschriften(wert, meldung):
    with pytest.raises(ValueError, match=meldung):
        build.pruefe_beschriftungen(wert)


def test_ungueltige_ueberschriften_stoppen_den_build(baue):
    with pytest.raises(ValueError, match="x-beschriftungen"):
        baue({**beispiel(), "x-beschriftungen": {"unbekannt": "X"}})
