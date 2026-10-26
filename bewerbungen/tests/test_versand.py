"""Tests für das Erfassen des Versands (MIN-263): Fassung einmal ablegen, Entwürfe als genutzt markieren,
Register aktualisieren, in Git einfrieren."""
import datetime
import subprocess

import pytest

import unterlagen
import versand
import versionen
from ablage import Ablage
from conftest import BRIEF_ID
from register import Register

DATUM = datetime.date(2026, 10, 26)


@pytest.fixture
def bereit(datenordner, tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    unterlagen.baue(datenordner, Register(datenordner).hole(BRIEF_ID), tmp_path / "build")
    return datenordner


def erfasse(ordner, bewerbung_id=BRIEF_ID, versionierung=None, **optionen):
    return versand.erfasse_versand(ordner, bewerbung_id, DATUM, versionierung or versionen.GitVersionen(ordner), **optionen)


def test_versand_aktualisiert_register(bereit):
    ergebnis = erfasse(bereit)

    b = Register(bereit).hole(BRIEF_ID)
    assert b["status"] == "Beworben"
    assert b["beworben_am"] == "2026-10-26"
    assert b["versand"]["art"] == "elektronisch"
    assert set(b["versand"]["dateien"]) == {"lebenslauf", "anschreiben"}
    assert b["jobroom"]["datum"] == "2026-10-26"
    assert b["jobroom"]["arbeitgeber"] == "Beispiel AG"
    assert ergebnis["commit"]


def test_fassung_liegt_unter_versendet(bereit):
    erfasse(bereit)

    dateien = Register(bereit).hole(BRIEF_ID)["versand"]["dateien"]
    pfad = bereit / dateien["lebenslauf"]
    assert pfad.parent.name == "versendet"
    assert pfad.name.startswith("2026-10-26-")
    assert pfad.read_bytes() == unterlagen.pdf_pfade(bereit, BRIEF_ID)["lebenslauf"].read_bytes()


def test_gleiche_fassung_existiert_nur_einmal(bereit):
    zweite = Register(bereit).neu(firma="Zweite AG", stelle="Data Engineer", variante="daten")
    ordner = unterlagen.pdf_pfade(bereit, zweite["id"])["lebenslauf"].parent
    ordner.mkdir(parents=True)
    (ordner / "lebenslauf.pdf").write_bytes(unterlagen.pdf_pfade(bereit, BRIEF_ID)["lebenslauf"].read_bytes())

    erfasse(bereit)
    erfasse(bereit, zweite["id"])

    a = Register(bereit).hole(BRIEF_ID)["versand"]["dateien"]["lebenslauf"]
    b = Register(bereit).hole(zweite["id"])["versand"]["dateien"]["lebenslauf"]
    assert a == b
    assert len([p for p in (bereit / "versendet").iterdir() if p.suffix == ".pdf"]) == 2  # Lebenslauf + Anschreiben


def test_entwuerfe_werden_genutzt(bereit):
    ablage = Ablage(bereit)
    entwurf = ablage.speichere(bereit / "cv.yaml", "vor dem Versand")

    erfasse(bereit)

    with pytest.raises(ValueError, match="genutzt"):
        ablage.loesche(entwurf.id)
    genutzt = {e.datei for e in ablage.liste() if e.genutzt}
    assert {"cv.yaml", "jobs/daten.yaml", f"bewerbungen/{BRIEF_ID}/anschreiben.yaml"} <= genutzt


def test_git_commit_enthaelt_fassung_und_daten(bereit):
    ergebnis = erfasse(bereit)

    dateien = subprocess.run(["git", "-C", str(bereit), "show", "--name-only", "--format=", ergebnis["commit"]],
                             capture_output=True, text=True, check=True).stdout.split()
    assert "cv.yaml" in dateien
    assert "bewerbungen.yaml" in dateien
    assert "varianten.yaml" in dateien
    assert f"bewerbungen/{BRIEF_ID}/anschreiben.yaml" in dateien
    assert any(d.startswith("versendet/") for d in dateien)
    assert not any(d.endswith("anschreiben.pdf") and d.startswith("bewerbungen/") for d in dateien)


def test_nicht_zweimal_versenden(bereit):
    erfasse(bereit)

    with pytest.raises(ValueError, match="bereits"):
        erfasse(bereit)


def test_ohne_lebenslauf(datenordner):
    with pytest.raises(ValueError, match="Lebenslauf"):
        erfasse(datenordner)


def test_ohne_git(bereit):
    ergebnis = erfasse(bereit, versionierung=versionen.OhneGit(bereit))

    assert ergebnis["commit"] is None
    assert any("Git" in h for h in ergebnis["hinweise"])
    assert Register(bereit).hole(BRIEF_ID)["status"] == "Beworben"


def test_hinweis_bei_mehreren_bewerbungen_derselben_firma(bereit):
    Register(bereit).neu(firma="Beispiel AG", stelle="Tester", status="Beworben", beworben_am="2026-10-20")

    ergebnis = erfasse(bereit)

    assert any("Beispiel AG" in h for h in ergebnis["hinweise"])


def test_ungueltige_art(bereit):
    with pytest.raises(ValueError, match="art"):
        erfasse(bereit, art="Brieftaube")


class KaputtesGit:
    hinweis = "Git"

    def friere_ein(self, pfade, nachricht):
        raise RuntimeError("Git-Commit fehlgeschlagen: pre-commit hook")

    def verlauf(self, anzahl=50):
        return []


def test_git_fehler_meldet_hinweis_statt_abbruch(bereit):
    ergebnis = erfasse(bereit, versionierung=KaputtesGit())

    assert ergebnis["commit"] is None
    assert any("pre-commit hook" in h for h in ergebnis["hinweise"])
    assert Register(bereit).hole(BRIEF_ID)["status"] == "Beworben"
