"""Bewerbungsdossier as one PDF, plus the CV and the cover letter as single files (G16, G39).

The dossier file names the CV and the letter and holds the contents of the optional pages
(docs/design/dossier.md). All three PDFs come from the same Typst parts of one design.

Examples:
  python dossier.py data/dossier-beispiel.yaml --out-dir build/dossier
  python dossier.py ../../daten/dossiers/firma.yaml --build-dir ../../daten/.build --out-dir ../../daten/out/firma
"""
import argparse
import datetime
import json
import pathlib
import re
from dataclasses import dataclass

import typst
import yaml

import dossier_data
import mark as mark_module
from anschreiben import bereite_vor
from build import ROOT, SPRACHEN, pruefe_beschriftungen, pruefe_foto_optionen, waehle_sprache
from tailor import tailor
from typst_root import TypstRoot, typst_root

THEMES = ROOT / "themes"
ICONS = THEMES / "icons"
DEFAULT_THEME = "dossier-siegel"
ACCENT = re.compile(r"#[0-9a-fA-F]{6}")
ENTRIES = {"dossier": "dossier-main.typ", "cv": "main.typ", "letter": "anschreiben-main.typ"}
FILE_NAMES = {"dossier": "dossier.pdf", "cv": "lebenslauf.pdf", "letter": "anschreiben.pdf"}
MIX = THEMES / "dossier-mix.typ"  # the dossier when its pages come from more than one design
# The pages whose design can be chosen on its own (G39): option on the command line → key in dossier.json
PAGE_DESIGNS = {"deckblatt": "cover", "anschreiben": "letter", "lebenslauf": "cv", "weitere": "pages"}
OUTLINE = THEMES / "outline.typ"
# Labels a design may draw as outlines only, e.g. the tabs of Register in the page background
OUTLINED_LABELS = {
    "de": {"anschreiben": "Anschreiben", "lebenslauf": "Lebenslauf", "beilagen": "Beilagen", "referenzen": "Referenzen"},
    "en": {"anschreiben": "Cover letter", "lebenslauf": "CV", "beilagen": "Attachments", "referenzen": "References"},
}


@dataclass(frozen=True)
class Result:
    dossier: pathlib.Path
    cv: pathlib.Path
    letter: pathlib.Path
    data: pathlib.Path
    theme: str
    root: TypstRoot
    entries: dict[str, pathlib.Path]
    logo_missing: bool = False


def is_design(name: str) -> bool:
    return all((THEMES / name / entry).is_file() for entry in ENTRIES.values())


def page_designs(theme: str, chosen: dict[str, str | None]) -> dict[str, str]:
    """The design of each page: the one chosen for it, otherwise the theme."""
    designs = {key: chosen.get(option) or theme for option, key in PAGE_DESIGNS.items()}
    unknown = sorted({name for name in designs.values() if not is_design(name)})
    if unknown:
        raise ValueError(f"Kein Dossier-Design: {', '.join(unknown)} (es fehlt {', '.join(ENTRIES.values())})")
    return designs


def entries_for(designs: dict[str, str]) -> dict[str, pathlib.Path]:
    """Typst entry per file: one design alone uses its own entries, a mix the shared one for the dossier.
    The single files always come from the design of their page."""
    one = len(set(designs.values())) == 1
    return {"dossier": THEMES / designs["cover"] / ENTRIES["dossier"] if one else MIX,
            "cv": THEMES / designs["cv"] / ENTRIES["cv"],
            "letter": THEMES / designs["letter"] / ENTRIES["letter"]}


def icon_catalogue() -> set[str]:
    """Names of the interest icons (Lucide subset in themes/icons)."""
    return {path.stem for path in ICONS.glob("*.svg")}


def _load_yaml(path: pathlib.Path) -> dict:
    if not path.is_file():
        raise ValueError(f"Datei nicht gefunden: {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _referenced(base: pathlib.Path, given: str | None, data: dict, key: str) -> pathlib.Path:
    name = given or data.get(key)
    if not name:
        raise ValueError(f"In der Dossier-Datei fehlt {key}: (oder die Option auf der Befehlszeile)")
    return (pathlib.Path(given) if given else base / name).resolve()


def _checked_cv(cv: dict, job: dict | None, language: str) -> dict:
    result = waehle_sprache(tailor(cv, job), language)
    basics = result.get("basics", {})
    if "x-image" in basics:
        basics["x-image"] = pruefe_foto_optionen(basics["x-image"])
    if "x-beschriftungen" in result:
        result["x-beschriftungen"] = pruefe_beschriftungen(result["x-beschriftungen"])
    return result


def outlined_labels(language: str, build: pathlib.Path, root: TypstRoot, compiler: typst.Compiler) -> dict[str, str]:
    """Renders each label as glyph outlines (SVG) and returns its Typst path per key."""
    folder = build / "outlined"
    folder.mkdir(exist_ok=True)
    paths = {}
    for key, label in OUTLINED_LABELS[language].items():
        svg = folder / f"{key}.svg"
        compiler.compile(input=str(root.locate(OUTLINE)), output=str(svg), format="svg", sys_inputs={"label": label})
        paths[key] = root.typst_path(svg)
    return paths


def prepare(cv: dict, letter: dict, pages: dict, language: str, today: datetime.date, root: TypstRoot,
            style: dict | None = None, outlined: dict | None = None, designs: dict | None = None,
            mark: dict | None = None) -> dict:
    """One JSON for all parts: CV, letter, optional pages and the read data extensions."""
    basics = cv.get("basics", {})
    catalogue = icon_catalogue()
    interests = [{**item, "icon": root.typst_path(ICONS / f"{item['icon']}.svg") if item["icon"] else None,
                  "icon-name": item["icon"]}
                 for item in dossier_data.interests(cv.get("interests"), catalogue)]
    return {
        "language": language,
        "stand": today.strftime("%d.%m.%Y"),
        "style": dict(style or {}),
        "cv": cv,
        "person": {
            "name": basics.get("name", ""),
            "label": basics.get("label"),
            "monogram": dossier_data.monogram(basics),
            "contact": dossier_data.contact(basics),
            "photo": basics.get("image"),
            "photo-options": basics.get("x-image", {}),
            "steps": dossier_data.steps_done(cv),
            "mark": dict(mark or {"variant": mark_module.FITTING, "logo": None}),
        },
        "skills": dossier_data.skill_groups(cv.get("skills")),
        "timeline": dossier_data.timeline(cv.get("work"), today),
        "durations": dossier_data.durations(cv, today, language),
        "outlined": dict(outlined or {}),
        "languages": dossier_data.language_group(cv.get("languages")),
        "interests": interests,
        "letter": {**bereite_vor(letter, cv, today), "heading": dossier_data.letter_heading(letter, language)},
        "pages": pages,
        "designs": dict(designs or {}),
    }


def _compile(compiler: typst.Compiler, root: TypstRoot, entry: pathlib.Path, out: pathlib.Path,
             data: pathlib.Path) -> pathlib.Path:
    compiler.compile(input=str(root.locate(entry)), output=str(out), format="pdf",
                     sys_inputs={"data": root.typst_path(data)})
    return out


def query(result: Result, selector: str, part: str = "cv") -> list:
    """Values of the metadata a part leaves behind, e.g. `<dossier-level>` for every drawn level graphic."""
    found = typst.query(
        str(result.root.locate(result.entries[part])),
        selector,
        field="value",
        root=str(result.root.path),
        font_paths=[str(ROOT / "fonts")],
        sys_inputs={"data": result.root.typst_path(result.data)},
    )
    return json.loads(found)


def _mark(cv: dict, base: pathlib.Path, args: argparse.Namespace) -> dict:
    """The mark of cv.yaml (G18), with --zeichen and --logo from the command line going first."""
    basics = dict(cv.get("basics", {}))
    if args.logo:
        logo = pathlib.Path(args.logo).resolve()
        base, basics["x-logo"] = logo.parent, logo.name
        basics.setdefault("x-zeichen", mark_module.LOGO)
    if args.zeichen:
        basics["x-zeichen"] = args.zeichen
    return mark_module.settings(basics, base, dossier_data.monogram(basics))


def main(argv: list[str] | None = None) -> Result:
    ap = argparse.ArgumentParser(description="Bewerbungsdossier und Einzeldateien als PDF erzeugen")
    ap.add_argument("data", help="Dossier-Datei (YAML) mit lebenslauf, anschreiben, gruss, dank, kennzahlen, anlagen")
    ap.add_argument("--cv", help="Lebenslauf (YAML); sonst `lebenslauf:` in der Dossier-Datei")
    ap.add_argument("--brief", help="Anschreiben (YAML); sonst `anschreiben:` in der Dossier-Datei")
    ap.add_argument("--job", help="Bewerbungsdatei mit Tags und Überschreibungen (YAML)")
    ap.add_argument("--theme", default=DEFAULT_THEME, help="Design aller Seiten, soweit keines eigens gewählt ist")
    for option in PAGE_DESIGNS:
        ap.add_argument(f"--design-{option}", help=f"Design für {option} (Standard: --theme)")
    ap.add_argument("--lang", default="de", choices=SPRACHEN)
    ap.add_argument("--akzent", help="Akzentfarbe als #rrggbb (Standard: basics.x-akzent, sonst die Hauptfarbe "
                                     "des Designs auf dem Deckblatt)")
    ap.add_argument("--zeichen", choices=mark_module.VARIANTS, help="Zeichen (Standard: basics.x-zeichen, sonst passend)")
    ap.add_argument("--logo", help="Eigenes Logo als PNG, JPG oder SVG (Standard: basics.x-logo)")
    ap.add_argument("--ohne-zeitachse", action="store_true",
                    help="Design Raster ohne waagrechte Zeitachse, für sehr strenge Bewerbungssoftware")
    ap.add_argument("--build-dir", help="Ordner für Zwischenstände (Standard: build/ im Modul)")
    ap.add_argument("--out-dir", default="build/dossier")
    args = ap.parse_args(argv)

    if args.akzent and not ACCENT.fullmatch(args.akzent):
        raise ValueError(f"--akzent muss eine Farbe wie #38495d sein, nicht {args.akzent!r}")
    if not is_design(args.theme):
        raise ValueError(f"Theme {args.theme!r} ist kein Dossier-Design (es fehlt {', '.join(ENTRIES.values())})")
    designs = page_designs(args.theme, {option: getattr(args, f"design_{option}") for option in PAGE_DESIGNS})
    entries = entries_for(designs)

    file_path = pathlib.Path(args.data).resolve()
    file_data = _load_yaml(file_path)
    pages = dossier_data.dossier_pages(file_data)
    cv_path = _referenced(file_path.parent, args.cv, file_data, "lebenslauf")
    letter_path = _referenced(file_path.parent, args.brief, file_data, "anschreiben")
    letter = _load_yaml(letter_path)
    raw_cv = _load_yaml(cv_path)
    job = _load_yaml(pathlib.Path(args.job).resolve()) if args.job else None
    cv = _checked_cv(raw_cv, job, args.lang)

    build = pathlib.Path(args.build_dir).resolve() if args.build_dir else ROOT / "build"
    build.mkdir(parents=True, exist_ok=True)
    image = cv.get("basics", {}).get("image")
    photo = (cv_path.parent / image).resolve() if image else None
    chosen_mark = _mark(cv, cv_path.parent, args)
    logo = chosen_mark["logo"]
    root = typst_root(build, [THEMES] + ([photo] if photo else []) + ([logo] if logo else []))
    if photo:
        cv["basics"]["image"] = root.typst_path(photo)

    accent = args.akzent.lower() if args.akzent else mark_module.accent_for(cv.get("basics", {}), designs["cover"])
    style = {"farbe-akzent": accent, **({"zeitachse": False} if args.ohne_zeitachse else {})}
    drawn_mark = {"variant": chosen_mark["variant"],
                  "logo": root.typst_path(logo) if logo is not None else None}
    # One compiler for all files of a build: fonts load once
    compiler = typst.Compiler(root=str(root.path), font_paths=[str(ROOT / "fonts")])
    data = prepare(cv, letter, pages, args.lang, datetime.date.today(), root, style,
                   outlined_labels(args.lang, build, root, compiler), designs, drawn_mark)
    data_json = build / "dossier.json"
    data_json.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")

    out = pathlib.Path(args.out_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    built = {part: _compile(compiler, root, entry, out / FILE_NAMES[part], data_json) for part, entry in entries.items()}
    for path in built.values():
        print(path)
    return Result(dossier=built["dossier"], cv=built["cv"], letter=built["letter"], data=data_json,
                  theme=args.theme, root=root, entries=entries, logo_missing=chosen_mark["logo-missing"])


if __name__ == "__main__":
    main()
