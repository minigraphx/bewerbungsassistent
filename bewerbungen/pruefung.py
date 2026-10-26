"""Automatische Prüfung vor dem Absenden (MIN-262).

Prüft die PDFs formal: Text extrahierbar (Bewerbungssoftware/ATS), Seitenzahl, Platzhalter, und im Anschreiben
Firma, Stelle, Datum sowie eine einheitliche Anrede (Du/Sie). Der inhaltliche Abgleich mit den Anforderungen der
Stelle und mit den Belegen ist Aufgabe des Skills `bewerbung` (LLM). Der Nutzer sieht sich nur die PDFs an,
die Befunde stehen daneben.
"""
import dataclasses
import datetime
import pathlib
import re

from pypdf import PdfReader
from pypdf.errors import PdfReadError

import unterlagen

PLATZHALTER = re.compile(r"TODO|XXX|\{\{|\}\}|\[\[|Lorem ipsum|<Firma>|<Stelle>|<Name>", re.IGNORECASE)
RECHTSFORMEN = re.compile(r"\b(AG|GmbH|SA|Sàrl|Genossenschaft|Group|Schweiz|Switzerland)\b\.?", re.IGNORECASE)
MONATE = {m: i + 1 for i, m in enumerate(("Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August",
                                           "September", "Oktober", "November", "Dezember"))}
MONATE_EN = {m: i + 1 for i, m in enumerate(("January", "February", "March", "April", "May", "June", "July",
                                              "August", "September", "October", "November", "December"))}
MAX_SEITEN = {"lebenslauf": 3, "anschreiben": 1}
NAMEN = {"lebenslauf": "Lebenslauf", "anschreiben": "Anschreiben"}
MAX_ALTER_TAGE = 14


@dataclasses.dataclass(frozen=True)
class Befund:
    stufe: str  # ok | hinweis | fehler
    text: str


def _seiten(pdf: pathlib.Path) -> list[str]:
    return [seite.extract_text() or "" for seite in PdfReader(pdf).pages]


def pruefe_pdf(pdf: pathlib.Path, art: str) -> list[Befund]:
    name = NAMEN[art]
    if not pdf.is_file():
        return [Befund("fehler", f"{name}: PDF fehlt ({pdf.name}). Zuerst die Unterlagen erstellen.")]
    try:
        seiten = _seiten(pdf)
    except (PdfReadError, ValueError, OSError) as fehler:
        return [Befund("fehler", f"{name}: PDF lässt sich nicht lesen ({fehler})")]
    befunde = []
    text = "\n".join(seiten)
    if len(text.strip()) < 200:
        befunde.append(Befund("fehler", f"{name}: kaum Text extrahierbar – Bewerbungssoftware (ATS) liest es nicht"))
    else:
        befunde.append(Befund("ok", f"{name}: Text extrahierbar ({len(seiten)} Seite{'n' if len(seiten) != 1 else ''})"))
    if len(seiten) > MAX_SEITEN[art]:
        stufe = "fehler" if art == "anschreiben" else "hinweis"
        befunde.append(Befund(stufe, f"{name}: {len(seiten)} Seiten, empfohlen höchstens {MAX_SEITEN[art]} Seite(n)"))
    if PLATZHALTER.search(text):
        befunde.append(Befund("fehler", f"{name}: Platzhalter gefunden ({PLATZHALTER.search(text).group(0)})"))
    return befunde


def _datum_im_text(text: str) -> datetime.date | None:
    for monate in (MONATE, MONATE_EN):
        muster = rf"(\d{{1,2}})\.? ({'|'.join(monate)}) (\d{{4}})"
        treffer = re.search(muster, text)
        if treffer:
            return datetime.date(int(treffer.group(3)), monate[treffer.group(2)], int(treffer.group(1)))
    return None


def firmennamen(firma: str) -> list[str]:
    """Namen, unter denen die Firma im Anschreiben stehen darf: "Tochter (Mutter AG)" → Tochter, Mutter;
    "unbekannt (über ONE Agency)" → ONE Agency. Rechtsformen fallen weg, "unbekannt" zählt nicht."""
    teile = [t.strip() for t in re.split(r"[()]", firma) if t.strip()]
    namen = [RECHTSFORMEN.sub("", re.sub(r"^über\s+", "", t)).strip(" ,-") for t in teile]
    return [n for n in namen if n and n.lower() != "unbekannt"] or [firma]


def pruefe_anschreiben_text(text: str, bewerbung: dict, heute: datetime.date) -> list[Befund]:
    befunde = []
    namen = firmennamen(bewerbung["firma"])
    genannt = next((n for n in namen if n.lower() in text.lower()), None)
    if genannt:
        befunde.append(Befund("ok", f"Anschreiben: Firma „{genannt}“ genannt"))
    else:
        befunde.append(Befund("fehler", f"Anschreiben: Firma „{' / '.join(namen)}“ kommt nicht vor – falsche Vorlage?"))
    woerter = [w for w in re.findall(r"\w{4,}", bewerbung["stelle"])]
    gefunden = [w for w in woerter if w.lower() in text.lower()]
    if not woerter or len(gefunden) * 2 >= len(woerter):
        befunde.append(Befund("ok", "Anschreiben: Stellentitel genannt"))
    else:
        befunde.append(Befund("hinweis", f"Anschreiben: Stelle „{bewerbung['stelle']}“ kaum erwähnt – Betreff prüfen"))
    datum = _datum_im_text(text)
    if datum is None:
        befunde.append(Befund("hinweis", "Anschreiben: kein Datum gefunden"))
    elif datum > heute or (heute - datum).days > MAX_ALTER_TAGE:
        befunde.append(Befund("hinweis", f"Anschreiben: Datum {datum:%d.%m.%Y} ist nicht aktuell"))
    else:
        befunde.append(Befund("ok", f"Anschreiben: Datum {datum:%d.%m.%Y}"))
    du = re.search(r"\b(Liebe[rs]?|Hallo|Hoi)\b", text) is not None
    sie = re.search(r"\b(Sehr geehrte[rn]?)\b", text) is not None
    if du and re.search(r"\b(Sie|Ihnen|Ihre[rnms]?)\b", text):
        befunde.append(Befund("hinweis", "Anschreiben: Anrede in Du-Form, im Text aber Sie/Ihnen/Ihre"))
    elif sie and re.search(r"\b(euch|eure[rnms]?|ihr)\b", text):
        befunde.append(Befund("hinweis", "Anschreiben: Anrede in Sie-Form, im Text aber euch/eure/ihr"))
    if PLATZHALTER.search(text):
        befunde.append(Befund("fehler", f"Anschreiben: Platzhalter gefunden ({PLATZHALTER.search(text).group(0)})"))
    return befunde


def pruefe(daten: pathlib.Path, bewerbung: dict, heute: datetime.date) -> list[Befund]:
    """Alle Prüfungen einer Bewerbung; Fehler zuerst."""
    pfade = unterlagen.pdf_pfade(daten, bewerbung["id"])
    befunde = pruefe_pdf(pfade["lebenslauf"], "lebenslauf")
    if pfade["anschreiben"].is_file() or pfade["anschreiben"].with_suffix(".yaml").is_file():
        befunde += pruefe_pdf(pfade["anschreiben"], "anschreiben")
        if pfade["anschreiben"].is_file():
            try:
                text = "\n".join(_seiten(pfade["anschreiben"]))
            except (PdfReadError, ValueError, OSError):
                text = ""
            if text:
                befunde += pruefe_anschreiben_text(text, bewerbung, heute)
    else:
        befunde.append(Befund("hinweis", "Kein Anschreiben (anschreiben.yaml fehlt)"))
    reihenfolge = {"fehler": 0, "hinweis": 1, "ok": 2}
    return sorted(befunde, key=lambda b: reihenfolge[b.stufe])
