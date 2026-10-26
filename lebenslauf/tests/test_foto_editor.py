"""Tests für den lokalen Foto-Editor: Server, Zugriffsschutz und Speichern über HTTP."""
import http.client
import json
import shutil
import threading
import urllib.parse

import pytest

import build
import foto_editor
import fotoausschnitt

CV = "basics:\n  name: Erika Muster\n  image: foto.png\n  # Kommentar bleibt\n"


@pytest.fixture
def editor(tmp_path):
    ordner = tmp_path / "daten"
    ordner.mkdir()
    shutil.copy(build.ROOT / "tests" / "halbe.png", ordner / "foto.png")
    daten = ordner / "cv.yaml"
    daten.write_text(CV, encoding="utf-8")
    server = foto_editor.erstelle_server(daten, tmp_path / "build", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server, daten
    server.shutdown()
    server.server_close()


def anfrage(server, methode, pfad, body=None, headers=None, host=None):
    _, port = server.server_address
    verbindung = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    kopf = {"Host": host or f"127.0.0.1:{port}", **(headers or {})}
    verbindung.request(methode, pfad, body=body, headers=kopf)
    antwort = verbindung.getresponse()
    inhalt = antwort.read()
    verbindung.close()
    return antwort.status, antwort.getheader("Content-Type", ""), inhalt


def mit_token(server, pfad, **werte):
    return pfad + "?" + urllib.parse.urlencode({"t": server.token, **werte})


STANDARD_ANFRAGE = {"mirror": "false", "zoom": "1", "x": "0.5", "y": "0.5"}


def test_lauscht_nur_lokal(editor):
    server, _ = editor

    assert server.server_address[0] == "127.0.0.1"


def test_seite_enthaelt_token(editor):
    server, _ = editor

    status, typ, inhalt = anfrage(server, "GET", "/")

    assert status == 200
    assert typ.startswith("text/html")
    assert server.token in inhalt.decode("utf-8")


def test_optionen(editor):
    server, _ = editor

    status, _, inhalt = anfrage(server, "GET", mit_token(server, "/optionen"))

    assert status == 200
    assert json.loads(inhalt) == fotoausschnitt.STANDARD


def test_vorschau(editor):
    server, _ = editor

    status, typ, inhalt = anfrage(server, "GET", mit_token(server, "/vorschau.png", **STANDARD_ANFRAGE))

    assert status == 200
    assert typ == "image/png"
    assert inhalt.startswith(b"\x89PNG")


def test_vorschau_ungueltig(editor):
    server, _ = editor

    status, _, inhalt = anfrage(server, "GET", mit_token(server, "/vorschau.png", **{**STANDARD_ANFRAGE, "zoom": "9"}))

    assert status == 400
    assert "zoom" in json.loads(inhalt)["fehler"]


def test_original_foto(editor):
    server, _ = editor

    status, typ, inhalt = anfrage(server, "GET", mit_token(server, "/foto"))

    assert status == 200
    assert typ == "image/png"
    assert inhalt == (build.ROOT / "tests" / "halbe.png").read_bytes()


def test_speichern(editor):
    server, daten = editor
    body = json.dumps({"mirror": True, "zoom": 1.5, "x": 0.4, "y": 0.2})

    status, _, _ = anfrage(
        server, "POST", "/speichern", body, {"Content-Type": "application/json", "X-Token": server.token}
    )

    assert status == 200
    assert fotoausschnitt.lies_foto(daten)[1] == {"mirror": True, "zoom": 1.5, "x": 0.4, "y": 0.2}
    assert "# Kommentar bleibt" in daten.read_text(encoding="utf-8")


def test_speichern_ungueltig(editor):
    server, daten = editor
    body = json.dumps({"mirror": True, "zoom": 0, "x": 0.4, "y": 0.2})

    status, _, inhalt = anfrage(
        server, "POST", "/speichern", body, {"Content-Type": "application/json", "X-Token": server.token}
    )

    assert status == 400
    assert "zoom" in json.loads(inhalt)["fehler"]
    assert daten.read_text(encoding="utf-8") == CV


def test_speichern_kein_json(editor):
    server, daten = editor

    status, _, _ = anfrage(
        server, "POST", "/speichern", "kaputt", {"Content-Type": "application/json", "X-Token": server.token}
    )

    assert status == 400
    assert daten.read_text(encoding="utf-8") == CV


@pytest.mark.parametrize(
    "methode, pfad, headers",
    [
        ("GET", "/optionen", {}),
        ("GET", "/optionen?t=falsch", {}),
        ("GET", "/optionen?t=%C3%A4", {}),
        ("GET", "/foto", {}),
        ("GET", "/vorschau.png", {}),
        ("POST", "/speichern", {"Content-Type": "application/json"}),
        ("POST", "/speichern", {"Content-Type": "application/json", "X-Token": "falsch"}),
    ],
)
def test_ohne_gueltiges_token_verboten(editor, methode, pfad, headers):
    server, daten = editor
    body = json.dumps(fotoausschnitt.STANDARD) if methode == "POST" else None

    status, _, _ = anfrage(server, methode, pfad, body, headers)

    assert status == 403
    assert daten.read_text(encoding="utf-8") == CV


def test_speichern_braucht_json_content_type(editor):
    server, daten = editor

    status, _, _ = anfrage(
        server, "POST", "/speichern", json.dumps(fotoausschnitt.STANDARD), {"Content-Type": "text/plain", "X-Token": server.token}
    )

    assert status == 415
    assert daten.read_text(encoding="utf-8") == CV


def test_fremder_host_verboten(editor):
    """Schutz gegen DNS-Rebinding: nur Anfragen an 127.0.0.1 oder localhost."""
    server, _ = editor

    status, _, _ = anfrage(server, "GET", "/", host="boese.example")

    assert status == 403


def test_unbekannter_pfad(editor):
    server, _ = editor

    status, _, _ = anfrage(server, "GET", mit_token(server, "/../cv.yaml"))

    assert status == 404
