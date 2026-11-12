"""The redesign sources in docs/design stay in step with the list in docs/design/README.md (#258)."""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
DESIGN = ROOT / "docs" / "design"
SOURCES = DESIGN / "seiten" / "redesign"
PICTURES = DESIGN / "entwurf" / "redesign"
SECTION = "## Neugestaltung der App ab 0.3"
SCREEN_IDS = [f"A{number}" for number in range(1, 12)]
ROW = re.compile(r"^\| (?P<id>A\d+|Baustein) \| \[(?P<picture>[^\]]+)\]\(entwurf/redesign/(?P=picture)\) \| .+ \| "
                 r"\d+ px \| \[(?P<source>[^\]]+)\]\(seiten/redesign/(?P=source)\) \|$")


def listed_rows() -> list[dict]:
    text = (DESIGN / "README.md").read_text(encoding="utf-8")
    assert SECTION in text, f"README.md ohne Abschnitt {SECTION!r}"
    section = text.split(SECTION, 1)[1].split("\n## ", 1)[0]
    return [found.groupdict() for found in map(ROW.match, section.splitlines()) if found]


def app_boards() -> list[str]:
    """Boards of the page App; the page Webseite belongs to the website repo, its sources are not here."""
    boards = json.loads((SOURCES / "canvas.json").read_text(encoding="utf-8"))["boards"]
    return [name for name, board in boards.items() if board.get("page", "app") == "app"]


def test_every_source_and_picture_is_listed_and_every_listed_file_exists():
    rows = listed_rows()

    assert sorted(row["source"] for row in rows) == sorted(path.name for path in SOURCES.glob("*.dc.html"))
    assert sorted(row["picture"] for row in rows) == sorted(path.name for path in PICTURES.glob("*.jpg"))


def test_the_screens_a1_to_a11_are_listed_in_order():
    ids = [row["id"] for row in listed_rows() if row["id"] != "Baustein"]

    assert ids == SCREEN_IDS


def test_each_app_board_of_the_canvas_has_its_source():
    assert sorted(app_boards()) == sorted(path.name for path in SOURCES.glob("*.dc.html"))


def test_the_new_set_leaves_the_earlier_sources_in_place():
    for earlier in ("Main.dc.html", "Suche.dc.html", "Bewerbung.dc.html", "Angaben.dc.html", "Einstellungen.dc.html"):
        assert (DESIGN / "seiten" / earlier).read_text(encoding="utf-8") != (SOURCES / earlier).read_text(encoding="utf-8")
