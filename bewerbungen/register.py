"""Bewerbungsregister (MIN-306): alle Bewerbungen mit Daten, Status und Job-Room-Angaben.

Gespeichert in `bewerbungen.yaml` im Datenordner. Jede Bewerbung hat eine eindeutige ID; geschrieben wird
nur über die ID, nie über eine Position. Import und Export im Spaltenformat der Google-Sheet-Jobliste.

  python register.py importiere jobliste.csv ../../daten
  python register.py exportiere ../../daten > jobliste.csv
"""
import argparse
import csv
import datetime
import pathlib
import re
import sys
import threading
import unicodedata

from dateien import lies_yaml, schreibe_yaml

DATEI = "bewerbungen.yaml"
STATUS = ("Gemerkt", "Bewerben", "Beworben", "Gespräch", "Absage", "Zusage", "Verworfen", "Zurückgezogen")
TEXTFELDER = ("firma_schluessel", "firma", "stelle", "ort", "pensum", "vermittler", "portal", "link", "notiz", "variante")
DATUMSFELDER = ("eingetragen_am", "beworben_am", "frist", "absage_am", "gespraech_am")
JOBROOM_ART = ("elektronisch", "schriftlich", "persönlich", "telefonisch")
JOBROOM_ERGEBNIS = ("offen", "Absage", "Vorstellungsgespräch", "Anstellung")
JOBROOM_PENSUM = ("Vollzeit", "Teilzeit")
JOBROOM_TEXT = ("arbeitgeber", "adresse", "kontaktperson", "kontakt", "stelle")
JOBROOM_FELDER = ("datum", *JOBROOM_TEXT, "pensum", "art", "ergebnis", "rav_zuweisung", "erfasst_am")
SPALTEN = ["Firmen-Schlüssel", "Arbeitgeber", "Stelle", "Ort", "Pensum", "Inserent / Vermittler", "Portal(e)",
           "Link", "Status", "Beworben am", "Frist", "Notiz"]
ZUSATZ_SPALTEN = ["Eingetragen am", "Passung"]  # Spalten N und O der Jobliste (M ist die Duplikat-Formel)
MAX_ID = 64
ID_MUSTER = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


# Werte prüfen


def iso_datum(wert, feld: str) -> str:
    """ISO (2026-09-23) oder Schweizer Format (23.09.2026) → ISO; alles andere ist ein Fehler."""
    text = str(wert).strip()
    for format in ("%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.datetime.strptime(text, format).date().isoformat()
        except ValueError:
            continue
    raise ValueError(f"{feld}: kein gültiges Datum ({text!r}), erwartet z.B. 23.09.2026")


def schweizer_datum(iso: str | None) -> str:
    return datetime.date.fromisoformat(iso).strftime("%d.%m.%Y") if iso else ""


def pruefe_passung(wert) -> int | float:
    """Passung als Schweizer Note 1–6 in halben Schritten (6 = passt ohne Haken); auch "4,5" aus der Jobliste."""
    if isinstance(wert, bool):
        raise ValueError("passung muss eine Note von 1 bis 6 sein")
    try:
        note = float(str(wert).strip().replace(",", "."))
    except ValueError:
        raise ValueError(f"passung muss eine Note von 1 bis 6 sein, nicht {wert!r}") from None
    if not 1 <= note <= 6 or note * 2 != int(note * 2):
        raise ValueError(f"passung muss eine Note von 1 bis 6 in halben Schritten sein, nicht {wert!r}")
    return int(note) if note.is_integer() else note


def _pruefe_jobroom(j) -> dict:
    if not isinstance(j, dict):
        raise ValueError("jobroom muss eine Zuordnung sein")
    unbekannt = set(j) - set(JOBROOM_FELDER)
    if unbekannt:
        raise ValueError(f"jobroom: unbekannte Felder {sorted(unbekannt)}")
    erlaubt = {"art": JOBROOM_ART, "ergebnis": JOBROOM_ERGEBNIS, "pensum": JOBROOM_PENSUM}
    neu = {}
    for key, wert in j.items():
        if wert in (None, ""):
            continue
        if key in ("datum", "erfasst_am"):
            neu[key] = iso_datum(wert, f"jobroom.{key}")
        elif key in erlaubt:
            if wert not in erlaubt[key]:
                raise ValueError(f"jobroom.{key} muss eines von {', '.join(erlaubt[key])} sein, nicht {wert!r}")
            neu[key] = wert
        elif key == "rav_zuweisung":
            if not isinstance(wert, bool):
                raise ValueError("jobroom.rav_zuweisung muss true oder false sein")
            neu[key] = wert
        else:
            neu[key] = str(wert).strip()
    return neu


def pruefe_bewerbung(b: dict) -> dict:
    """Bewerbung prüfen und als neues, bereinigtes Dict liefern (leere Felder entfallen)."""
    if not isinstance(b, dict):
        raise ValueError("Bewerbung muss eine Zuordnung sein")
    bekannt = {"id", "status", "versand", "jobroom", "passung", *TEXTFELDER, *DATUMSFELDER}
    unbekannt = set(b) - bekannt
    if unbekannt:
        raise ValueError(f"Unbekannte Felder: {sorted(unbekannt)}")
    if not isinstance(b.get("id"), str) or not ID_MUSTER.fullmatch(b["id"]):
        raise ValueError(f"id muss aus Kleinbuchstaben, Ziffern und Bindestrichen bestehen, nicht {b.get('id')!r}")
    for pflicht in ("firma", "stelle"):
        if not b.get(pflicht) or not str(b[pflicht]).strip():
            raise ValueError(f"{pflicht} fehlt")
    status = b.get("status") or "Gemerkt"
    if status not in STATUS:
        raise ValueError(f"status muss eines von {', '.join(STATUS)} sein, nicht {status!r}")
    link = str(b.get("link") or "").strip()
    if link and not link.startswith(("https://", "http://")):
        raise ValueError("link muss mit https:// oder http:// beginnen")
    neu = {"id": b["id"], "status": status}
    for key in TEXTFELDER:
        if b.get(key) not in (None, ""):
            neu[key] = str(b[key]).strip()
    for key in DATUMSFELDER:
        if b.get(key) not in (None, ""):
            neu[key] = iso_datum(b[key], key)
    if b.get("passung") not in (None, ""):
        neu["passung"] = pruefe_passung(b["passung"])
    if b.get("jobroom"):
        jobroom = _pruefe_jobroom(b["jobroom"])
        if jobroom:
            neu["jobroom"] = jobroom
    if b.get("versand"):
        if not isinstance(b["versand"], dict):
            raise ValueError("versand muss eine Zuordnung sein")
        neu["versand"] = dict(b["versand"])
    return neu


def slug(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")


def erzeuge_id(firma: str, stelle: str, vorhandene: set[str]) -> str:
    basis = f"{slug(firma)}-{slug(stelle)}".strip("-") or "bewerbung"
    if len(basis) > MAX_ID:
        basis = basis[:MAX_ID + 1].rsplit("-", 1)[0]  # an einer Wortgrenze kürzen
    kandidat, n = basis, 2
    while kandidat in vorhandene:
        kandidat, n = f"{basis}-{n}", n + 1
    return kandidat


# Job-Room (Nachweis der Arbeitsbemühungen)


def jobroom_vorschlag(b: dict) -> dict:
    """Werte fürs Job-Room-Formular aus der Bewerbung ableiten; bereits erfasste Werte haben Vorrang."""
    ergebnis = {"Absage": "Absage", "Gespräch": "Vorstellungsgespräch", "Zusage": "Anstellung"}.get(b.get("status"), "offen")
    zahlen = [int(z) for z in re.findall(r"\d+", b.get("pensum", ""))]
    pensum = "Vollzeit" if zahlen and min(zahlen) >= 100 else ("Teilzeit" if zahlen else None)
    vorschlag = {
        "datum": b.get("beworben_am"),
        "arbeitgeber": b.get("firma"),
        "stelle": b.get("stelle"),
        "pensum": pensum,
        "art": "elektronisch",
        "ergebnis": ergebnis,
        "rav_zuweisung": False,
    }
    return {k: v for k, v in {**vorschlag, **(b.get("jobroom") or {})}.items() if v not in (None, "")}


# Register


class Register:
    def __init__(self, ordner: pathlib.Path) -> None:
        self.ordner = ordner.resolve()
        self.pfad = self.ordner / DATEI
        self._sperre = threading.Lock()

    def alle(self) -> list[dict]:
        return [pruefe_bewerbung(b) for b in lies_yaml(self.pfad, [])]

    def hole(self, bewerbung_id: str) -> dict:
        for b in self.alle():
            if b["id"] == bewerbung_id:
                return b
        raise KeyError(f"Bewerbung {bewerbung_id!r} nicht gefunden")

    def _schreibe(self, bewerbungen: list[dict]) -> None:
        schreibe_yaml(self.pfad, bewerbungen, "# Bewerbungsregister, geschrieben vom Bewerbungsassistenten\n")

    def speichere(self, bewerbung: dict) -> dict:
        """Bewerbung neu anlegen oder per ID ersetzen."""
        neu = pruefe_bewerbung(bewerbung)
        with self._sperre:
            alle = self.alle()
            ids = [b["id"] for b in alle]
            liste = [neu if b["id"] == neu["id"] else b for b in alle] if neu["id"] in ids else alle + [neu]
            self._schreibe(liste)
        return neu

    def neu(self, firma: str, stelle: str, **felder) -> dict:
        vorhandene = {b["id"] for b in self.alle()}
        bewerbung_id = felder.pop("id", None) or erzeuge_id(felder.get("firma_schluessel") or firma, stelle, vorhandene)
        if bewerbung_id in vorhandene:
            raise ValueError(f"Bewerbung {bewerbung_id!r} gibt es schon")
        eingetragen = felder.pop("eingetragen_am", None) or datetime.date.today().isoformat()
        return self.speichere({"id": bewerbung_id, "firma": firma, "stelle": stelle, "eingetragen_am": eingetragen,
                               **felder})

    def fuehre_zusammen(self, importiert: list[dict]) -> list[dict]:
        """Importierte Bewerbungen ergänzen; vorhandene IDs bleiben unverändert. Liefert die neuen."""
        with self._sperre:
            alle = self.alle()
            vorhandene = {b["id"] for b in alle}
            neue = [pruefe_bewerbung(b) for b in importiert if b["id"] not in vorhandene]
            self._schreibe(alle + neue)
        return neue


# Jobliste (Google Sheet, Tab "Stellen")


def _aus_zeile(zeile: list[str], vorhandene: set[str]) -> dict:
    werte = (list(zeile) + [""] * 13)[:13]
    zusatz = [str(w).strip() for w in (list(zeile) + [""] * 15)[13:15]]
    schluessel, firma, stelle, ort, pensum, vermittler, portal, link, status_roh, beworben, frist, notiz, dup = (
        w.strip() for w in werte
    )
    notizen = [notiz] if notiz else []
    status = next((s for s in STATUS if status_roh.startswith(s)), "Gemerkt")
    if status_roh and status_roh != status:
        notizen.append(f"Status in der Jobliste: {status_roh}")
    b = {"id": erzeuge_id(schluessel or firma, stelle, vorhandene), "firma_schluessel": schluessel, "firma": firma,
         "stelle": stelle, "ort": ort, "pensum": pensum, "vermittler": vermittler, "portal": portal,
         "status": status}
    if link.startswith(("https://", "http://")):
        b["link"] = link
    elif link:
        notizen.append(f"Link: {link}")
    for key, text in (("beworben_am", beworben), ("frist", frist)):
        try:
            if text:
                b[key] = iso_datum(text, key)
        except ValueError:
            notizen.append(f"{'Beworben' if key == 'beworben_am' else 'Frist'}: {text}")
    if zusatz[0]:
        b["eingetragen_am"] = iso_datum(zusatz[0], "eingetragen_am")
    if zusatz[1]:
        b["passung"] = zusatz[1]
    absage = re.search(r"Absage (\d{2}\.\d{2}\.\d{4})", notiz)
    if absage:
        b["absage_am"] = iso_datum(absage.group(1), "absage_am")
    if dup:
        notizen.append(dup)
    b["notiz"] = "; ".join(notizen)
    return pruefe_bewerbung(b)


def aus_jobliste(zeilen: list[list[str]]) -> list[dict]:
    """Zeilen der Jobliste (mit Kopfzeile) in Bewerbungen umwandeln; leere Zeilen werden übersprungen."""
    bewerbungen, vorhandene = [], set()
    for zeile in zeilen[1:]:
        if len(zeile) < 3 or not (zeile[1].strip() and zeile[2].strip()):
            continue
        b = _aus_zeile(zeile, vorhandene)
        vorhandene.add(b["id"])
        bewerbungen.append(b)
    return bewerbungen


def zusatzspalten(b: dict) -> list:
    """Werte für die Spalten N und O der Jobliste; die Passung als Zahl, damit das Sheet sie als Note zeigt."""
    return [schweizer_datum(b.get("eingetragen_am")), b.get("passung", "")]


def als_jobliste(bewerbungen: list[dict]) -> list[list[str]]:
    zeilen = [list(SPALTEN)]
    for b in bewerbungen:
        zeilen.append([b.get("firma_schluessel", ""), b["firma"], b["stelle"], b.get("ort", ""), b.get("pensum", ""),
                       b.get("vermittler", ""), b.get("portal", ""), b.get("link", ""), b["status"],
                       schweizer_datum(b.get("beworben_am")), schweizer_datum(b.get("frist")), b.get("notiz", "")])
    return zeilen


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Bewerbungsregister: Import und Export im Format der Jobliste")
    sub = ap.add_subparsers(dest="befehl", required=True)
    imp = sub.add_parser("importiere", help="CSV-Export der Jobliste ins Register übernehmen (vorhandene bleiben)")
    imp.add_argument("csv")
    imp.add_argument("daten")
    exp = sub.add_parser("exportiere", help="Register als CSV im Format der Jobliste ausgeben")
    exp.add_argument("daten")
    args = ap.parse_args(argv)
    reg = Register(pathlib.Path(args.daten))
    if args.befehl == "importiere":
        with open(args.csv, newline="", encoding="utf-8") as f:
            neue = reg.fuehre_zusammen(aus_jobliste(list(csv.reader(f))))
        print(f"{len(neue)} neue Bewerbungen übernommen")
    else:
        csv.writer(sys.stdout).writerows(als_jobliste(reg.alle()))


if __name__ == "__main__":
    main()
