"""Tests für den Text-Editor der Inhalte (MIN-302): erlaubte Dateien, Prüfung je Dateityp, Vorschau."""
import pytest
import yaml

import inhalte
from conftest import BRIEF_ID


def test_bearbeitbare_dateien(datenordner):
    (datenordner / "suchprofil.md").write_text("# Suchprofil\n", encoding="utf-8")
    (datenordner / "notiz.txt").write_text("nein\n", encoding="utf-8")

    dateien = inhalte.bearbeitbare_dateien(datenordner)

    assert "cv.yaml" in dateien
    assert "jobs/daten.yaml" in dateien
    assert f"bewerbungen/{BRIEF_ID}/anschreiben.yaml" in dateien
    assert "bewerbungen.yaml" in dateien
    assert "varianten.yaml" in dateien
    assert "suchprofil.md" in dateien
    assert "notiz.txt" not in dateien


@pytest.mark.parametrize("datei", ["notiz.txt", "../cv.yaml", ".entwuerfe/index.yaml", "/etc/passwd", "versendet/x.pdf"])
def test_nicht_erlaubt(datenordner, datei):
    with pytest.raises(ValueError, match="nicht bearbeitbar"):
        inhalte.pruefe_datei(datenordner, datei)


def test_kaputtes_yaml(datenordner, tmp_path):
    with pytest.raises(ValueError, match="YAML"):
        inhalte.pruefe_inhalt(datenordner, "cv.yaml", "basics: [", tmp_path / "build")


def test_lebenslauf_muss_basics_haben(datenordner, tmp_path):
    with pytest.raises(ValueError, match="basics"):
        inhalte.pruefe_inhalt(datenordner, "cv.yaml", "work: []\n", tmp_path / "build")


def test_lebenslauf_gueltig_mit_vorschau(datenordner, tmp_path):
    text = (datenordner / "cv.yaml").read_text(encoding="utf-8").replace("Erika Beispiel", "Erika Neu")

    pdf = inhalte.pruefe_inhalt(datenordner, "cv.yaml", text, tmp_path / "build")

    assert pdf.is_file()
    assert (datenordner / "cv.yaml").read_text(encoding="utf-8").count("Erika Neu") == 0  # nichts gespeichert


def test_ungueltige_foto_optionen_im_lebenslauf(datenordner, tmp_path):
    text = (datenordner / "cv.yaml").read_text(encoding="utf-8").replace("basics:\n", "basics:\n  x-image: {zoom: 9}\n", 1)

    with pytest.raises(ValueError, match="zoom"):
        inhalte.pruefe_inhalt(datenordner, "cv.yaml", text, tmp_path / "build")


def test_zuschnitt_wird_mit_lebenslauf_gebaut(datenordner, tmp_path):
    pdf = inhalte.pruefe_inhalt(datenordner, "jobs/daten.yaml", "tags: [daten]\nmax_highlights: 2\n", tmp_path / "build")

    assert pdf.is_file()


def test_anschreiben_pflichtfelder(datenordner, tmp_path):
    with pytest.raises(ValueError, match="betreff"):
        inhalte.pruefe_inhalt(datenordner, f"bewerbungen/{BRIEF_ID}/anschreiben.yaml",
                              "empfaenger: [A]\nanrede: Hallo\ntext: x\ngruss: y\n", tmp_path / "build")


def test_anschreiben_gueltig_mit_vorschau(datenordner, tmp_path):
    datei = f"bewerbungen/{BRIEF_ID}/anschreiben.yaml"
    text = (datenordner / datei).read_text(encoding="utf-8")

    assert inhalte.pruefe_inhalt(datenordner, datei, text, tmp_path / "build").is_file()


def test_register_doppelte_id(datenordner, tmp_path):
    eintrag = {"id": "a", "firma": "A", "stelle": "B"}

    with pytest.raises(ValueError, match="doppelt"):
        inhalte.pruefe_inhalt(datenordner, "bewerbungen.yaml", yaml.safe_dump([eintrag, eintrag]), tmp_path / "build")


def test_varianten_ungueltig(datenordner, tmp_path):
    with pytest.raises(ValueError, match="quelle"):
        inhalte.pruefe_inhalt(datenordner, "varianten.yaml", "- id: x\n", tmp_path / "build")


def test_markdown_ohne_pruefung(datenordner, tmp_path):
    (datenordner / "suchprofil.md").write_text("# alt\n", encoding="utf-8")

    assert inhalte.pruefe_inhalt(datenordner, "suchprofil.md", "# neu\n", tmp_path / "build") is None


def test_fehler_beim_probebau_wird_verstaendlich(datenordner, tmp_path):
    text = (datenordner / "cv.yaml").read_text(encoding="utf-8") + "work: 5\n"

    with pytest.raises(ValueError, match="Probebau"):
        inhalte.pruefe_inhalt(datenordner, "cv.yaml", text, tmp_path / "build")
