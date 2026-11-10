"""The choice among several kununu companies names only what the extension reads for a candidate (#199)."""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
EXTENSION = ROOT / "erweiterung" / "lib" / "kununu.js"
PAGE = ROOT / "bewerbungen" / "seiten" / "firmen.js"
GUIDE = ROOT / "docs" / "installation.md"
HINT = "Ort und Anzahl Bewertungen helfen beim Wählen."


def _candidate_fields() -> set[str]:
    source = EXTENSION.read_text(encoding="utf-8")
    body = source.split("function candidate(", 1)[1].split("\n}\n", 1)[0]
    return set(re.findall(r"\b(ort|branche|bewertungen)\s*:", body))


def test_the_extension_reads_place_and_reviews_but_no_branche():
    assert _candidate_fields() == {"ort", "bewertungen"}


def test_page_and_guide_name_only_what_a_candidate_has():
    fields = _candidate_fields()
    for path in (PAGE, GUIDE):
        text = path.read_text(encoding="utf-8")
        if "branche" not in fields:
            assert "branche" not in text.lower(), path.name
        assert HINT in text, path.name
