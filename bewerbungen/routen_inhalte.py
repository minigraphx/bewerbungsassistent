"""API-Routen für den Text-Editor der Inhalte (MIN-302)."""
import inhalte
from dateien import schreibe_atomar
from server import datei_antwort, json_antwort, pflicht

VORSCHAU = "inhalt-probe/vorschau.pdf"


def liste(k, parameter, body):
    return json_antwort({"dateien": inhalte.bearbeitbare_dateien(k.daten)})


def lesen(k, parameter, body):
    rel = pflicht(parameter, "datei")
    pfad = inhalte.pruefe_datei(k.daten, rel)
    return json_antwort({"datei": rel, "text": pfad.read_text(encoding="utf-8") if pfad.is_file() else ""})


def _text(body) -> str:
    if not isinstance(body, dict) or not isinstance(body.get("text"), str):
        raise ValueError("text erwartet")
    return body["text"]


def pruefen(k, parameter, body):
    rel = pflicht(parameter, "datei")
    with k.sperre:
        pdf = inhalte.pruefe_inhalt(k.daten, rel, _text(body), k.build)
    return json_antwort({"ok": True, "vorschau": pdf is not None})


def speichern(k, parameter, body):
    rel = pflicht(parameter, "datei")
    text = _text(body)
    pfad = inhalte.pruefe_datei(k.daten, rel)
    with k.sperre:
        pdf = inhalte.pruefe_inhalt(k.daten, rel, text, k.build)
    k.mit_entwurf(pfad, f"{rel} bearbeitet", lambda: schreibe_atomar(pfad, text.encode("utf-8")))
    return json_antwort({"ok": True, "vorschau": pdf is not None})


def vorschau(k, parameter, body):
    return datei_antwort(k.build / VORSCHAU, "application/pdf")


GET = {
    "/api/inhalte": liste,
    "/api/inhalt": lesen,
    "/api/inhalt/vorschau.pdf": vorschau,
}
POST = {
    "/api/inhalt/pruefen": pruefen,
    "/api/inhalt": speichern,
}
