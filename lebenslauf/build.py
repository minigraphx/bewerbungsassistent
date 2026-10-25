"""Lebenslauf als PDF erzeugen.

Beispiele:
  python build.py data/beispiel.yaml
  python build.py data/beispiel.yaml --job jobs/beispiel-ki.yaml --theme einspaltig -o out/ki.pdf
"""
import argparse
import datetime
import json
import pathlib
import shutil

import typst
import yaml

from tailor import tailor

ROOT = pathlib.Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data", help="Stamm-Lebenslauf (YAML, JSON-Resume-Schema)")
    ap.add_argument("--job", help="Bewerbungsdatei mit Tags und Überschreibungen (YAML)")
    ap.add_argument("--theme", default="zweispaltig")
    ap.add_argument("--lang", default="de")
    ap.add_argument("-o", "--out", default="build/lebenslauf.pdf")
    args = ap.parse_args()

    data_path = pathlib.Path(args.data).resolve()
    cv = yaml.safe_load(data_path.read_text(encoding="utf-8"))
    job = yaml.safe_load(pathlib.Path(args.job).read_text(encoding="utf-8")) if args.job else None
    cv = tailor(cv, job)

    build = ROOT / "build"
    build.mkdir(exist_ok=True)
    bild = cv.get("basics", {}).get("image")
    if bild:
        quelle = (data_path.parent / bild).resolve()
        ziel = build / ("foto" + quelle.suffix)
        shutil.copyfile(quelle, ziel)
        cv["basics"]["image"] = "/build/" + ziel.name
    (build / "cv.json").write_text(json.dumps(cv, ensure_ascii=False, indent=1), encoding="utf-8")

    out = pathlib.Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    stand = (job or {}).get("stand") or datetime.date.today().strftime("%d.%m.%Y")
    typst.compile(
        str(ROOT / "themes" / args.theme / "main.typ"),
        output=str(out),
        root=str(ROOT),
        font_paths=[str(ROOT / "fonts")],
        sys_inputs={"data": "/build/cv.json", "lang": args.lang, "stand": stand},
    )
    print(out)


if __name__ == "__main__":
    main()
