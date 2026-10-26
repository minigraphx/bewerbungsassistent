"""Anschreiben als PDF erzeugen, im Design des Lebenslauf-Themes.

Beispiele:
  python anschreiben.py data/anschreiben-beispiel.yaml -o build/anschreiben.pdf
  python anschreiben.py ../../daten/anschreiben/firma.yaml --cv ../../daten/cv.yaml \\
      --build-dir ../../daten/.build -o ../../daten/out/firma-anschreiben.pdf
"""
import argparse
import datetime
import json
import os
import pathlib

import typst
import yaml

from build import ROOT, typst_pfad

SPRACHEN = ("de", "en")
PFLICHTFELDER = ("empfaenger", "betreff", "anrede", "text", "gruss")
MONATE = {
    "de": ("Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
           "August", "September", "Oktober", "November", "Dezember"),
    "en": ("January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December"),
}


def formatiere_datum(datum: datetime.date | str, sprache: str) -> str:
    """24. Oktober 2026 (de) bzw. 24 October 2026 (en)."""
    d = datum if isinstance(datum, datetime.date) else datetime.date.fromisoformat(str(datum))
    monat = MONATE[sprache][d.month - 1]
    return f"{d.day}. {monat} {d.year}" if sprache == "de" else f"{d.day} {monat} {d.year}"


def pruefe_brief(brief: dict) -> dict:
    """Pflichtfelder und Typen prüfen; liefert die Daten unverändert zurück."""
    if not isinstance(brief, dict):
        raise ValueError("Das Anschreiben muss eine YAML-Zuordnung sein")
    fehlend = [f for f in PFLICHTFELDER if not brief.get(f)]
    if fehlend:
        raise ValueError(f"Im Anschreiben fehlen: {', '.join(fehlend)}")
    empfaenger = brief["empfaenger"]
    if not isinstance(empfaenger, list) or not all(isinstance(z, str) and z for z in empfaenger):
        raise ValueError("empfaenger muss eine Liste von Zeilen sein, z.B. [Firma AG, Strasse 1, 3000 Bern]")
    if brief.get("sprache", "de") not in SPRACHEN:
        raise ValueError(f"sprache muss eine von {', '.join(SPRACHEN)} sein, nicht {brief['sprache']!r}")
    for feld in ("betreff", "anrede", "text", "gruss"):
        if not isinstance(brief[feld], str):
            raise ValueError(f"{feld} muss Text sein")
    return brief


def absender_aus_cv(cv: dict) -> dict:
    """Name und Kontaktzeile (Adresse · Telefon · E-Mail) aus `basics` des Lebenslaufs."""
    basics = cv.get("basics") or {}
    ort = basics.get("location") or {}
    plz_ort = " ".join(str(x) for x in (ort.get("postalCode"), ort.get("city")) if x)
    adresse = ", ".join(x for x in (ort.get("address"), plz_ort) if x)
    zeile = " · ".join(str(x) for x in (adresse, basics.get("phone"), basics.get("email")) if x)
    return {"name": basics.get("name", ""), "zeile": zeile}


def absaetze(text: str) -> list[str]:
    """Absätze an Leerzeilen trennen; Zeilenumbrüche innerhalb eines Absatzes werden zu Leerzeichen."""
    bloecke = [b for b in text.replace("\r\n", "\n").split("\n\n")]
    return [" ".join(z.strip() for z in b.splitlines() if z.strip()) for b in bloecke if b.strip()]


def bereite_vor(brief: dict, cv: dict | None, heute: datetime.date) -> dict:
    """Daten für das Typst-Template: Absender, Ort und Datum fertig formatiert, Text in Absätzen."""
    pruefe_brief(brief)
    sprache = brief.get("sprache", "de")
    if brief.get("absender"):
        absender = dict(brief["absender"])
    elif cv is not None:
        absender = absender_aus_cv(cv)
    else:
        raise ValueError("Kein absender im Anschreiben und kein Lebenslauf angegeben (lebenslauf: oder --cv)")
    datum = formatiere_datum(brief.get("datum") or heute, sprache)
    ort = brief.get("ort")
    return {
        "sprache": sprache,
        "absender": absender,
        "empfaenger": list(brief["empfaenger"]),
        "ort_datum": f"{ort}, {datum}" if ort else datum,
        "betreff": brief["betreff"],
        "anrede": brief["anrede"],
        "absaetze": absaetze(brief["text"]),
        "gruss": brief["gruss"],
        "unterschrift": brief.get("unterschrift") or absender.get("name", ""),
    }


def lade_cv(brief_pfad: pathlib.Path, brief: dict, cv_pfad: str | None) -> dict | None:
    pfad = pathlib.Path(cv_pfad) if cv_pfad else (brief_pfad.parent / brief["lebenslauf"] if brief.get("lebenslauf") else None)
    if pfad is None:
        return None
    if not pfad.is_file():
        raise ValueError(f"Lebenslauf nicht gefunden: {pfad}")
    return yaml.safe_load(pfad.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> pathlib.Path:
    ap = argparse.ArgumentParser(description="Anschreiben als PDF erzeugen")
    ap.add_argument("data", help="Anschreiben (YAML)")
    ap.add_argument("--cv", help="Lebenslauf (YAML) für den Absender; sonst `lebenslauf:` im Anschreiben")
    ap.add_argument("--theme", default="zweispaltig")
    ap.add_argument("--build-dir", help="Ordner für Zwischenstände (Standard: build/ im Modul)")
    ap.add_argument("-o", "--out", default="build/anschreiben.pdf")
    args = ap.parse_args(argv)

    brief_pfad = pathlib.Path(args.data).resolve()
    brief = yaml.safe_load(brief_pfad.read_text(encoding="utf-8")) or {}
    daten = bereite_vor(brief, lade_cv(brief_pfad, brief, args.cv), datetime.date.today())

    build = pathlib.Path(args.build_dir).resolve() if args.build_dir else ROOT / "build"
    build.mkdir(parents=True, exist_ok=True)
    wurzel = pathlib.Path(os.path.commonpath([ROOT, build]))
    daten_json = build / "anschreiben.json"
    daten_json.write_text(json.dumps(daten, ensure_ascii=False, indent=1), encoding="utf-8")

    vorlage = ROOT / "themes" / args.theme / "anschreiben-main.typ"
    if not vorlage.is_file():
        raise ValueError(f"Theme {args.theme!r} hat keine Vorlage für Anschreiben ({vorlage.name})")
    out = pathlib.Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    typst.compile(
        str(vorlage),
        output=str(out),
        root=str(wurzel),
        font_paths=[str(ROOT / "fonts")],
        sys_inputs={"data": typst_pfad(daten_json, wurzel)},
    )
    print(out)
    return out


if __name__ == "__main__":
    main()
