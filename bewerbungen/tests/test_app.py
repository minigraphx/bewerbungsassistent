"""Tests der lokalen Oberfläche über HTTP: Zugriffsschutz, Bewerbungen, Unterlagen, Versand, Entwürfe, Foto."""
import datetime
import http.client
import io
import json
import shutil
import threading
import urllib.parse

import pypdf
import pytest

import app
import build
from ablage import Ablage
from conftest import BRIEF_ID
from kontext import Kontext
from register import Register
from versionen import GitVersionen


@pytest.fixture
def server(datenordner, tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    shutil.copy(build.ROOT / "tests" / "halbe.png", datenordner / "foto.png")
    cv = datenordner / "cv.yaml"
    cv.write_text(cv.read_text(encoding="utf-8").replace("basics:\n", "basics:\n  image: foto.png\n", 1), encoding="utf-8")
    k = Kontext(daten=datenordner.resolve(), build=(tmp_path / "build").resolve(), ablage=Ablage(datenordner),
                versionierung=GitVersionen(datenordner), heute=lambda: datetime.date(2026, 10, 26))
    s = app.erstelle_server(datenordner, kontext=k)
    thread = threading.Thread(target=s.serve_forever, daemon=True)
    thread.start()
    yield s
    s.shutdown()
    s.server_close()


def anfrage(s, methode, pfad, body=None, headers=None, host=None):
    port = s.server_address[1]
    verbindung = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
    kopf = {"Host": host or f"127.0.0.1:{port}", **(headers or {})}
    verbindung.request(methode, pfad, body=body, headers=kopf)
    antwort = verbindung.getresponse()
    inhalt = antwort.read()
    verbindung.close()
    return antwort.status, antwort.getheader("Content-Type", ""), inhalt, antwort


def get(s, pfad, **parameter):
    status, typ, inhalt, _ = anfrage(s, "GET", pfad + "?" + urllib.parse.urlencode({"t": s.token, **parameter}))
    return status, typ, inhalt


def post(s, pfad, body, **parameter):
    ziel = pfad + ("?" + urllib.parse.urlencode(parameter) if parameter else "")
    status, _, inhalt, _ = anfrage(s, "POST", ziel, json.dumps(body),
                                   {"Content-Type": "application/json", "X-Token": s.token})
    return status, json.loads(inhalt)


# Zugriffsschutz


def test_lauscht_nur_lokal(server):
    assert server.server_address[0] == "127.0.0.1"


@pytest.mark.parametrize("pfad", ["/", "/bewerbung", "/entwuerfe", "/foto", "/inhalte"])
def test_seiten_mit_token_und_csp(server, pfad):
    status, typ, inhalt, antwort = anfrage(server, "GET", pfad)

    assert status == 200
    assert typ.startswith("text/html")
    assert server.token in inhalt.decode("utf-8")
    assert "script-src 'self'" in antwort.getheader("Content-Security-Policy")
    assert "<script>" not in inhalt.decode("utf-8")  # keine Inline-Skripte


@pytest.mark.parametrize("pfad", ["/stil.css", "/app.js", "/uebersicht.js", "/bewerbung.js", "/entwuerfe.js", "/foto.js", "/inhalte.js"])
def test_statische_dateien(server, pfad):
    status, _, inhalt, _ = anfrage(server, "GET", pfad)

    assert status == 200
    assert inhalt


@pytest.mark.parametrize("pfad", ["/api/bewerbungen", "/api/bewerbungen?t=falsch", "/api/bewerbungen?t=%C3%A4"])
def test_api_ohne_token(server, pfad):
    assert anfrage(server, "GET", pfad)[0] == 403


def test_post_ohne_token(server):
    status, *_ = anfrage(server, "POST", "/api/bewerbung/neu", json.dumps({"firma": "A", "stelle": "B"}),
                         {"Content-Type": "application/json"})

    assert status == 403
    assert len(Register(server.kontext.daten).alle()) == 1


def test_post_braucht_json(server):
    status, *_ = anfrage(server, "POST", "/api/bewerbung/neu", "firma=A",
                         {"Content-Type": "application/x-www-form-urlencoded", "X-Token": server.token})

    assert status == 415


def test_fremder_host(server):
    assert anfrage(server, "GET", "/", host="boese.example")[0] == 403


def test_unbekannter_pfad(server):
    assert get(server, "/../cv.yaml")[0] == 404


# Bewerbungen


def test_liste_und_details(server):
    status, _, inhalt = get(server, "/api/bewerbungen")
    assert status == 200
    assert [b["id"] for b in json.loads(inhalt)["bewerbungen"]] == [BRIEF_ID]

    status, _, inhalt = get(server, "/api/bewerbung", id=BRIEF_ID)
    details = json.loads(inhalt)
    assert details["bewerbung"]["firma"] == "Beispiel AG"
    assert details["jobroom"]["pensum"] == "Teilzeit"
    assert details["hat_anschreiben"] is True


def test_unbekannte_bewerbung(server):
    assert get(server, "/api/bewerbung", id="gibt-es-nicht")[0] == 404


def test_neu_und_speichern_legt_entwuerfe_an(server):
    status, b = post(server, "/api/bewerbung/neu", {"firma": "Neu AG", "stelle": "Tester"})
    assert status == 200

    status, gespeichert = post(server, "/api/bewerbung", {**b, "status": "Bewerben", "notiz": "über Kontakt"})

    assert status == 200
    assert Register(server.kontext.daten).hole(b["id"])["notiz"] == "über Kontakt"
    assert len(server.kontext.ablage.liste(server.kontext.daten / "bewerbungen.yaml")) >= 2


def test_speichern_ungueltig(server):
    status, antwort = post(server, "/api/bewerbung", {"id": BRIEF_ID, "firma": "Beispiel AG", "stelle": "X", "status": "Kaputt"})

    assert status == 400
    assert "status" in antwort["fehler"]


def test_versand_nicht_ueber_formular(server):
    post(server, "/api/bewerbung", {"id": BRIEF_ID, "firma": "Beispiel AG", "stelle": "Data Engineer",
                                    "versand": {"datum": "2020-01-01"}})

    assert "versand" not in Register(server.kontext.daten).hole(BRIEF_ID)


def test_stellentext_und_vorschlag(server):
    status, _ = post(server, "/api/stellentext", {"text": "Wir suchen Python und Airflow."}, id=BRIEF_ID)
    assert status == 200

    status, _, inhalt = get(server, "/api/varianten/vorschlag", id=BRIEF_ID)

    assert json.loads(inhalt)["vorschlaege"][0]["id"] == "daten"


def test_unterlagen_pruefung_und_versand(server):
    status, gebaut = post(server, "/api/unterlagen", {}, id=BRIEF_ID)
    assert status == 200
    assert gebaut["gebaut"] == ["anschreiben", "lebenslauf"]

    status, typ, inhalt = get(server, "/api/pdf", id=BRIEF_ID, art="anschreiben")
    assert typ == "application/pdf" and inhalt.startswith(b"%PDF")

    status, _, inhalt = get(server, "/api/pruefung", id=BRIEF_ID)
    assert all(b["stufe"] != "fehler" for b in json.loads(inhalt)["befunde"])

    status, ergebnis = post(server, "/api/versand", {"datum": "2026-10-26", "art": "elektronisch"}, id=BRIEF_ID)
    assert status == 200, ergebnis
    assert ergebnis["commit"]
    datei = ergebnis["bewerbung"]["versand"]["dateien"]["lebenslauf"]

    status, typ, inhalt = get(server, "/api/versendet", datei=datei)
    assert status == 200 and inhalt.startswith(b"%PDF")

    status, _, inhalt = get(server, "/api/versionen")
    assert json.loads(inhalt)["versionen"][0]["nachricht"].startswith("Versand: Beispiel AG")


@pytest.mark.parametrize("datei", ["cv.yaml", "versendet/../cv.yaml", "/etc/passwd"])
def test_versendet_nur_aus_versendet(server, datei):
    assert get(server, "/api/versendet", datei=datei)[0] in (400, 404)


def test_pdf_ungueltige_art(server):
    assert get(server, "/api/pdf", id=BRIEF_ID, art="cv")[0] == 400


# Entwürfe


def test_entwuerfe_ansehen_vergleichen_loeschen(server):
    k = server.kontext
    cv = k.daten / "cv.yaml"
    eins = k.ablage.speichere(cv, "eins")
    cv.write_text(cv.read_text(encoding="utf-8") + "# Ergänzung\n", encoding="utf-8")
    zwei = k.ablage.speichere(cv, "zwei")

    status, _, inhalt = get(server, "/api/entwuerfe", datei="cv.yaml")
    assert [e["id"] for e in json.loads(inhalt)["entwuerfe"]] == [zwei.id, eins.id]

    status, _, inhalt = get(server, "/api/entwurf/vergleich", a=eins.id, b=zwei.id)
    assert "+# Ergänzung" in json.loads(inhalt)["diff"]

    status, _ = post(server, "/api/entwurf/wiederherstellen", {"id": eins.id})
    assert status == 200
    assert "# Ergänzung" not in cv.read_text(encoding="utf-8")

    status, _ = post(server, "/api/entwurf/loeschen", {"id": zwei.id})
    assert status == 200
    assert zwei.id not in [e.id for e in k.ablage.liste()]


def test_entwurf_als_pdf(server):
    k = server.kontext
    cv = k.daten / "cv.yaml"
    alt = k.ablage.speichere(cv, "alt")
    cv.write_text(cv.read_text(encoding="utf-8").replace("Erika Beispiel", "Erika Neu"), encoding="utf-8")

    status, _, inhalt = get(server, "/api/entwuerfe")
    assert json.loads(inhalt)["entwuerfe"][0]["pdf"] is True
    assert json.loads(inhalt)["entwuerfe"][0]["titel"] == "Lebenslauf"

    status, typ, pdf = get(server, "/api/entwurf/pdf", id=alt.id)
    assert status == 200 and typ == "application/pdf"
    assert "Erika Beispiel" in "".join(s.extract_text() for s in pypdf.PdfReader(io.BytesIO(pdf)).pages)


def test_entwurf_ohne_pdf_ansicht(server):
    k = server.kontext
    e = k.ablage.speichere(k.daten / "varianten.yaml", "Varianten")

    status, _, inhalt = get(server, "/api/entwuerfe")
    assert [x["pdf"] for x in json.loads(inhalt)["entwuerfe"] if x["id"] == e.id] == [False]
    assert get(server, "/api/entwurf/pdf", id=e.id)[0] == 400


def test_entwuerfe_ausserhalb(server):
    assert get(server, "/api/entwuerfe", datei="../../etc/passwd")[0] == 400


# Foto


def test_foto_optionen_vorschau_speichern(server):
    status, _, inhalt = get(server, "/api/foto/optionen")
    assert json.loads(inhalt) == {"mirror": False, "zoom": 1, "x": 0.5, "y": 0.5}

    status, typ, inhalt = get(server, "/api/foto/vorschau.png", mirror="true", zoom="1.5", x="0.4", y="0.2")
    assert typ == "image/png" and inhalt.startswith(b"\x89PNG")

    status, gespeichert = post(server, "/api/foto/speichern", {"mirror": True, "zoom": 1.5, "x": 0.4, "y": 0.2})
    assert status == 200
    assert gespeichert["mirror"] is True
    assert len(server.kontext.ablage.liste(server.kontext.daten / "cv.yaml")) == 2


def test_foto_ungueltig(server):
    status, antwort = post(server, "/api/foto/speichern", {"zoom": 0})

    assert status == 400
    assert "zoom" in antwort["fehler"]


# Inhalte


def test_inhalte_lesen_pruefen_speichern(server):
    status, _, inhalt = get(server, "/api/inhalte")
    assert {"datei": "cv.yaml", "titel": "Lebenslauf", "pdf": True} in json.loads(inhalt)["dateien"]

    status, _, inhalt = get(server, "/api/inhalt", datei="cv.yaml")
    text = json.loads(inhalt)["text"]

    status, antwort = post(server, "/api/inhalt/pruefen", {"text": text.replace("Erika Beispiel", "Erika Neu")}, datei="cv.yaml")
    assert status == 200 and antwort["vorschau"] is True
    status, typ, pdf = get(server, "/api/inhalt/vorschau.pdf")
    assert typ == "application/pdf" and pdf.startswith(b"%PDF")

    status, antwort = post(server, "/api/inhalt", {"text": text.replace("Erika Beispiel", "Erika Neu")}, datei="cv.yaml")
    assert status == 200
    assert "Erika Neu" in (server.kontext.daten / "cv.yaml").read_text(encoding="utf-8")
    assert len(server.kontext.ablage.liste(server.kontext.daten / "cv.yaml")) == 2


def test_inhalte_ungueltig_wird_nicht_gespeichert(server):
    vorher = (server.kontext.daten / "cv.yaml").read_text(encoding="utf-8")

    status, antwort = post(server, "/api/inhalt", {"text": "basics: ["}, datei="cv.yaml")

    assert status == 400 and "YAML" in antwort["fehler"]
    assert (server.kontext.daten / "cv.yaml").read_text(encoding="utf-8") == vorher


def test_inhalt_als_pdf(server):
    (server.kontext.daten / "suchprofil.md").write_text("# Suchprofil\n\n| Portal | Modus |\n|---|---|\n| a | b |\n", encoding="utf-8")

    for datei in ("cv.yaml", "suchprofil.md", f"bewerbungen/{BRIEF_ID}/anschreiben.yaml"):
        status, typ, pdf = get(server, "/api/inhalt/pdf", datei=datei)
        assert (status, typ) == (200, "application/pdf") and pdf.startswith(b"%PDF"), datei


def test_inhalt_ohne_pdf_ansicht(server):
    status, typ, inhalt = get(server, "/api/inhalt/pdf", datei="bewerbungen.yaml")

    assert status == 400 and "PDF" in json.loads(inhalt)["fehler"]


@pytest.mark.parametrize("datei", ["../cv.yaml", ".entwuerfe/index.yaml", "notiz.txt"])
def test_inhalte_nur_erlaubte_dateien(server, datei):
    assert get(server, "/api/inhalt", datei=datei)[0] == 400
    assert get(server, "/api/inhalt/pdf", datei=datei)[0] == 400
    assert post(server, "/api/inhalt", {"text": "x"}, datei=datei)[0] == 400


def test_ungueltige_content_length(server):
    port = server.server_address[1]
    verbindung = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    verbindung.putrequest("POST", "/api/bewerbung/neu", skip_host=True)
    for name, wert in (("Host", f"127.0.0.1:{port}"), ("Content-Type", "application/json"),
                       ("X-Token", server.token), ("Content-Length", "viel")):
        verbindung.putheader(name, wert)
    verbindung.endheaders()

    assert verbindung.getresponse().status == 400


def test_kein_einbetten_in_fremde_seiten(server):
    _, _, _, antwort = anfrage(server, "GET", "/")

    assert "frame-ancestors 'self'" in antwort.getheader("Content-Security-Policy")
