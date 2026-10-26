"""Versand erfassen (MIN-263). Abgeschickt wird von Hand (Online-Formular, E-Mail); danach hält dieser
Schritt fest, was wann an wen ging:

1. Die PDFs kommen nach `versendet/<datum>-<hash>.pdf`. Jede Fassung existiert nur einmal, auch wenn
   mehrere Firmen sie bekommen (gleicher Inhalt = gleiche Datei).
2. Die Entwürfe der Daten (Lebenslauf, Zuschnitt, Foto, Anschreiben) werden als genutzt markiert und sind
   damit nicht mehr löschbar.
3. Das Register bekommt Status „Beworben“, Datum, Verweis auf die Fassungen und die Job-Room-Angaben.
4. Alles zusammen wird in Git eingefroren (ohne Git: siehe versionen.OhneGit).
"""
import datetime
import hashlib
import pathlib
import shutil
import subprocess

import yaml

import unterlagen
from ablage import Ablage
from dateien import im_ordner
from register import JOBROOM_ART, Register, jobroom_vorschlag
from varianten import Varianten
from versionen import OhneGit, Versionierung

ORDNER = "versendet"


def lege_ab(daten: pathlib.Path, pdf: pathlib.Path, datum: datetime.date) -> pathlib.Path:
    """PDF unter versendet/ ablegen; existiert der gleiche Inhalt schon, wird die vorhandene Datei verwendet."""
    inhalt = pdf.read_bytes()
    digest = hashlib.sha256(inhalt).hexdigest()
    ordner = daten / ORDNER
    ordner.mkdir(exist_ok=True)
    for vorhanden in ordner.glob(f"*-{digest[:12]}.pdf"):
        if hashlib.sha256(vorhanden.read_bytes()).hexdigest() == digest:
            return vorhanden
    ziel = ordner / f"{datum.isoformat()}-{digest[:12]}.pdf"
    shutil.copyfile(pdf, ziel)
    return ziel


def _datenquellen(daten: pathlib.Path, bewerbung: dict) -> list[pathlib.Path]:
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
    quellen += [p for p in (ordner / "anschreiben.yaml", ordner / "stelle.md") if p.is_file()]
    return quellen


def _hinweise_firma(alle: list[dict], bewerbung: dict) -> list[str]:
    andere = [b for b in alle if b["id"] != bewerbung["id"] and b["firma"] == bewerbung["firma"]
              and b["status"] in ("Beworben", "Gespräch")]
    return [f"Bei {bewerbung['firma']} läuft schon eine Bewerbung: {b['stelle']} ({b['status']})" for b in andere]


def erfasse_versand(daten: pathlib.Path, bewerbung_id: str, datum: datetime.date, versionierung: Versionierung,
                    art: str = "elektronisch") -> dict:
    daten = daten.resolve()
    if art not in JOBROOM_ART:
        raise ValueError(f"art muss eine von {', '.join(JOBROOM_ART)} sein")
    register = Register(daten)
    bewerbung = register.hole(bewerbung_id)
    if bewerbung.get("versand"):
        raise ValueError(f"Diese Bewerbung wurde bereits am {bewerbung['versand']['datum']} versendet")
    pdfs = {a: p for a, p in unterlagen.pdf_pfade(daten, bewerbung_id).items() if p.is_file()}
    if "lebenslauf" not in pdfs:
        raise ValueError("Lebenslauf-PDF fehlt: zuerst die Unterlagen erstellen und prüfen")

    abgelegt = {a: lege_ab(daten, p, datum) for a, p in pdfs.items()}
    zweck = f"Versand: {bewerbung['firma']} – {bewerbung['stelle']} ({datum:%d.%m.%Y})"
    quellen = _datenquellen(daten, bewerbung)
    Ablage(daten).markiere_genutzt(quellen, zweck)

    versendet = {"datum": datum.isoformat(), "art": art,
                 "dateien": {a: p.relative_to(daten).as_posix() for a, p in abgelegt.items()}}
    neu = {**bewerbung, "status": "Beworben", "beworben_am": datum.isoformat(), "versand": versendet}
    neu = register.speichere({**neu, "jobroom": {**jobroom_vorschlag(neu), "art": art}})

    # Ohne Git bleiben frühere Fassungen unter versendet/ liegen und werden hier nachgeholt (MIN-304)
    alle_fassungen = sorted((daten / ORDNER).glob("*.pdf"))
    varianten = [p for p in (daten / "varianten.yaml",) if p.is_file()]
    hinweise = _hinweise_firma(register.alle(), neu)
    try:
        commit = versionierung.friere_ein([*alle_fassungen, *quellen, *varianten, register.pfad], zweck)
    except (RuntimeError, subprocess.CalledProcessError, OSError) as fehler:
        # Der Versand ist erfasst; eingefroren wird beim nächsten Versand mit (versendet/ und Register sind dabei)
        commit = None
        hinweise.append(f"Versand erfasst, aber nicht in Git eingefroren: {fehler}")
    if isinstance(versionierung, OhneGit):
        hinweise.append(versionierung.hinweis)
    return {"bewerbung": neu, "commit": commit, "hinweise": hinweise}
