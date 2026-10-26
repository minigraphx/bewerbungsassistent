"""API-Routen für Bewerbungen: Register, Stellentext, Varianten, Unterlagen, Prüfung, Versand."""
import dataclasses
import datetime

import pruefung
import unterlagen
import versand
from dateien import im_ordner, schreibe_atomar
from register import STATUS, jobroom_vorschlag
from server import datei_antwort, json_antwort, pflicht
from varianten import vorschlagen

STATUS_REIHENFOLGE = {s: i for i, s in enumerate(("Bewerben", "Gespräch", "Beworben", "Gemerkt", "Zusage",
                                                   "Absage", "Verworfen", "Zurückgezogen"))}


def _stellentext(k, bewerbung_id: str) -> str:
    pfad = unterlagen.bewerbungsordner(k.daten, bewerbung_id) / "stelle.md"
    return pfad.read_text(encoding="utf-8") if pfad.is_file() else ""


def liste(k, parameter, body):
    alle = sorted(k.register().alle(), key=lambda b: (STATUS_REIHENFOLGE.get(b["status"], 99),
                                                      b.get("beworben_am") or "9999", b["firma"].lower()))
    return json_antwort({"bewerbungen": alle, "status": list(STATUS)})


def details(k, parameter, body):
    b = k.register().hole(pflicht(parameter, "id"))
    pfade = unterlagen.pdf_pfade(k.daten, b["id"])
    return json_antwort({
        "bewerbung": b,
        "jobroom": jobroom_vorschlag(b),
        "stellentext": _stellentext(k, b["id"]),
        "pdfs": {art: p.is_file() for art, p in pfade.items()},
        "hat_anschreiben": pfade["anschreiben"].with_suffix(".yaml").is_file(),
        "varianten": k.varianten().alle(),
        "status": list(STATUS),
    })


def speichern(k, parameter, body):
    if not isinstance(body, dict) or not body.get("id"):
        raise ValueError("Bewerbung mit id erwartet")
    register = k.register()

    def schreiben():
        # Unter der Sperre lesen: ein gleichzeitiger Versand darf nicht überschrieben werden.
        # Der Versand wird nur über /api/versand gesetzt, nie über das Formular.
        alt = register.hole(body["id"])
        versand_alt = {"versand": alt["versand"]} if alt.get("versand") else {}
        return register.speichere({**{key: v for key, v in body.items() if key != "versand"}, **versand_alt})

    gespeichert = k.mit_entwurf(register.pfad, f"Bewerbung {body['id']} geändert", schreiben)
    return json_antwort(gespeichert)


def neu_anlegen(k, parameter, body):
    if not isinstance(body, dict):
        raise ValueError("firma und stelle erwartet")
    register = k.register()
    firma, stelle = str(body.get("firma") or "").strip(), str(body.get("stelle") or "").strip()
    if not firma or not stelle:
        raise ValueError("firma und stelle angeben")
    b = k.mit_entwurf(register.pfad, f"Bewerbung {firma} – {stelle} angelegt", lambda: register.neu(firma=firma, stelle=stelle))
    return json_antwort(b)


def stellentext_speichern(k, parameter, body):
    b = k.register().hole(pflicht(parameter, "id"))
    if not isinstance(body, dict) or not isinstance(body.get("text"), str):
        raise ValueError("text erwartet")
    pfad = unterlagen.bewerbungsordner(k.daten, b["id"]) / "stelle.md"
    k.mit_entwurf(pfad, f"Stellentext {b['firma']}", lambda: schreibe_atomar(pfad, body["text"].encode("utf-8")))
    return json_antwort({"ok": True})


def varianten_vorschlag(k, parameter, body):
    b = k.register().hole(pflicht(parameter, "id"))
    text = _stellentext(k, b["id"])
    if not text.strip():
        raise ValueError("Zuerst den Stellentext einfügen und speichern")
    return json_antwort({"vorschlaege": vorschlagen(text, k.varianten().alle())})


def unterlagen_bauen(k, parameter, body):
    b = k.register().hole(pflicht(parameter, "id"))
    with k.sperre:
        gebaut = unterlagen.baue(k.daten, b, k.build)
    return json_antwort({"gebaut": sorted(gebaut)})


def pdf(k, parameter, body):
    art = pflicht(parameter, "art")
    pfade = unterlagen.pdf_pfade(k.daten, pflicht(parameter, "id"))
    if art not in pfade:
        raise ValueError("art muss lebenslauf oder anschreiben sein")
    return datei_antwort(pfade[art], "application/pdf")


def versendet(k, parameter, body):
    rel = pflicht(parameter, "datei")
    if not rel.startswith(f"{versand.ORDNER}/") or not rel.endswith(".pdf"):
        raise ValueError("Nur Dateien aus versendet/")
    return datei_antwort(im_ordner(k.daten, rel), "application/pdf")


def pruefen(k, parameter, body):
    b = k.register().hole(pflicht(parameter, "id"))
    return json_antwort({"befunde": [dataclasses.asdict(x) for x in pruefung.pruefe(k.daten, b, k.heute())]})


def versenden(k, parameter, body):
    if not isinstance(body, dict):
        raise ValueError("datum und art erwartet")
    datum = datetime.date.fromisoformat(str(body.get("datum") or k.heute().isoformat()))
    with k.sperre:
        ergebnis = versand.erfasse_versand(k.daten, pflicht(parameter, "id"), datum, k.versionierung,
                                           art=body.get("art") or "elektronisch")
    return json_antwort(ergebnis)


GET = {
    "/api/bewerbungen": liste,
    "/api/bewerbung": details,
    "/api/varianten/vorschlag": varianten_vorschlag,
    "/api/pdf": pdf,
    "/api/versendet": versendet,
    "/api/pruefung": pruefen,
}
POST = {
    "/api/bewerbung": speichern,
    "/api/bewerbung/neu": neu_anlegen,
    "/api/stellentext": stellentext_speichern,
    "/api/unterlagen": unterlagen_bauen,
    "/api/versand": versenden,
}
