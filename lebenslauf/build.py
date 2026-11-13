"""Lebenslauf als PDF erzeugen.

Beispiele:
  python build.py data/beispiel.yaml
  python build.py data/beispiel.yaml --job jobs/beispiel-ki.yaml --theme einspaltig -o out/ki.pdf
  python build.py ../../daten/cv.yaml --build-dir ../../daten/.build -o ../../daten/out/cv.pdf
"""
import argparse
import datetime
import json
import pathlib

import typst
import yaml

import page_fill
from tailor import tailor
from typst_root import typst_root

ROOT = pathlib.Path(__file__).resolve().parent
ZOOM_MIN, ZOOM_MAX = 1, 4
SPRACHEN = ("de", "en")
# Abschnitte, deren Überschrift ein Lebenslauf mit `x-beschriftungen` ersetzen darf (MIN-335);
# die Namen entsprechen `beschriftungen` in themes/common.typ.
ABSCHNITTE = ("profil", "erfahrung", "projekte", "weitere-projekte", "faehigkeiten", "lehre", "sprachen",
              "interessen", "bildung")
MAX_BESCHRIFTUNG = 60


def ist_mehrsprachig(wert) -> bool:
    return isinstance(wert, dict) and bool(wert) and set(wert) <= set(SPRACHEN) and all(isinstance(v, str) for v in wert.values())


def waehle_sprache(wert, sprache: str):
    """Mehrsprachige Texte ({de: ..., en: ...}) auf eine Sprache reduzieren; fehlt sie, gilt Deutsch (MIN-300)."""
    if isinstance(wert, dict):
        if ist_mehrsprachig(wert):
            return wert.get(sprache) or wert.get("de") or next(iter(wert.values()))
        return {k: waehle_sprache(v, sprache) for k, v in wert.items()}
    if isinstance(wert, list):
        return [waehle_sprache(v, sprache) for v in wert]
    return wert


def pruefe_foto_optionen(optionen: dict) -> dict:
    """`basics.x-image` prüfen: mirror (ja/nein), zoom (1–4), x und y (0–1, Bildausschnitt)."""
    if not isinstance(optionen, dict):
        raise ValueError("basics.x-image muss eine Zuordnung sein, z.B. {mirror: true, zoom: 1.3}")
    unbekannt = set(optionen) - {"mirror", "zoom", "x", "y"}
    if unbekannt:
        raise ValueError(f"basics.x-image: unbekannte Felder {sorted(unbekannt)}; erlaubt sind mirror, zoom, x, y")
    if "mirror" in optionen and not isinstance(optionen["mirror"], bool):
        raise ValueError("basics.x-image.mirror muss true oder false sein")
    grenzen = {"zoom": (ZOOM_MIN, ZOOM_MAX), "x": (0, 1), "y": (0, 1)}
    for key, (unten, oben) in grenzen.items():
        wert = optionen.get(key)
        if wert is None:
            continue
        if isinstance(wert, bool) or not isinstance(wert, (int, float)) or not unten <= wert <= oben:
            raise ValueError(f"basics.x-image.{key} muss eine Zahl von {unten} bis {oben} sein, nicht {wert!r}")
    return dict(optionen)


def json_value(value) -> str:
    """A value JSON has no type for: a date YAML reads from 2022-06-01 without quotes goes to Typst as its text (#181)."""
    if isinstance(value, datetime.date):
        return value.isoformat()
    raise TypeError(f"{type(value).__name__} lässt sich nicht als JSON schreiben")


PHOTO_FIELDS = ("image", "x-image")


def without_photo(cv: dict) -> dict:
    """The CV without photo and crop (G62): the person chose not to show the photo in new documents."""
    basics = {key: value for key, value in (cv.get("basics") or {}).items() if key not in PHOTO_FIELDS}
    return {**cv, "basics": basics}


def pruefe_beschriftungen(werte) -> dict:
    """`x-beschriftungen` prüfen: eigene Überschriften je Abschnitt, z.B. {erfahrung: Schnupperlehren}."""
    if not isinstance(werte, dict):
        raise ValueError("x-beschriftungen muss eine Zuordnung sein, z.B. {erfahrung: Schnupperlehren & Erfahrungen}")
    unbekannt = set(werte) - set(ABSCHNITTE)
    if unbekannt:
        raise ValueError(f"x-beschriftungen: unbekannte Abschnitte {sorted(unbekannt)}; erlaubt sind {', '.join(ABSCHNITTE)}")
    for key, text in werte.items():
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"x-beschriftungen.{key} muss ein nicht leerer Text sein")
        if len(text) > MAX_BESCHRIFTUNG:
            raise ValueError(f"x-beschriftungen.{key} darf höchstens {MAX_BESCHRIFTUNG} Zeichen haben")
    return {key: text.strip() for key, text in werte.items()}


def main(argv: list[str] | None = None) -> pathlib.Path:
    ap = argparse.ArgumentParser()
    ap.add_argument("data", help="Stamm-Lebenslauf (YAML, JSON-Resume-Schema)")
    ap.add_argument("--job", help="Bewerbungsdatei mit Tags und Überschreibungen (YAML)")
    ap.add_argument("--theme", default="zweispaltig")
    ap.add_argument("--lang", default="de", choices=SPRACHEN)
    ap.add_argument("--lebenslauf-seiten", type=int, default=page_fill.LIMITS["cv"], choices=page_fill.CV_PAGES,
                    help="Höchstens so viele Seiten (G51); länger wird enger gesetzt")
    ap.add_argument("--ohne-foto", action="store_true", help="Ohne Foto, auch wenn cv.yaml eines nennt (G62)")
    ap.add_argument("--build-dir", help="Ordner für Zwischenstände (Standard: build/ im Modul)")
    ap.add_argument("-o", "--out", default="build/lebenslauf.pdf")
    args = ap.parse_args(argv)

    data_path = pathlib.Path(args.data).resolve()
    cv = yaml.safe_load(data_path.read_text(encoding="utf-8"))
    job = yaml.safe_load(pathlib.Path(args.job).read_text(encoding="utf-8")) if args.job else None
    cv = waehle_sprache(tailor(cv, job), args.lang)
    if args.ohne_foto:
        cv = without_photo(cv)
    if "x-image" in cv.get("basics", {}):
        cv["basics"]["x-image"] = pruefe_foto_optionen(cv["basics"]["x-image"])
    if "x-beschriftungen" in cv:
        cv["x-beschriftungen"] = pruefe_beschriftungen(cv["x-beschriftungen"])

    build = pathlib.Path(args.build_dir).resolve() if args.build_dir else ROOT / "build"
    build.mkdir(parents=True, exist_ok=True)
    bild = cv.get("basics", {}).get("image")
    foto = (data_path.parent / bild).resolve() if bild else None
    # Typst liest nur innerhalb seines Stammordners: Themes, Build und Foto (auf anderen Laufwerken kopiert).
    wurzel = typst_root(build, [ROOT / "themes"] + ([foto] if foto else []))
    if foto:
        cv["basics"]["image"] = wurzel.typst_path(foto)
    daten_json = build / "cv.json"
    daten_json.write_text(json.dumps(cv, ensure_ascii=False, indent=1, default=json_value), encoding="utf-8")

    out = pathlib.Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    stand = (job or {}).get("stand") or datetime.date.today().strftime("%d.%m.%Y")
    vorlage = str(wurzel.locate(ROOT / "themes" / args.theme / "main.typ"))
    schriften = [str(ROOT / "fonts")]
    eingaben = {"data": wurzel.typst_path(daten_json), "lang": args.lang, "stand": stand}
    # Within the page limit (G51) and no nearly empty last page (G49): density chosen before the PDF is written
    eingaben = page_fill.levels(lambda e: page_fill.markers(vorlage, str(wurzel.path), schriften, e), eingaben, ("cv",),
                                page_fill.limits(args.lebenslauf_seiten))
    typst.compile(vorlage, output=str(out), root=str(wurzel.path), font_paths=schriften, sys_inputs=eingaben)
    print(out)
    return out


if __name__ == "__main__":
    main()
