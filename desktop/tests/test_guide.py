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


def test_the_guide_says_macos_opens_the_app_only_once_it_is_confirmed():
    """#253: macOS does not open the app at all until the person confirms it in the system settings."""
    install = guide_section("App installieren")

    assert ("Darum öffnet macOS sie beim ersten Mal erst, wenn Sie es in den Systemeinstellungen bestätigen."
            in install)
    assert "fragt macOS beim ersten Öffnen einmal nach" not in install


def test_the_guide_explains_each_signature_message_of_a_macos_update():
    source = (ROOT / "desktop" / "updates_macos.py").read_text(encoding="utf-8")
    messages = re.findall(r'"([^"]*Signatur[^"]*)"', source)
    troubles = guide_section("Häufige Fehler")

    assert len(messages) == 2
    assert [message for message in messages if f"„{message}“" not in troubles] == []
