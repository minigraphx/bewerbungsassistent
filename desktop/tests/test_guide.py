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
