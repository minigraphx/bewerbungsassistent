"""The refusals of the photo crop and the Git errors of versionen.py in French and English (#455, G10).

lebenslauf/fotoausschnitt.py and build.py refuse a crop, and build.py a heading of x-beschriftungen, in German, since
lebenslauf runs on its own and never imports the app. The app says those refusals in its language wherever it shows
them: the page Foto, „Unterlagen erstellen“ for two files as for a dossier, „Inhalte als Text“ and the preview in
„Lebenslauf erstellen“. A failed Git commit after sending shows its frame in the app language too; what Git itself
wrote stays as Git wrote it. With the preview off, and for lebenslauf on its own, every message stays German byte for
byte. Field names, values and paths are data and stay as written. All data is invented; Git runs only in temporary
folders.
"""
import ast
import datetime
import json
import shutil
import threading

import pytest

import app
import build
import fotoausschnitt
import refusal_messages
import sprachen_pruefen
import translation_catalog
import unterlagen
import versionen
from ablage import Ablage
from kontext import Kontext
from sample_folder import BRIEF_ID
from test_app import get, post, server  # noqa: F401  (server is a fixture)
from test_cv_preview import PREVIEW, choice, form
from test_today_languages import no_preview, preview, store_language  # noqa: F401  (fixtures)
from ui_message import T

NBSP = chr(0xA0)
LEBENSLAUF = sprachen_pruefen.ROOT / "lebenslauf"
LEBENSLAUF_FILES = (LEBENSLAUF / "fotoausschnitt.py", LEBENSLAUF / "build.py", LEBENSLAUF / "refusal.py")
MODULE_FILE = sprachen_pruefen.BASE / "refusal_messages.py"
needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="Git is not installed")


def catalog() -> translation_catalog.Catalog:
    return translation_catalog.load(translation_catalog.CATALOG_DIR)


def said(message, language: str) -> str:
    return str(message) if language == "de" else message.in_language(catalog(), language)


def refusal(call) -> str:
    """The message `call` is refused with once the app has said it: the first argument of its ValueError."""
    with pytest.raises(ValueError) as refused_:
        with refusal_messages.in_app_language():
            call()
    return refused_.value.args[0]


def refused(s, path: str, body, status: int = 400, **parameter) -> str:
    code, answer = post(s, path, body, **parameter)
    assert code == status, answer
    return answer["fehler"]


def refused_get(s, path: str, status: int = 400, **parameter) -> str:
    code, _, body = get(s, path, **parameter)
    assert code == status, body
    return json.loads(body)["fehler"]


def cv_with(folder, lines: str) -> None:
    """cv.yaml of the folder with `lines` added under basics, or at the top level when they are not indented."""
    cv = folder / "cv.yaml"
    text = cv.read_text(encoding="utf-8")
    added = text.replace("basics:\n", f"basics:\n{lines}", 1) if lines.startswith("  ") else lines + text
    cv.write_text(added, encoding="utf-8")


@pytest.fixture
def cv_file(tmp_path):
    cv = tmp_path / "cv.yaml"
    cv.write_text("basics:\n  name: Erika Muster\n", encoding="utf-8")
    return cv


# The files


def test_the_crop_modules_and_the_messages_are_finished():
    finished = {path.resolve() for path in sprachen_pruefen.FERTIG}

    assert {path.resolve() for path in (*LEBENSLAUF_FILES[:2], MODULE_FILE)} <= finished


def test_the_crop_modules_and_the_messages_have_no_gap():
    assert [str(gap) for gap in sprachen_pruefen.gaps((*LEBENSLAUF_FILES, MODULE_FILE), catalog())] == []


def test_every_source_includes_the_crop_modules_so_their_entries_are_no_orphans():
    assert set(LEBENSLAUF_FILES[:2]) <= set(sprachen_pruefen.app_sources())


@pytest.mark.parametrize("path", LEBENSLAUF_FILES, ids=lambda path: path.name)
def test_lebenslauf_imports_nothing_of_the_app(path):
    app_modules = {module.stem for module in sprachen_pruefen.BASE.glob("*.py")}
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import)
                for alias in node.names}
    imported |= {node.module.split(".")[0] for node in ast.walk(tree)
                 if isinstance(node, ast.ImportFrom) and node.module}

    assert imported & app_modules == set()


# Each refusal of the crop in the three languages, and German on its own as before

CROP_REFUSALS = {
    "no mapping": (lambda: build.pruefe_foto_optionen(["zoom"]), {
        "de": "basics.x-image muss eine Zuordnung sein, z.B. {mirror: true, zoom: 1.3}",
        "fr": f"basics.x-image doit être un mappage, p.{NBSP}ex. {{mirror: true, zoom: 1.3}}",
        "en": "basics.x-image must be a mapping, e.g. {mirror: true, zoom: 1.3}",
    }),
    "unknown fields": (lambda: build.pruefe_foto_optionen({"mirror": True, "spiegeln": True, "drehen": 90}), {
        "de": "basics.x-image: unbekannte Felder ['drehen', 'spiegeln']; erlaubt sind mirror, zoom, x, y",
        "fr": f"basics.x-image{NBSP}: champs inconnus ['drehen', 'spiegeln']{NBSP}; champs autorisés{NBSP}: "
              "mirror, zoom, x, y",
        "en": "basics.x-image: unknown fields ['drehen', 'spiegeln']; allowed: mirror, zoom, x, y",
    }),
    "mirror no yes or no": (lambda: build.pruefe_foto_optionen({"mirror": "ja"}), {
        "de": "basics.x-image.mirror muss true oder false sein",
        "fr": "basics.x-image.mirror doit être true ou false",
        "en": "basics.x-image.mirror must be true or false",
    }),
    "zoom out of range": (lambda: build.pruefe_foto_optionen({"zoom": 5}), {
        "de": "basics.x-image.zoom muss eine Zahl von 1 bis 4 sein, nicht 5",
        "fr": "basics.x-image.zoom doit être un nombre de 1 à 4, et non 5",
        "en": "basics.x-image.zoom must be a number from 1 to 4, not 5",
    }),
    "x no number": (lambda: build.pruefe_foto_optionen({"x": "links"}), {
        "de": "basics.x-image.x muss eine Zahl von 0 bis 1 sein, nicht 'links'",
        "fr": "basics.x-image.x doit être un nombre de 0 à 1, et non 'links'",
        "en": "basics.x-image.x must be a number from 0 to 1, not 'links'",
    }),
    "values missing": (lambda: fotoausschnitt.optionen_aus_anfrage({"zoom": "1", "x": "0.5"}), {
        "de": "Es fehlen Werte: mirror, y",
        "fr": f"Il manque des valeurs{NBSP}: mirror, y",
        "en": "Missing values: mirror, y",
    }),
    "mirror of a request": (lambda: fotoausschnitt.optionen_aus_anfrage(
            {"mirror": "vielleicht", "zoom": "1", "x": "0.5", "y": "0.5"}), {
        "de": "mirror muss true oder false sein",
        "fr": "mirror doit être true ou false",
        "en": "mirror must be true or false",
    }),
    "number of a request": (lambda: fotoausschnitt.optionen_aus_anfrage(
            {"mirror": "false", "zoom": "gross", "x": "0.5", "y": "0.5"}), {
        "de": "zoom muss eine Zahl sein, nicht 'gross'",
        "fr": "zoom doit être un nombre, et non 'gross'",
        "en": "zoom must be a number, not 'gross'",
    }),
    "headings no mapping": (lambda: build.pruefe_beschriftungen("Schule"), {
        "de": "x-beschriftungen muss eine Zuordnung sein, z.B. {erfahrung: Schnupperlehren & Erfahrungen}",
        "fr": f"x-beschriftungen doit être un mappage, p.{NBSP}ex. {{erfahrung: Stages d'orientation & expériences}}",
        "en": "x-beschriftungen must be a mapping, e.g. {erfahrung: Trial apprenticeships & experience}",
    }),
    "headings of unknown sections": (lambda: build.pruefe_beschriftungen({"hobbys": "Freizeit"}), {
        "de": "x-beschriftungen: unbekannte Abschnitte ['hobbys']; erlaubt sind " + ", ".join(build.ABSCHNITTE),
        "fr": f"x-beschriftungen{NBSP}: sections inconnues ['hobbys']{NBSP}; sections autorisées{NBSP}: "
              + ", ".join(build.ABSCHNITTE),
        "en": "x-beschriftungen: unknown sections ['hobbys']; allowed: " + ", ".join(build.ABSCHNITTE),
    }),
    "heading empty": (lambda: build.pruefe_beschriftungen({"erfahrung": " "}), {
        "de": "x-beschriftungen.erfahrung muss ein nicht leerer Text sein",
        "fr": "x-beschriftungen.erfahrung doit être un texte non vide",
        "en": "x-beschriftungen.erfahrung must be non-empty text",
    }),
    "heading too long": (lambda: build.pruefe_beschriftungen({"erfahrung": "x" * (build.MAX_BESCHRIFTUNG + 1)}), {
        "de": f"x-beschriftungen.erfahrung darf höchstens {build.MAX_BESCHRIFTUNG} Zeichen haben",
        "fr": f"x-beschriftungen.erfahrung ne doit pas dépasser {build.MAX_BESCHRIFTUNG} caractères",
        "en": f"x-beschriftungen.erfahrung may have at most {build.MAX_BESCHRIFTUNG} characters",
    }),
}


@pytest.mark.parametrize("language", ["de", "fr", "en"])
@pytest.mark.parametrize("case", CROP_REFUSALS)
def test_each_refusal_of_the_crop_is_said_in_the_app_language(case, language):
    call, words = CROP_REFUSALS[case]

    assert said(refusal(call), language) == words[language]


@pytest.mark.parametrize("case", CROP_REFUSALS)
def test_on_its_own_lebenslauf_refuses_in_german_byte_for_byte(case):
    call, words = CROP_REFUSALS[case]

    with pytest.raises(ValueError) as refused_:
        call()

    assert str(refused_.value) == words["de"]
    assert type(refused_.value.args[0]) is str


@pytest.mark.parametrize("language", ["de", "fr", "en"])
def test_without_a_cv_the_crop_is_refused_in_the_app_language(language, tmp_path):
    assert said(refusal(lambda: fotoausschnitt.lies_foto(tmp_path / "cv.yaml")), language) == {
        "de": "Es gibt noch keinen Lebenslauf. Bitte zuerst die Angaben erfassen.",
        "fr": "Il n'y a pas encore de CV. Merci de saisir d'abord les informations.",
        "en": "There is no CV yet. Please enter the details first.",
    }[language]


@pytest.mark.parametrize("language", ["de", "fr", "en"])
def test_a_cv_without_photo_is_named_in_the_app_language_with_its_path(language, cv_file):
    assert said(refusal(lambda: fotoausschnitt.lies_foto(cv_file)), language) == {
        "de": f"{cv_file}: basics.image fehlt, es gibt kein Foto zum Zuschneiden",
        "fr": f"{cv_file}{NBSP}: basics.image manque, il n'y a pas de photo à recadrer",
        "en": f"{cv_file}: basics.image is missing, there is no photo to crop",
    }[language]


@pytest.mark.parametrize("language", ["de", "fr", "en"])
def test_a_photo_that_is_gone_is_named_in_the_app_language_with_its_path(language, cv_file):
    cv_file.write_text("basics:\n  image: foto.png\n", encoding="utf-8")
    photo = cv_file.parent / "foto.png"

    assert said(refusal(lambda: fotoausschnitt.lies_foto(cv_file)), language) == {
        "de": f"Foto nicht gefunden: {photo}",
        "fr": f"Photo introuvable{NBSP}: {photo}",
        "en": f"Photo not found: {photo}",
    }[language]


def test_the_german_of_the_photo_and_the_cv_stays_as_before(cv_file):
    with pytest.raises(ValueError) as without_photo:
        fotoausschnitt.lies_foto(cv_file)
    cv_file.write_text("basics:\n  image: foto.png\n", encoding="utf-8")
    with pytest.raises(ValueError) as gone:
        fotoausschnitt.lies_foto(cv_file)

    assert str(without_photo.value) == f"{cv_file}: basics.image fehlt, es gibt kein Foto zum Zuschneiden"
    assert str(gone.value) == f"Foto nicht gefunden: {cv_file.parent / 'foto.png'}"


def test_other_errors_pass_unchanged():
    with pytest.raises(KeyError, match="anders"):
        with refusal_messages.in_app_language():
            raise KeyError("anders")


# The routes: the page Foto


def test_the_page_foto_refuses_a_crop_in_french(server, preview):  # noqa: F811
    store_language(server.kontext.daten, "fr")

    assert refused(server, "/api/foto/speichern", {"mirror": True, "zoom": 9, "x": 0.5, "y": 0.5}) == (
        "basics.x-image.zoom doit être un nombre de 1 à 4, et non 9")
    assert refused_get(server, "/api/foto/vorschau.png", mirror="false", zoom="gross", x="0.5", y="0.5") == (
        "zoom doit être un nombre, et non 'gross'")


def test_the_page_foto_names_a_photo_that_is_gone_in_english(server, preview):  # noqa: F811
    store_language(server.kontext.daten, "en")
    photo = server.kontext.daten / "foto.png"
    photo.unlink()

    assert refused_get(server, "/api/foto/optionen") == f"Photo not found: {photo}"


def test_the_page_foto_stays_german_with_the_preview_off(server, no_preview):  # noqa: F811
    store_language(server.kontext.daten, "fr")

    assert refused(server, "/api/foto/speichern", {"mirror": "ja", "zoom": 1, "x": 0.5, "y": 0.5}) == (
        "basics.x-image.mirror muss true oder false sein")
    assert refused_get(server, "/api/foto/vorschau.png", zoom="1", x="0.5") == "Es fehlen Werte: mirror, y"


# The routes that build a CV: Unterlagen erstellen, Inhalte als Text and the preview in Lebenslauf erstellen


def test_unterlagen_erstellen_names_a_bad_crop_in_french(server, preview):  # noqa: F811
    store_language(server.kontext.daten, "fr")
    cv_with(server.kontext.daten, "  x-image: {mirror: ja}\n")

    assert refused(server, "/api/unterlagen", {}, id=BRIEF_ID) == "basics.x-image.mirror doit être true ou false"


def test_unterlagen_erstellen_names_a_bad_heading_of_a_dossier_in_english(server, preview):  # noqa: F811
    store_language(server.kontext.daten, "en")
    register = server.kontext.register()
    register.speichere({**register.hole(BRIEF_ID), "unterlagen": "dossier"})
    cv_with(server.kontext.daten, "x-beschriftungen: {erfahrung: ''}\n")

    assert refused(server, "/api/unterlagen", {}, id=BRIEF_ID) == (
        "x-beschriftungen.erfahrung must be non-empty text")


def test_unterlagen_erstellen_names_a_bad_crop_in_german_with_the_preview_off(server, no_preview):  # noqa: F811
    store_language(server.kontext.daten, "en")
    cv_with(server.kontext.daten, "  x-image: {zoom: 9}\n")

    status, answer = post(server, "/api/unterlagen", {}, id=BRIEF_ID)

    assert status == 400
    assert json.dumps(answer, ensure_ascii=False) == (
        '{"fehler": "basics.x-image.zoom muss eine Zahl von 1 bis 4 sein, nicht 9"}')


def test_inhalte_als_text_names_a_bad_crop_in_english(server, preview):  # noqa: F811
    store_language(server.kontext.daten, "en")
    text = (server.kontext.daten / "cv.yaml").read_text(encoding="utf-8").replace(
        "basics:\n", "basics:\n  x-image: {zoom: 9}\n", 1)

    assert refused(server, "/api/inhalt/pruefen", {"text": text}, datei="cv.yaml") == (
        "basics.x-image.zoom must be a number from 1 to 4, not 9")


def test_the_preview_in_lebenslauf_erstellen_names_a_bad_crop_in_french(server, preview):  # noqa: F811
    store_language(server.kontext.daten, "fr")
    cv_with(server.kontext.daten, "  x-image: {spiegel: ja}\n")

    status, answer = post(server, PREVIEW, choice(form(server)))

    assert status == 400, answer
    assert answer["fehler"] == (f"basics.x-image{NBSP}: champs inconnus ['spiegel']{NBSP}; champs autorisés{NBSP}: "
                                "mirror, zoom, x, y")


# The Git errors of versionen.py


@pytest.fixture
def git_home(tmp_path, monkeypatch):
    """Git without the person's own configuration: a home of its own and no system file."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


class CommitRefused(versionen.GitVersionen):
    """Real Git in a temporary folder whose commit Git refuses: it takes no commit with an empty message."""

    def friere_ein(self, pfade, nachricht):
        return super().friere_ein(pfade, "")


def git_failure(call) -> T:
    with pytest.raises(RuntimeError) as failed:
        call()
    return failed.value.args[0]


@needs_git
@pytest.mark.parametrize("language", ["de", "fr", "en"])
def test_a_failed_git_command_is_said_in_the_app_language_with_what_git_wrote(language, tmp_path, git_home):
    (tmp_path / "cv.yaml").write_text("basics: {}\n", encoding="utf-8")
    versions = versionen.GitVersionen(tmp_path)
    versions.friere_ein([tmp_path / "cv.yaml"], "Erster Stand")

    message = git_failure(lambda: versions.inhalt("abcdef1", "cv.yaml"))
    git_wrote = message.values["meldung"]

    assert git_wrote and "abcdef1" in git_wrote
    assert said(message, language) == {
        "de": f"git show fehlgeschlagen: {git_wrote}",
        "fr": f"git show a échoué{NBSP}: {git_wrote}",
        "en": f"git show failed: {git_wrote}",
    }[language]


@needs_git
@pytest.mark.parametrize("language", ["de", "fr", "en"])
def test_a_refused_commit_is_said_in_the_app_language_with_what_git_wrote(language, tmp_path, git_home):
    (tmp_path / "cv.yaml").write_text("basics: {}\n", encoding="utf-8")

    message = git_failure(lambda: CommitRefused(tmp_path).friere_ein([tmp_path / "cv.yaml"], "Versand"))
    git_wrote = message.values["meldung"]

    assert git_wrote
    assert said(message, language) == {
        "de": f"Git-Commit fehlgeschlagen: {git_wrote}",
        "fr": f"Le commit Git a échoué{NBSP}: {git_wrote}",
        "en": f"Git commit failed: {git_wrote}",
    }[language]


@pytest.fixture
def refusing_git(datenordner, tmp_path, git_home):
    """The app whose data folder has Git, but every commit is refused."""
    k =Kontext(daten=datenordner.resolve(), build=(tmp_path / "build").resolve(), ablage=Ablage(datenordner),
                versionierung=CommitRefused(datenordner), heute=lambda: datetime.date(2026, 10, 26))
    s = app.erstelle_server(datenordner, kontext=k)
    thread = threading.Thread(target=s.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    yield s
    s.shutdown()
    s.server_close()


def sent_hints(s) -> list[str]:
    status, built = post(s, "/api/unterlagen", {}, id=BRIEF_ID)
    assert status == 200, built
    status, answer = post(s, "/api/versand", {"datum": "2026-10-26", "art": "elektronisch"}, id=BRIEF_ID)
    assert status == 200, answer
    return answer["hinweise"]


@needs_git
def test_sending_names_a_refused_commit_in_french_and_keeps_what_git_wrote(refusing_git, preview):  # noqa: F811
    store_language(refusing_git.kontext.daten, "fr")

    hint, = [hint for hint in sent_hints(refusing_git) if "Git" in hint]

    frame = f"Envoi enregistré, mais pas figé dans Git{NBSP}: Le commit Git a échoué{NBSP}: "
    assert hint.startswith(frame), hint
    assert len(hint) > len(frame)
    assert "fehlgeschlagen" not in hint


@needs_git
def test_sending_names_a_refused_commit_in_english(refusing_git, preview):  # noqa: F811
    store_language(refusing_git.kontext.daten, "en")

    hint, = [hint for hint in sent_hints(refusing_git) if "Git" in hint]

    assert hint.startswith("Recorded as sent, but not frozen in Git: Git commit failed: "), hint


@needs_git
def test_sending_names_a_refused_commit_in_german_with_the_preview_off(refusing_git, no_preview):  # noqa: F811
    store_language(refusing_git.kontext.daten, "fr")

    hint, = [hint for hint in sent_hints(refusing_git) if "Git" in hint]

    assert hint.startswith("Versand erfasst, aber nicht in Git eingefroren: Git-Commit fehlgeschlagen: "), hint
    assert unterlagen.pdf_pfade(refusing_git.kontext.daten, BRIEF_ID)["lebenslauf"].is_file()
