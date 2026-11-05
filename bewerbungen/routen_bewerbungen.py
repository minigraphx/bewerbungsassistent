"""API-Routen für Bewerbungen: Register, Stellentext, Varianten, Unterlagen, Prüfung, Versand."""
import dataclasses
import datetime
import pathlib

import yaml

import letter_approval
import pruefung
import unterlagen
import versand
from dateien import im_ordner, schreibe_atomar
from own_files import MAX_FILE_BYTES
from register import STATUS, jobroom_angaben
from server import datei_antwort, json_antwort, pflicht
from varianten import vorschlagen

EIGENE_ROUTEN = ("versand", "zertifikate", "ausfuellen", "rav_eingetragen_am")
STATUS_REIHENFOLGE = {s: i for i, s in enumerate(("Bewerben", "Gespräch", "Beworben", "Gemerkt", "Zusage",
                                                   "Absage", "Verworfen", "Zurückgezogen"))}


def _stellentext(k, bewerbung_id: str) -> str:
    pfad = unterlagen.bewerbungsordner(k.daten, bewerbung_id) / "stelle.md"
    return pfad.read_text(encoding="utf-8") if pfad.is_file() else ""


def liste(k, parameter, body):
    alle = sorted(k.register().alle(), key=lambda b: (STATUS_REIHENFOLGE.get(b["status"], 99),
                                                      b.get("beworben_am") or "9999", b["firma"].lower()))
    return json_antwort({"bewerbungen": alle, "status": list(STATUS)})


def grundlagen(k, parameter, body):
    """Whether the person has entered the basics yet; the first start leads to „Meine Angaben“ (MIN-366)."""
    own_cv = (k.daten / unterlagen.OWN_CV).is_file()
    return json_antwort({"lebenslauf": own_cv or (k.daten / "cv.yaml").is_file(), "suchprofil": (k.daten / "suchprofil.md").is_file()})


def details(k, parameter, body):
    b = k.register().hole(pflicht(parameter, "id"))
    pfade = unterlagen.wirksame_pdfs(k.daten, b)
    return json_antwort({
        "bewerbung": b,
        "jobroom": jobroom_angaben(b),
        "stellentext": _stellentext(k, b["id"]),
        "pdfs": {art: p.is_file() for art, p in pfade.items()},
        "pdf_stand": {art: p.stat().st_mtime_ns if p.is_file() else None for art, p in pfade.items()},
        "eigener_lebenslauf": unterlagen.eigener_lebenslauf(k.daten, b) is not None,
        "eigener_lebenslauf_da": (k.daten / unterlagen.OWN_CV).is_file(),
        "eigenes_anschreiben": unterlagen.own_letter(k.daten, b) is not None,
        "hat_anschreiben": pfade["anschreiben"].is_file() or unterlagen.letter_source(k.daten, b["id"]).is_file(),
        "anschreiben_text": _letter_text(k, b["id"]),
        "anschreiben_freigabe": letter_approval.state(k.daten, b),
        "ki_pruefung": letter_approval.review(k.daten, b["id"]),
        "formular_abweichend": versand.form_differs(k.daten, b),
        "max_datei": MAX_FILE_BYTES,
        "varianten": k.varianten().alle(),
        "status": list(STATUS),
    })


def _letter_text(k, entry_id: str) -> dict | None:
    """The draft as the page shows it for reading; None without one or when it cannot be read."""
    path = unterlagen.letter_source(k.daten, entry_id)
    try:
        letter = yaml.safe_load(path.read_text(encoding="utf-8")) if path.is_file() else None
    except (OSError, yaml.YAMLError):
        return None
    if not isinstance(letter, dict):
        return None
    paragraphs = [part.strip() for part in str(letter.get("text") or "").split("\n\n") if part.strip()]
    return {"betreff": str(letter.get("betreff") or ""), "anrede": str(letter.get("anrede") or ""),
            "absaetze": [" ".join(part.split()) for part in paragraphs], "gruss": str(letter.get("gruss") or "")}


def freigeben(k, parameter, body):
    entry = k.register().hole(pflicht(body if isinstance(body, dict) else {}, "id"))
    return json_antwort(letter_approval.approve(k.daten, entry, k.heute()))


def speichern(k, parameter, body):
    if not isinstance(body, dict) or not body.get("id"):
        raise ValueError("Bewerbung mit id erwartet")
    register = k.register()

    def schreiben():
        # Unter der Sperre lesen: ein gleichzeitiger Versand darf nicht überschrieben werden.
        # Versand, Zertifikate, Stand des Formulars und Eintrag im RAV setzen eigene Routen, nie das Formular.
        # Fields not named stay: the page and Claude write side by side (MIN-377), each only sends what it changes.
        alt = register.hole(body["id"])
        return register.speichere({**alt, **{key: v for key, v in body.items() if key not in EIGENE_ROUTEN}})

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
    wanted = pflicht(parameter, "id")
    with k.sperre:
        b = k.register().hole(wanted)
        if b.get("versand"):  # a letter built now would look like the one that went out
            raise ValueError(unterlagen.SENT_STAYS)
        gebaut = unterlagen.baue(k.daten, b, k.build)
    return json_antwort({"gebaut": sorted(gebaut)})


def pdf(k, parameter, body):
    art = pflicht(parameter, "art")
    wanted = pflicht(parameter, "id")
    if art not in unterlagen.pdf_pfade(k.daten, wanted):
        raise ValueError("art muss lebenslauf oder anschreiben sein")
    return datei_antwort(unterlagen.wirksame_pdfs(k.daten, k.register().hole(wanted))[art], "application/pdf")


def versendet(k, parameter, body):
    rel = pflicht(parameter, "datei")
    typ = {".pdf": "application/pdf", ".zip": "application/zip"}.get(pathlib.PurePosixPath(rel).suffix)
    if not rel.startswith(f"{versand.ORDNER}/") or typ is None:
        raise ValueError("Nur Dateien aus versendet/")
    return datei_antwort(im_ordner(k.daten, rel), typ)


def pruefen(k, parameter, body):
    b = k.register().hole(pflicht(parameter, "id"))
    return json_antwort({"befunde": [dataclasses.asdict(x) for x in pruefung.pruefe(k.daten, b, k.heute())]})


def versenden(k, parameter, body):
    if not isinstance(body, dict):
        raise ValueError("datum und art erwartet")
    datum = datetime.date.fromisoformat(str(body.get("datum") or k.heute().isoformat()))
    with k.sperre:
        ergebnis = versand.erfasse_versand(k.daten, pflicht(parameter, "id"), datum, k.versionierung,
                                           art=body.get("art") or "elektronisch",
                                           from_form=body.get("fassung_formular") is True)
    return json_antwort(ergebnis)


GET = {
    "/api/bewerbungen": liste,
    "/api/grundlagen": grundlagen,
    "/api/bewerbung": details,
    "/api/varianten/vorschlag": varianten_vorschlag,
    "/api/pdf": pdf,
    "/api/versendet": versendet,
    "/api/pruefung": pruefen,
}
POST = {
    "/api/bewerbung": speichern,
    "/api/bewerbung/neu": neu_anlegen,
    "/api/anschreiben/freigeben": freigeben,
    "/api/stellentext": stellentext_speichern,
    "/api/unterlagen": unterlagen_bauen,
    "/api/versand": versenden,
}
