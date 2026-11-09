"""The FAQ answers whether several people can use the app (#198) and points to the guide for switching."""
import re

from test_faq import FAQ, faq, github_slug, headings

QUESTION = "Können mehrere Personen die App nutzen?"
GUIDE = FAQ.parent / "installation.md"
GUIDE_LINK = "[Mehrere Personen](installation.md#mehrere-personen)"


def answer() -> str:
    section = faq().split(f"## {QUESTION}\n", 1)[1]
    return re.split(r"\n#{1,6}\s", section, maxsplit=1)[0]


def guide_slugs() -> set[str]:
    lines = GUIDE.read_text(encoding="utf-8").splitlines()
    return {github_slug(line.lstrip("#").strip()) for line in lines if re.match(r"#{1,6}\s", line)}


def test_the_question_is_a_plain_heading_in_the_table_of_contents():
    assert QUESTION in headings()
    assert f"- [{QUESTION}](#{github_slug(QUESTION)})" in faq()


def test_the_answer_links_the_guide_chapter_on_switching():
    assert GUIDE_LINK in answer()
    assert "mehrere-personen" in guide_slugs()


def test_the_answer_says_what_the_guide_says():
    text = answer()
    assert "eigenen Datenordner" in text
    assert "eigenes Benutzerkonto" in text
    assert "denselben Zugang" in text
