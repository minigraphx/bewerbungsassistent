"""API-Routen für Entwürfe und Versionen (MIN-303)."""
import yaml

import draft_groups
import inhalte
import versand
from dateien import im_ordner
import routes_own_files
from routen_inhalte import pdf_aus_text
from server import Antwort, json_antwort, pflicht

MAX_DRAFTS = 1000


def _mit_ansicht(e) -> dict:
    return {**e.als_dict(), "titel": inhalte.titel(e.datei),
            "pdf": e.datei.endswith(".pdf") or inhalte.hat_pdf_ansicht(e.datei)}


def _limit(parameter) -> int | None:
    """Optional `anzahl`: how many of the newest drafts to return."""
    value = parameter.get("anzahl")
    if value is None:
        return None
    if not value.isascii() or not value.isdigit() or not 1 <= int(value) <= MAX_DRAFTS:
        raise ValueError(f"anzahl muss eine Zahl von 1 bis {MAX_DRAFTS} sein")
    return int(value)


def _applications(k) -> list[dict]:
    """The applications; a register that does not read leaves the folder names, the drafts stay visible."""
    try:
        return k.register().alle()
    except (ValueError, TypeError, KeyError, yaml.YAMLError):
        return []


def _companies(applications: list[dict]) -> dict[str, str]:
    return {b["id"]: b.get("firma", "") for b in applications}


def _sendings(applications: list[dict]) -> dict[str, dict]:
    try:
        return versand.sendings(applications)
    except (ValueError, TypeError, KeyError):
        # A sending date that does not read leaves those versions marked with their purpose only
        return {}


def entwuerfe(k, parameter, body):
    """Drafts newest first, and `gruppen` for the page (#120); job ads only when their file is asked for."""
    datei = parameter.get("datei")
    limit = _limit(parameter)
    alle = [e for e in k.ablage.liste() if not draft_groups.is_job_ad(e.datei)]
    auswahl = k.ablage.liste(im_ordner(k.daten, datei)) if datei else alle
    shown = [_mit_ansicht(e) for e in auswahl]
    applications = _applications(k)
    return json_antwort({"entwuerfe": shown[:limit], "dateien": sorted({e.datei for e in alle}),
                         "gruppen": draft_groups.group(shown, _companies(applications), _sendings(applications))})


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
        routes_own_files.refresh_chosen(k, e.datei)
    return json_antwort({"ok": True, "datei": e.datei})


def versionen(k, parameter, body):
    return json_antwort({"versionen": versand.versendete(k.daten, k.versionierung), "hinweis": k.versionierung.hinweis})


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
