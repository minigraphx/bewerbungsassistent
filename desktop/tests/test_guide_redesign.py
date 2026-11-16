"""The guide shows the redesigned app of 0.5 (#266): its page names, who sets it up for a child, the trial code and help.

The sidebar replaced the menu Mehr; the page Meine Dateien is now Lebenslauf und Dateien with the kinds Zeugnis, Diplom
and Zertifikat (G63); the apprenticeship track calls the page Lehrstellen. A parent or legal guardian sets the app up
for a child, as the consent in the app says (bewerbungen/ai/consent.py). An invitation code is a one-off trial credit of
CHF 5 (G80), requested by e-mail, never handed out by a Begleitperson. The website links the section on the CV for one
application (#118), so its heading stays as it is.
"""
import re

from test_guide_order import QUICK, body, heading_id, sections, text

GUARDIAN = "Elternteil oder gesetzliche Vertretung"
HELP_PAGE = "(https://bewerbungsbegleiter.ch/hilfe.html#kontakt)"
CV_SECTION = "Lebenslauf für eine Stelle erstellen"
CV_ANCHOR = "lebenslauf-für-eine-stelle-erstellen"


def quick_step(number: int) -> str:
    return re.split(r"^\d+\. ", body(QUICK, 2), flags=re.M)[number]


def table_row(section: str, message: str) -> str:
    rows = [line for line in section.splitlines() if line.startswith(f"| „{message}“")]
    assert len(rows) == 1, message
    return rows[0]


def test_the_guide_names_the_pages_of_the_sidebar_and_no_menu_mehr():
    guide = text()

    for old in ("**Mehr**", "Menü **Mehr**", "Meine Dateien", "Stellen suchen**", "Lehrstellen suchen",
                "Arbeitszeugnisse und Zeugnisse", "Kosten der KI", "Erweiterten Einstellungen"):
        assert old not in guide, old
    assert "**Lehrstellen**" in body("Für Lehrstellen", 3)
    assert "Klicken Sie auf **Stellen**" in quick_step(4)


def test_meine_angaben_takes_every_document_in_one_area_and_the_person_corrects_the_kind():
    # G84, #270: the words of the page, so the guide matches what the person sees
    for part in (quick_step(3), body("Angaben erfassen", 3)):
        assert "**Dateien hierher ziehen**" in part and "**Dateien wählen**" in part
        assert "Art" in part and "ändern" in part.lower()
    entering = body("Angaben erfassen", 3)
    for words in ("**Am Namen erkannt**", "**Nicht sicher erkannt, bitte prüfen**", "**Zeugnis**",
                  "**Zertifikat oder Diplom**", "**Entfernen**", "ohne KI"):
        assert words in entering, words


def test_meine_angaben_names_cost_and_time_before_vorbefuellen():
    # G85, #271: the line under the button, before anything goes to the AI
    for part in (quick_step(3), body("Angaben erfassen", 3)):
        before_run = part.split("Dann klicken Sie auf **Vorbefüllen**", 1)[0].split("Erst mit einem Klick", 1)[0]
        assert "Unter" in before_run and "**Vorbefüllen**" in before_run, part
        assert "an die KI gehen" in before_run and "kostet" in before_run and "dauert" in before_run, part
    entering = body("Angaben erfassen", 3)
    for words in ("«2 Dateien gehen an die KI. Etwa CHF 0.04 und 1 Minute.»", "im Guthaben bleibt", "in USD",
                  "mit dem Grund", "**anfordern**"):
        assert words in entering, words


def test_a_parent_or_legal_guardian_sets_the_app_up_for_a_child():
    guide = text()
    intro = guide.split("\n## ", 1)[0]

    assert "Begleitperson" not in guide and "deine Eltern" not in guide
    assert GUARDIAN in intro
    assert GUARDIAN in body("KI einrichten", 4)
    assert GUARDIAN in body("Für Lehrstellen", 3)


def test_the_invitation_code_is_a_trial_credit_requested_by_email():
    need = body("Was Sie brauchen", 3)

    for words in ("Probeguthaben von CHF 5", "per E-Mail", "solange es Codes gibt", "neuen Code an", HELP_PAGE):
        assert words in need, words
    assert "Pilotphase begleitet" not in text()


def test_quick_start_step_one_names_the_code_as_an_optional_trial_credit():
    first = quick_step(1)

    assert "kein Schritt der Einrichtung" in first and "Probeguthaben von CHF 5" in first
    assert "**KI einrichten**" in first and "wann Sie sie brauchen" in first


def test_access_no_longer_valid_points_to_a_new_code():
    row = table_row(body("Häufige Fehler", 3), "Der Zugang zur KI gilt nicht mehr.")

    assert "neuen Einladungscode" in row and "(#hilfe)" in row


def test_help_links_the_contact_page_of_the_website():
    help_section = body("Hilfe", 3)

    assert HELP_PAGE in help_section and "Einladungscode" in help_section


def test_the_cv_for_one_application_has_its_own_section_with_the_picture():
    work = [title for title, _ in sections(3, body("Mit der App arbeiten", 2))]
    assert CV_SECTION in work and heading_id(CV_SECTION) == CV_ANCHOR
    section = body(CV_SECTION, 3)

    for words in ("**Lebenslauf erstellen**", "Stationen", "Reihenfolge", "**Zweispaltig**", "**Einspaltig**",
                  "**Name der Fassung**", "**Lebenslauf übernehmen**", "**Lebenslauf-Variante**", "**Aussehen wählen**",
                  "**Lebenslauf und Dateien**", "alle neuen Lebensläufe", "](bilder/bewerbung.jpg)",
                  "**Vorschau · 2 Seiten**", "**Gross ansehen**", "an die KI geht nichts",
                  "auf dem Handy direkt über **Lebenslauf übernehmen**", "Ist keine Station angehakt",
                  "steht in Meine Angaben etwas, das die App nicht lesen kann"):
        assert words in section, words
    assert "gerade nicht bauen" not in section, "the old wording of a failed preview is gone"
    assert f"(#{CV_ANCHOR})" in quick_step(5)


def test_lebenslauf_und_dateien_shows_the_kinds_zeugnis_diplom_zertifikat():
    files = body("Fertige Dateien verwenden", 3)

    for words in ("**Lebenslauf und Dateien**", "**Ich nehme mein eigenes PDF**", "**Zeugnisse und Zertifikate**",
                  "**Zeugnis**", "**Diplom**", "**Zertifikat**", "](bilder/meine-dateien.jpg)"):
        assert words in files, words


def test_suche_einstellen_says_the_order_of_the_terms_and_how_to_change_it():
    # G87, #285: from the top, new ones at the end, by dragging or with the arrows, also with the keyboard
    for part, term in ((body("Stellen suchen und bewerben", 3), "Begriff"), (body("Für Lehrstellen", 3), "Beruf")):
        assert "von oben nach unten" in part and "die wichtigsten zuerst" in part, part
        assert f"ein neuer {term} kommt ans Ende" in part, part
        assert "an seinen Platz" in part and "Pfeilen" in part and "Tastatur" in part, part
        assert "der frühere Stand bleibt als Entwurf erhalten" in part, part
    # the list itself carries the order, so Meine Angaben and the rating see it too
    assert "Die Reihenfolge ist auch die Priorität deiner Berufe" in body("Für Lehrstellen", 3)


def test_the_pictures_say_what_they_show_today():
    guide = text()

    # G84, #270: one drop area, each file with its kind to correct
    assert "mit einer Fläche Dateien hierher ziehen und dem Knopf Dateien wählen" in guide
    assert "jede mit ihrer Art zum Ändern und Entfernen" in guide and "](bilder/angaben.jpg)" in guide
    picture = guide.split("](bilder/angaben.jpg)", 1)[0].rsplit("![", 1)[1]
    assert "gleich nach dem Hinzufügen" in picture
    assert "dem Hinweis «Am Namen erkannt» oder, beim Scan, «Nicht sicher erkannt, bitte prüfen»" in picture
    # G85, #271: the picture goes on to the line under Vorbefüllen
    assert "dem Knopf Vorbefüllen und darunter der Zeile «3 Dateien gehen an die KI. Etwa CHF 0.09 und 1 Minute.»" in picture
    assert "was im Guthaben bleibt" in picture and "welche Datei nicht an die KI geht" in picture
    check = body("Stellen suchen und bewerben", 3)
    assert "](bilder/pruefung.jpg)" in check and "**So lassen**" in check
    picture = check.split("](bilder/pruefung.jpg)", 1)[0].rsplit("![", 1)[1]
    # G92, #323: a CV too long shows cuts to tick instead of So lassen
    assert "Lebenslauf: 3 Seiten" in picture and "Gekürzt neu erstellen" in picture
    assert "Drei Seiten erlauben" in picture and "So lassen" not in picture
    assert "**Gekürzt neu erstellen**" in check and "**Zurückholen**" in check
    assert "**Drei Seiten erlaubt, nur für diese Bewerbung.** mit **Zurücknehmen**" in check
    assert "**Zurücknehmen** bei **Drei Seiten erlaubt** gilt wieder die Grenze von zwei Seiten." in check
    assert "die nächste Kürzung ist angehakt.**" in check and "Meine Angaben und Varianten bleiben" in check
    assert "Schliessen" not in picture and "×" not in picture
    # G93, #324: each tile names its pages and how the app balanced them
    assert "beim Anschreiben 1 Seite · etwas enger gesetzt" in picture
    assert "**1 Seite · etwas enger gesetzt**" in check and "**7 Seiten · Lebenslauf etwas enger gesetzt**" in check
    assert "damit keine Seite fast leer bleibt und die Seitenzahl eingehalten wird" in check
    # G96, #333: a CV too long even at its tightest stays as tight as possible, like the letter
    assert ("Ein zu langer Lebenslauf bleibt wie ein zu langes Anschreiben so eng wie möglich gesetzt, etwa "
            "**5 Seiten · so eng wie möglich**.") in check
    assert "Passt ein Lebenslauf auch so eng wie möglich nicht" not in check
    assert "beim Lebenslauf 3 Seiten · so eng wie möglich" in picture
    assert "Ist der Lebenslauf auch so eng wie möglich gesetzt zu lang, nennt der Befund" in check
    # G94, #325: a letter over one page stays as tight as possible, cut in the letter or left as it is
    assert "Ein zu langes Anschreiben bleibt so eng gesetzt, etwa **2 Seiten · so eng wie möglich**." in check
    assert ("**Im Anschreiben kürzen** führt zum Schritt **Anschreiben**, wo über dem längsten Absatz **Längster Absatz** "
            "steht; **Anschreiben ändern** gleich daneben öffnet den Text.") in check
    assert "**So lassen** verwendet das Anschreiben so, wie es ist. Gekürzt wird es nur von Ihnen." in check
    # the picture shows natural invented stations, not the generated ones of the tests
    assert "Projektleiterin Daten" not in picture and "Muster Informatik 0" not in picture
    assert "3 Stichpunkte bei «Datenanalystin, Aare Versicherungen AG» (2013–2015)" in picture
