"""The guide starts with the goal (#223, UX finding 14): five steps to the first application, technical parts later.

docs/installation.md opens with „Schnellstart für Bewerbungen“ (#235, no time promise), five numbered steps from installing to the first
application, each with one picture. Data folder, updates, several people and Linux stand under „Bei Bedarf“, and the
names of files only under „Für Geübte“.
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
GUIDE = ROOT / "docs" / "installation.md"
QUICK = "Schnellstart für Bewerbungen"
TOP_LEVEL = [QUICK, "Einmal einrichten", "Mit der App arbeiten", "Bei Bedarf"]
LATER = ["Updates", "Mehrere Personen", "Datenordner", "Unter Linux", "Für Geübte"]
# Headings the website links to; its build fails on a dead anchor.
KEPT_IDS = ("app-installieren", "mehrere-personen", "für-geübte")
PICTURE = re.compile(r"!\[[^\]]*\]\((bilder/[^)\s]+)\)")
FILE_NAME = re.compile(r"`[^`\n]*?(?<!:/)(?:\b[\w*<>-]+\.(?:yaml|yml|json|jsonl|md|pdf|zip|exe|app|AppImage|txt|jpg|png)\b"
                       r"|\b[\w.-]+/(?=[`\s<]))[^`\n]*`")


def text() -> str:
    return GUIDE.read_text(encoding="utf-8")


def sections(level: int, source: str) -> list[tuple[str, str]]:
    """(heading, body) for each heading of exactly this level, the body up to the next heading of this level or above."""
    marks = "#" * level
    parts = re.split(rf"^(#{{1,{level}}}) (.+)$", source, flags=re.M)
    found = []
    for index in range(1, len(parts), 3):
        if parts[index] == marks:
            found.append((parts[index + 1].strip(), parts[index + 2]))
    return found


def body(heading: str, level: int, source: str | None = None) -> str:
    matches = [content for title, content in sections(level, source or text()) if title == heading]
    assert matches, f"{'#' * level} {heading} fehlt"
    return matches[0]


def heading_id(heading: str) -> str:
    return re.sub(r"\s", "-", re.sub(r"[^\w\s-]", "", heading.strip().lower()))


def test_the_guide_starts_with_the_way_to_the_first_application():
    assert [title for title, _ in sections(2, text())] == TOP_LEVEL
    intro = text().split("\n## ", 1)[0]
    assert "Springen zu" not in intro, "the steps come before the table of contents"


def test_five_numbered_steps_each_with_one_picture_that_exists():
    quick = body(QUICK, 2)
    steps = re.split(r"^\d+\. ", quick, flags=re.M)[1:]
    numbers = re.findall(r"^(\d+)\. ", quick, flags=re.M)

    assert numbers == ["1", "2", "3", "4", "5"]
    for number, step in zip(numbers, steps):
        pictures = PICTURE.findall(step)
        assert len(pictures) == 1, f"step {number} has {len(pictures)} pictures"
    assert "installier" in steps[0].lower() and "abschick" in steps[4].lower()


def test_every_picture_of_the_guide_exists():
    pictures = PICTURE.findall(text())
    assert pictures and [p for p in pictures if not (GUIDE.parent / p).is_file()] == []


def test_data_folder_updates_several_people_and_linux_stand_under_bei_bedarf():
    later = [title for title, _ in sections(3, body("Bei Bedarf", 2))]
    assert [title for title in later if title in LATER] == LATER
    for title, content in sections(3, body("Einmal einrichten", 2)) + sections(3, body("Mit der App arbeiten", 2)):
        assert "AppImage" not in content and "Ubuntu" not in content, f"Linux details under {title}"
    assert "#### Was im Datenordner liegt" in body("Für Geübte", 3)


def test_file_names_appear_only_under_fuer_geuebte():
    source = text()
    expert = body("Für Geübte", 3)
    outside = source.replace(expert, "")
    named = FILE_NAME.findall(outside)

    assert named == []
    assert FILE_NAME.search(expert), "the file names moved, they did not vanish"


def test_the_headings_the_website_links_to_are_kept():
    ids = {heading_id(h) for h in re.findall(r"^#{1,6} (.+)$", text(), re.M)}
    assert set(KEPT_IDS) <= ids


def test_the_quick_start_promises_no_time_and_nothing_links_to_its_old_anchor():
    """#235: the website guide build takes no inline HTML anchor, and nothing points to the old title."""
    assert "15 Minuten" not in text()
    assert "<a id=" not in text()
    for path in ROOT.rglob("*.md"):
        if ".git" not in path.parts and "node_modules" not in path.parts:
            assert "#in-15-minuten-zur-ersten-bewerbung" not in path.read_text(encoding="utf-8"), path


def test_the_guide_says_pilotphase_like_the_website():
    assert "im Pilot " not in text() and "im Pilot." not in text() and "im Pilot," not in text()


def test_the_guide_explains_suchbegriffe_pruefen_with_the_names_of_the_app():
    """#231: the hint and the view of #210, in the words the app uses."""
    work = [title for title, _ in sections(3, body("Mit der App arbeiten", 2))]
    assert "Suchbegriffe prüfen" in work
    section = body("Suchbegriffe prüfen", 3)
    for name in ("Ein Begriff lässt viel Unpassendes durch", "Suchbegriffe prüfen lassen", "Ausblenden", "Text ansehen",
                 "Neu vorschlagen", "Rückgängig machen", "Entwürfe und Versionen", "Was geht an die KI?"):
        assert f"**{name}**" in section, name
    assert "nur, was Sie" in section and "übernehmen" in section
