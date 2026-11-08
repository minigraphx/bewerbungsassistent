"""The line diff shown before a Markdown file is replaced (G26)."""
from text_diff import line_diff

LONG = "\n".join(f"Zeile {n}" for n in range(1, 21)) + "\n"


def test_same_text_has_no_lines():
    assert line_diff("a\nb\n", "a\nb") == []


def test_changed_line_shows_what_goes_and_what_comes_with_context():
    new = LONG.replace("Zeile 10\n", "Zeile zehn\n")

    lines = line_diff(LONG, new)

    assert lines == [{"art": "luecke", "text": ""},
                     {"art": "gleich", "text": "Zeile 8"}, {"art": "gleich", "text": "Zeile 9"},
                     {"art": "weg", "text": "Zeile 10"}, {"art": "neu", "text": "Zeile zehn"},
                     {"art": "gleich", "text": "Zeile 11"}, {"art": "gleich", "text": "Zeile 12"},
                     {"art": "luecke", "text": ""}]


def test_changes_far_apart_are_separated_by_a_gap():
    new = LONG.replace("Zeile 1\n", "Erste\n").replace("Zeile 20\n", "Letzte\n")

    kinds = [line["art"] for line in line_diff(LONG, new)]

    assert kinds == ["weg", "neu", "gleich", "gleich", "luecke", "gleich", "gleich", "weg", "neu"]


def test_a_new_file_shows_only_added_lines():
    assert line_diff("", "# Titel\n") == [{"art": "neu", "text": "# Titel"}]
