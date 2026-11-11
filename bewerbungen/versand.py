"""Versand erfassen (MIN-263). Abgeschickt wird von Hand (Online-Formular, E-Mail); danach hält dieser
Schritt fest, was wann an wen ging:

1. Die PDFs kommen nach `versendet/<datum>-<hash>.pdf`. Jede Fassung existiert nur einmal, auch wenn
   mehrere Firmen sie bekommen (gleicher Inhalt = gleiche Datei).
2. Die Entwürfe der Daten (Lebenslauf, Zuschnitt, Foto, Anschreiben) werden als genutzt markiert und sind
   damit nicht mehr löschbar.
3. Das Register bekommt Status „Beworben“, Datum, Art und Verweis auf die Fassungen.
4. Ist Git installiert, kommt alles zusätzlich als Commit ins lokale Git (siehe versionen.py).
"""
import datetime
import hashlib
import pathlib
import shutil
import subprocess

import yaml

import form_copy
import merged_pdf
import unterlagen
from ablage import Ablage
from dateien import im_ordner
from register import JOBROOM_ART, Register
from varianten import Varianten
from versionen import Versionierung

ZERTIFIKATE_ZIP = "zertifikate.zip"  # MIN-346, see certificates.py
ORDNER = "versendet"
GIT_HISTORY = 1000  # commits searched for the commit of a Versand
FORM_VERSION_KEPT = "Festgehalten ist, was das Formular bekommen hat. Die neuere Fassung ging nicht mit: {files}."
COPY_LEFT = "Die Kopie für das Formular liess sich nicht entfernen: {error}"


def purpose(bewerbung: dict, datum: datetime.date) -> str:
    """What a sending is called on the drafts it used (`genutzt_fuer`) and in Git."""
    return f"Versand: {bewerbung['firma']} – {bewerbung['stelle']} ({datum:%d.%m.%Y})"


def sendings(bewerbungen: list[dict]) -> dict[str, dict]:
    """Company and date of each sent application, by the purpose its drafts carry."""
    found = {}
    for bewerbung in bewerbungen:
        versand = bewerbung.get("versand")
        if versand:
            datum = datetime.date.fromisoformat(versand["datum"])
            found[purpose(bewerbung, datum)] = {"firma": bewerbung.get("firma"), "datum": versand["datum"]}
    return found


def lege_ab(daten: pathlib.Path, pdf: pathlib.Path, datum: datetime.date) -> pathlib.Path:
    """PDF unter versendet/ ablegen; existiert der gleiche Inhalt schon, wird die vorhandene Datei verwendet."""
    inhalt = pdf.read_bytes()
    digest = hashlib.sha256(inhalt).hexdigest()
    ordner = daten / ORDNER
    ordner.mkdir(exist_ok=True)
    for vorhanden in ordner.glob(f"*-{digest[:12]}{pdf.suffix}"):
        if hashlib.sha256(vorhanden.read_bytes()).hexdigest() == digest:
            return vorhanden
    ziel = ordner / f"{datum.isoformat()}-{digest[:12]}{pdf.suffix}"
    shutil.copyfile(pdf, ziel)
    return ziel


def _datenquellen(daten: pathlib.Path, bewerbung: dict, gesendeter_brief: pathlib.Path | None) -> list[pathlib.Path]:
    """Dateien, aus denen die Unterlagen entstanden sind."""
    quellen = []
    cv = daten / "cv.yaml"
    if cv.is_file():
        quellen.append(cv)
        bild = ((yaml.safe_load(cv.read_text(encoding="utf-8")) or {}).get("basics") or {}).get("image")
        if bild and (daten / bild).is_file():
            quellen.append(im_ordner(daten, bild))
    if bewerbung.get("variante"):
        variante = Varianten(daten).hole(bewerbung["variante"])
        for feld in ("quelle", "datei"):
            if variante.get(feld):
                quellen.append(im_ordner(daten, variante[feld]))
    ordner = unterlagen.bewerbungsordner(daten, bewerbung["id"])
    # An own letter went out instead of the draft, so the draft is no source of what was sent. A form can hold another
    # letter than the own one that counts now.
    eigener = unterlagen.own_letter(daten, bewerbung)
    ohne_entwurf = eigener and gesendeter_brief and form_copy.same_content(gesendeter_brief, eigener)
    brief = [] if ohne_entwurf else [ordner / unterlagen.LETTER_SOURCE]
    quellen += [p for p in (*brief, ordner / "stelle.md") if p.is_file()]
    return quellen


def _hinweise_firma(alle: list[dict], bewerbung: dict) -> list[str]:
    andere = [b for b in alle if b["id"] != bewerbung["id"] and b["firma"] == bewerbung["firma"]
              and b["status"] in ("Beworben", "Gespräch")]
    return [f"Bei {bewerbung['firma']} läuft schon eine Bewerbung: {b['stelle']} ({b['status']})" for b in andere]


def _aktuelle_dateien(daten: pathlib.Path, bewerbung: dict) -> dict[str, pathlib.Path]:
    pdfs = {a: p for a, p in unterlagen.wirksame_pdfs(daten, bewerbung).items() if p.is_file()}
    dossier = unterlagen.effective_dossier(daten, bewerbung)
    if dossier:  # G40: goes out next to the two files, which portals with separate uploads still need
        pdfs = {**pdfs, unterlagen.DOSSIER: dossier}
    zertifikate = unterlagen.bewerbungsordner(daten, bewerbung["id"]) / ZERTIFIKATE_ZIP
    return {**pdfs, "zertifikate": zertifikate} if zertifikate.is_file() else pdfs


def _unterschiede(daten: pathlib.Path, bewerbung: dict, aus_formular: dict, aktuell: dict) -> list[str]:
    einzeln = {art: pfad for art, pfad in aus_formular.items() if art not in merged_pdf.KEYS}
    return [*form_copy.differing(einzeln, aktuell), *merged_pdf.changed(daten, bewerbung, aus_formular)]


def form_differs(daten: pathlib.Path, bewerbung: dict) -> list[str]:
    """What an open form holds in another version than the one that counts now."""
    if bewerbung.get("versand"):
        return []
    return _unterschiede(daten, bewerbung, form_copy.copies(daten, bewerbung["id"]), _aktuelle_dateien(daten, bewerbung))


def _hinweise_fassungen(daten: pathlib.Path, bewerbung: dict, aus_formular: dict, aktuell: dict) -> list[str]:
    """Says when the record names another version than the one that counts now, and removes the copies."""
    anders = [form_copy.LABELS[art] for art in _unterschiede(daten, bewerbung, aus_formular, aktuell)]
    hinweise = [FORM_VERSION_KEPT.format(files=", ".join(anders))] if anders else []
    try:
        form_copy.forget_all(daten, bewerbung["id"])
    except OSError as fehler:
        hinweise.append(COPY_LEFT.format(error=fehler))
    return hinweise


def erfasse_versand(daten: pathlib.Path, bewerbung_id: str, datum: datetime.date, versionierung: Versionierung,
                    art: str = "elektronisch", zusatz: dict | None = None, from_form: bool = False) -> dict:
    """`from_form`: the person sent it from the form, so what the form got is what went out."""
    daten = daten.resolve()
    if art not in JOBROOM_ART:
        raise ValueError(f"art muss eine von {', '.join(JOBROOM_ART)} sein")
    register = Register(daten)
    bewerbung = register.hole(bewerbung_id)
    if bewerbung.get("versand"):
        raise ValueError(f"Diese Bewerbung wurde bereits am {bewerbung['versand']['datum']} versendet")
    aktuell = _aktuelle_dateien(daten, bewerbung)
    aus_formular = form_copy.copies(daten, bewerbung_id) if from_form else {}
    fassungen = {**aktuell, **aus_formular}
    if "lebenslauf" not in fassungen:
        raise ValueError("Lebenslauf-PDF fehlt: zuerst die Unterlagen erstellen und prüfen")

    abgelegt = {a: lege_ab(daten, p, datum) for a, p in fassungen.items()}
    zweck = purpose(bewerbung, datum)
    quellen = _datenquellen(daten, bewerbung, fassungen.get("anschreiben"))
    Ablage(daten).markiere_genutzt(quellen, zweck)

    versendet = {"datum": datum.isoformat(), "art": art,
                 "dateien": {a: p.relative_to(daten).as_posix() for a, p in abgelegt.items()}}
    neu = {**bewerbung, "status": "Beworben", "beworben_am": datum.isoformat(), "versand": versendet, **(zusatz or {})}
    neu = register.speichere(neu)

    # Ohne Git bleiben frühere Fassungen unter versendet/ liegen und werden hier nachgeholt (MIN-304)
    alle_fassungen = sorted(p for muster in ("*.pdf", "*.zip") for p in (daten / ORDNER).glob(muster))
    varianten = [p for p in (daten / "varianten.yaml",) if p.is_file()]
    hinweise = [*_hinweise_firma(register.alle(), neu), *_hinweise_fassungen(daten, bewerbung, aus_formular, aktuell)]
    try:
        commit = versionierung.friere_ein([*alle_fassungen, *quellen, *varianten, register.pfad], zweck)
    except (RuntimeError, subprocess.CalledProcessError, OSError) as fehler:
        # Der Versand ist erfasst; eingefroren wird beim nächsten Versand mit (versendet/ und Register sind dabei)
        commit = None
        hinweise.append(f"Versand erfasst, aber nicht in Git eingefroren: {fehler}")
    return {"bewerbung": neu, "commit": commit, "hinweise": hinweise}


def versendete(daten: pathlib.Path, versionierung: Versionierung) -> list[dict]:
    """Sent applications, newest first: PDFs and data files from register and drafts, plus the Git commit if any."""
    daten = daten.resolve()
    commits = {v["nachricht"]: v["commit"] for v in versionierung.verlauf(GIT_HISTORY)}
    entwuerfe = Ablage(daten).liste()
    eintraege = []
    for bewerbung in Register(daten).alle():
        versand = bewerbung.get("versand")
        if not versand:
            continue
        zweck = purpose(bewerbung, datetime.date.fromisoformat(versand["datum"]))
        quellen = {e.datei for e in entwuerfe if zweck in e.genutzt_fuer}
        eintraege.append({"nachricht": zweck, "datum": versand["datum"], "commit": commits.get(zweck),
                          "dateien": sorted(quellen | set(versand.get("dateien", {}).values()))})
    return sorted(eintraege, key=lambda e: e["datum"], reverse=True)
