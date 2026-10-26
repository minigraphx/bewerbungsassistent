"""Tests für den Entwurf-Befehl: Änderungen ausserhalb der Oberfläche (z.B. durch Claude) als Entwurf sichern."""
import json

import pytest

import entwurf
from ablage import Ablage


def test_sichert_vorher_und_nachher(datenordner, capsys):
    cv = datenordner / "cv.yaml"

    entwurf.main([str(datenordner), "cv.yaml", "-m", "Profil gekürzt"])
    cv.write_text(cv.read_text(encoding="utf-8") + "# neu\n", encoding="utf-8")
    entwurf.main([str(datenordner), "cv.yaml", "-m", "Profil gekürzt"])

    eintraege = Ablage(datenordner).liste(cv)
    assert [e.beschreibung for e in eintraege] == ["Profil gekürzt", "Profil gekürzt"]
    assert ".entwuerfe/" in (datenordner / ".gitignore").read_text(encoding="utf-8")


def test_unveraendert_kein_neuer_entwurf(datenordner, capsys):
    entwurf.main([str(datenordner), "cv.yaml"])
    capsys.readouterr()

    entwurf.main([str(datenordner), "cv.yaml"])

    assert json.loads(capsys.readouterr().out) == [{"datei": "cv.yaml", "entwurf": None, "hinweis": "unverändert"}]
    assert len(Ablage(datenordner).liste(datenordner / "cv.yaml")) == 1


def test_mehrere_und_fehlende_dateien(datenordner, capsys):
    entwurf.main([str(datenordner), "cv.yaml", "anschreiben/stil.md"])

    ergebnis = json.loads(capsys.readouterr().out)
    assert ergebnis[0]["entwurf"]
    assert ergebnis[1] == {"datei": "anschreiben/stil.md", "entwurf": None, "hinweis": "existiert noch nicht"}


@pytest.mark.parametrize("datei", ["../ausserhalb.yaml", "/etc/passwd"])
def test_nur_im_datenordner(datenordner, datei):
    with pytest.raises(ValueError):
        entwurf.main([str(datenordner), datei])
