"""The page of one application and its steps in French and English (#426, G10, docs/design/sprachen.md).

With the preview on and French or English as the app language, the page /bewerbung comes with its steps, cards,
dialogs and buttons in that language, and the routes behind its steps answer in it: why a form cannot open yet, the
approval of the letter, the folder of files and recording the dispatch. With the preview off it all stays German, byte
for byte. Stored values stay German in every language: the stage, the kind of dispatch, firm and job. What the scripts
of the page say at run time is tested in tests/application_page_languages.test.cjs. All data is invented.
"""
import threading

import pytest

import app
import apply
import form_copy
import server as server_module
import sprachen_pruefen
import translation_catalog
import unterlagen
import versand
from test_today_languages import connect, no_preview, preview, request, store_language  # noqa: F401  (fixtures)

PAGE = "/bewerbung"
NBSP = chr(0xA0)
REGISTER = """\
- id: muster-ag-planer
  firma: Muster AG
  stelle: Planer:in
  status: Bewerben
  eingetragen_am: '2026-11-01'
- id: beispiel-gmbh-kurs
  firma: Beispiel GmbH
  stelle: Kursleiter:in
  status: Bewerben
  eingetragen_am: '2026-11-01'
  link: https://www.example.org/stelle/2
- id: probe-ag-sent
  firma: Probe AG
  stelle: Disponent:in
  status: Beworben
  eingetragen_am: '2026-11-01'
  beworben_am: '2026-11-02'
  versand:
    datum: '2026-11-02'
    art: elektronisch
- id: test-ag-gespraech
  firma: Test AG
  stelle: Planer:in
  status: Gespräch
  eingetragen_am: '2026-11-01'
"""
# Steps, cards, dialogs and buttons as the server sends them; a text set in its Sie form.
APPLICATION_FR = ("<title>Candidature</title>", 'aria-label="Avancement de la candidature"', ">Variante du CV<",
                  "Le CV utilisé est le fichier de", ">CV et fichiers<", ", tel quel. Une variante choisie a la priorité.",
                  ">Proposer une variante<", ">CV pour ce poste<", ">Modifier la lettre<", ">Ajouter un paragraphe<",
                  ">Formule d'appel<", ">Valider<", ">Créer et vérifier les documents<", ">Lettre de motivation et CV<",
                  ">Concevoir le dossier<", ">Enregistrer l'envoi<", ">Envoyée le<",
                  '<option value="elektronisch">électronique</option>', '<option value="telefonisch">par téléphone</option>',
                  ">Consigner<", ">Invitation à un entretien<", ">Refus<", ">Réponse positive<", ">Ouvrir Job-Room<",
                  ">Mettre fin à la candidature<", ">Retirer<", ">Historique<", ">Modifier les informations<",
                  ">Personne de contact<", "Candidature sur assignation de l'ORP", ">Page de garde<",
                  ">Pour tous les dossiers<", ">Couleur d'accent<", ">Revenir au réglage par défaut<",
                  f"Abandonner les modifications{NBSP}?")
APPLICATION_EN = ("<title>Application</title>", 'aria-label="Progress of the application"', ">CV variant<",
                  "The CV is the file from", ">CV and files<", ", as it is. A chosen variant comes first.",
                  ">Suggest a variant<", ">CV for this job<", ">Edit the cover letter<", ">Add a paragraph<",
                  ">Salutation<", ">Approve<", ">Create and check documents<", ">Cover letter and CV<",
                  ">Design the dossier<", ">Record as sent<", ">Sent on<",
                  '<option value="elektronisch">electronic</option>', '<option value="persönlich">in person</option>',
                  ">Record<", ">Invitation to an interview<", ">Rejection<", ">Offer<", ">Open Job-Room<",
                  ">End the application<", ">Withdraw<", ">History<", ">Edit details<", ">Contact person<",
                  "Application assigned by the RAV", ">Cover page<", ">For all dossiers<", ">Accent colour<",
                  ">Back to default<", "Discard changes?")
APPLICATION_DE = (">Lebenslauf-Variante<", ">Variante vorschlagen<", ">Anschreiben ändern<", ">Absatz hinzufügen<",
                  ">Freigeben<", ">Unterlagen erstellen und prüfen<", ">Dossier gestalten<", ">Versand erfassen<",
                  ">elektronisch<", ">Festhalten<", ">Einladung zum Gespräch<", ">Bewerbung beenden<", ">Verlauf<",
                  ">Angaben ändern<", ">Kontaktperson<", ">Deckblatt<", ">Akzentfarbe<", "Änderungen verwerfen?")
PAGE_FILES = ("seiten/bewerbung.html", "seiten/bewerbung-logik.js", "seiten/formular-logik.js",
              "seiten/bewerbung-wieder.js")
# Applying through the form, the Job-Room entry, the dispatch and the approval of the letter; routes_apply, routes_rav,
# rav and routen_bewerbungen are finished already (#419, #420).
ROUTE_FILES = ("apply.py", "versand.py", "letter_approval.py", "form_copy.py", "routes_apply.py", "routes_rav.py",
               "rav.py", "routen_bewerbungen.py")
# The hint under „Kurzprofil“: one sentence around a link, as three text sets so each language orders its own words.
CV_HINT_FR = ('<span data-text="lebenslauf.angaben-hier">D\'après vos informations. Vous pouvez raccourcir et réorganiser '
              f'ici{NBSP}; pour</span> <a href="/angaben" data-text="lebenslauf.angaben-link">modifier les informations '
              'elles-mêmes</a><span data-text="lebenslauf.angaben-dort">, passez par Mes informations.</span>')
CV_HINT_EN = ('<span data-text="lebenslauf.angaben-hier">From your details. You can shorten and reorder here; to</span> '
              '<a href="/angaben" data-text="lebenslauf.angaben-link">change the details themselves</a>'
              '<span data-text="lebenslauf.angaben-dort">, go to My details.</span>')
CV_HINT_DE = ('<span data-text="lebenslauf.angaben-hier">Aus Ihren Angaben. Kürzen und umstellen geht hier;</span> '
              '<a href="/angaben" data-text="lebenslauf.angaben-link">Angaben selbst ändern</a>'
              '<span data-text="lebenslauf.angaben-dort"> geht unter Meine Angaben.</span>')
# The link next to the limits of the AI's suggestions stands alone
AI_NOTE_LINK = ('</span> <a href="/angaben">{}</a></p>')
NO_LINK_FR = f"Pas de lien vers le formulaire{NBSP}: ouvrir la candidature et saisir le lien"
NO_LINK_EN = "No link to the form: open the application and enter the link"
NO_CV_FR = (f"PDF du CV manquant{NBSP}: ouvrir la candidature, puis «{NBSP}Créer et vérifier les documents{NBSP}» ou "
            f"téléverser le CV sous «{NBSP}CV et fichiers{NBSP}»")
NO_CV_EN = "CV PDF missing: open the application, then “Create and check documents”, or upload the CV under “CV and files”"


@pytest.fixture
def started(tmp_path):
    """The app on a data folder with four invented applications: no link, no CV, sent, at the interview."""
    folder = tmp_path / "daten"
    folder.mkdir()
    (folder / "bewerbungen.yaml").write_text(REGISTER, encoding="utf-8")
    server = app.erstelle_server(folder, tmp_path / "build")
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    yield server, folder
    server.shutdown()
    server.server_close()


def page(server) -> tuple[int, str]:
    connection, headers = connect(server)
    connection.request("GET", f"/?t={server.token}", headers=headers)
    cookie = connection.getresponse()
    cookie.read()
    connection.request("GET", f"{PAGE}?id=muster-ag-planer",
                       headers={**headers, "Cookie": cookie.getheader("Set-Cookie").split(";", 1)[0]})
    answer = connection.getresponse()
    body = answer.read().decode("utf-8")
    connection.close()
    return answer.status, body


def application_page(server) -> str:
    """The page as the server sends it in German: its token filled in and the links the server hides taken out."""
    html = (server_module.SEITEN / app.SEITEN[PAGE]).read_text(encoding="utf-8").replace("__TOKEN__", server.token)
    for link in server.hidden_links:
        html = html.replace(link, "")
    return html


def refused(server, method: str, path: str, body: dict | None = None) -> str:
    status, answer = request(server, method, path, body)
    assert status == 400, answer
    return answer["fehler"]


def reasons(server) -> dict[str, dict]:
    status, answer = request(server, "GET", "/api/bewerben/auswahl")
    assert status == 200, answer
    return {row["id"]: {key: value for key, value in row.items() if key != "id"} for row in answer["bewerbungen"]}


def catalog() -> translation_catalog.Catalog:
    return translation_catalog.load(translation_catalog.CATALOG_DIR)


# The page


def test_the_application_page_shows_its_steps_cards_and_dialogs_in_french(started, preview):
    server, folder = started
    store_language(folder, "fr")

    status, body = page(server)

    assert status == 200
    assert '<html lang="fr">' in body
    assert [text for text in APPLICATION_FR if text not in body] == []
    assert [text for text in APPLICATION_DE if text in body] == []


def test_the_application_page_shows_its_steps_cards_and_dialogs_in_english(started, preview):
    server, folder = started
    store_language(folder, "en")

    status, body = page(server)

    assert status == 200
    assert [text for text in APPLICATION_EN if text not in body] == []
    assert [text for text in APPLICATION_DE if text in body] == []


def test_the_application_page_stays_german_byte_for_byte_with_the_preview_off(started, no_preview):
    server, folder = started
    store_language(folder, "fr")

    status, body = page(server)

    assert (status, body) == (200, application_page(server))
    assert [text for text in APPLICATION_DE if text not in body] == []
    assert CV_HINT_DE in body
    assert AI_NOTE_LINK.format("Angaben selbst ändern") in body


def test_the_hint_under_the_profile_orders_its_words_around_the_link_in_each_language(started, preview):
    server, folder = started

    store_language(folder, "fr")
    french = page(server)[1]
    store_language(folder, "en")
    english = page(server)[1]

    # no space before the comma that follows the link: the set replaces the whole text, like Texte.anwenden
    assert CV_HINT_FR in french
    assert CV_HINT_EN in english
    assert AI_NOTE_LINK.format("Modifier dans Mes informations") in french
    assert AI_NOTE_LINK.format("Edit in My details") in english


def test_the_kinds_of_dispatch_keep_their_stored_value_in_every_language(started, preview):
    server, folder = started
    store_language(folder, "en")

    body = page(server)[1]

    # the select sends its value, so a translated option still stores the German kind
    assert all(f'<option value="{kind}">' in body for kind in versand.JOBROOM_ART)


def test_the_page_its_scripts_and_its_route_modules_are_finished():
    finished = {str(path.relative_to(sprachen_pruefen.BASE)) for path in sprachen_pruefen.FERTIG
                if path.is_relative_to(sprachen_pruefen.BASE)}

    assert set(PAGE_FILES) | set(ROUTE_FILES) <= finished


def test_the_page_its_scripts_and_its_route_modules_have_no_gap():
    files = [sprachen_pruefen.BASE / name for name in (*PAGE_FILES, *ROUTE_FILES)]

    assert [str(gap) for gap in sprachen_pruefen.gaps(files, catalog())] == []


# Why a form cannot open yet (apply.blocker)


def test_why_a_form_cannot_open_comes_in_french_with_the_step_it_leads_to(started, preview):
    server, folder = started
    store_language(folder, "fr")

    found = reasons(server)

    assert found["muster-ag-planer"] == {"grund": NO_LINK_FR, "schritt": "link"}
    assert found["beispiel-gmbh-kurs"] == {"grund": NO_CV_FR, "schritt": "unterlagen"}
    assert found["probe-ag-sent"] == {"grund": "Déjà envoyée"}
    # the stage is stored German and stays so inside the French sentence
    assert found["test-ag-gespraech"] == {"grund": f"Statut «{NBSP}Gespräch{NBSP}»"}


def test_why_a_form_cannot_open_comes_in_english(started, preview):
    server, folder = started
    store_language(folder, "en")

    found = reasons(server)

    assert found["muster-ag-planer"] == {"grund": NO_LINK_EN, "schritt": "link"}
    assert found["beispiel-gmbh-kurs"] == {"grund": NO_CV_EN, "schritt": "unterlagen"}
    assert found["test-ag-gespraech"] == {"grund": "Status “Gespräch”"}


def test_a_letter_not_yet_approved_names_its_step_in_every_language(tmp_path):
    folder = tmp_path / "daten"
    folder.mkdir()
    entry = {"id": "beispiel-gmbh-kurs", "firma": "Beispiel GmbH", "status": "Bewerben", "link": "https://www.example.org/2"}
    cv = unterlagen.wirksame_pdfs(folder, entry)["lebenslauf"]
    cv.parent.mkdir(parents=True, exist_ok=True)
    cv.write_bytes(b"%PDF-1.4 invented")
    letter = unterlagen.letter_source(folder, entry["id"])
    letter.parent.mkdir(parents=True, exist_ok=True)
    letter.write_text("betreff: Bewerbung\ntext: Erfunden.\n", encoding="utf-8")

    reason = apply.blocker(folder, entry)

    assert str(reason) == apply.NOT_APPROVED
    assert apply.reason_step(reason) == "freigeben"
    assert reason.in_language(catalog(), "fr") == (
        f"Lettre de motivation pas encore validée{NBSP}: ouvrir la candidature, lire la lettre et «{NBSP}Valider{NBSP}»")
    assert reason.in_language(catalog(), "en") == (
        "Cover letter not approved yet: open the application, read the letter and “Approve”")


def test_a_form_refused_by_the_extension_says_why_in_french(started, preview):
    server, folder = started
    store_language(folder, "fr")

    assert refused(server, "GET", "/api/bewerben/daten?id=muster-ag-planer") == NO_LINK_FR
    assert refused(server, "POST", "/api/bewerben/ordner", {"id": "muster-ag-planer"}) == (
        f"Il n'y a pas encore de fichiers pour cette candidature. Merci d'utiliser d'abord «{NBSP}Créer et vérifier les "
        f"documents{NBSP}» ou de les téléverser sous «{NBSP}CV et fichiers{NBSP}».")
    store_language(folder, "en")
    assert refused(server, "POST", "/api/bewerben/ordner", {"id": "muster-ag-planer"}) == (
        "There are no files for this application yet. Please first use “Create and check documents” or upload them "
        "under “CV and files”.")


# The approval of the letter and recording the dispatch


def test_approving_the_letter_is_refused_in_french_and_english(started, preview):
    server, folder = started

    store_language(folder, "fr")
    assert refused(server, "POST", "/api/anschreiben/freigeben", {"id": "muster-ag-planer"}) == (
        "Il n'y a pas encore de lettre de motivation à valider.")
    assert refused(server, "POST", "/api/anschreiben/freigeben", {"id": "probe-ag-sent"}) == (
        "Cette candidature a déjà été envoyée.")
    store_language(folder, "en")
    assert refused(server, "POST", "/api/anschreiben/freigeben", {"id": "muster-ag-planer"}) == (
        "There is no cover letter to approve yet.")


def test_recording_the_dispatch_is_refused_in_french_and_english(started, preview):
    server, folder = started

    store_language(folder, "fr")
    assert refused(server, "POST", "/api/versand?id=probe-ag-sent", {"art": "elektronisch"}) == (
        "Cette candidature a déjà été envoyée le 2026-11-02")
    assert refused(server, "POST", "/api/versand?id=muster-ag-planer", {"art": "per Brieftaube"}) == (
        "art doit être l'un de elektronisch, schriftlich, persönlich, telefonisch")
    assert refused(server, "POST", "/api/versand?id=muster-ag-planer", {"art": "schriftlich"}) == (
        f"PDF du CV manquant{NBSP}: créer et vérifier d'abord les documents")
    store_language(folder, "en")
    assert refused(server, "POST", "/api/versand?id=probe-ag-sent", {"art": "elektronisch"}) == (
        "This application was already sent on 2026-11-02")
    assert refused(server, "POST", "/api/versand?id=muster-ag-planer", {"art": "schriftlich"}) == (
        "CV PDF missing: create and check the documents first")


def test_the_notes_after_the_dispatch_keep_firm_job_and_stage_german():
    others = [{"id": "a", "firma": "Muster AG", "stelle": "Planer:in", "status": "Gespräch"}]

    [note] = versand._hinweise_firma(others, {"id": "b", "firma": "Muster AG", "stelle": "Zeichner:in"})

    assert str(note) == "Bei Muster AG läuft schon eine Bewerbung: Planer:in (Gespräch)"
    assert note.in_language(catalog(), "fr") == (
        f"Une candidature est déjà en cours chez Muster AG{NBSP}: Planer:in (Gespräch)")
    assert note.in_language(catalog(), "en") == "There is already an open application at Muster AG: Planer:in (Gespräch)"


def test_the_versions_a_form_kept_are_named_in_the_app_language():
    labels = [form_copy.LABELS["lebenslauf"], form_copy.LABELS["zertifikate"]]

    assert [label.in_language(catalog(), "fr") for label in labels] == ["CV", "Certificats"]
    assert [label.in_language(catalog(), "en") for label in labels] == ["CV", "Certificates"]
    assert list(form_copy.LABELS.values()) == ["Lebenslauf", "Anschreiben", "Zertifikate", "Unterlagen", "Nachweise"]


def test_the_routes_of_the_page_stay_german_with_the_preview_off(started, no_preview):
    server, folder = started
    store_language(folder, "fr")

    found = reasons(server)
    assert found["muster-ag-planer"] == {"grund": apply.NO_LINK, "schritt": "link"}
    assert found["test-ag-gespraech"] == {"grund": "Status „Gespräch“"}
    assert refused(server, "POST", "/api/anschreiben/freigeben", {"id": "probe-ag-sent"}) == (
        "Diese Bewerbung ist schon versendet.")
    assert refused(server, "POST", "/api/versand?id=probe-ag-sent", {"art": "elektronisch"}) == (
        "Diese Bewerbung wurde bereits am 2026-11-02 versendet")


# The plain messages the server matches as a whole, and the names the brief fixes.
REVIEWED = {
    "Im Lebenslauf fehlen die Angaben zur Person.": ("Le CV ne contient pas les informations personnelles.",
                                                      "The CV lacks the personal details."),
    "Dieser Teil der Datei fehlt.": ("Cette partie du fichier manque.", "This part of the file is missing."),
    "Der Ordner liess sich nicht vorbereiten. Bitte nochmals versuchen.": (
        "Le dossier n'a pas pu être préparé. Merci de réessayer.", "The folder could not be prepared. Please try again."),
    "Ein eigenes Anschreiben braucht keine Freigabe.": (
        "Une lettre de motivation téléversée n'a pas besoin de validation.", "An uploaded cover letter needs no approval."),
    "2 · Aussehen": ("2 · Apparence", "2 · Appearance"),
    "Als Text bearbeiten (für Geübte)": ("Modifier en mode texte (utilisateurs avancés)",
                                         "Edit as text (for experienced users)"),
    "Versand erfassen": ("Enregistrer l'envoi", "Record as sent"),
    "Versand erfasst ({art})": ("Envoi enregistré ({art})", "Recorded as sent ({art})"),
    "Form ändern": ("Changer de format", "Change format"),
    "Eigene Farbe": ("Couleur personnalisée", "Custom colour"),
    "1 Hinweis": ("1 remarque", "1 remark"),
    "{anzahl} Hinweise": ("{anzahl} remarques", "{anzahl} remarks"),
    "Begrüssung („Kurz vorgestellt“)": ("Accueil (page de présentation)", "Welcome (introduction page)"),
    "Angaben selbst ändern": ("Modifier dans Mes informations", "Edit in My details"),
    "Vor dem Senden ersetzt die App Name, Adresse, Kontakte und Ansprechpersonen durch Platzhalter; Bilder und Scans "
    "gehen nie an die KI. Eine Einschätzung, kein Urteil: Die KI kann sich irren.": (
        f"Avant l'envoi, l'app remplace le nom, l'adresse, les coordonnées et les personnes de contact par des substituts"
        f"{NBSP}; les images et les scans ne sont jamais envoyés à l'IA. Une estimation, pas un jugement{NBSP}: l'IA peut "
        "se tromper.",
        "Before sending, the app replaces name, address, contacts and contact persons with placeholders; images and "
        "scans never go to the AI. An estimate, not a verdict: the AI can be wrong."),
    "Die KI entwirft beide Texte aus den Bausteinen, mit Platzhaltern statt Name und Kontakt. Danach lassen sie sich "
    "hier anpassen. Ohne Text entfällt die Seite im Dossier.": (
        "L'IA rédige les deux textes à partir des modules de texte, avec des substituts à la place du nom et des "
        "coordonnées. Ensuite, ils peuvent être adaptés ici. Sans texte, la page disparaît du dossier.",
        "The AI drafts both texts from the text blocks, with placeholders instead of name and contact. They can then be "
        "adjusted here. Without text, the page is left out of the dossier."),
    "Zeichen und Farbe gelten für alle Dossiers. Jede Wahl ist sofort gespeichert; «Abbrechen» nimmt sie nicht zurück. "
    "Schon erstellte Dossiers bleiben, wie sie sind; mit «Unterlagen erstellen» entsteht dieses neu.": (
        f"L'emblème et la couleur valent pour tous les dossiers. Chaque choix est enregistré tout de suite{NBSP}; "
        f"«{NBSP}Annuler{NBSP}» ne l'annule pas. Les dossiers déjà créés restent tels quels{NBSP}; avec «{NBSP}Créer et "
        f"vérifier les documents{NBSP}», celui-ci est recréé.",
        "Mark and colour apply to all dossiers. Each choice is saved at once; “Cancel” does not undo it. Dossiers "
        "already created stay as they are; “Create and check documents” creates this one anew."),
    "«Passend zum Design» ist die Farbe des Designs: Siegel Schieferblau, Raster Weinrot, Register Tannengrün. Sie "
    "wechselt mit dem Design; eine benannte Farbe bleibt. Schrift auf der Farbe wählt die App selbst, weiss oder dunkel.": (
        f"«{NBSP}Assortie au design{NBSP}» est la couleur du design{NBSP}: bleu ardoise pour Sceau, bordeaux pour Trame, "
        f"vert sapin pour Registre. Elle change avec le design{NBSP}; une couleur nommée reste. L'app choisit elle-même "
        "la couleur du texte sur l'accent, blanc ou foncé.",
        "“Matching the design” is the design's colour: slate blue for Seal, wine red for Grid, fir green for Register. It "
        "changes with the design; a named colour stays. The app picks the text colour on it itself, white or dark."),
    "Absage": ("Refus", "Rejection"),
    "Zusage": ("Réponse positive", "Offer"),
    "Einladung zur Schnupperlehre": ("Invitation à un stage d'orientation", "Invitation to a trial apprenticeship"),
    "Bewerbung auf Zuweisung des RAV": ("Candidature sur assignation de l'ORP", "Application assigned by the RAV"),
}


@pytest.mark.parametrize("german", REVIEWED)
def test_the_reviewed_wording_is_in_the_catalog(german):
    assert (catalog().text(german, "fr"), catalog().text(german, "en")) == REVIEWED[german]
