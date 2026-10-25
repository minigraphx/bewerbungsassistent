"""Lebenslauf als PDF erzeugen.

Beispiele:
  python build.py data/beispiel.yaml
  python build.py data/beispiel.yaml --job jobs/beispiel-ki.yaml --theme einspaltig -o out/ki.pdf
  python build.py ../../daten/cv.yaml --build-dir ../../daten/.build -o ../../daten/out/cv.pdf
"""
import argparse
import datetime
import json
import os
import pathlib

import typst
import yaml

from tailor import tailor

ROOT = pathlib.Path(__file__).resolve().parent


def typst_pfad(pfad: pathlib.Path, wurzel: pathlib.Path) -> str:
    """Pfad so, wie Typst ihn relativ zum Projekt-Stammordner erwartet."""
    return "/" + pfad.relative_to(wurzel).as_posix()


def main(argv: list[str] | None = None) -> pathlib.Path:
    ap = argparse.ArgumentParser()
    ap.add_argument("data", help="Stamm-Lebenslauf (YAML, JSON-Resume-Schema)")
    ap.add_argument("--job", help="Bewerbungsdatei mit Tags und Überschreibungen (YAML)")
    ap.add_argument("--theme", default="zweispaltig")
    ap.add_argument("--lang", default="de")
    ap.add_argument("--build-dir", help="Ordner für Zwischenstände (Standard: build/ im Modul)")
    ap.add_argument("-o", "--out", default="build/lebenslauf.pdf")
    args = ap.parse_args(argv)

    data_path = pathlib.Path(args.data).resolve()
    cv = yaml.safe_load(data_path.read_text(encoding="utf-8"))
    job = yaml.safe_load(pathlib.Path(args.job).read_text(encoding="utf-8")) if args.job else None
    cv = tailor(cv, job)

    build = pathlib.Path(args.build_dir).resolve() if args.build_dir else ROOT / "build"
    build.mkdir(parents=True, exist_ok=True)
    bild = cv.get("basics", {}).get("image")
    foto = (data_path.parent / bild).resolve() if bild else None
    # Typst liest nur innerhalb seines Stammordners: gemeinsamer Oberordner von Modul, Build und Foto.
    wurzel = pathlib.Path(os.path.commonpath([ROOT, build] + ([foto] if foto else [])))
    if foto:
        cv["basics"]["image"] = typst_pfad(foto, wurzel)
    daten_json = build / "cv.json"
    daten_json.write_text(json.dumps(cv, ensure_ascii=False, indent=1), encoding="utf-8")

    out = pathlib.Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    stand = (job or {}).get("stand") or datetime.date.today().strftime("%d.%m.%Y")
    typst.compile(
        str(ROOT / "themes" / args.theme / "main.typ"),
        output=str(out),
        root=str(wurzel),
        font_paths=[str(ROOT / "fonts")],
        sys_inputs={"data": typst_pfad(daten_json, wurzel), "lang": args.lang, "stand": stand},
    )
    print(out)
    return out


if __name__ == "__main__":
    main()
