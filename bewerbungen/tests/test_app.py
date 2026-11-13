"""Tests der lokalen Oberfläche über HTTP: Zugriffsschutz, Bewerbungen, Unterlagen, Versand, Entwürfe, Foto."""
import datetime
import http.client
import io
import json
import re
import shutil
import threading
import urllib.parse

import pypdf
import pytest

import app
import build
import server as server_modul
from ablage import Ablage
from sample_folder import BRIEF_ID
from kontext import Kontext
from register import Register
from versionen import GitVersionen


@pytest.fixture
def server(request, datenordner, tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    shutil.copy(build.ROOT / "tests" / "halbe.png", datenordner / "foto.png")
    cv = datenordner / "cv.yaml"
    cv.write_text(cv.read_text(encoding="utf-8").replace("basics:\n", "basics:\n  image: foto.png\n", 1), encoding="utf-8")
    k = Kontext(daten=datenordner.resolve(), build=(tmp_path / "build").resolve(), ablage=Ablage(datenordner),
                versionierung=GitVersionen(datenordner), heute=lambda: datetime.date(2026, 10, 26))
    s = app.erstelle_server(datenordner, kontext=k, questions_page=request.node.get_closest_marker("questions_page") is not None)
    thread = threading.Thread(target=s.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
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


def session_header(s):
    """What the browser sends after it came in through the link with the token."""
    _, _, _, antwort = anfrage(s, "GET", f"/?t={s.token}")
    return {"Cookie": antwort.getheader("Set-Cookie").split(";", 1)[0]}


def get(s, pfad, **parameter):
    """Like a browser: the link with the token leads to the page, with the session."""
    status, typ, inhalt, antwort = anfrage(s, "GET", pfad + "?" + urllib.parse.urlencode({"t": s.token, **parameter}))
    if status == 303:
        kopf = {"Cookie": antwort.getheader("Set-Cookie").split(";", 1)[0]}
        status, typ, inhalt, _ = anfrage(s, "GET", antwort.getheader("Location"), headers=kopf)
    return status, typ, inhalt


def post(s, pfad, body, **parameter):
    ziel = pfad + ("?" + urllib.parse.urlencode(parameter) if parameter else "")
    status, _, inhalt, _ = anfrage(s, "POST", ziel, json.dumps(body),
                                   {"Content-Type": "application/json", "X-Token": s.token})
    return status, json.loads(inhalt)


# Zugriffsschutz


def test_lauscht_nur_lokal(server):
    assert server.server_address[0] == "127.0.0.1"


@pytest.mark.parametrize("pfad", ["/", "/bewerbung", "/dateien", "/entwuerfe", "/foto", "/inhalte", "/treffer"])
def test_seiten_mit_token_und_csp(server, pfad):
    status, typ, inhalt, antwort = anfrage(server, "GET", pfad, headers=session_header(server))

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


@pytest.mark.parametrize("name", ["DMSans-400.ttf", "DMSans-400i.ttf", "DMSans-500.ttf", "DMSans-700.ttf"])
def test_fonts_are_served_by_the_app(server, name):
    status, typ, inhalt, _ = anfrage(server, "GET", f"/fonts/{name}")

    assert status == 200
    assert typ == "font/ttf"
    assert inhalt[:4] == b"\x00\x01\x00\x00"  # TrueType


def test_logo_is_served_by_the_app_as_a_single_colour_vector(server):
    status, typ, inhalt, _ = anfrage(server, "GET", "/as-logo.svg")

    svg = inhalt.decode("utf-8")
    assert status == 200
    assert typ == "image/svg+xml"
    assert "<image" not in svg and "base64" not in svg  # a vector, no embedded picture
    assert set(re.findall(r"#[0-9a-fA-F]{6}", svg)) == {"#27333f", "#f0f3f6"}  # text colour, light and dark


def test_settings_show_the_logo_under_about_the_app():
    script = (server_modul.SEITEN / "app.js").read_text(encoding="utf-8")
    settings = (server_modul.SEITEN / "einstellungen.html").read_text(encoding="utf-8")

    assert 'src: "/as-logo.svg"' in script and '<h2 id="ueber-titel">Über die App</h2>' in settings
    # the about block only counts when the packaged app actually appends it to that section (G54)
    assert 'getElementById("ueber-die-app")' in script
    assert re.search(r"ort\.append\([^;]*ueberDieApp\(info\.version\)", script)


def test_a_new_version_is_asked_about_in_a_dialog_first():
    script = (server_modul.SEITEN / "app.js").read_text(encoding="utf-8")
    angaben = (server_modul.SEITEN / "angaben.html").read_text(encoding="utf-8")

    assert re.search(r"if \(info\.update\.fragen\) updateDialog\(info\.update\);\s*else updateBanner\(info\.update\);", script)
    assert 'senden("/api/app/spaeter", {})' in script and "dialog.showModal()" in script
    assert ".dialog::backdrop" in angaben  # the page of the onboarding form brings its own styles


def test_stylesheet_loads_fonts_only_from_the_app(server):
    css = anfrage(server, "GET", "/stil.css")[2].decode("utf-8")

    assert 'url("/fonts/DMSans-400.ttf")' in css
    assert "http" not in css


def test_overview_view_buttons_wrap_on_a_narrow_screen(server):
    css = anfrage(server, "GET", "/stil.css")[2].decode("utf-8")

    rule = re.search(r"^\.overview__views \{([^}]*)\}", css, re.M).group(1)
    assert re.search(r"(^|;)\s*flex-wrap:\s*wrap\s*(;|$)", rule)


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


def test_a_page_hands_out_no_token_without_proof(server):
    status, typ, inhalt, _ = anfrage(server, "GET", "/")

    assert status == 403 and typ.startswith("text/html")
    assert server.token.encode() not in inhalt and "Programmsymbol" in inhalt.decode("utf-8")


@pytest.mark.parametrize("kopf", [{"Cookie": "bewerbungsbegleiter-0=falsch"}, {"Cookie": "kaputt=;;\x7f"}, {}])
def test_a_wrong_cookie_is_no_proof(server, kopf):
    status, _, inhalt, _ = anfrage(server, "GET", "/treffer?t=falsch", headers=kopf)

    assert status == 403 and server.token.encode() not in inhalt


def test_the_link_with_the_token_sets_the_session_and_cleans_the_address(server):
    status, _, _, antwort = anfrage(server, "GET", f"/bewerbung?id=b1&t={server.token}")

    assert status == 303 and antwort.getheader("Location") == "/bewerbung?id=b1"
    cookie = antwort.getheader("Set-Cookie")
    assert "HttpOnly" in cookie and "SameSite=Lax" in cookie and "Path=/" in cookie
    assert server.token not in cookie


def test_the_session_of_another_port_does_not_count(server):
    name, wert = session_header(server)["Cookie"].split("=", 1)
    assert str(server.server_address[1]) in name

    status, _, _, _ = anfrage(server, "GET", "/", headers={"Cookie": f"bewerbungsbegleiter-1={wert}"})

    assert status == 403


def test_files_of_the_pages_need_no_proof_and_hold_no_token(server):
    status, _, inhalt, _ = anfrage(server, "GET", "/stil.css")

    assert status == 200 and server.token.encode() not in inhalt


def test_the_entry_link_carries_the_token(server):
    assert server.entry_url == f"{server.url}?t={server.token}"


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


def test_the_end_buttons_stay_outside_what_hides_before_sending(server):
    page = anfrage(server, "GET", "/bewerbung", headers=session_header(server))[2].decode("utf-8")

    end = page.index('id="beenden-teil"')
    record = page.index('id="s-festhalten"')
    assert page.index('id="verwerfen"') > end and page.index('id="zurueckziehen"') > end
    assert not record < end < page.index("</section>", record)
    assert ">Verwerfen</button>" in page and ">Zurückziehen</button>" in page


def test_an_application_past_its_deadline_is_withdrawn_with_drafts(server):
    _, b = post(server, "/api/bewerbung/neu", {"firma": "Muster AG", "stelle": "Sachbearbeiterin"})
    post(server, "/api/bewerbung", {"id": b["id"], "status": "Beworben", "beworben_am": "2026-01-05", "frist": "2026-01-15"})
    vorher = len(server.kontext.ablage.liste(server.kontext.daten / "bewerbungen.yaml"))

    status, gespeichert = post(server, "/api/bewerbung", {"id": b["id"], "status": "Zurückgezogen"})

    assert status == 200
    assert gespeichert["status"] == "Zurückgezogen"
    assert len(server.kontext.ablage.liste(server.kontext.daten / "bewerbungen.yaml")) > vorher


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


def test_copies_of_certificates_stay_out_of_git(datenordner):
    app.erstelle_server(datenordner).server_close()

    zeilen = (datenordner / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "dokumente/" in zeilen


def test_latest_drafts_of_a_file_are_limited(server):
    k = server.kontext
    cv = k.daten / "cv.yaml"
    ids = []
    for nummer in range(4):
        cv.write_text(cv.read_text(encoding="utf-8") + f"# {nummer}\n", encoding="utf-8")
        ids.append(k.ablage.speichere(cv, f"Stand {nummer}").id)

    status, _, inhalt = get(server, "/api/entwuerfe", datei="cv.yaml", anzahl="2")
    assert status == 200
    assert [e["id"] for e in json.loads(inhalt)["entwuerfe"]] == [ids[3], ids[2]]


@pytest.mark.parametrize("anzahl", ["0", "-1", "zwei", "1001"])
def test_invalid_draft_limit_is_rejected(server, anzahl):
    assert get(server, "/api/entwuerfe", datei="cv.yaml", anzahl=anzahl)[0] == 400


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


def test_photo_is_reported_as_present(server):
    status, _, inhalt = get(server, "/api/foto/vorhanden")
    assert status == 200 and json.loads(inhalt)["vorhanden"] is True


def test_missing_photo_is_optional_not_an_error(server):
    cv = server.kontext.daten / "cv.yaml"
    cv.write_text(cv.read_text(encoding="utf-8").replace("  image: foto.png\n", "", 1), encoding="utf-8")

    status, _, inhalt = get(server, "/api/foto/vorhanden")
    assert status == 200 and json.loads(inhalt)["vorhanden"] is False


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


# First start (MIN-366): one menu everywhere, an empty data folder never gives an internal error

def nav_of(html: str) -> str:
    return re.search(r"<nav[ >].*?</nav>", html, re.S).group(0)


def test_all_pages_share_one_menu():
    pages = sorted(server_modul.SEITEN.glob("*.html"))
    navs = {page.name: nav_of(page.read_text(encoding="utf-8")) for page in pages}

    assert len(navs) >= 7 and len(set(navs.values())) == 1, navs
    nav = next(iter(navs.values()))
    main, more = nav.split('<div class="app-nav__more"')  # below 900 px only the first part stays outside „Menü“ (G54)
    for link in ("/", "/treffer", "/#liste-teil", "/angaben"):
        assert f'href="{link}"' in main
    for link in ("/dateien", "/fragen", "/einstellungen"):
        assert f'href="{link}"' in more


@pytest.fixture
def leerer_server(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    ordner = tmp_path / "leer"
    ordner.mkdir()
    s = app.erstelle_server(ordner, build=tmp_path / "build")
    threading.Thread(target=s.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True).start()
    yield s
    s.shutdown()
    s.server_close()


def test_empty_data_folder_gives_no_internal_error(leerer_server):
    s = leerer_server
    fehler = {}
    for pfad in s.routen_get:
        query = urllib.parse.urlencode({"t": s.token, "id": "x", "pfad": "cv.yaml", "datei": "cv.yaml"})
        status = anfrage(s, "GET", f"{pfad}?{query}")[0]
        if status >= 500:
            fehler[pfad] = status

    assert not fehler


def test_basics_tell_whether_the_person_has_entered_anything(leerer_server, server):
    assert json.loads(get(leerer_server, "/api/grundlagen")[2]) == {"lebenslauf": False, "suchprofil": False}
    assert json.loads(get(server, "/api/grundlagen")[2])["lebenslauf"] is True


def test_saving_some_fields_keeps_what_someone_else_wrote_meanwhile(server):
    _, b = post(server, "/api/bewerbung/neu", {"firma": "Neu AG", "stelle": "Tester"})
    post(server, "/api/bewerbung", {"id": b["id"], "notiz": "von Claude", "passung": 2})

    status, saved = post(server, "/api/bewerbung", {"id": b["id"], "ort": "Bern"})

    assert status == 200
    assert (saved["notiz"], saved["passung"], saved["ort"], saved["firma"]) == ("von Claude", 2, "Bern", "Neu AG")


def test_an_empty_field_clears_the_value(server):
    _, b = post(server, "/api/bewerbung/neu", {"firma": "Neu AG", "stelle": "Tester"})
    post(server, "/api/bewerbung", {"id": b["id"], "notiz": "alt"})

    _, saved = post(server, "/api/bewerbung", {"id": b["id"], "notiz": ""})

    assert "notiz" not in saved


def test_details_say_when_the_documents_were_built(server):
    _, _, inhalt = get(server, "/api/bewerbung", id=BRIEF_ID)
    stand = json.loads(inhalt)["pdf_stand"]
    post(server, "/api/unterlagen", {}, id=BRIEF_ID)
    built = json.loads(get(server, "/api/bewerbung", id=BRIEF_ID)[2])["pdf_stand"]

    assert set(stand) == {"lebenslauf", "anschreiben"}
    assert isinstance(built["anschreiben"], int) and built["anschreiben"] != stand["anschreiben"]


PAGES_WITH_MENU = ["/", "/bewerbung", "/dateien", "/entwuerfe", "/foto", "/inhalte", "/treffer", "/einstellungen", "/einrichtung"]


def test_the_page_for_questions_is_off_unless_switched_on(server):
    assert get(server, "/fragen")[0] == 404
    assert get(server, "/fragen.js")[0] == 404
    assert get(server, "/api/fragen/stand")[0] == 404
    assert post(server, "/api/fragen/senden", {"frage": "Was fehlt?"})[0] == 404
    for path in PAGES_WITH_MENU:
        status, _, content = get(server, path)
        assert status == 200 and b"/fragen" not in content, path


def test_every_script_of_the_pages_is_served(server):
    for path in PAGES_WITH_MENU:
        page = get(server, path)[2].decode("utf-8")
        for script in re.findall(r'<script src="([^"]+)"', page):
            assert get(server, script)[0] == 200, (path, script)


@pytest.mark.questions_page
def test_switched_on_the_page_for_questions_is_in_the_menu(server):
    assert get(server, "/fragen")[0] == 200
    assert get(server, "/api/fragen/stand")[0] == 200
    for path in PAGES_WITH_MENU:
        assert b'href="/fragen"' in get(server, path)[2], path
