"""The design doc for the dossier (#200, G16, G39): three designs, each with its page sequence, and a shared foundation."""
import pathlib
import re

import pytest

DOC = pathlib.Path(__file__).resolve().parents[2] / "docs" / "design" / "dossier.md"
DESIGNS = ("Siegel", "Raster", "Register")
FOUNDATION = ("Teile und Dateien", "Datenerweiterungen", "Regel für Niveaus", "Akzentfarbe", "Icons",
              "Lesbarkeit für Bewerbungssoftware", "Aufbau in Typst")
# The proposal was developed without any private reference; the doc must not point to one.
PRIVATE = re.compile(r"private\w*\s+vorlage|bewerbungsassistent-daten|\.dc\.html|canvas-dossier", re.IGNORECASE)


def _text() -> str:
    assert DOC.is_file(), "docs/design/dossier.md fehlt"
    return DOC.read_text(encoding="utf-8")


def _section(design: str) -> str:
    text = _text()
    match = re.search(rf"^## Entwurf \w: „{design}“\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    assert match, f"Abschnitt für {design} fehlt"
    return match[1]


@pytest.mark.parametrize("design", DESIGNS)
def test_each_design_has_its_page_sequence(design):
    section = _section(design)
    sequence = section.split("**Seitenfolge im Dossier**", 1)[1].strip("\n").split("\n\n", 1)[0]
    steps = re.findall(r"^\d+\. (.+)$", sequence, re.M)

    assert len(steps) >= 4
    assert any(step.startswith("Deckblatt") for step in steps)
    assert any(step.startswith("Anschreiben") for step in steps)
    assert any(step.startswith("Lebenslauf") for step in steps)


def test_the_shared_foundation_is_described():
    text = _text()
    assert [part for part in FOUNDATION if part not in text] == []


def test_the_doc_names_the_approval_and_no_private_reference():
    text = _text()
    assert "10.11.2026" in text and "https://claude.ai/artifact/7E4L7uKhqSdXHAJCMcaRcT" in text
    assert PRIVATE.findall(text) == []
