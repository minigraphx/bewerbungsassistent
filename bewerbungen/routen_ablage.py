"""API-Routen für Entwürfe und Versionen (MIN-303)."""
import inhalte
from dateien import im_ordner
from routen_inhalte import pdf_aus_text
from server import Antwort, json_antwort, pflicht


def _mit_ansicht(e) -> dict:
    return {**e.als_dict(), "titel": inhalte.titel(e.datei),
            "pdf": e.datei.endswith(".pdf") or inhalte.hat_pdf_ansicht(e.datei)}


def entwuerfe(k, parameter, body):
    datei = parameter.get("datei")
    alle = k.ablage.liste()
    auswahl = k.ablage.liste(im_ordner(k.daten, datei)) if datei else alle
    return json_antwort({"entwuerfe": [_mit_ansicht(e) for e in auswahl],
                         "dateien": sorted({e.datei for e in alle})})


def entwurf(k, parameter, body):
    e = k.ablage.hole(pflicht(parameter, "id"))
    roh = k.ablage.inhalt(e.id)
    try:
        text = None if b"\x00" in roh else roh.decode("utf-8")
    except UnicodeDecodeError:
        text = None
    return json_antwort({"entwurf": e.als_dict(), "text": text})


def entwurf_roh(k, parameter, body):
    e = k.ablage.hole(pflicht(parameter, "id"))
    typ = "application/pdf" if e.datei.endswith(".pdf") else "text/plain; charset=utf-8"
    return Antwort(200, typ, k.ablage.inhalt(e.id))


def entwurf_pdf(k, parameter, body):
    """Den Stand eines Entwurfs als PDF: PDFs direkt, Lebenslauf, Anschreiben und Markdown frisch gebaut."""
    e = k.ablage.hole(pflicht(parameter, "id"))
    if e.datei.endswith(".pdf"):
        return Antwort(200, "application/pdf", k.ablage.inhalt(e.id))
    try:
        text = k.ablage.inhalt(e.id).decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError("Entwurf ist keine Textdatei") from None
    return pdf_aus_text(k, e.datei, text)


def vergleich(k, parameter, body):
    return json_antwort({"diff": k.ablage.vergleiche(pflicht(parameter, "a"), pflicht(parameter, "b"))})


def loeschen(k, parameter, body):
    if not isinstance(body, dict):
        raise ValueError("id erwartet")
    with k.sperre:
        k.ablage.loesche(pflicht(body, "id"))
    return json_antwort({"ok": True})


def wiederherstellen(k, parameter, body):
    if not isinstance(body, dict):
        raise ValueError("id erwartet")
    with k.sperre:
        e = k.ablage.stelle_her(pflicht(body, "id"))
    return json_antwort({"ok": True, "datei": e.datei})


def versionen(k, parameter, body):
    return json_antwort({"versionen": k.versionierung.verlauf(), "hinweis": k.versionierung.hinweis})


GET = {
    "/api/entwuerfe": entwuerfe,
    "/api/entwurf": entwurf,
    "/api/entwurf/roh": entwurf_roh,
    "/api/entwurf/pdf": entwurf_pdf,
    "/api/entwurf/vergleich": vergleich,
    "/api/versionen": versionen,
}
POST = {
    "/api/entwurf/loeschen": loeschen,
    "/api/entwurf/wiederherstellen": wiederherstellen,
}
