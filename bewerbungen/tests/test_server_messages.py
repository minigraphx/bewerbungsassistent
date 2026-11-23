"""Server messages in the app language (#415, G10, docs/design/sprachen.md).

A route says a message for the person as `ui_texts.T(template, **values)`: German as a string, so the code reads it as
before, and translatable, because it keeps its template. The server says errors and the T messages of an answer in the
app language; a plain German error constant by exact match. Data values are never translated, even when they equal a
catalog key. The switch stays off for users until #95 is done; the fixture routes here use the preview.
"""
import copy
import http.client
import json
import logging
import pathlib
import pickle
import threading
import types

import pytest

import server as server_module
import translation_catalog
import ui_texts
from ui_texts import T

FIXTURE_CATALOG = pathlib.Path(__file__).parent / "fixtures" / "sprachen" / "katalog"
DUE = "Abgabe bis {datum}"
DUE_FR = "À remettre d'ici le 20.11.2026"
DUE_DE = "Abgabe bis 20.11.2026"
VALUE = "Bitte einen Wert angeben."
VALUE_FR = "Merci d'indiquer une valeur."
LOCKED = "Die Datei ist gesperrt."
LOCKED_FR = "Le fichier est verrouillé."


def catalog() -> translation_catalog.Catalog:
    return translation_catalog.load(FIXTURE_CATALOG)


# T keeps German and its template


def test_t_is_the_german_text_and_keeps_template_and_values():
    message = T(DUE, datum="20.11.2026")

    assert message == DUE_DE
    assert isinstance(message, str)
    assert (message.template, message.values) == (DUE, {"datum": "20.11.2026"})


def test_an_error_with_a_t_reads_as_before():
    assert str(ValueError(T(DUE, datum="20.11.2026"))) == DUE_DE


def test_t_fills_only_the_placeholders_it_has_values_for():
    assert T("{anzahl} von {gesamt} offen", anzahl=3) == "3 von {gesamt} offen"


def test_t_survives_copy_and_pickle():
    message = T(DUE, datum="20.11.2026")

    for again in (copy.deepcopy(message), pickle.loads(pickle.dumps(message))):
        assert (again, again.template, again.values) == (DUE_DE, DUE, {"datum": "20.11.2026"})


# uebersetze for direct callers


def test_uebersetze_says_a_t_in_french_with_its_values():
    assert ui_texts.uebersetze(T(DUE, datum="20.11.2026"), "fr", catalog()) == DUE_FR


def test_uebersetze_translates_a_t_inside_the_values():
    message = T(DUE, datum=T(VALUE))

    assert ui_texts.uebersetze(message, "fr", catalog()) == f"À remettre d'ici le {VALUE_FR}"


def test_uebersetze_takes_a_plain_german_text_by_exact_match():
    assert ui_texts.uebersetze(LOCKED, "fr", catalog()) == LOCKED_FR
    assert ui_texts.uebersetze(LOCKED + " ", "fr", catalog()) == LOCKED + " "


def test_uebersetze_keeps_german_and_a_text_without_entry():
    message = T(DUE, datum="20.11.2026")

    assert ui_texts.uebersetze(message, "de", catalog()) is message
    assert ui_texts.uebersetze(T("Nicht im Katalog {n}", n=2), "en", catalog()) == "Nicht im Katalog 2"


def test_uebersetze_keeps_german_with_a_broken_catalog_and_says_why(monkeypatch, tmp_path, caplog):
    (tmp_path / "kaputt.json").write_text("{", encoding="utf-8")
    monkeypatch.setattr(translation_catalog, "CATALOG_DIR", tmp_path)

    with caplog.at_level(logging.ERROR, logger="bewerbungsbegleiter"):
        assert ui_texts.uebersetze(LOCKED, "fr") == LOCKED
    assert "kaputt.json" in caplog.text


def test_translate_marked_changes_only_t_and_leaves_data_values():
    payload = {"hinweis": T(DUE, datum="20.11.2026"), "stand": LOCKED, "liste": [VALUE, T(VALUE)], "paar": (T(VALUE), 1)}

    translated = ui_texts.translate_marked(payload, "fr", catalog())

    assert translated == {"hinweis": DUE_FR, "stand": LOCKED, "liste": [VALUE, VALUE_FR], "paar": (VALUE_FR, 1)}
    assert payload["hinweis"] == DUE_DE  # the route's value stays as it was


# Fixture routes through the server


def raises_template(k, parameter, body):
    raise ValueError(T(DUE, datum="20.11.2026"))


def raises_constant(k, parameter, body):
    raise ValueError(LOCKED)


def raises_not_found(k, parameter, body):
    raise server_module.NichtGefunden(T(VALUE))


def raises_status(k, parameter, body):
    raise server_module.StatusError(T(VALUE), 409)


def raises_action(k, parameter, body):
    raise server_module.ActionError(T(VALUE), "ki-einrichten")


HINT_PAYLOAD = {"hinweis": T(DUE, datum="20.11.2026"), "stand": LOCKED,
                "befunde": [{"titel": VALUE, "text": T(VALUE)}]}


def returns_hint(k, parameter, body):
    return server_module.json_antwort(HINT_PAYLOAD)


ROUTES = {"/api/probe/vorlage": raises_template, "/api/probe/konstante": raises_constant,
          "/api/probe/fehlt": raises_not_found, "/api/probe/status": raises_status,
          "/api/probe/aktion": raises_action, "/api/probe/hinweis": returns_hint}


@pytest.fixture
def folder(tmp_path):
    data = tmp_path / "daten"
    data.mkdir()
    return data


@pytest.fixture
def fixture_catalog(monkeypatch):
    monkeypatch.setattr(translation_catalog, "CATALOG_DIR", FIXTURE_CATALOG)


@pytest.fixture
def serve(folder):
    s = server_module.Server(types.SimpleNamespace(daten=folder), ROUTES, {}, {})
    thread = threading.Thread(target=s.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    yield s
    s.shutdown()
    s.server_close()


def store_language(folder: pathlib.Path, language: str) -> None:
    (folder / "sprachen.yaml").write_text(f"app: {language}\n", encoding="utf-8")


def get(s, path: str, token: bool = True):
    port = s.server_address[1]
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
    connection.request("GET", f"{path}?t={s.token}" if token else path, headers={"Host": f"127.0.0.1:{port}"})
    answer = connection.getresponse()
    body = answer.read()
    connection.close()
    return answer.status, body


def answers(s) -> dict:
    return {path: (status, json.loads(body)) for path in ROUTES for status, body in [get(s, path)]}


GERMAN = {
    "/api/probe/vorlage": (400, {"fehler": DUE_DE}),
    "/api/probe/konstante": (400, {"fehler": LOCKED}),
    "/api/probe/fehlt": (404, {"fehler": VALUE}),
    "/api/probe/status": (409, {"fehler": VALUE}),
    "/api/probe/aktion": (400, {"fehler": VALUE, "aktion": "ki-einrichten"}),
    "/api/probe/hinweis": (200, {"hinweis": DUE_DE, "stand": LOCKED, "befunde": [{"titel": VALUE, "text": VALUE}]}),
}


def test_errors_and_hints_answer_in_french_with_the_preview_on(serve, folder, fixture_catalog, monkeypatch):
    monkeypatch.setenv(ui_texts.PREVIEW_ENV, "1")
    store_language(folder, "fr")

    assert answers(serve) == {
        "/api/probe/vorlage": (400, {"fehler": DUE_FR}),
        "/api/probe/konstante": (400, {"fehler": LOCKED_FR}),
        "/api/probe/fehlt": (404, {"fehler": VALUE_FR}),
        "/api/probe/status": (409, {"fehler": VALUE_FR}),
        "/api/probe/aktion": (400, {"fehler": VALUE_FR, "aktion": "ki-einrichten"}),
        # stand and titel equal catalog keys, but they are data: only the T values change
        "/api/probe/hinweis": (200, {"hinweis": DUE_FR, "stand": LOCKED, "befunde": [{"titel": VALUE, "text": VALUE_FR}]}),
    }


def test_errors_and_hints_stay_german_when_the_app_speaks_german(serve, folder, fixture_catalog, monkeypatch):
    monkeypatch.setenv(ui_texts.PREVIEW_ENV, "1")
    store_language(folder, "de")

    assert answers(serve) == GERMAN


def test_errors_and_hints_stay_german_with_the_preview_off(serve, folder, fixture_catalog, monkeypatch):
    monkeypatch.delenv(ui_texts.PREVIEW_ENV, raising=False)
    store_language(folder, "fr")

    assert answers(serve) == GERMAN


def test_a_german_answer_is_byte_for_byte_what_the_route_encoded(serve, folder, fixture_catalog, monkeypatch):
    monkeypatch.setenv(ui_texts.PREVIEW_ENV, "1")
    store_language(folder, "de")

    assert get(serve, "/api/probe/hinweis") == (200, server_module.json_antwort(HINT_PAYLOAD).inhalt)


def test_a_constant_of_the_server_itself_translates_by_exact_match(serve, folder, monkeypatch, tmp_path):
    (tmp_path / "server.json").write_text(json.dumps({"Nicht gefunden": {"fr": "Introuvable", "en": "Not found"}}),
                                          encoding="utf-8")
    monkeypatch.setattr(translation_catalog, "CATALOG_DIR", tmp_path)
    monkeypatch.setenv(ui_texts.PREVIEW_ENV, "1")
    store_language(folder, "en")

    status, body = get(serve, "/api/gibt-es-nicht", token=False)

    assert (status, json.loads(body)) == (404, {"fehler": "Not found"})
