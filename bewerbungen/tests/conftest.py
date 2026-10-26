"""Gemeinsame Testdaten: ein Datenordner mit den erfundenen Beispieldaten des Lebenslauf-Moduls."""
import shutil

import pytest
import yaml

import build
from register import Register
from varianten import Varianten

BEISPIEL = build.ROOT / "data"
BRIEF_ID = "beispiel-ag-data-engineer"


@pytest.fixture
def datenordner(tmp_path):
    """Datenordner wie im privaten Repo: cv.yaml, Zuschnitt, Variante, eine Bewerbung mit Anschreiben."""
    ordner = tmp_path / "daten"
    (ordner / "jobs").mkdir(parents=True)
    shutil.copy(BEISPIEL / "beispiel.yaml", ordner / "cv.yaml")
    shutil.copy(build.ROOT / "jobs" / "beispiel-daten.yaml", ordner / "jobs" / "daten.yaml")
    brief = yaml.safe_load((BEISPIEL / "anschreiben-beispiel.yaml").read_text(encoding="utf-8"))
    brief = {**brief, "lebenslauf": "../../cv.yaml", "datum": "2026-10-24"}
    (ordner / "bewerbungen" / BRIEF_ID).mkdir(parents=True)
    (ordner / "bewerbungen" / BRIEF_ID / "anschreiben.yaml").write_text(
        yaml.safe_dump(brief, allow_unicode=True), encoding="utf-8")
    Varianten(ordner).speichere({"id": "daten", "quelle": "jobs/daten.yaml", "tags": ["daten"],
                                 "stichworte": ["Python", "Airflow"], "beschreibung": "Daten-Fassung"})
    Register(ordner).neu(firma="Beispiel AG", stelle="Data Engineer", id=BRIEF_ID, variante="daten",
                         pensum="80–100%")
    return ordner
