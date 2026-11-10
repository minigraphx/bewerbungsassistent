"""Automatische Prüfung vor dem Absenden (MIN-262).

Prüft die PDFs formal: Text extrahierbar (Bewerbungssoftware/ATS), Seitenzahl, Platzhalter, und im Anschreiben
Firma, Stelle, Datum, eine einheitliche Anrede (Du/Sie) und die Ansprechperson in Adresse und Anrede. Der inhaltliche Abgleich mit den Anforderungen der
Stelle und mit den Belegen ist Aufgabe des Skills `bewerbung` (LLM). Der Nutzer sieht sich nur die PDFs an,
die Befunde stehen daneben.
"""
import dataclasses
import datetime
import pathlib
import re

import yaml
from pypdf import PdfReader
from pypdf.errors import PdfReadError

import unterlagen

PLATZHALTER = re.compile(r"TODO|XXX|\{\{|\}\}|\[\[|Lorem ipsum|<Firma>|<Stelle>|<Name>", re.IGNORECASE)
RECHTSFORMEN = re.compile(r"\b(AG|GmbH|SA|Sàrl|Genossenschaft|Group|Schweiz|Switzerland)\b\.?", re.IGNORECASE)
MONATE = {m: i + 1 for i, m in enumerate(("Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August",
                                           "September", "Oktober", "November", "Dezember"))}
MONATE_EN = {m: i + 1 for i, m in enumerate(("January", "February", "March", "April", "May", "June", "July",
                                              "August", "September", "October", "November", "December"))}
MAX_SEITEN = {"lebenslauf": 3, "anschreiben": 1, "dossier": 8}  # dossier: cover, letter, CV and optional pages
NAMEN = {"lebenslauf": "Lebenslauf", "anschreiben": "Anschreiben", "dossier": "Dossier"}
MAX_ALTER_TAGE = 14
CARE_OF = re.compile(r"^(z\.?\s*H\.?(d\.?)?|zu Handen|c/o|Attn\.?:?)\s+", re.IGNORECASE)
PERSON_LINE = re.compile(r"^(Frau|Herr)\s+((?:(?:Prof\.|Dr\.)\s+)*)(.+)$")
SURNAME_PARTICLES = {"von", "van", "de", "del", "di", "du", "le", "la", "zu", "zur"}
WRONG_FORMS = {"Frau": ("Sehr geehrter", "Lieber", "Herr"), "Herr": ("Sehr geehrte", "Liebe", "Frau")}  # words of the other title


@dataclasses.dataclass(frozen=True)
class Befund:
    stufe: str  # ok | hinweis | fehler
    text: str


def _seiten(pdf: pathlib.Path) -> list[str]:
    return [seite.extract_text() or "" for seite in PdfReader(pdf).pages]


def pruefe_pdf(pdf: pathlib.Path, art: str, as_it_is: bool = False) -> list[Befund]:
    """With `as_it_is` the person uploaded the file to use it unchanged: what is not broken is their decision."""
    name = NAMEN[art]
    content_stufe = "hinweis" if as_it_is else "fehler"
    if not pdf.is_file():
        return [Befund("fehler", f"{name}: PDF fehlt ({pdf.name}). Zuerst die Unterlagen erstellen.")]
    try:
        seiten = _seiten(pdf)
    except (PdfReadError, ValueError, OSError) as fehler:
        return [Befund("fehler", f"{name}: PDF lässt sich nicht lesen ({fehler})")]
    befunde = []
    text = "\n".join(seiten)
    if len(text.strip()) < 200:
        befunde.append(Befund(content_stufe, f"{name}: kaum Text extrahierbar – Bewerbungssoftware (ATS) liest es nicht"))
    else:
        befunde.append(Befund("ok", f"{name}: Text extrahierbar ({len(seiten)} Seite{'n' if len(seiten) != 1 else ''})"))
    if len(seiten) > MAX_SEITEN[art]:
        stufe = "fehler" if art == "anschreiben" and not as_it_is else "hinweis"
        befunde.append(Befund(stufe, f"{name}: {len(seiten)} Seiten, empfohlen höchstens {MAX_SEITEN[art]} Seite(n)"))
    if PLATZHALTER.search(text):
        befunde.append(Befund(content_stufe, f"{name}: Platzhalter gefunden ({PLATZHALTER.search(text).group(0)})"))
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


def pruefe_anschreiben_text(text: str, bewerbung: dict, heute: datetime.date, as_it_is: bool = False) -> list[Befund]:
    content_stufe = "hinweis" if as_it_is else "fehler"
    befunde = []
    namen = firmennamen(bewerbung["firma"])
    genannt = next((n for n in namen if n.lower() in text.lower()), None)
    if genannt:
        befunde.append(Befund("ok", f"Anschreiben: Firma „{genannt}“ genannt"))
    else:
        befunde.append(Befund(content_stufe, f"Anschreiben: Firma „{' / '.join(namen)}“ kommt nicht vor – falsche Vorlage?"))
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
        befunde.append(Befund(content_stufe, f"Anschreiben: Platzhalter gefunden ({PLATZHALTER.search(text).group(0)})"))
    return befunde


def _contact_person(address: object) -> dict | None:
    """The person named in the address: title, first names and surname. A company such as „Frau Holle AG“ is none."""
    lines = address if isinstance(address, list) else []
    for line in (CARE_OF.sub("", str(entry).strip()) for entry in lines):
        match = PERSON_LINE.match(line)
        if not match or RECHTSFORMEN.search(line):
            continue
        words = match.group(3).split()
        start = next((i for i, word in enumerate(words) if word.lower() in SURNAME_PARTICLES and i > 0), len(words) - 1)
        return {"title": match.group(1), "first": words[:start], "surname": " ".join(words[start:])}
    return None


def _has_words(text: str, words: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(words)}(?!\w)", text, re.IGNORECASE) is not None


def check_contact_person(address: object, salutation: object) -> list[Befund]:
    """With a person in the address, the salutation must name that person in the right form (MIN-358)."""
    person = _contact_person(address)
    if person is None:
        return []
    text = salutation.strip() if isinstance(salutation, str) else ""
    shown = f"{person['title']} {person['surname']}"
    named = _has_words(text, person["surname"]) or any(_has_words(text, first) for first in person["first"])
    if not named:
        return [Befund("fehler", f"Anschreiben: In der Adresse steht {shown}, in der Anrede „{text}“ nicht")]
    if any(_has_words(text, word) for word in WRONG_FORMS[person["title"]]):
        return [Befund("fehler", f"Anschreiben: Form der Anrede „{text}“ passt nicht zu {shown}")]
    return [Befund("ok", f"Anschreiben: Anrede passt zu {shown}")]


def contact_person_findings(letter: pathlib.Path) -> list[Befund]:
    """From the source of the letter; a file that cannot be read shows up when building the PDF."""
    try:
        data = yaml.safe_load(letter.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return []
    return check_contact_person(data.get("empfaenger"), data.get("anrede")) if isinstance(data, dict) else []


def pruefe(daten: pathlib.Path, bewerbung: dict, heute: datetime.date) -> list[Befund]:
    """Alle Prüfungen einer Bewerbung; Fehler zuerst."""
    pfade = unterlagen.wirksame_pdfs(daten, bewerbung)
    gesendet = bool(bewerbung.get("versand"))
    as_it_is = unterlagen.eigener_lebenslauf(daten, bewerbung) is not None or gesendet
    letter_as_it_is = unterlagen.own_letter(daten, bewerbung) is not None or gesendet
    quelle = unterlagen.letter_source(daten, bewerbung["id"])
    befunde = pruefe_pdf(pfade["lebenslauf"], "lebenslauf", as_it_is=as_it_is)
    if pfade["anschreiben"].is_file() or quelle.is_file():
        befunde += pruefe_pdf(pfade["anschreiben"], "anschreiben", as_it_is=letter_as_it_is)
        if pfade["anschreiben"].is_file():
            try:
                text = "\n".join(_seiten(pfade["anschreiben"]))
            except (PdfReadError, ValueError, OSError):
                text = ""
            if text:
                befunde += pruefe_anschreiben_text(text, bewerbung, heute, as_it_is=letter_as_it_is)
        if not letter_as_it_is:
            befunde += contact_person_findings(quelle)
    else:
        befunde.append(Befund("hinweis", "Kein Anschreiben: weder ein Entwurf noch ein eigenes PDF"))
    dossier = unterlagen.dossier_file(daten, bewerbung)
    if dossier:  # G40: only while chosen or once sent, so the preset checks what it always did
        befunde += pruefe_pdf(dossier, "dossier", as_it_is=gesendet)
    reihenfolge = {"fehler": 0, "hinweis": 1, "ok": 2}
    return sorted(befunde, key=lambda b: reihenfolge[b.stufe])
