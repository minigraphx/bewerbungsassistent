"""The guide docs/installation.md: links into it resolve and it stays in the format the website renders."""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
GUIDE = ROOT / "docs" / "installation.md"
LINKING = [GUIDE, ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md")),
           ROOT / "bewerbungen" / "README.md", ROOT / "desktop" / "README.md"]
ALLOWED_HTML = re.compile(r"^(<details>|<summary>[^<>]+</summary>|</details>)$")


def without_code(text):
    return re.sub(r"`[^`\n]*`", "", re.sub(r"```.*?```", "", text, flags=re.S))


def heading_id(heading):
    # The website derives ids from the text: lowercase, punctuation dropped, spaces to '-', umlauts kept.
    return re.sub(r"\s", "-", re.sub(r"[^\w\s-]", "", heading.strip().lower()))


def guide_anchors(source):
    text = source.read_text(encoding="utf-8")
    for target in re.findall(r"\]\(([^)\s]+)\)", text):
        if source == GUIDE and target.startswith("#"):
            yield target[1:]
        elif re.search(r"(^|/)installation\.md#", target):
            yield target.split("#", 1)[1]


def test_every_link_into_the_guide_names_an_existing_heading():
    ids = {heading_id(h) for h in re.findall(r"^#{1,6} (.+)$", without_code(GUIDE.read_text(encoding="utf-8")), re.M)}
    broken = [f"{source.relative_to(ROOT)}#{anchor}"
              for source in dict.fromkeys(LINKING) for anchor in guide_anchors(source) if anchor not in ids]

    assert broken == []


def test_the_guide_uses_only_the_html_the_website_accepts():
    text = GUIDE.read_text(encoding="utf-8")
    lines = text.split("\n")
    tags = [line for line in without_code(text).split("\n") if re.search(r"</?[A-Za-z!]", line)]
    summaries_without_blank = [n for n, line in enumerate(lines) if line.startswith("<summary>") and lines[n + 1] != ""]

    assert [line for line in tags if not ALLOWED_HTML.match(line)] == []
    assert summaries_without_blank == [] and text.count("<details>") == text.count("</details>")


def test_the_guide_is_titled_and_written_in_swiss_spelling():
    text = GUIDE.read_text(encoding="utf-8")

    assert text.startswith("# Anleitung\n") and "ß" not in text


def guide_section(heading):
    """The text under a level-3 heading of the guide, up to the next one."""
    text = GUIDE.read_text(encoding="utf-8")
    start = text.index(f"\n### {heading}\n")
    end = text.find("\n### ", start + 1)
    return text[start:end if end != -1 else None]


def test_the_guide_says_how_the_app_is_signed():
    install = guide_section("App installieren")

    assert "noch nicht signiert" not in GUIDE.read_text(encoding="utf-8")
    assert "eigene Signatur des Projekts" in install and "nicht von Apple" in install
    assert "Unter Windows ist die App nicht signiert" in install and "SmartScreen" in install


def test_the_guide_explains_each_signature_message_of_a_macos_update():
    source = (ROOT / "desktop" / "updates_macos.py").read_text(encoding="utf-8")
    messages = re.findall(r'"([^"]*Signatur[^"]*)"', source)
    troubles = guide_section("Häufige Fehler")

    assert len(messages) == 2
    assert [message for message in messages if f"„{message}“" not in troubles] == []


JUMP_LIST = "**Springen zu**"
QUICK_START = "## Schnellstart für Bewerbungen"
JUMP_ENTRY = re.compile(r"^ *- \[([^\]]+)\]\(#([^)\s]+)\)$")


def jump_list(text):
    """(title, anchor) of each entry under „Springen zu“, in order."""
    lines = text[text.index(JUMP_LIST) + len(JUMP_LIST):].lstrip("\n").split("\n")
    entries = []
    for line in lines:
        found = JUMP_ENTRY.match(line)
        if not found:
            break
        entries.append((found.group(1), found.group(2)))
    return entries


def test_the_jump_list_stands_right_before_the_quick_start_and_lists_every_chapter():
    """#252: at phone width the list was far down, after the five pictures; every h2 and h3 is in it."""
    text = GUIDE.read_text(encoding="utf-8")
    entries = jump_list(text)
    chapters = re.findall(r"^#{2,3} (.+)$", without_code(text), re.M)
    after_list = text[text.index(JUMP_LIST):].split("\n\n", 2)[2].lstrip("\n")

    assert after_list.startswith(QUICK_START + "\n")
    assert entries[0] == ("Schnellstart für Bewerbungen", heading_id("Schnellstart für Bewerbungen"))
    assert [title for title, _ in entries] == chapters
    assert [anchor for _, anchor in entries] == [heading_id(chapter) for chapter in chapters]


def test_every_quick_start_step_ends_with_where_to_read_more():
    quick = GUIDE.read_text(encoding="utf-8").split(QUICK_START + "\n", 1)[1].split("\n## ", 1)[0]
    steps = re.split(r"^\d+\. ", quick, flags=re.M)[1:]

    assert len(steps) == 5
    assert [n for n, step in enumerate(steps, 1) if "Mehr unter [" not in step] == []
    assert ("Mehr unter [Stellen suchen und bewerben](#stellen-suchen-und-bewerben) und "
            "[Fertige Dateien verwenden](#fertige-dateien-verwenden).") in steps[4]
