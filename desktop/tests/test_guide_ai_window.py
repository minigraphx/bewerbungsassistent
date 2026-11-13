"""The guide shows the AI as a window, not as a step of the setup (G60, #272).

The quick start names the invitation code as optional and set up through „KI einrichten“; under „App einrichten“ the
section „KI einrichten“ shows the window in docs/bilder/einrichtung-ki.jpg, and nothing speaks of a step KI any more.
"""
from test_guide_order import QUICK, body, sections, text

PICTURE = "](bilder/einrichtung-ki.jpg)"


def test_the_first_quick_step_names_the_code_as_optional_through_ki_einrichten():
    first = body(QUICK, 2).split("\n2. ", 1)[0]

    assert "**KI einrichten**" in first
    assert "falls Sie einen haben, Ihren Einladungscode für die KI" in first
    assert "und nimmt Ihren Einladungscode" not in first


def test_app_einrichten_shows_the_window_with_its_picture():
    setup = body("App einrichten", 3)
    titles = [title for title, _ in sections(4, setup)]

    assert "KI einrichten" in titles and "Schritt 2: KI" not in titles
    window = body("KI einrichten", 4, setup)
    assert PICTURE in window
    for words in ("Einwilligung", "Elternteil", "Einladungscode", "Claude-Abo", "eigenen API-Schlüssel", "Einladungslink",
                  "Schliessen"):
        assert words in window, words


def test_no_step_ki_and_no_ohne_ki_weiter_remain():
    guide = text()

    assert "Ohne KI weiter" not in guide
    assert "#schritt-2-ki" not in guide
    assert "drei kurze Schritte" not in guide.lower()
    assert "Das ist Schritt 2 der Einrichtung." in body("Browser-Erweiterung hinzufügen", 3)
