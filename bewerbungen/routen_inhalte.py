"""API-Routen für Inhalte (MIN-302): Ansicht als PDF, Text-Editor mit Prüfung."""
import inhalte
from dateien import schreibe_atomar
from server import Antwort, datei_antwort, json_antwort, pflicht

VORSCHAU = "inhalt-probe/vorschau.pdf"


def liste(k, parameter, body):
    return json_antwort({"dateien": [{"datei": d, "titel": inhalte.titel(d), "pdf": inhalte.hat_pdf_ansicht(d)}
                                     for d in inhalte.bearbeitbare_dateien(k.daten)]})


def pdf_aus_text(k, rel: str, text: str) -> Antwort:
    """Den Text als PDF bauen und direkt ausliefern (unter der Sperre gelesen, kein Wettlauf zwischen Tabs)."""
    if not inhalte.hat_pdf_ansicht(rel):
        inhalte.pruefe_datei(k.daten, rel)
        raise ValueError(f"{inhalte.titel(rel)} hat keine PDF-Ansicht, nur als Text")
    with k.sperre:
        pdf = inhalte.pruefe_inhalt(k.daten, rel, text, k.build)
        inhalt = pdf.read_bytes()
    return Antwort(200, "application/pdf", inhalt)


def als_pdf(k, parameter, body):
    rel = pflicht(parameter, "datei")
    pfad = inhalte.pruefe_datei(k.daten, rel)
    return pdf_aus_text(k, rel, pfad.read_text(encoding="utf-8") if pfad.is_file() else "")


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
    "/api/inhalt/pdf": als_pdf,
}
POST = {
    "/api/inhalt/pruefen": pruefen,
    "/api/inhalt": speichern,
}
