"""The guide explains the layout check of the documents before sending (G51, G52, #237, #305).

„Stellen suchen und bewerben“ says what the check measures and that each finding names document and page and has
„So lassen“; „Häufige Fehler“ quotes the message that keeps the form closed exactly as routes_apply shows it.
"""
from routes_apply import CONFIRM_FIRST
from test_guide_order import body, text

MEASURES = ("letzte Seite", "Überschrift allein am Ende einer Seite", "über den Rand", "über anderen Text")
STEP = "**Unterlagen erstellen und prüfen**"  # the step's name since #321


def _check_sentence() -> str:
    applying = body("Stellen suchen und bewerben", 3)
    # the step is also named where the form is chosen; the check is the sentence that says what the app checks
    found = [sentence for sentence in applying.split(". ") if STEP in sentence and "prüft" in sentence]
    assert found, "Stellen suchen und bewerben nennt die Prüfung unter «Unterlagen erstellen und prüfen» nicht"
    return found[0]


def test_applying_says_what_the_layout_check_measures():
    sentence = _check_sentence()

    for words in MEASURES:
        assert words in sentence, words


def test_applying_says_each_finding_names_document_and_page_and_has_so_lassen():
    applying = body("Stellen suchen und bewerben", 3)

    assert "Jeder Befund nennt das Dokument und die Seite und hat einen Knopf **So lassen**" in applying


def test_common_errors_quote_the_message_exactly_and_say_what_helps():
    errors = body("Häufige Fehler", 3)
    rows = [line for line in errors.split("\n") if line.startswith(f"| „{CONFIRM_FIRST}“ |")]

    assert len(rows) == 1, "Häufige Fehler zitiert CONFIRM_FIRST nicht genau"
    helps = rows[0].split(" | ", 1)[1]
    assert STEP in helps and "**So lassen**" in helps


def test_the_quote_appears_nowhere_else_in_another_wording():
    guide = text()

    assert guide.count("ansehen und mit «So lassen» bestätigen") == guide.count(CONFIRM_FIRST) == 1
