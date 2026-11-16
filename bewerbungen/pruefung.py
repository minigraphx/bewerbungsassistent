"""Automatische Prüfung vor dem Absenden (MIN-262).

Prüft die PDFs formal: Text extrahierbar (Bewerbungssoftware/ATS), Seitenzahl, Platzhalter, in jedem erzeugten PDF
den Satz (G52, layout_check.py: Füllung der letzten Seite, allein stehende Überschriften, Text am Rand, Überlappungen),
und im Anschreiben
Firma, Stelle, Datum, eine einheitliche Anrede (Du/Sie) und die Ansprechperson in Adresse und Anrede. Der inhaltliche Abgleich mit den Anforderungen der
Stelle und mit den Belegen ist Aufgabe des Skills `bewerbung` (LLM). Der Nutzer sieht sich nur die PDFs an,
die Befunde stehen daneben.
"""
import dataclasses
import datetime
import pathlib
import re
from collections.abc import Callable

import yaml
from pypdf import PdfReader
from pypdf.errors import PdfReadError

import pfade  # noqa: F401  (makes the module lebenslauf importable)
import cut_choice
import cuts
import cv_cuts
import layout_check
import layout_confirmed
import mark_settings
import page_limit
import unterlagen

PLATZHALTER = re.compile(r"TODO|XXX|\{\{|\}\}|\[\[|Lorem ipsum|<Firma>|<Stelle>|<Name>", re.IGNORECASE)
RECHTSFORMEN = re.compile(r"\b(AG|GmbH|SA|Sàrl|Genossenschaft|Group|Schweiz|Switzerland)\b\.?", re.IGNORECASE)
MONATE = {m: i + 1 for i, m in enumerate(("Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August",
                                           "September", "Oktober", "November", "Dezember"))}
MONATE_EN = {m: i + 1 for i, m in enumerate(("January", "February", "March", "April", "May", "June", "July",
                                              "August", "September", "October", "November", "December"))}
LOGO_MISSING = ("Das Logo fehlt. Das Dossier zeigt darum die Initialen im Zeichen des Designs. "
                "Logo wählen unter «Erweitert».")
# G51: the letter one page, the CV two unless three are allowed (page_limit); dossier: cover, letter, CV and more
MAX_SEITEN = {"lebenslauf": page_limit.DEFAULT, "anschreiben": 1, "dossier": 8}
ONLY_IN_BASICS = "Weiter kürzen lässt sich nur unter «Meine Angaben»."
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
    schluessel: str | None = None  # a layout breach the person confirms before sending (G52, layout_confirmed)
    bestaetigt: bool = False
    # A CV over its limit (G92): the lines over, the cuts to tick and whether three pages can be allowed; it is never
    # confirmed with «So lassen», only cut or allowed (cut_choice.py)
    kuerzen: dict | None = None
    # A letter over one page (G94): about how many lines are over and the place of its longest paragraph, which the
    # step Anschreiben marks; cut there or confirmed with «So lassen»
    letter_cut: dict | None = None


def _seiten(pdf: pathlib.Path) -> list[str]:
    return [seite.extract_text() or "" for seite in PdfReader(pdf).pages]


def _lines_over(pdf: pathlib.Path, limit: int) -> int:
    try:
        return layout_check.lines_beyond(pdf, limit)
    except (PdfReadError, ValueError, OSError, KeyError, IndexError, TypeError):
        return 0  # the finding says it does not fit, without a number


def _cv_over_limit(pdf: pathlib.Path, pages: int, limit: int, key: str | None, offer: Callable[[int], dict]) -> Befund:
    """A built CV over its limit (G92): how many lines are over, and the choice of cuts or three pages."""
    lines = _lines_over(pdf, limit)
    tighter = (f"Auch enger gesetzt sind es etwa {lines} {'Zeile' if lines == 1 else 'Zeilen'} zu viel." if lines
               else "Auch enger gesetzt passt er nicht.")
    text = f"Lebenslauf: {pages} Seiten, erlaubt sind höchstens {limit}. {tighter}"
    choice = offer(limit)
    if not choice["optionen"] and not choice["drei_seiten"]:
        return Befund("hinweis", f"{text} {ONLY_IN_BASICS}")
    return Befund("hinweis", text, schluessel=key, kuerzen={"zeilen": lines, **choice})


def _letter_over_limit(pdf: pathlib.Path, pages: int, key: str | None, letter: str) -> Befund:
    """A built letter over its one page (G94): set as tight as possible, so the finding names how many lines are
    over and its longest paragraph; the person cuts it in the letter or confirms it as it is."""
    lines = _lines_over(pdf, MAX_SEITEN["anschreiben"])
    tight = (f"Auch so eng wie möglich gesetzt sind es etwa {lines} {'Zeile' if lines == 1 else 'Zeilen'} zu viel."
             if lines else "Auch so eng wie möglich gesetzt passt es nicht.")
    named = cuts.for_letter(letter)
    text = f"Anschreiben: {pages} Seiten, erlaubt ist eine. {tight}"
    if named:
        text += f" Kürzen lässt sich: {', '.join(named)}."
    return Befund("fehler", text, schluessel=key,
                  letter_cut={"lines": lines, "paragraph": cuts.longest_paragraph(letter)})


def _over_limit(art: str, pages: int, limit: int, as_it_is: bool, key: str | None = None) -> Befund:
    """A document over its page limit (G51) that the app cannot cut: an own or sent file, the dossier as a whole, or
    a CV variant that is a finished file."""
    name = NAMEN[art]
    if as_it_is or art == "dossier":
        return Befund("hinweis", f"{name}: {pages} Seiten, empfohlen höchstens {limit} Seite(n)")
    return Befund("hinweis", f"{name}: {pages} Seiten, erlaubt sind höchstens {limit}. Auch enger gesetzt passt er "
                             "nicht.", schluessel=key)


def layout_findings(pdf: pathlib.Path, art: str, headings: tuple[str, ...] = (),
                    skipped: frozenset[str] = frozenset()) -> list[Befund]:
    """The breaches of the layout rules in a generated PDF, each with its own key (G52); `skipped` names rules
    not to report."""
    name = NAMEN[art]
    try:
        breaches = [b for b in layout_check.check(pdf, art, headings=headings) if b.rule not in skipped]
    except (PdfReadError, ValueError, OSError, KeyError, IndexError, TypeError) as fehler:
        return [Befund("hinweis", f"{name}: Der Satz der Seiten liess sich nicht messen ({fehler}). Bitte das PDF "
                                  "selbst ansehen.", schluessel=layout_confirmed.key(pdf, "messung", 1))]
    found, seen = [], {}
    for breach in breaches:
        number = seen[(breach.rule, breach.page)] = seen.get((breach.rule, breach.page), -1) + 1
        found.append(Befund("hinweis", f"{name}, Seite {breach.page}: {breach.reason}",
                            schluessel=layout_confirmed.key(pdf, breach.rule, breach.page, number)))
    return found


def pruefe_pdf(pdf: pathlib.Path, art: str, as_it_is: bool = False, limit: int | None = None,
               letter: str = "", headings: tuple[str, ...] = (),
               offer: Callable[[int], dict] | None = None) -> list[Befund]:
    """With `as_it_is` the person uploaded the file to use it unchanged: what is not broken is their decision, and
    only a generated PDF is measured for its layout. `limit` is the page limit (MAX_SEITEN without one); `letter` is
    the text of a built letter, whose longest paragraph a letter over one page names (G94), `offer` gives a built CV
    the cuts to tick (G92); `headings` are the CV's own section headings."""
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
    limit = limit or MAX_SEITEN[art]
    skipped = frozenset()
    if len(seiten) > limit:
        key = None if as_it_is else layout_confirmed.key(pdf, "seiten", limit + 1)
        if art == "lebenslauf" and offer is not None and not as_it_is:
            over = _cv_over_limit(pdf, len(seiten), limit, key, offer)
            befunde.append(over)
            # the last page is the one being cut away: its fill waits until the CV keeps its limit (G92)
            skipped = frozenset({"fuellung"}) if over.kuerzen else skipped
        elif art == "anschreiben" and not as_it_is:
            befunde.append(_letter_over_limit(pdf, len(seiten), key, letter))
            # G94: its second page is as short as the tightest setting leaves it, on purpose
            skipped = frozenset({"fuellung"})
        else:
            befunde.append(_over_limit(art, len(seiten), limit, as_it_is, key))
    if PLATZHALTER.search(text):
        befunde.append(Befund(content_stufe, f"{name}: Platzhalter gefunden ({PLATZHALTER.search(text).group(0)})"))
    if not as_it_is:
        befunde += layout_findings(pdf, art, headings, skipped)
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


def _letter_text(letter: pathlib.Path) -> str:
    try:
        data = yaml.safe_load(letter.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return ""
    text = data.get("text") if isinstance(data, dict) else None
    return text if isinstance(text, str) else ""


def _own_headings(cv: object) -> tuple[str, ...]:
    """The section headings a CV names itself (`x-beschriftungen`, MIN-335)."""
    labels = cv.get("x-beschriftungen") if isinstance(cv, dict) else None
    return tuple(v for v in labels.values() if isinstance(v, str)) if isinstance(labels, dict) else ()


def _with_confirmations(daten: pathlib.Path, entry_id: str, befunde: list[Befund]) -> list[Befund]:
    """Confirmed breaches; a letter over one page the person leaves as it is (G94) no longer counts as an error."""
    done = layout_confirmed.confirmed(daten, entry_id)
    return [_confirmed(b) if b.schluessel in done else b for b in befunde]


def _confirmed(befund: Befund) -> Befund:
    stufe = "hinweis" if befund.letter_cut else befund.stufe
    return dataclasses.replace(befund, bestaetigt=True, stufe=stufe)


def pruefe(daten: pathlib.Path, bewerbung: dict, heute: datetime.date) -> list[Befund]:
    """Alle Prüfungen einer Bewerbung; Fehler zuerst."""
    pfade = unterlagen.wirksame_pdfs(daten, bewerbung)
    gesendet = bool(bewerbung.get("versand"))
    as_it_is = unterlagen.eigener_lebenslauf(daten, bewerbung) is not None or gesendet
    letter_as_it_is = unterlagen.own_letter(daten, bewerbung) is not None or gesendet
    quelle = unterlagen.letter_source(daten, bewerbung["id"])
    cv = unterlagen.tailored_cv(daten, bewerbung)
    headings = _own_headings(cv)
    offer = (lambda limit: cut_choice.offer(daten, bewerbung, limit)) if unterlagen.cuts_apply(daten, bewerbung) else None
    befunde = pruefe_pdf(pfade["lebenslauf"], "lebenslauf", as_it_is=as_it_is,
                         limit=cv_cuts.pages(daten, bewerbung["id"]), headings=headings, offer=offer)
    if pfade["anschreiben"].is_file() or quelle.is_file():
        befunde += pruefe_pdf(pfade["anschreiben"], "anschreiben", as_it_is=letter_as_it_is,
                              letter="" if letter_as_it_is else _letter_text(quelle))
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
        befunde += pruefe_pdf(dossier, "dossier", as_it_is=gesendet, headings=headings)
        if not gesendet and mark_settings.state_of_logo(daten) == "fehlt":
            befunde.append(Befund("hinweis", LOGO_MISSING))
    reihenfolge = {"fehler": 0, "hinweis": 1, "ok": 2}
    return sorted(_with_confirmations(daten, bewerbung["id"], befunde), key=lambda b: reihenfolge[b.stufe])
