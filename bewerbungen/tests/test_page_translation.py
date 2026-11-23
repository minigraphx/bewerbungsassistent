"""Pages in the app language (#414, G10): the server translates a page from the catalog and hands its scripts the
catalog as /uebersetzung.js. The switch stays off for users until #95 is done; the preview turns it on for development.
"""
import base64
import hashlib
import http.client
import json
import logging
import pathlib
import re
import subprocess
import threading
import types

import pytest

import app
import page_translation
import server as server_module
import translation_catalog
import ui_texts

HERE = pathlib.Path(__file__).parent
FIXTURES = HERE / "fixtures" / "sprachen"
TEXTE_JS = HERE.parent / "seiten" / "texte.js"
MISSING_TEXT = "Dieser Satz steht absichtlich nicht im Katalog."
ALL_PAGES = sorted({name for name in {**app.SEITEN, **app.QUESTIONS_PAGES}.values() if name.endswith(".html")}
                   | {app.DESKTOP_ONLY_PAGE})


def store_language(folder: pathlib.Path, language: str) -> None:
    (folder / "sprachen.yaml").write_text(f"app: {language}\n", encoding="utf-8")


@pytest.fixture
def folder(tmp_path):
    data = tmp_path / "daten"
    data.mkdir()
    return data


@pytest.fixture
def preview(monkeypatch):
    monkeypatch.setenv(ui_texts.PREVIEW_ENV, "1")


@pytest.fixture
def fixture_catalog(monkeypatch):
    monkeypatch.setattr(translation_catalog, "CATALOG_DIR", FIXTURES / "katalog")


@pytest.fixture
def serve(folder):
    """A server with the fixture page next to the pages of the app."""
    pages = {**app.SEITEN, **app.QUESTIONS_PAGES, "/probe": str(FIXTURES / "probe.html"),
             "/probe.js": str(FIXTURES / "probe.js")}
    s = server_module.Server(types.SimpleNamespace(daten=folder), {}, {}, pages)
    thread = threading.Thread(target=s.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    yield s
    s.shutdown()
    s.server_close()


def fetch(s, path: str, session: bool = True):
    port = s.server_address[1]
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
    headers = {"Host": f"127.0.0.1:{port}"}
    if session:
        connection.request("GET", f"/?t={s.token}", headers=headers)
        cookie = connection.getresponse()
        cookie.read()
        headers = {**headers, "Cookie": cookie.getheader("Set-Cookie").split(";", 1)[0]}
    connection.request("GET", path, headers=headers)
    answer = connection.getresponse()
    body = answer.read()
    connection.close()
    return answer.status, answer, body


def page_as_today(s, name: str) -> bytes:
    """What _seite served before #414: the file with the token, without the links to pages that are switched off."""
    html = (server_module.SEITEN / name).read_text(encoding="utf-8").replace("__TOKEN__", s.token)
    return html.encode("utf-8")


def path_of(name: str) -> str:
    return next((path for path, file in {**app.SEITEN, **app.QUESTIONS_PAGES}.items() if file == name), None)


# German stays byte for byte


@pytest.mark.parametrize("name", [name for name in ALL_PAGES if path_of(name)])
def test_a_page_in_german_is_byte_identical_with_the_preview_on(serve, folder, preview, name):
    store_language(folder, "de")

    status, _, body = fetch(serve, path_of(name))

    assert (status, body) == (200, page_as_today(serve, name))


@pytest.mark.parametrize("name", [name for name in ALL_PAGES if path_of(name)])
def test_the_switch_is_off_for_users_so_every_page_stays_german(serve, folder, monkeypatch, name):
    monkeypatch.delenv(ui_texts.PREVIEW_ENV, raising=False)
    store_language(folder, "fr")

    status, _, body = fetch(serve, path_of(name))

    assert (status, body) == (200, page_as_today(serve, name))


def test_every_page_of_the_app_stays_german_through_translate():
    for name in ALL_PAGES:
        html = (server_module.SEITEN / name).read_text(encoding="utf-8")
        assert page_translation.translate(html, "de") is html


# The language source


def test_the_switch_is_off_in_the_code():
    assert ui_texts.SWITCH_ON is False


def test_without_the_preview_the_app_speaks_german(folder, monkeypatch):
    monkeypatch.delenv(ui_texts.PREVIEW_ENV, raising=False)
    store_language(folder, "fr")

    assert ui_texts.sprache(types.SimpleNamespace(daten=folder)) == "de"


def test_the_preview_follows_the_stored_language(folder, preview):
    k = types.SimpleNamespace(daten=folder)
    assert ui_texts.sprache(k) == "de"

    store_language(folder, "en")
    assert ui_texts.sprache(k) == "en"

    store_language(folder, "fr")
    assert ui_texts.sprache(k) == "fr"


def test_the_preview_needs_exactly_one(folder, monkeypatch):
    monkeypatch.setenv(ui_texts.PREVIEW_ENV, "ja")
    store_language(folder, "fr")

    assert ui_texts.sprache(types.SimpleNamespace(daten=folder)) == "de"


def test_a_context_without_data_folder_speaks_german(preview):
    assert ui_texts.sprache(None) == "de"


# A page in French


def test_the_fixture_page_comes_in_french(serve, folder, preview, fixture_catalog):
    store_language(folder, "fr")

    status, answer, body = fetch(serve, "/probe")
    html = body.decode("utf-8")

    assert status == 200
    assert '<html lang="fr">' in html
    assert "<title>Page d'essai</title>" in html
    assert "<h1>Aperçu des candidatures</h1>" in html
    assert "<p>Enregistré &amp; sauvegardé.</p>" in html
    assert 'aria-label="Terme de recherche" placeholder="Par exemple informaticien"' in html
    assert 'alt="Logo de l&#x27;app"' in html
    assert '<button type="button" title="Recharger la liste">Recharger</button>' in html
    assert '<p data-text="fragen.label">Votre question</p>' in html
    assert f"<p>{MISSING_TEXT}</p>" in html  # a missing entry stays German
    assert "<p>Bewerbungsbegleiter</p>" in html
    assert "<style>/* Neu laden */</style>" in html  # styles and scripts are never touched
    assert "script-src 'self'" in answer.getheader("Content-Security-Policy")


def test_the_catalog_script_comes_right_before_the_first_script(serve, folder, preview, fixture_catalog):
    store_language(folder, "en")

    _, _, body = fetch(serve, "/probe")

    assert '<script src="/uebersetzung.js?sprache=en"></script>\n<script src="/texte.js"></script>' in body.decode("utf-8")
    assert '<html lang="en">' in body.decode("utf-8")


def test_the_catalog_script_holds_the_texts_of_one_language(serve, fixture_catalog):
    status, answer, body = fetch(serve, "/uebersetzung.js?sprache=fr", session=False)
    script = body.decode("utf-8")

    assert status == 200
    assert answer.getheader("Content-Type").startswith("text/javascript")
    assert '"Abgabe bis {datum}": "À remettre d\'ici le {datum}"' in script
    assert '"fragen.label": {"sie": "Votre question", "du": "Ta question"}' in script
    assert "Due by" not in script


@pytest.mark.parametrize("query", ["?sprache=de", "?sprache=it", ""])
def test_the_catalog_script_only_exists_for_french_and_english(serve, query):
    status, _, _ = fetch(serve, f"/uebersetzung.js{query}", session=False)

    assert status == 404


def test_texte_t_speaks_french_on_the_served_page_and_falls_back_to_german(serve, folder, preview, fixture_catalog,
                                                                           tmp_path):
    store_language(folder, "fr")
    _, _, page = fetch(serve, "/probe")
    source = re.search(r'<script src="(/uebersetzung\.js\?sprache=\w+)"></script>', page.decode("utf-8")).group(1)
    _, _, script = fetch(serve, source, session=False)
    (tmp_path / "uebersetzung.js").write_bytes(script)
    lang = re.search(r'<html lang="(\w+)">', page.decode("utf-8")).group(1)
    run = ("const vm = require('node:vm'); const fs = require('node:fs');"
           "const [texte, uebersetzung, lang] = process.argv.slice(1);"
           "const context = { document: { documentElement: { lang } } }; context.window = context;"
           "vm.createContext(context);"
           "vm.runInContext(fs.readFileSync(uebersetzung, 'utf8'), context);"
           "vm.runInContext(fs.readFileSync(texte, 'utf8'), context);"
           "const T = context.Texte;"
           "process.stdout.write(JSON.stringify([T.t('Abgabe bis {datum}', { datum: '20.11.2026' }),"
           " T.t('Nicht im Katalog: {anzahl}', { anzahl: 3 }), T.text('fragen.label', 'stelle-du')]));")

    result = subprocess.run(["node", "-e", run, str(TEXTE_JS), str(tmp_path / "uebersetzung.js"), lang],
                            capture_output=True, text=True, check=True)

    assert json.loads(result.stdout) == ["À remettre d'ici le 20.11.2026", "Nicht im Katalog: 3", "Ta question"]


def test_meine_angaben_keeps_its_own_policy_and_inline_script(serve, folder, preview, fixture_catalog):
    store_language(folder, "fr")

    status, answer, body = fetch(serve, "/angaben")
    html = body.decode("utf-8")

    assert status == 200
    assert html.index('<script src="/uebersetzung.js?sprache=fr"></script>') < html.index('<script src="/texte.js">')
    policy = answer.getheader("Content-Security-Policy")
    assert "script-src 'self'" in policy
    inline = re.findall(r"<script>(.*?)</script>", html, re.S) + re.findall(r"<style>(.*?)</style>", html, re.S)
    assert len(inline) == 2
    for content in inline:
        digest = base64.b64encode(hashlib.sha256(content.encode("utf-8")).digest()).decode("ascii")
        assert f"'sha256-{digest}'" in policy


def test_a_broken_catalog_leaves_the_page_german_and_says_why(serve, folder, preview, monkeypatch, tmp_path, caplog):
    (tmp_path / "kaputt.json").write_text("{", encoding="utf-8")
    monkeypatch.setattr(translation_catalog, "CATALOG_DIR", tmp_path)
    store_language(folder, "fr")

    with caplog.at_level(logging.ERROR, logger="bewerbungsbegleiter"):
        status, _, body = fetch(serve, "/probe")

    assert status == 200
    assert "<h1>Bewerbungen im Überblick</h1>" in body.decode("utf-8")
    assert "kaputt.json" in caplog.text


# The verifier's two gaps of #414 (fixed with #415)


def test_a_single_quoted_attribute_is_translated_like_a_double_quoted_one():
    html = "<button type='button' title='Liste neu laden'>Neu laden</button><img alt='Zeichen der App'>"

    translated = page_translation.translate(html, "fr", translation_catalog.load(FIXTURES / "katalog"))

    assert translated == ("<button type='button' title='Recharger la liste'>Recharger</button>"
                          "<img alt='Logo de l&#x27;app'>")
    assert {found.text for found in page_translation.page_texts(html)} == {"Liste neu laden", "Neu laden",
                                                                           "Zeichen der App"}


def test_textarea_content_is_the_persons_and_stays_while_its_placeholder_is_translated():
    html = ('<textarea placeholder="Zum Beispiel Informatiker">Neu laden\n<script>Neu laden</script></textarea>'
            '<p>Neu laden</p><script src="/texte.js"></script>')

    translated = page_translation.translate(html, "fr", translation_catalog.load(FIXTURES / "katalog"))

    assert translated == ('<textarea placeholder="Par exemple informaticien">Neu laden\n<script>Neu laden</script>'
                          '</textarea><p>Recharger</p><script src="/uebersetzung.js?sprache=fr"></script>\n'
                          '<script src="/texte.js"></script>')
    assert [found.text for found in page_translation.page_texts(html)] == ["Zum Beispiel Informatiker", "Neu laden"]
