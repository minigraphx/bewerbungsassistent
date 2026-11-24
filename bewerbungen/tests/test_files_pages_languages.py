"""Lebenslauf und Dateien, Foto, Entwürfe, Inhalte and Fragen in French and English (#430, G10).

With the preview on and French or English as the app language, the five pages, their routes and the modules behind
them speak it, and each page is finished: its HTML, every script it loads and every route module behind those scripts
is in FERTIG without a gap. With the preview off they stay German, byte for byte. Data stays as it is: file names, the
notes of drafts, Git messages, stored kinds. What the scripts say at run time is tested in
tests/files_pages_languages.test.cjs. All data is invented.
"""
import base64
import inspect
import io
import json
import pathlib
import re

import pytest
from PIL import Image

import ablage
import app
import dateien
import proof_kinds
import routen_foto
import routes_chat
import server as server_module
import sprachen_pruefen
import translation_catalog
import ui_texts
import versionen
from ai import chat
from sample_folder import BRIEF_ID
from test_app import get, post, server  # noqa: F401  (server is a fixture)
from test_draft_groups import drafts
from test_today_languages import no_preview, preview, store_language  # noqa: F401  (fixtures)

NBSP = chr(0xA0)
PAGES = {"/dateien": "seiten/dateien.html", "/foto": "seiten/foto.html", "/entwuerfe": "seiten/entwuerfe.html",
         "/inhalte": "seiten/inhalte.html", "/fragen": "seiten/fragen.html"}
SCRIPT_FILES = ("seiten/dateien-logik.js", "seiten/dateien.js", "seiten/foto.js", "seiten/entwuerfe-logik.js",
                "seiten/entwuerfe.js", "seiten/inhalte.js", "seiten/fragen.js")
# The routes of the photo, of the contents and of the questions, with the modules behind them and behind the drafts;
# routes_own_files, routen_ablage and routen_bewerbungen came with earlier steps.
MODULE_FILES = ("routen_foto.py", "photo_file.py", "photos.py", "photo_shown.py", "routen_inhalte.py",
                "routes_chat.py", "ai/chat.py", "proof_kinds.py", "ablage.py", "versionen.py", "dateien.py")
API_ROUTE = re.compile(r"/api/[a-z0-9/_.-]*[a-z0-9]")


def catalog() -> translation_catalog.Catalog:
    return translation_catalog.load(translation_catalog.CATALOG_DIR)


def said(message, language: str) -> str:
    """A message as the person reads it: a T by its template, a plain German text by exact match."""
    return str(message) if language == "de" else ui_texts.uebersetze(message, language, catalog())


def finished() -> set[pathlib.Path]:
    return {path.resolve() for path in sprachen_pruefen.FERTIG}


def page_scripts(page: str) -> list[pathlib.Path]:
    html = (sprachen_pruefen.BASE / page).read_text(encoding="utf-8")
    return [sprachen_pruefen.BASE / "seiten" / name for name in re.findall(r'<script src="/([^"?]+\.js)"', html)]


def page(s, path: str) -> str:
    status, _, body = get(s, path)
    assert status == 200
    return body.decode("utf-8")


def german_page(s, path: str) -> str:
    """The page as the server sends it in German: its token filled in and the links the server hides taken out."""
    html = (server_module.SEITEN / pathlib.Path(PAGES[path]).name).read_text(encoding="utf-8").replace("__TOKEN__", s.token)
    for link in s.hidden_links:
        html = html.replace(link, "")
    return html


def answer(s, path: str, **parameter) -> tuple[int, dict]:
    status, _, body = get(s, path, **parameter)
    return status, json.loads(body)


def refused(s, path: str, body, status: int = 400, **parameter) -> str:
    code, found = post(s, path, body, **parameter)
    assert code == status, found
    return found["fehler"]


def png(width: int = 40, height: int = 50) -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (width, height), (90, 120, 160)).save(out, "PNG")
    return out.getvalue()


def upload_photo(s, data: bytes):
    return post(s, "/api/foto/hochladen", {"name": "bild.png", "daten": base64.b64encode(data).decode("ascii")})


# The files of this step and the five pages as a whole


def test_the_pages_their_scripts_and_their_modules_are_finished():
    names = {str(path.relative_to(sprachen_pruefen.BASE)) for path in sprachen_pruefen.FERTIG
             if path.is_relative_to(sprachen_pruefen.BASE)}

    assert set(PAGES.values()) | set(SCRIPT_FILES) | set(MODULE_FILES) <= names


def test_the_pages_their_scripts_and_their_modules_have_no_gap():
    files = [sprachen_pruefen.BASE / name for name in (*PAGES.values(), *SCRIPT_FILES, *MODULE_FILES)]

    assert [str(gap) for gap in sprachen_pruefen.gaps(files, catalog())] == []


@pytest.mark.parametrize("html", PAGES.values())
def test_every_script_a_page_loads_is_finished_without_a_gap(html):
    scripts = page_scripts(html)

    assert len(scripts) > 5, scripts
    assert [path.name for path in scripts if path.resolve() not in finished()] == []
    assert [str(gap) for gap in sprachen_pruefen.gaps([sprachen_pruefen.BASE / html, *scripts], catalog())] == []


@pytest.mark.questions_page
def test_every_route_module_behind_the_five_pages_is_finished(server):  # noqa: F811
    asked = {route for html in PAGES.values() for path in page_scripts(html)
             for route in API_ROUTE.findall(path.read_text(encoding="utf-8"))}
    handlers = [table[route] for route in sorted(asked) for table in (server.routen_get, server.routen_post)
                if route in table]
    modules = {pathlib.Path(inspect.getsourcefile(handler)).resolve() for handler in handlers}

    assert len(modules) > 6, modules
    assert {"routen_foto.py", "routen_inhalte.py", "routes_chat.py", "routen_ablage.py"} <= {path.name for path in modules}
    assert sorted(path.name for path in modules if path not in finished()) == []


def test_the_text_sets_of_the_pages_are_in_the_catalog():
    keys = ("dateien.cv-titel", "dateien.app", "dateien.eigen", "dateien.app-wie", "dateien.ihr-pdf",
            "dateien.wie-es-ist", "dateien.ordnet", "dateien.zurueck-zur-app", "entwuerfe.intro", "entwuerfe.alle",
            "inhalte.intro", "fragen.hilfe", "fragen.label", "fragen.sprecher")
    missing = [(key, language, form) for key in keys for language in ("fr", "en")
               for form in (("sie", "du") if language == "fr" else ("sie",)) if not catalog().form(key, language, form)]

    assert missing == []


def test_french_says_tu_where_the_set_says_du():
    assert catalog().form("dateien.cv-titel", "fr", "du") == "Ton CV"
    assert catalog().form("dateien.cv-titel", "fr", "sie") == "Votre CV"
    assert catalog().form("fragen.sprecher", "fr", "du") == "Toi"
    assert catalog().form("fragen.label", "en", "sie") == "Your question"
    assert catalog().form("fragen.hilfe", "fr", "lehrstelle").startswith(
        "Pose ici tes questions sur la recherche d'une place d'apprentissage")


# The pages


def test_lebenslauf_und_dateien_shows_its_cards_and_dialogs_in_french(server, preview):  # noqa: F811
    store_language(server.kontext.daten, "fr")

    body = page(server, "/dateien")

    assert '<html lang="fr">' in body
    assert [text for text in (
        "<title>CV et fichiers</title>", "Votre CV", "L'app le crée", "J'utilise mon propre PDF",
        f"Design{NBSP}: Deux colonnes", "Choisir l'apparence", "Certificats de travail, bulletins et certificats",
        "Glisser les fichiers ici", "Ajouter une photo", "Ajuster le cadrage", "Afficher dans le CV",
        "Versions antérieures", f"Retirer le PDF personnel{NBSP}?", "Apparence du CV",
        f"sous «{NBSP}Concevoir le dossier{NBSP}».",
    ) if text not in body] == []
    assert [text for text in ("Ihr Lebenslauf", "Zeugnisse und Zertifikate", "Foto hinzufügen", "Frühere Fassungen",
                              "Aussehen wählen") if text in body] == []


def test_the_photo_page_shows_its_editor_and_upload_in_english(server, preview):  # noqa: F811
    store_language(server.kontext.daten, "en")

    body = page(server, "/foto")

    assert '<html lang="en">' in body
    assert [text for text in (
        "<title>Photo crop</title>", "← CV and files", "The crop for the CV. The photo itself stays unchanged.",
        'aria-label="Preview of the photo crop"', 'alt="Preview at about print size"', "about print size (4.65 cm)",
        "Mirror", "Crop horizontal (x)", "Default values", "Your photos", "Upload photo",
        "A photo as JPG or PNG, at most", "MB. Camera, place and time details in the image are not saved.",
        'aria-label="Latest drafts of the CV"',
    ) if text not in body] == []
    assert [text for text in ("Spiegeln", "Standardwerte", "Ihre Fotos", "Foto wählen") if text in body] == []


def test_the_drafts_page_shows_its_parts_around_the_folder_name_in_french(server, preview):  # noqa: F811
    store_language(server.kontext.daten, "fr")

    body = page(server, "/entwuerfe")

    assert [text for text in (
        "<title>Brouillons et versions</title>", "← Retour", "Chaque enregistrement crée une version.",
        f"le PDF se trouve sous <code>versendet/</code> et ne change plus.", 'aria-label="Afficher les brouillons"',
        "Seulement ceux utilisés", "Afficher tous les brouillons", "Pas encore de brouillons.", "Versions envoyées",
    ) if text not in body] == []
    assert "Entwürfe und Versionen" not in body


def test_the_contents_page_shows_its_editor_in_english(server, preview):  # noqa: F811
    store_language(server.kontext.daten, "en")

    body = page(server, "/inhalte")

    assert [text for text in (
        "<title>Contents</title>", "For experienced users", "Contents as text",
        "Here you see what the app builds your documents from", 'aria-label="File"', 'title="PDF view"',
        "It is easier to edit under “Applications”.", "Check and preview", "Discard changes",
        'aria-label="Latest drafts of this file"',
    ) if text not in body] == []
    assert [text for text in ("Für Geübte", "Prüfen und Vorschau", "Änderungen verwerfen") if text in body] == []


@pytest.mark.questions_page
def test_the_questions_page_shows_its_frame_in_french(server, preview):  # noqa: F811
    store_language(server.kontext.daten, "fr")

    body = page(server, "/fragen")

    assert [text for text in ("<title>Questions</title>", "Questions à l'IA", ">Envoyer</button>") if text not in body] == []
    assert ">Senden</button>" not in body


@pytest.mark.questions_page
@pytest.mark.parametrize("path", PAGES)
def test_each_page_stays_german_byte_for_byte_with_the_preview_off(server, no_preview, path):  # noqa: F811
    store_language(server.kontext.daten, "fr")

    assert page(server, path) == german_page(server, path)


# The photo


def test_a_photo_is_refused_in_french(server, preview, monkeypatch):  # noqa: F811
    store_language(server.kontext.daten, "fr")
    monkeypatch.setattr(routen_foto, "MAX_PHOTO_BYTES", 2_000_000)

    assert upload_photo(server, b"GIF89a....")[1]["fehler"] == "Merci de choisir une photo en JPG ou PNG."
    assert refused(server, "/api/foto/hochladen", {"daten": "kein base64!"}) == (
        "L'image n'a pas pu être lue. Merci de choisir une autre photo en JPG ou PNG.")
    assert upload_photo(server, b"\x89PNG" + b"0" * 2_000_000)[1]["fehler"] == (
        f"La photo est trop volumineuse{NBSP}: 2 Mo au maximum.")
    assert refused(server, "/api/foto/speichern", []) == "Options attendues"
    assert refused(server, "/api/foto/aktiv", []) == "datei attendu"
    assert refused(server, "/api/foto/zeigen", {"zeigen": "ja"}) == (
        f"Merci de choisir{NBSP}: afficher la photo dans le CV ou non.")
    assert refused(server, "/api/foto/loeschen", {"datei": "foto.png"}) == (
        "La photo active ne peut pas être supprimée. Utiliser d'abord une autre photo.")
    assert refused(server, "/api/foto/aktiv", {"datei": "fotos/weg.jpg"}, 404) == (
        "Cette photo n'existe plus. Merci de recharger la page.")


def test_without_a_cv_the_upload_is_refused_in_english(server, preview):  # noqa: F811
    store_language(server.kontext.daten, "en")
    (server.kontext.daten / "cv.yaml").unlink()

    assert upload_photo(server, png())[1]["fehler"] == "There is no CV yet. Please enter the details first, then the photo."


def test_the_photo_stays_german_with_the_preview_off(server, no_preview, monkeypatch):  # noqa: F811
    store_language(server.kontext.daten, "fr")
    monkeypatch.setattr(routen_foto, "MAX_PHOTO_BYTES", 2_000_000)

    assert upload_photo(server, b"\x89PNG" + b"0" * 2_000_000)[1]["fehler"] == "Das Foto ist zu gross: höchstens 2 MB."
    assert refused(server, "/api/foto/loeschen", {"datei": "foto.png"}) == (
        "Das aktive Foto lässt sich nicht löschen. Zuerst ein anderes Foto verwenden.")


def test_the_note_of_a_saved_crop_stays_german_in_french(server, preview):  # noqa: F811
    store_language(server.kontext.daten, "fr")

    status, _ = post(server, "/api/foto/speichern", {"mirror": True, "zoom": 1.2, "x": 0.5, "y": 0.5})
    notes = [draft["beschreibung"] for draft in answer(server, "/api/entwuerfe")[1]["entwuerfe"]]

    assert status == 200 and "Fotoausschnitt geändert" in notes


# The contents


def test_the_contents_name_their_files_in_french_and_keep_the_paths(server, preview):  # noqa: F811
    store_language(server.kontext.daten, "fr")

    titles = {entry["datei"]: entry["titel"] for entry in answer(server, "/api/inhalte")[1]["dateien"]}

    assert titles["cv.yaml"] == "CV"
    assert titles["jobs/daten.yaml"] == "Adaptation du CV daten"
    assert titles["varianten.yaml"] == "Variantes du CV (données)"
    assert titles[f"bewerbungen/{BRIEF_ID}/anschreiben.yaml"] == f"Lettre de motivation {BRIEF_ID}"


def test_a_file_without_a_pdf_view_is_named_in_english(server, preview):  # noqa: F811
    store_language(server.kontext.daten, "en")

    status, found = answer(server, "/api/inhalt/pdf", datei="varianten.yaml")

    assert status == 400
    assert found["fehler"] == "CV variants (data) has no PDF view, only as text"


def test_the_contents_stay_german_with_the_preview_off(server, no_preview):  # noqa: F811
    store_language(server.kontext.daten, "fr")

    titles = {entry["datei"]: entry["titel"] for entry in answer(server, "/api/inhalte")[1]["dateien"]}

    assert titles["jobs/daten.yaml"] == "Lebenslauf-Zuschnitt daten"
    assert answer(server, "/api/inhalt/pdf", datei="varianten.yaml")[1]["fehler"] == (
        "Lebenslauf-Varianten (Daten) hat keine PDF-Ansicht, nur als Text")


# The drafts and versions


def test_the_drafts_name_their_groups_and_documents_in_english(server, preview):  # noqa: F811
    store_language(server.kontext.daten, "en")
    drafts(server, ("cv.yaml", "Angaben erfasst"), (f"bewerbungen/{BRIEF_ID}/anschreiben.yaml", "Brief"),
           ("anschreiben/stil.md", "Stil"), ("suchprofil.md", "Suche"), ("notizen.md", "Notiz"))

    groups = answer(server, "/api/entwuerfe")[1]["gruppen"]

    assert [group["titel"] for group in groups] == ["CV", "Cover letter", "Style and building blocks", "Search profile",
                                                    "Other"]
    # the company comes from the register and stays as it is stored
    assert [document["titel"] for document in groups[1]["dokumente"]] == ["Cover letter Beispiel AG"]
    assert groups[2]["dokumente"][0]["titel"] == "Style profile"
    # the note of a draft is the person's or the app's record and stays as it was saved
    assert groups[0]["dokumente"][0]["fassungen"][0]["beschreibung"] == "Angaben erfasst"


def test_the_drafts_are_refused_and_compared_in_french(server, preview):  # noqa: F811
    store_language(server.kontext.daten, "fr")
    photo = server.kontext.daten / "foto.png"
    photo.write_bytes(png(20, 20))
    first = server.kontext.ablage.speichere(photo, "Bild")
    photo.write_bytes(png(30, 30))
    second = server.kontext.ablage.speichere(photo, "Bild neu")

    status, found = answer(server, "/api/entwurf", id="weg")
    compared = answer(server, "/api/entwurf/vergleich", a=first.id, b=second.id)[1]["diff"]

    assert (status, found["fehler"]) == (404, "Brouillon 'weg' introuvable")
    assert compared == "Le contenu est binaire (p. ex. PDF) et ne peut pas être comparé comme texte."


def test_the_hint_on_versions_sent_comes_in_english_and_stays_german_without_the_preview(server, preview, monkeypatch):  # noqa: F811
    store_language(server.kontext.daten, "en")

    hint = answer(server, "/api/versionen")[1]["hinweis"]
    monkeypatch.delenv(ui_texts.PREVIEW_ENV)

    assert hint == ("Versions sent are saved: the PDFs under versendet/, the data as used drafts. In addition, the local "
                    "Git of the data folder records each dispatch (no automatic push).")
    assert answer(server, "/api/versionen")[1]["hinweis"] == versionen.GitVersionen.hinweis


@pytest.mark.parametrize("language", ["de", "fr", "en"])
def test_a_draft_in_use_is_kept_in_the_app_language(language, tmp_path):
    (tmp_path / "cv.yaml").write_text("basics: {}\n", encoding="utf-8")
    store = ablage.Ablage(tmp_path)
    draft, = store.markiere_genutzt([tmp_path / "cv.yaml"], "Versand Muster AG")
    with pytest.raises(ValueError) as refusal:
        store.loesche(draft.id)

    assert said(refusal.value.args[0], language) == {
        "de": "Entwurf ist genutzt (Versand Muster AG) und kann nicht gelöscht werden",
        "fr": "Le brouillon est utilisé (Versand Muster AG) et ne peut pas être supprimé",
        "en": "The draft is in use (Versand Muster AG) and cannot be deleted",
    }[language]


@pytest.mark.parametrize("language", ["de", "fr", "en"])
def test_a_path_outside_the_data_folder_and_a_bad_commit_are_named_in_the_app_language(language, tmp_path):
    with pytest.raises(ValueError) as outside:
        dateien.relativ(tmp_path.parent / "fremd.txt", tmp_path)
    with pytest.raises(ValueError) as commit:
        versionen.GitVersionen(tmp_path).inhalt("xyz", "cv.yaml")

    path, folder = tmp_path.parent / "fremd.txt", tmp_path
    assert [said(error.value.args[0], language) for error in (outside, commit)] == {
        "de": [f"{path} liegt nicht im Datenordner {folder}", "Ungültige Commit-ID"],
        "fr": [f"{path} ne se trouve pas dans le dossier de données {folder}", "ID de commit non valable"],
        "en": [f"{path} is not in the data folder {folder}", "Invalid commit ID"],
    }[language]


@pytest.mark.parametrize("language", ["de", "fr", "en"])
def test_an_unreadable_list_of_kinds_is_named_in_the_app_language(language, tmp_path):
    (tmp_path / "dokumente").mkdir()
    (tmp_path / proof_kinds.FILE).write_text("- keine Zuordnung\n", encoding="utf-8")
    with pytest.raises(ValueError) as refusal:
        proof_kinds.load(tmp_path)

    assert said(refusal.value.args[0], language) == {
        "de": "Die Liste der Dateiarten (dokumente/arten.yaml) lässt sich nicht lesen. Unter „Entwürfe und Versionen“ "
              "liegt der Stand davor.",
        "fr": f"La liste des types de fichiers (dokumente/arten.yaml) ne peut pas être lue. La version antérieure se "
              f"trouve sous «{NBSP}Brouillons et versions{NBSP}».",
        "en": "The list of file kinds (dokumente/arten.yaml) cannot be read. The earlier version is under “Drafts and "
              "versions”.",
    }[language]


# The questions


@pytest.mark.questions_page
def test_a_question_is_refused_in_french_before_anything_goes_to_the_ai(server, preview, monkeypatch):  # noqa: F811
    store_language(server.kontext.daten, "fr")

    assert refused(server, "/api/fragen/senden", {"frage": " "}) == "Merci d'écrire une question."
    assert refused(server, "/api/fragen/senden", {"frage": "x" * (chat.MAX_QUESTION + 1)}) == (
        "Merci de ne pas dépasser 1000 caractères.")
    monkeypatch.setattr(routes_chat, "_remaining", lambda k: 0)
    assert refused(server, "/api/fragen/senden", {"frage": "Wie weiter?"}) == (
        "Les questions du jour sont épuisées. La suite demain.")


@pytest.mark.questions_page
def test_the_chat_for_apprentices_is_off_in_english_and_says_so_in_german_without_the_preview(server, preview, monkeypatch):  # noqa: F811
    store_language(server.kontext.daten, "en")
    (server.kontext.daten / "einrichtung.yaml").write_text("gesucht: lehrstelle\nanrede: du\nrav: false\n", encoding="utf-8")
    english = "The chat is only available from age 18 and is switched off for the apprenticeship search."

    assert answer(server, "/api/fragen/stand")[1]["hinweis"] == english
    assert refused(server, "/api/fragen/senden", {"frage": "Hallo?"}) == english
    monkeypatch.delenv(ui_texts.PREVIEW_ENV)
    assert answer(server, "/api/fragen/stand")[1]["hinweis"] == routes_chat.ADULTS_ONLY
    assert refused(server, "/api/fragen/senden", {"frage": "Hallo?"}) == (
        "Der Chat steht nur ab 18 Jahren zur Verfügung und ist bei der Lehrstellensuche ausgeschaltet.")


def test_the_page_routes_of_the_app_still_know_the_five_pages():
    assert {path: app.SEITEN.get(path) or app.QUESTIONS_PAGES.get(path) for path in PAGES} == {
        path: pathlib.Path(html).name for path, html in PAGES.items()}
