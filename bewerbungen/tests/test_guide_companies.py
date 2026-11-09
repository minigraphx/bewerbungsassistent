"""The guide explains the page Firmen and kununu (#191), with the names the app shows."""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
GUIDE = ROOT / "docs" / "installation.md"
PAGES = ROOT / "bewerbungen" / "seiten"
HEADING = "### Firmen und kununu"
SOURCES = ("firmen.html", "firmen.js", "firmen-logik.js", "texte.js", "treffer.html", "treffer-firma.js")


def _section() -> str:
    text = GUIDE.read_text(encoding="utf-8")
    assert HEADING in text, f"{HEADING} fehlt in docs/installation.md"
    return text.split(HEADING, 1)[1].split("\n### ", 1)[0]


def test_the_guide_says_where_the_page_is_and_what_kununu_values_mean():
    section = _section()

    assert "**Mehr**, **Firmen**" in section and "**Lehrbetriebe**" in section
    assert "Mitarbeitende" in section and "nicht von der App" in section
    assert "Unter 10 Bewertungen" in section and "90 Tagen" in section


def test_the_guide_says_a_check_runs_on_click_and_sends_only_the_company_name():
    section = _section()

    assert "nur, wenn Sie auf **Prüfen** klicken" in section
    assert "nur der Firmenname" in section


def test_the_guide_says_how_to_assign_a_company_or_enter_a_value_by_hand():
    section = _section()

    for step in ("**Selbst zuordnen**", "**Passende wählen**", "**Von Hand eintragen**", "**Zuordnen**"):
        assert step in section
    assert "den Knopf hat jede Firma, für die noch kein Wert gespeichert ist" in section


def test_every_name_in_bold_is_shown_by_the_app():
    shown = "\n".join((PAGES / name).read_text(encoding="utf-8") for name in SOURCES)
    names = set(re.findall(r"\*\*([^*]+)\*\*", _section()))
    # „kununu 3.8“ is an example of the badge, built from „kununu “ and the value
    missing = [name for name in names - {"kununu 3.8"} if name not in shown]

    assert missing == []
    assert "`kununu ${" in shown
