"""Meine Angaben in French and English, the documents and the prefill (#433, G10, docs/design/sprachen.md).

With the preview on and French or English as the app language, the routes of the page answer in it: refused
documents, checks of the answers with where they stand, the choice per existing file, the hint on a CV that stays,
and why a document does not go to the AI. The page is finished: its HTML, every script it loads and every module
behind its routes is in FERTIG without a gap. With the preview off everything stays German, and the onboarding modules
keep their German text for the skill einstieg and the import scripts. What the scripts say at run time is tested in
onboarding/tests/documents_languages.test.cjs. All data is invented.
"""
import ast
import copy
import pathlib
import pickle

import build_template
import documents
import import_bundle
import language_sources
import read_documents
import routes_angaben
import sprachen_pruefen
import translation_catalog
import ui_message
import ui_texts
import validation
from test_angaben import call, consent_given, install_client, prefill_reply, started, upload, valid_bundle  # noqa: F401
from test_setup_languages import no_preview, preview, store_language  # noqa: F401  (fixtures)

NBSP = chr(0xA0)
ROOT = sprachen_pruefen.ROOT
ONBOARDING = ROOT / "onboarding"
FORM = validation.load_form()
# The modules behind the routes that word what the page shows: checks, documents, ZIP files, import, reading, prefill.
MESSAGE_MODULES = ("validation.py", "documents.py", "archive.py", "rejected.py", "import_bundle.py", "import_documents.py",
                   "read_documents.py", "prefill.py", "prefill_estimate.py", "basics_merge.py", "basics_read.py",
                   "cv_read.py", "known_tags.py")
PNG = b"\x89PNG\r\n\x1a\n erfunden"


def catalog() -> translation_catalog.Catalog:
    return translation_catalog.load(translation_catalog.CATALOG_DIR)


def said(message, language: str) -> str:
    return str(message) if language == "de" else ui_texts.uebersetze(message, language, catalog())


def finished() -> set[pathlib.Path]:
    return {path.resolve() for path in sprachen_pruefen.FERTIG}


def page_scripts() -> list[pathlib.Path]:
    """Every script angaben.html runs: the ones build_template inlines and the ones of the app it loads."""
    names = [*build_template.SCRIPTS, *build_template.APP_SCRIPTS]
    loaded = [name.split('"')[0] for name in build_template.APP_PAGE_SCRIPTS.split('src="/')[1:]]
    return [ONBOARDING / "src" / name for name in names] + [sprachen_pruefen.BASE / "seiten" / name for name in loaded]


def imported_modules() -> set[pathlib.Path]:
    """The modules routes_angaben imports, at the top and inside make_routes, that are part of the app."""
    tree = ast.parse(pathlib.Path(routes_angaben.__file__).read_text(encoding="utf-8"))
    names = {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    names |= {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
    folders = (ONBOARDING, sprachen_pruefen.BASE, sprachen_pruefen.DESKTOP)
    return {path.resolve() for name in names for folder in folders
            if (path := folder / (name.replace(".", "/") + ".py")).is_file()}


# The page as a whole


def test_every_script_the_page_runs_is_finished_without_a_gap():
    scripts = page_scripts()

    assert len(scripts) > 20, scripts
    assert [path.name for path in scripts if path.resolve() not in finished()] == []
    assert [str(gap) for gap in sprachen_pruefen.gaps(scripts, catalog())] == []


def test_the_routes_and_every_module_they_import_are_finished_without_a_gap():
    modules = imported_modules() | {pathlib.Path(routes_angaben.__file__).resolve()}

    assert {"routes_angaben.py", "import_bundle.py", "prefill.py", "documents.py"} <= {path.name for path in modules}
    assert sorted(path.name for path in modules if path not in finished()) == []
    assert [str(gap) for gap in sprachen_pruefen.gaps(modules, catalog())] == []


def test_the_modules_that_word_the_messages_are_finished_without_a_gap():
    paths = [ONBOARDING / name for name in MESSAGE_MODULES]

    assert [path.name for path in paths if path.resolve() not in finished()] == []
    assert [str(gap) for gap in sprachen_pruefen.gaps(paths, catalog())] == []


def test_every_source_includes_the_modules_of_onboarding():
    sources = set(sprachen_pruefen.app_sources())

    assert {ONBOARDING / name for name in MESSAGE_MODULES} <= sources


def test_the_scanner_reads_each_message_of_an_import_refusal(tmp_path):
    module = tmp_path / "einlesen.py"
    module.write_text("LIMIT = 5\n\n\ndef read(name):\n"
                      "    raise ImportRejected(['Die Datei fehlt.', f'Zu gross: {LIMIT}', T('Zu viele: {n}', n=LIMIT)])\n",
                      encoding="utf-8")

    found = [(item.kind, item.text) for item in language_sources.items((module,))]

    assert sorted(found) == [("leftover", "Zu gross: {LIMIT}"), ("text", "Die Datei fehlt."), ("text", "Zu viele: {n}")]


# The checks of the answers, with where they stand


def test_a_check_names_where_it_stands_and_what_is_wrong_in_the_app_language():
    error = validation.ValidationError("work.0.highlights.1.tags.0", "format")
    message = validation.describe(FORM, "job", error)

    assert said(message, "de") == ("Berufliche Stationen, Station 1, Tätigkeiten und Erfolge, Zeile 2, Tags, Tag 1: "
                                   "Ungültiges Format, zum Beispiel: daten.")
    assert said(message, "fr") == (f"Parcours professionnel, Entrée 1, Activités et réussites, ligne 2, Tags, tag 1{NBSP}: "
                                   f"Format non valable, par exemple{NBSP}: données.")
    assert said(message, "en") == ("Work experience, Entry 1, Tasks and achievements, line 2, Tags, tag 1: "
                                   "Invalid format, for example: data.")


def test_a_label_is_named_up_to_its_bracket_in_every_language():
    error = validation.ValidationError("person.birthDate", "max")
    message = validation.describe(FORM, "job", error)

    assert said(message, "de") == "Person und Kontakt, Geburtsdatum: Zu lang (höchstens 30 Zeichen)."
    assert "(" not in said(message, "fr").split(NBSP)[0] and "(" not in said(message, "en").split(":")[0]
    assert said(message, "en").startswith("Person and contact, Date of birth: ")


def test_a_message_and_a_label_survive_a_copy():
    label = ui_message.Label("Geburtsdatum (freiwillig)")
    message = validation.describe(FORM, "job", validation.ValidationError("person.email", "format"))

    for made in (copy.deepcopy(message), pickle.loads(pickle.dumps(message))):
        assert said(made, "en") == said(message, "en") == "Person and contact, Email: Invalid format, for example: " \
            "firstname.lastname@example.ch."
    for made in (label, copy.copy(label), pickle.loads(pickle.dumps(label))):
        assert str(made) == "Geburtsdatum" and said(made, "en") == "Date of birth"


def test_the_onboarding_modules_keep_their_german_text():
    entries = [{"category": "lebenslauf-bisher", "name": "cv.exe", "size": 10}]

    assert documents.describe(FORM, "job", entries, validation.ValidationError("documents.0", "extension")) == (
        "Bisheriger Lebenslauf, cv.exe: Dieser Dateityp geht nicht. Erlaubt sind PDF, Word (.docx, .doc) und Textdateien (.txt).")
    assert documents.allowed_text(FORM, documents.categories(FORM)["zeugnisse"]) == (
        "PDF, Word (.docx, .doc), Textdateien (.txt) und Bilder (.jpg, .png)")
    assert read_documents.SCAN == "Enthält keinen lesbaren Text, vermutlich ein Scan. Angaben von Hand ergänzen."
    assert ui_message.joined(["Erster Satz.", "Zweiter Satz."]) == "Erster Satz. Zweiter Satz."


def test_file_types_in_a_sentence_start_small_in_french_and_english_but_pdf_and_word_keep_theirs():
    allowed = documents.allowed_text(FORM, documents.categories(FORM)["zeugnisse"])

    assert said(allowed, "fr") == "PDF, Word (.docx, .doc), fichiers texte (.txt) et images (.jpg, .png)"
    assert said(allowed, "en") == "PDF, Word (.docx, .doc), text files (.txt) and images (.jpg, .png)"
    assert said(allowed, "de") == "PDF, Word (.docx, .doc), Textdateien (.txt) und Bilder (.jpg, .png)"


def test_a_starting_file_without_its_json_names_it_as_a_file_in_french():
    message = ui_message.T("Die Datei muss genau eine {datei} enthalten.", datei="einstieg.json")

    assert said(message, "fr") == "Le fichier doit contenir exactement un fichier einstieg.json."
    assert said(message, "de") == "Die Datei muss genau eine einstieg.json enthalten."


def test_messages_of_several_problems_are_each_said_in_the_app_language():
    joined = ui_message.joined([ui_message.T("Die Datei fehlt."), ui_message.T("Diese Datei ist schon dabei.")])

    assert said(joined, "fr") == "Le fichier manque. Ce fichier figure déjà dans la liste."
    assert said(ui_message.joined(["Die Datei fehlt."]), "en") == "The file is missing."


# The routes of the page


def test_a_document_against_the_rules_is_refused_in_french(started, preview):  # noqa: F811
    server, folder, _ = started
    store_language(folder, "fr")

    status, answer = upload(server, name="lebenslauf.exe")

    assert status == 400
    assert answer["fehler"] == (f"CV actuel, lebenslauf.exe{NBSP}: Ce type de fichier n'est pas accepté. "
                                f"Sont acceptés{NBSP}: PDF, Word (.docx, .doc) et fichiers texte (.txt).")


def test_the_same_document_twice_and_a_gone_one_are_refused_in_english(started, preview):  # noqa: F811
    server, folder, _ = started
    store_language(folder, "en")
    upload(server)

    assert upload(server)[1]["fehler"] == "Current CV, lebenslauf.pdf: This file is already included."
    assert call(server, "/api/angaben/unterlage-entfernen", {"datei": "dokumente/zeugnisse/weg.pdf"})[1]["fehler"] == (
        "This document does not exist (any more).")
    assert call(server, "/api/angaben/unterlage", {"category": "zeugnisse", "name": "z.pdf", "data": "%%%"})[1]["fehler"] == (
        "The file could not be read.")


def test_a_kind_the_file_cannot_have_is_refused_in_french(started, preview):  # noqa: F811
    server, folder, _ = started
    store_language(folder, "fr")
    upload(server, name="zeugnis.png", category="zeugnisse", data=PNG)

    status, answer = call(server, "/api/angaben/unterlage-art",
                          {"datei": "dokumente/zeugnisse/zeugnis.png", "category": "lebenslauf-bisher"})

    assert status == 400
    assert answer["fehler"] == (f"CV actuel, zeugnis.png{NBSP}: Ce type de fichier n'est pas accepté. "
                                f"Sont acceptés{NBSP}: PDF, Word (.docx, .doc) et fichiers texte (.txt).")


def test_answers_against_the_rules_name_the_field_in_french(started, preview):  # noqa: F811
    server, folder, _ = started
    store_language(folder, "fr")
    bundle = valid_bundle()
    bundle["data"]["person"]["email"] = "keine-adresse"

    status, answer = call(server, "/api/angaben/uebernehmen", {"bundle": bundle})

    example = catalog().text(FORM["formats"]["email"]["example"], "fr") or FORM["formats"]["email"]["example"]
    assert status == 400
    assert answer["fehler"] == f"Personne et contact, E-mail{NBSP}: Format non valable, par exemple{NBSP}: {example}."


def test_existing_files_ask_per_file_in_english(started, preview):  # noqa: F811
    server, folder, _ = started
    call(server, "/api/angaben/uebernehmen", {"bundle": valid_bundle()})
    store_language(folder, "en")

    status, answer = call(server, "/api/angaben/uebernehmen", {"bundle": valid_bundle()})

    assert status == 409
    assert answer["fehler"].startswith("These files exist already: suchprofil.md")
    assert answer["fehler"].endswith("Choose for each file whether it stays or is replaced; the old version is kept as a draft.")
    assert {choice["titel"] for choice in answer["wahl"]} <= {"Search profile", "Style profile", "Text blocks"}
    assert all(choice["datei"].endswith(".md") for choice in answer["wahl"])


def test_a_cv_that_stays_is_named_in_english(started, preview):  # noqa: F811
    server, folder, _ = started
    store_language(folder, "en")
    (folder / "cv.yaml").write_text("basics: [nicht: lesbar\n", encoding="utf-8")

    status, answer = call(server, "/api/angaben/uebernehmen", {"bundle": valid_bundle(), "ersetzen": True})

    assert status == 200 and answer["unveraendert"] == ["cv.yaml"]
    assert answer["hinweis"] == ("The CV (cv.yaml) stays as it was: the file cannot be read, so the details do not go "
                                 "into it. It can be changed under “Content as text”.")


def test_why_a_document_does_not_go_to_the_ai_is_said_in_french(started, preview):  # noqa: F811
    server, folder, _ = started
    store_language(folder, "fr")
    upload(server, name="zeugnis.png", category="zeugnisse", data=PNG)

    status, answer = call(server, routes_angaben.PREFILL_ESTIMATE_ROUTE)

    assert status == 200
    assert answer["nicht_gelesen"] == [{"name": "zeugnis.png", "grund": (
        f"Image{NBSP}: rien ne peut y être masqué, elle n'est donc pas envoyée à l'IA. Compléter les informations à la main.")}]


def test_the_prefill_asks_for_the_name_first_in_english(started, preview, monkeypatch):  # noqa: F811
    server, folder, _ = started
    store_language(folder, "en")
    install_client(monkeypatch, prefill_reply())
    upload(server, name="cv.txt", data=b"Text")

    status, answer = call(server, "/api/angaben/vorbefuellen", {"track": "job", "data": {}})

    assert status == 400
    assert answer["fehler"] == ("First enter the name under “Person and contact”: that way the app recognises it in the "
                                "documents and does not send it to the AI.")


def test_the_prefill_names_a_skipped_document_in_english(started, preview, monkeypatch):  # noqa: F811
    server, folder, _ = started
    store_language(folder, "en")
    install_client(monkeypatch, prefill_reply())
    upload(server, name="cv.txt", data="Erika Beispiel, Entwicklerin bei Muster GmbH seit 2019".encode())
    upload(server, name="alt.doc", category="anschreiben-bisher", data=b"Alt")

    status, answer = call(server, "/api/angaben/vorbefuellen", {"track": "job", "data": {"person": {"name": "Erika Beispiel"}}})

    assert status == 200
    assert answer["skipped"] == [{"name": "alt.doc", "reason": "Old Word format: save as PDF and upload again, or add the details by hand."}]


def test_everything_stays_german_with_the_preview_off(started, no_preview):  # noqa: F811
    server, folder, _ = started
    store_language(folder, "fr")
    upload(server, name="zeugnis.png", category="zeugnisse", data=PNG)

    assert upload(server, name="lebenslauf.exe")[1]["fehler"] == (
        "Bisheriger Lebenslauf, lebenslauf.exe: Dieser Dateityp geht nicht. Erlaubt sind PDF, Word (.docx, .doc) und "
        "Textdateien (.txt).")
    assert call(server, routes_angaben.PREFILL_ESTIMATE_ROUTE)[1]["nicht_gelesen"][0]["grund"] == (
        read_documents.IMAGE)
    assert call(server, "/api/angaben/unterlage-entfernen", {"datei": "x"})[1]["fehler"] == "Diese Unterlage gibt es nicht (mehr)."


def test_the_import_of_a_file_keeps_its_german_messages_for_the_skill(tmp_path):
    bundle = tmp_path / "einstieg.json"
    bundle.write_text("{kein json", encoding="utf-8")

    try:
        import_bundle.import_file(tmp_path / "daten", bundle, __import__("datetime").date(2026, 11, 24))
    except import_bundle.ImportRejected as rejected:
        assert rejected.messages == ["Die Datei ist keine gültige Einstiegsdatei (JSON)."]
        assert str(rejected) == "Die Datei ist keine gültige Einstiegsdatei (JSON)."
    else:
        raise AssertionError("not refused")


def test_no_changed_file_keeps_a_raw_no_break_space():
    files = [ONBOARDING / name for name in MESSAGE_MODULES] + [pathlib.Path(routes_angaben.__file__),
                                                               sprachen_pruefen.BASE / "sprachen" / "angaben.json"]

    assert [path.name for path in files if NBSP in path.read_text(encoding="utf-8")] == []
