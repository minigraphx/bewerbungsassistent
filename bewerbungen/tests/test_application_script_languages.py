"""The main script of the application page and its check in French and English (#427, G10, docs/design/sprachen.md).

With the preview on and French or English as the app language, the routes behind the page answer in it: the findings
of the check before sending, why documents cannot be built, the variants, the suggested certificates and why a form
cannot open after the check. With the preview off it all stays German, byte for byte. Data stays German inside French
and English: firm, job, the words a letter uses and file names. What the scripts of the page say at run time is
tested in tests/application_script_languages.test.cjs. All data is invented.
"""
import datetime
import threading

import pytest

import app
import certificates
import cuts
import layout_check
import pruefung
import sprachen_pruefen
import translation_catalog
import unterlagen
import varianten
from test_today_languages import no_preview, preview, request, store_language  # noqa: F401  (fixtures)

NBSP = chr(0xA0)
TODAY = datetime.date(2026, 11, 20)
REGISTER = """\
- id: muster-ag-planer
  firma: Muster AG
  stelle: Planer:in Hochbau
  status: Bewerben
  eingetragen_am: '2026-11-01'
  link: https://www.example.org/stelle/1
- id: probe-ag-sent
  firma: Probe AG
  stelle: Disponent:in
  status: Beworben
  eingetragen_am: '2026-11-01'
  beworben_am: '2026-11-02'
  versand:
    datum: '2026-11-02'
    art: elektronisch
"""
SCRIPT_FILES = ("seiten/bewerbung.js", "seiten/ki.js", "seiten/firma-ausschliessen.js", "seiten/eigenes-anschreiben.js",
                "seiten/dateien-ordner.js")
# The check and its confirmation, building the documents, the variants and the certificates the page offers;
# routen_bewerbungen and routes_apply, whose routes call them, are finished already (#419, #420).
MODULE_FILES = ("pruefung.py", "layout_check.py", "layout_confirmed.py", "unterlagen.py", "varianten.py",
                "certificates.py", "routes_certificates.py", "routen_bewerbungen.py", "routes_apply.py")
CV_MISSING = {
    "de": "Lebenslauf: PDF fehlt (lebenslauf.pdf). Zuerst die Unterlagen erstellen.",
    "fr": f"CV{NBSP}: PDF manquant (lebenslauf.pdf). Créer d'abord les documents.",
    "en": "CV: PDF missing (lebenslauf.pdf). Create the documents first.",
}
NO_LETTER = {
    "de": "Kein Anschreiben: weder ein Entwurf noch ein eigenes PDF",
    "fr": f"Pas de lettre de motivation{NBSP}: ni brouillon ni PDF téléversé",
    "en": "No cover letter: neither a draft nor an uploaded PDF",
}
NO_CV = {
    "fr": (f"Pas encore de CV. Merci de le saisir sous «{NBSP}Mes informations{NBSP}» ou de le téléverser en PDF sous "
           f"«{NBSP}CV et fichiers{NBSP}»."),
    "en": "No CV yet. Please enter it under “My details” or upload it as a PDF under “CV and files”.",
}
LETTER = """Muster AG
Musterstrasse 1
8000 Zürich

Zürich, 18. November 2026

Bewerbung als Planerin

Sehr geehrte Damen und Herren

Gerne bewerbe ich mich. Wie geht es euch? TODO
"""


@pytest.fixture
def started(tmp_path):
    """The app on a data folder with an open and a sent invented application, without any PDF or CV."""
    folder = tmp_path / "daten"
    folder.mkdir()
    (folder / "bewerbungen.yaml").write_text(REGISTER, encoding="utf-8")
    server = app.erstelle_server(folder, tmp_path / "build")
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    yield server, folder
    server.shutdown()
    server.server_close()


def catalog() -> translation_catalog.Catalog:
    return translation_catalog.load(translation_catalog.CATALOG_DIR)


def said(message, language: str) -> str:
    return str(message) if language == "de" else message.in_language(catalog(), language)


def findings(server) -> list[str]:
    status, answer = request(server, "GET", "/api/pruefung?id=muster-ag-planer")
    assert status == 200, answer
    return [finding["text"] for finding in answer["befunde"]]


def refused(server, method: str, path: str, body: dict | None = None) -> str:
    status, answer = request(server, method, path, body)
    assert status == 400, answer
    return answer["fehler"]


# The files of this step


def test_the_scripts_and_the_modules_behind_the_check_are_finished():
    finished = {str(path.relative_to(sprachen_pruefen.BASE)) for path in sprachen_pruefen.FERTIG
                if path.is_relative_to(sprachen_pruefen.BASE)}

    assert set(SCRIPT_FILES) | set(MODULE_FILES) <= finished


def test_the_scripts_and_the_modules_behind_the_check_have_no_gap():
    files = [sprachen_pruefen.BASE / name for name in (*SCRIPT_FILES, *MODULE_FILES)]

    assert [str(gap) for gap in sprachen_pruefen.gaps(files, catalog())] == []


def test_the_text_sets_the_main_script_uses_are_in_the_catalog():
    sets = ("bewerbung.inserat", "bewerbung.eigenes", "bewerbung.versand", "bewerbung.jobroom", "bewerbung.warten",
            "bewerbung.absage", "bewerbung.freigeben", "bewerbung.kuerzen", "kuerzen.hinweis",
            "bewerbung.freigeben-offen", "bewerbung.freigeben-offen-eins", "bewerbung.geoeffnet",
            "bewerbung.jobroom-offen", "bewerbung.variante-waehlen", "versand.erfasst-hinweis",
            "versand.erfasst-hinweise")

    missing = [(key, language) for key in sets for language in ("fr", "en")
               if not catalog().form(key, language, "sie")]

    assert missing == []


# The findings of the check through its route


def test_the_findings_of_the_check_come_in_french(started, preview):
    server, folder = started
    store_language(folder, "fr")

    assert findings(server) == [CV_MISSING["fr"], NO_LETTER["fr"]]


def test_the_findings_of_the_check_come_in_english(started, preview):
    server, folder = started
    store_language(folder, "en")

    assert findings(server) == [CV_MISSING["en"], NO_LETTER["en"]]


def test_the_findings_of_the_check_stay_german_with_the_preview_off(started, no_preview):
    server, folder = started
    store_language(folder, "fr")

    assert findings(server) == [CV_MISSING["de"], NO_LETTER["de"]]


# The findings in the letter: firm, job, date and the words of the letter stay as they are


@pytest.mark.parametrize("language", ["de", "fr", "en"])
def test_the_findings_in_the_letter_name_firm_job_and_date_as_they_are(language):
    entry = {"firma": "Muster AG", "stelle": "Planer:in Hochbau"}

    shown = [said(b.text, language) for b in pruefung.pruefe_anschreiben_text(LETTER, entry, TODAY)]

    assert shown == {
        "de": ["Anschreiben: Firma „Muster“ genannt", "Anschreiben: Stellentitel genannt",
               "Anschreiben: Datum 18.11.2026", "Anschreiben: Anrede in Sie-Form, im Text aber euch/eure/ihr",
               "Anschreiben: Platzhalter gefunden (TODO)"],
        "fr": [f"Lettre de motivation{NBSP}: entreprise «{NBSP}Muster{NBSP}» nommée",
               f"Lettre de motivation{NBSP}: titre du poste mentionné",
               f"Lettre de motivation{NBSP}: date 18.11.2026",
               f"Lettre de motivation{NBSP}: formule d'appel au vouvoiement (Sie), mais le texte dit euch/eure/ihr",
               f"Lettre de motivation{NBSP}: espace réservé trouvé (TODO)"],
        "en": ["Cover letter: company “Muster” named","Cover letter: job title named",
               "Cover letter: date 18.11.2026", "Cover letter: formal salutation (Sie), but the text says euch/eure/ihr",
               "Cover letter: placeholder found (TODO)"],
    }[language]


def test_a_missing_firm_and_an_old_date_are_said_in_french_and_english():
    entry = {"firma": "Beispiel GmbH (über ONE Agency)", "stelle": "Kurs"}
    letter = "Hallo zusammen\n\nZürich, 1. Oktober 2026\n\nIch schreibe Ihnen gerne."

    shown = {language: [said(b.text, language) for b in pruefung.pruefe_anschreiben_text(letter, entry, TODAY)]
             for language in ("de", "fr", "en")}

    assert shown["de"][0] == "Anschreiben: Firma „Beispiel / ONE Agency“ kommt nicht vor – falsche Vorlage?"
    assert shown["fr"][0] == (f"Lettre de motivation{NBSP}: l'entreprise «{NBSP}Beispiel / ONE Agency{NBSP}» n'apparaît "
                              f"pas – mauvais modèle{NBSP}?")
    assert shown["en"][0] == "Cover letter: company “Beispiel / ONE Agency” does not appear – wrong template?"
    assert shown["fr"][2] == f"Lettre de motivation{NBSP}: la date 01.10.2026 n'est pas actuelle"
    assert shown["en"][2] == "Cover letter: date 01.10.2026 is not current"
    assert shown["en"][3] == "Cover letter: informal salutation (du), but the text says Sie/Ihnen/Ihre"


def test_the_contact_person_keeps_title_and_name_german():
    [wrong] = pruefung.check_contact_person(["Muster AG", "Frau Erika Beispiel"], "Sehr geehrter Herr Beispiel")
    [missing] = pruefung.check_contact_person(["Muster AG", "Frau Erika Beispiel"], "Guten Tag")
    [fits] = pruefung.check_contact_person(["Muster AG", "Frau Erika Beispiel"], "Sehr geehrte Frau Beispiel")

    assert str(wrong.text) == "Anschreiben: Form der Anrede „Sehr geehrter Herr Beispiel“ passt nicht zu Frau Beispiel"
    assert said(wrong.text, "fr") == (f"Lettre de motivation{NBSP}: la forme de la formule d'appel «{NBSP}Sehr geehrter "
                                      f"Herr Beispiel{NBSP}» ne correspond pas à Frau Beispiel")
    assert said(missing.text, "en") == "Cover letter: the address names Frau Beispiel, the salutation “Guten Tag” does not"
    assert said(fits.text, "en") == "Cover letter: salutation fits Frau Beispiel"


def test_an_unreadable_pdf_and_a_page_over_the_limit_are_said_in_the_app_language(tmp_path):
    broken = tmp_path / "lebenslauf.pdf"
    broken.write_bytes(b"%PDF-1.4 invented and broken")

    [unreadable] = pruefung.pruefe_pdf(broken, "lebenslauf")
    over_one = pruefung._over_limit("anschreiben", 2, 1, as_it_is=True)
    over_eight = pruefung._over_limit("dossier", 9, 8, as_it_is=False)

    assert str(unreadable.text).startswith("Lebenslauf: PDF lässt sich nicht lesen (")
    assert said(unreadable.text, "fr").startswith(f"CV{NBSP}: le PDF est illisible (")
    assert said(unreadable.text, "en").startswith("CV: the PDF cannot be read (")
    assert str(over_one.text) == "Anschreiben: 2 Seiten, empfohlen höchstens 1 Seite(n)"
    assert said(over_one.text, "fr") == f"Lettre de motivation{NBSP}: 2 pages, 1 page au maximum recommandée"
    assert said(over_one.text, "en") == "Cover letter: 2 pages, at most 1 page recommended"
    assert said(over_eight.text, "en") == "Dossier: 9 pages, at most 8 pages recommended"


def test_a_letter_over_one_page_names_its_longest_paragraph_by_its_own_words():
    letter = "Kurz.\n\nDieser Absatz ist deutlich länger als der erste und der letzte.\n\nEnde."
    opening = cuts.letter_opening(letter)
    text = pruefung.over_letter_text(pages=2, lines=3, opening=opening)

    assert cuts.for_letter(letter) == [f"der längste Absatz («{opening}»)"]
    assert str(text) == ("Anschreiben: 2 Seiten, erlaubt ist eine. Auch so eng wie möglich gesetzt sind es etwa 3 Zeilen "
                         "zu viel. Am meisten bringt der längste Absatz («Dieser Absatz ist deutlich länger …»).")
    assert said(text, "fr") == (f"Lettre de motivation{NBSP}: 2 pages, une seule est autorisée. Même avec la mise en page la "
                                "plus serrée, il y a environ 3 lignes de trop. Le plus efficace est de raccourcir le "
                                f"paragraphe le plus long («{NBSP}Dieser Absatz ist deutlich länger …{NBSP}»).")
    assert said(text, "en") == ("Cover letter: 2 pages, one is allowed. Even set as tightly as possible, it is about 3 lines "
                                "too long. Shortening the longest paragraph (“Dieser Absatz ist deutlich länger …”) "
                                "helps most.")
    assert said(pruefung.over_letter_text(pages=2, lines=1, opening=None), "en") == (
        "Cover letter: 2 pages, one is allowed. Even set as tightly as possible, it is about 1 line too long.")


def test_the_breaches_of_the_layout_quote_the_text_of_the_pdf_as_it_is():
    fill = layout_check.Breach(2, "fuellung", layout_check.fill_reason(0.2))
    heading = layout_check.Breach(1, "ueberschrift", layout_check.lone_heading_reason("Berufserfahrung"))

    assert str(fill.reason) == "nur zu 20 % gefüllt, verlangt ist mindestens ein Drittel."
    assert said(fill.reason, "fr") == f"remplie à 20{NBSP}% seulement, au moins un tiers est requis."
    assert said(fill.reason, "en") == "only 20% full, at least a third is required."
    assert said(heading.reason, "fr") == (f"Le titre «{NBSP}Berufserfahrung{NBSP}» est seul en bas de la page.")
    assert said(heading.reason, "en") == "The heading “Berufserfahrung” stands alone at the foot of the page."


def test_a_breach_found_in_a_pdf_names_document_and_page_in_the_app_language(tmp_path, monkeypatch):
    pdf = tmp_path / "anschreiben.pdf"
    pdf.write_bytes(b"%PDF-1.4 invented")
    breach = layout_check.Breach(2, "rand", layout_check.margin_reason("Mit freundlichen Grüssen"))
    monkeypatch.setattr(layout_check, "check", lambda *args, **kwargs: [breach])

    [finding] = pruefung.layout_findings(pdf, "anschreiben")

    assert str(finding.text) == "Anschreiben, Seite 2: Text ragt in den Rand des Designs hinein («Mit freundlichen Grüssen»)."
    assert said(finding.text, "fr") == (f"Lettre de motivation, page 2{NBSP}: Du texte déborde dans la marge du design "
                                        f"(«{NBSP}Mit freundlichen Grüssen{NBSP}»).")
    assert said(finding.text, "en") == ("Cover letter, page 2: Text reaches into the margin of the design "
                                        "(“Mit freundlichen Grüssen”).")


# Building the documents, the variants and the certificates


def test_building_the_documents_is_refused_in_french_and_english(started, preview):
    server, folder = started

    store_language(folder, "fr")
    assert refused(server, "POST", "/api/unterlagen?id=muster-ag-planer", {}) == NO_CV["fr"]
    assert refused(server, "POST", "/api/unterlagen?id=probe-ag-sent", {}) == (
        "Cette candidature a été envoyée. Ce qui est parti reste tel quel.")
    store_language(folder, "en")
    assert refused(server, "POST", "/api/unterlagen?id=muster-ag-planer", {}) == NO_CV["en"]


def test_building_the_documents_is_refused_in_german_with_the_preview_off(started, no_preview):
    server, folder = started
    store_language(folder, "fr")

    assert refused(server, "POST", "/api/unterlagen?id=muster-ag-planer", {}) == (
        "Noch kein Lebenslauf. Bitte unter „Meine Angaben“ erfassen oder unter „Lebenslauf und Dateien“ als PDF hochladen.")


def test_a_variant_that_is_not_there_keeps_its_name(tmp_path):
    with pytest.raises(KeyError) as raised:
        varianten.Varianten(tmp_path).hole("kurs-2026")

    message = raised.value.args[0]
    assert str(message) == "Variante 'kurs-2026' nicht gefunden"
    assert said(message, "fr") == "Variante 'kurs-2026' introuvable"
    assert said(message, "en") == "Variant 'kurs-2026' not found"


def test_a_suggested_certificate_names_its_word_from_the_ad():
    [suggestion] = certificates.suggest(["zertifikate/Excel-Kurs.pdf"], "Sie kennen Excel sehr gut.")

    assert str(suggestion["grund"]) == "Excel: steht im Inserat"
    assert said(suggestion["grund"], "fr") == f"Excel{NBSP}: figure dans l'annonce"
    assert said(suggestion["grund"], "en") == "Excel: in the ad"


# Why a form cannot open after the check (routes_apply._problem)


def _with_broken_cv(folder) -> None:
    cv = folder / "bewerbungen" / "muster-ag-planer" / "lebenslauf.pdf"
    cv.parent.mkdir(parents=True)
    cv.write_bytes(b"%PDF-1.4 invented and broken")


def test_a_form_refused_by_the_check_says_why_in_french_and_english(started, preview):
    server, folder = started
    _with_broken_cv(folder)

    store_language(folder, "fr")
    status, french = request(server, "POST", "/api/bewerben/start", {"ids": ["muster-ag-planer"]})
    store_language(folder, "en")
    english = request(server, "POST", "/api/bewerben/start", {"ids": ["muster-ag-planer"]})[1]

    assert status == 200
    assert french["abgelehnt"][0]["grund"].startswith(f"Vérification{NBSP}: CV{NBSP}: le PDF est illisible (")
    assert english["abgelehnt"][0]["grund"].startswith("Check: CV: the PDF cannot be read (")


def test_a_form_refused_by_the_check_stays_german_with_the_preview_off(started, no_preview):
    server, folder = started
    _with_broken_cv(folder)
    store_language(folder, "fr")

    answer = request(server, "POST", "/api/bewerben/start", {"ids": ["muster-ag-planer"]})[1]

    assert answer["abgelehnt"][0]["grund"].startswith("Prüfung: Lebenslauf: PDF lässt sich nicht lesen (")


# The wording the brief fixes and the plain messages the server matches as a whole


REVIEWED = {
    "Diese Bewerbung ist versendet. Was verschickt wurde, bleibt so.": (
        "Cette candidature a été envoyée. Ce qui est parti reste tel quel.",
        "This application has been sent. What went out stays as it is."),
    "Diese Meldung gibt es nicht mehr. Bitte erneut prüfen.": (
        "Ce message n'existe plus. Merci de vérifier à nouveau.", "This message no longer exists. Please check again."),
    "Note übernehmen": ("Appliquer la note", "Apply the grade"),
    "Notiz gespeichert": ("Mémo enregistré", "Note saved"),
    "Anschreiben freigegeben": ("Lettre de motivation validée", "Cover letter approved"),
}
# The UI/UX ruling on #427: Stand is a status, the uploaded letter is uploaded, the start page is Today, English names
# what was sent rather than a dispatch, and French counts what is supported before the whole.
RULED = {
    "Stand: {stand}": (f"Statut{NBSP}: {{stand}}", "Status: {stand}"),
    "{stelle}, Stand {stand}.": ("{stelle}, statut {stand}.", "{stelle}, status {stand}."),
    "Nicht bewerben: Die Bewerbung bleibt mit dem Stand „Verworfen“ in der Liste.": (
        f"Ne pas postuler{NBSP}: la candidature reste dans la liste avec le statut «{NBSP}Écartée{NBSP}».",
        "Do not apply: the application stays in the list with the status “Discarded”."),
    "Die Bewerbung nicht weiterverfolgen: Sie bleibt mit dem Stand „Zurückgezogen“ in der Liste.": (
        f"Ne pas poursuivre la candidature{NBSP}: elle reste dans la liste avec le statut «{NBSP}Retirée{NBSP}».",
        "Stop pursuing the application: it stays in the list with the status “Withdrawn”."),
    "Versand festhalten": ("Consigner l'envoi", "Record what was sent"),
    ("Beworben am {datum}, aber der Versand ist noch nicht festgehalten. «Versand erfassen» legt die Fassung ab, die "
     "verschickt wurde."): (
        (f"Candidature envoyée le {{datum}}, mais l'envoi n'est pas encore consigné. «{NBSP}Enregistrer l'envoi{NBSP}» "
         "conserve la version qui a été envoyée."),
        "Applied on {datum}, but what was sent is not recorded yet. “Record as sent” keeps the version that was sent."),
    "Wirklich erfassen? Nochmals klicken": (
        f"Vraiment enregistrer l'envoi{NBSP}? Cliquer encore une fois", "Really record as sent? Click again"),
    "Passt": ("Ce qui correspond", "What fits"),
    "Passt: {liste}": (f"Ce qui correspond{NBSP}: {{liste}}", "Matches: {liste}"),
    "0 von 1 Anforderungen belegt": ("0 exigence justifiée sur 1", "0 of 1 requirement supported"),
    "1 von 1 Anforderungen belegt": ("1 exigence justifiée sur 1", "1 of 1 requirement supported"),
    "1 von {anzahl} Anforderungen belegt": ("1 exigence justifiée sur {anzahl}", "1 of {anzahl} requirements supported"),
    "{belegt} von {anzahl} Anforderungen belegt": (
        "{belegt} exigences justifiées sur {anzahl}", "{belegt} of {anzahl} requirements supported"),
    "Abgabe bis {datum}": ("À envoyer d'ici le {datum}", "Due by {datum}"),
    "Eigenes Anschreiben verwenden": ("Utiliser une lettre de motivation téléversée", "Use an uploaded cover letter"),
    "Eigenes Anschreiben hochladen": ("Téléverser une lettre de motivation", "Upload a cover letter"),
    unterlagen.DOSSIER_OWN_FILE: (
        (f"Un dossier se crée à partir de «{NBSP}Mes informations{NBSP}» et du brouillon de la lettre de motivation, "
         f"pas d'un PDF terminé. Merci de choisir «{NBSP}Lettre de motivation et CV{NBSP}» ou de retirer le PDF "
         "téléversé."),
        ("A dossier is made from “My details” and the draft of the cover letter, not from a finished PDF. Please "
         "choose “Cover letter and CV” or remove the uploaded PDF.")),
    "Den Termin bei den Angaben eintragen, dann steht er hier und in der Übersicht.": (
        f"Saisir la date dans les informations{NBSP}; elle apparaît alors ici et sur la page Aujourd'hui.",
        "Enter the date in the details; it then shows here and on the Today page."),
    "Antwort abwarten": ("Attendre la réponse", "Wait for the reply"),
    "Die Antwort lässt sich unten eintragen, sobald sie kommt.": (
        "La réponse peut être saisie plus bas dès qu'elle arrive.", "The reply can be entered below as soon as it comes."),
    "Unterlagen ansehen": ("Examiner les documents", "Review the documents"),
    "Offen benannte Lücken": ("Lacunes mentionnées ouvertement", "Gaps stated openly"),
}


@pytest.mark.parametrize("german", RULED)
def test_the_wording_of_the_ui_ux_ruling_is_in_the_catalog(german):
    assert (catalog().text(german, "fr"), catalog().text(german, "en")) == RULED[german]


def test_a_variant_without_a_source_names_the_remark_in_english():
    with pytest.raises(ValueError) as raised:
        varianten.pruefe_variante({"id": "kurs"})

    assert str(raised.value) == "Es braucht quelle (Zuschnitt), datei (PDF) oder extern (Hinweis)"
    assert catalog().text(str(raised.value), "en") == "It needs quelle (tailoring), datei (PDF) or extern (remark)"


@pytest.mark.parametrize("german", REVIEWED)
def test_the_reviewed_wording_is_in_the_catalog(german):
    assert (catalog().text(german, "fr"), catalog().text(german, "en")) == REVIEWED[german]
