"""The window „KI einrichten“ (G60, #272): a feature that needs the AI while none is set up or agreed to tells the page
to open it, an invitation link keeps its request through the link with the token, and every page can load it."""
import shutil

import pytest

from ai import connection, consent, errors
from ai.connection import ACCESS_VARIABLE, KEY_VARIABLE, URL_VARIABLE
from sample_folder import BRIEF_ID
from test_ai_tasks import VORLAGEN
from test_app import anfrage, get, post, server  # noqa: F401  (server is a fixture)

SETUP = errors.SETUP_ACTION


@pytest.fixture
def without_ai(server, monkeypatch):  # noqa: F811
    daten = server.kontext.daten
    shutil.copy(VORLAGEN / "suchprofil.md", daten / "suchprofil.md")
    shutil.copytree(VORLAGEN / "anschreiben", daten / "anschreiben", dirs_exist_ok=True)
    (daten / "bewerbungen" / BRIEF_ID / "stelle.md").write_text("Data Engineer, Python.", encoding="utf-8")
    for name in (URL_VARIABLE, ACCESS_VARIABLE, KEY_VARIABLE):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr("ai.connection._keyring_access", lambda: None)
    return server


def test_the_action_names_the_window():
    assert SETUP == "ki-einrichten"


def test_a_feature_without_ai_asks_the_page_to_open_the_window(without_ai):
    status, answer = post(without_ai, "/api/ki/bewerten", {}, id=BRIEF_ID)

    assert status == 400
    assert answer["aktion"] == SETUP
    assert answer["fehler"] == errors.NOT_SET_UP
    assert "KI einrichten" in errors.NOT_SET_UP and "Erweiterte Einstellungen" not in errors.NOT_SET_UP


@pytest.mark.real_consent
def test_a_feature_without_consent_asks_for_the_window_too(without_ai, monkeypatch):
    monkeypatch.setenv(KEY_VARIABLE, "sk-test")

    status, answer = post(without_ai, "/api/ki/bewerten", {}, id=BRIEF_ID)

    assert status == 400 and answer["aktion"] == SETUP and answer["fehler"] == consent.MISSING
    assert "KI einrichten" in consent.MISSING


def test_other_errors_name_no_action(without_ai, monkeypatch):
    monkeypatch.setenv(KEY_VARIABLE, "sk-test")
    (without_ai.kontext.daten / "bewerbungen" / BRIEF_ID / "stelle.md").unlink()

    status, answer = post(without_ai, "/api/ki/bewerten", {}, id=BRIEF_ID)

    assert status == 400 and "aktion" not in answer


@pytest.mark.real_consent
def test_both_reasons_are_setup_errors(tmp_path, monkeypatch):
    for name in (URL_VARIABLE, ACCESS_VARIABLE, KEY_VARIABLE):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(errors.SetupNeeded):
        connection.find_connection({}, keyring_access=lambda: None)
    with pytest.raises(errors.SetupNeeded):
        consent.require(tmp_path, "stelle")


def test_the_link_with_the_token_keeps_the_request_for_the_window(server):  # noqa: F811
    status, _, _, answer = anfrage(server, "GET", f"/?t={server.token}&ki=einrichten")

    assert status == 303 and answer.getheader("Location") == "/?ki=einrichten"


@pytest.mark.parametrize("script", ["/ki-fenster.js", "/ki-zugang.js", "/einwilligung.js"])
def test_every_page_can_load_the_window(server, script):  # noqa: F811
    assert get(server, script)[0] == 200
