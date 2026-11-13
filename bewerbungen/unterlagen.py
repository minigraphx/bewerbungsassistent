"""Unterlagen einer Bewerbung bauen: Lebenslauf aus der gewählten Variante, Anschreiben aus
`bewerbungen/<id>/anschreiben.yaml`. Die PDFs liegen in `bewerbungen/<id>/` (nicht in Git, bis zum Versand).
Wer für die Bewerbung ein Dossier wählt (G40), bekommt dazu `dossier.pdf`; Lebenslauf und Anschreiben entstehen
dann aus denselben Teilen des Dossiers.
"""
import pathlib
import shutil

import yaml

import pfade  # noqa: F401  (macht das Modul lebenslauf importierbar)
import anschreiben as anschreiben_modul
import build as lebenslauf_modul
import cv_design
import dossier as dossier_modul
import page_limit
from dateien import im_ordner
from register import DESIGN_PAGES, DOSSIER_DESIGNS, ID_MUSTER
from tailor import tailor
from varianten import Varianten

ORDNER = "bewerbungen"
ARTEN = ("lebenslauf", "anschreiben")
CHOOSE_VARIANT = "Keine Lebenslauf-Variante gewählt. Bitte unter „Angaben“ eine wählen und speichern."
NO_CV = "Noch kein Lebenslauf. Bitte unter „Meine Angaben“ erfassen oder unter „Lebenslauf und Dateien“ als PDF hochladen."
OWN_CV = "dokumente/lebenslauf.pdf"  # uploaded on the page „Lebenslauf und Dateien“, see own_files.py
OWN_LETTER = "eigenes-anschreiben.pdf"  # uploaded on the page of the application, see own_files.py
LETTER_SOURCE = "anschreiben.yaml"
SENT_STAYS = "Diese Bewerbung ist versendet. Was verschickt wurde, bleibt so."
DOSSIER = "dossier"
DOSSIER_PAGES = "dossier.yaml"  # optional pages of the dossier (greeting, thanks, figures), written by Claude
DOSSIER_OWN_FILE = ("Ein Dossier entsteht aus „Meine Angaben“ und dem Entwurf des Anschreibens, nicht aus einem "
                    "fertigen PDF. Bitte „Anschreiben und Lebenslauf“ wählen oder das eigene PDF entfernen.")
DOSSIER_NO_LETTER = "Für das Dossier fehlt noch das Anschreiben. Bitte zuerst eines entwerfen."


def bewerbungsordner(daten: pathlib.Path, bewerbung_id: str) -> pathlib.Path:
    if not ID_MUSTER.fullmatch(bewerbung_id or ""):
        raise ValueError(f"Ungültige Bewerbungs-id: {bewerbung_id!r}")
    return daten.resolve() / ORDNER / bewerbung_id


def pdf_pfade(daten: pathlib.Path, bewerbung_id: str) -> dict[str, pathlib.Path]:
    ordner = bewerbungsordner(daten, bewerbung_id)
    return {art: ordner / f"{art}.pdf" for art in ARTEN}


def wants_dossier(bewerbung: dict) -> bool:
    """Whether the person chose a dossier for this application; without a choice it is the two files (G41)."""
    return bewerbung.get("unterlagen") == DOSSIER


def dossier_designs(bewerbung: dict) -> dict[str, str]:
    """The design of each page (G39): one for all pages as chosen, Siegel without a choice, and under „Erweitert“
    another one per page."""
    design = bewerbung.get("dossier_design") or DOSSIER_DESIGNS[0]
    pages = bewerbung.get("dossier_seiten") or {}
    return {page: pages.get(page) or design for page in DESIGN_PAGES}


def _design_arguments(bewerbung: dict) -> list[str]:
    """For lebenslauf/dossier.py, whose designs are the themes dossier-<name>."""
    designs = dossier_designs(bewerbung)
    return [argument for page, name in designs.items() for argument in (f"--design-{page}", f"dossier-{name}")]


def dossier_path(daten: pathlib.Path, bewerbung_id: str) -> pathlib.Path:
    return bewerbungsordner(daten, bewerbung_id) / f"{DOSSIER}.pdf"


def dossier_file(daten: pathlib.Path, bewerbung: dict) -> pathlib.Path | None:
    """Where the dossier that counts lies, built or not: once sent the one that went out, before that the built one
    while it is chosen. None when no dossier counts; one left from an earlier choice does not."""
    gesendet = ((bewerbung.get("versand") or {}).get("dateien") or {}).get(DOSSIER)
    if gesendet:
        return im_ordner(daten, gesendet)
    if bewerbung.get("versand") or not wants_dossier(bewerbung):
        return None
    return dossier_path(daten, bewerbung["id"])


def effective_dossier(daten: pathlib.Path, bewerbung: dict) -> pathlib.Path | None:
    """The dossier that counts, when it exists."""
    path = dossier_file(daten, bewerbung)
    return path if path and path.is_file() else None


def eigener_lebenslauf(daten: pathlib.Path, bewerbung: dict) -> pathlib.Path | None:
    """The CV the person uploaded, used as it is. Whoever chooses a variant for an application wants that one."""
    pfad = daten.resolve() / OWN_CV
    return pfad if pfad.is_file() and not bewerbung.get("variante") and not bewerbung.get("versand") else None


def letter_source(daten: pathlib.Path, bewerbung_id: str) -> pathlib.Path:
    """What the letter is built from. The file that counts can be another one, so never derive this from `wirksame_pdfs`."""
    return bewerbungsordner(daten, bewerbung_id) / LETTER_SOURCE


def own_letter_path(daten: pathlib.Path, bewerbung_id: str) -> pathlib.Path:
    return bewerbungsordner(daten, bewerbung_id) / OWN_LETTER


def own_letter(daten: pathlib.Path, bewerbung: dict) -> pathlib.Path | None:
    """The letter the person uploaded for this application, as long as it counts: it goes before a draft, until sent."""
    pfad = own_letter_path(daten, bewerbung["id"])
    return pfad if pfad.is_file() and not bewerbung.get("versand") else None


def wirksame_pdfs(daten: pathlib.Path, bewerbung: dict) -> dict[str, pathlib.Path]:
    """The files that count for this application: once sent, what went out, before that the person's own files.
    Building still writes to `pdf_pfade`."""
    gesendet = (bewerbung.get("versand") or {}).get("dateien") or {}
    eigene = {"lebenslauf": eigener_lebenslauf(daten, bewerbung), "anschreiben": own_letter(daten, bewerbung)}

    def gilt(art: str, gebaut: pathlib.Path) -> pathlib.Path:
        pfad = im_ordner(daten, gesendet[art]) if gesendet.get(art) else eigene[art]
        return pfad if pfad and pfad.is_file() else gebaut

    return {art: gilt(art, gebaut) for art, gebaut in pdf_pfade(daten, bewerbung["id"]).items()}


def _pages(daten: pathlib.Path) -> list[str]:
    """The pages the CV may have (G51), as the person chose under Einstellungen > Erweitert."""
    return ["--lebenslauf-seiten", str(page_limit.load(daten))]


def tailored_cv(daten: pathlib.Path, bewerbung: dict) -> dict:
    """The CV as built for this application, tailored to its variant; empty when it cannot be read."""
    try:
        cv = yaml.safe_load((daten / "cv.yaml").read_text(encoding="utf-8"))
        variante = Varianten(daten).hole(bewerbung["variante"]) if bewerbung.get("variante") else {}
        if not variante.get("quelle"):
            return cv if isinstance(cv, dict) else {}
        job = yaml.safe_load(im_ordner(daten, variante["quelle"]).read_text(encoding="utf-8"))
        return lebenslauf_modul.waehle_sprache(tailor(cv, job), variante.get("sprache") or "de")
    except (OSError, yaml.YAMLError, KeyError, ValueError, TypeError, AttributeError):
        return {}


def _baue_ganzen_lebenslauf(daten: pathlib.Path, design: list[str], build: pathlib.Path, ziel: pathlib.Path) -> None:
    """Variants come from Claude; whoever works in the app alone has none and still needs a CV. With variants, the person chooses."""
    if Varianten(daten).alle():
        raise ValueError(CHOOSE_VARIANT)
    if not (daten / "cv.yaml").is_file():
        raise ValueError(NO_CV)
    lebenslauf_modul.main([str(daten / "cv.yaml"), *design, *_pages(daten), "--build-dir", str(build), "-o", str(ziel)])


def _baue_lebenslauf(daten: pathlib.Path, bewerbung: dict, build: pathlib.Path, ziel: pathlib.Path) -> None:
    design = cv_design.theme_arguments(cv_design.for_application(daten, bewerbung))  # G61, resolved at each build
    if not bewerbung.get("variante"):
        return _baue_ganzen_lebenslauf(daten, design, build, ziel)
    variante = Varianten(daten).hole(bewerbung["variante"])
    if variante.get("quelle"):
        lebenslauf_modul.main([str(daten / "cv.yaml"), "--job", str(im_ordner(daten, variante["quelle"])),
                               "--lang", variante["sprache"], *design, *_pages(daten), "--build-dir", str(build),
                               "-o", str(ziel)])
    elif variante.get("datei"):
        shutil.copyfile(im_ordner(daten, variante["datei"]), ziel)
    elif not ziel.is_file():
        raise ValueError(
            f"Variante {variante['id']!r} ist extern ({variante['extern']}): "
            f"bitte das PDF als {ziel.relative_to(daten.resolve())} ablegen"
        )


def _cv_arguments(daten: pathlib.Path, bewerbung: dict) -> list[str]:
    """CV and tailoring for the dossier; it is built from the data, so a finished PDF cannot go in."""
    if eigener_lebenslauf(daten, bewerbung):
        raise ValueError(DOSSIER_OWN_FILE)
    if not (daten / "cv.yaml").is_file():
        raise ValueError(NO_CV)
    arguments = ["--cv", str(daten / "cv.yaml")]
    if not bewerbung.get("variante"):
        if Varianten(daten).alle():
            raise ValueError(CHOOSE_VARIANT)
        return arguments
    variante = Varianten(daten).hole(bewerbung["variante"])
    if not variante.get("quelle"):
        raise ValueError(DOSSIER_OWN_FILE)
    return [*arguments, "--job", str(im_ordner(daten, variante["quelle"])), "--lang", variante["sprache"]]


def _baue_dossier(daten: pathlib.Path, bewerbung: dict, build: pathlib.Path) -> dict[str, pathlib.Path]:
    """Dossier, CV and letter from the same parts of one design (lebenslauf/dossier.py), into the application's folder."""
    if own_letter(daten, bewerbung):
        raise ValueError(DOSSIER_OWN_FILE)
    cv = _cv_arguments(daten, bewerbung)
    letter = letter_source(daten, bewerbung["id"])
    if not letter.is_file():
        raise ValueError(DOSSIER_NO_LETTER)
    folder = bewerbungsordner(daten, bewerbung["id"])
    pages = folder / DOSSIER_PAGES
    if not pages.is_file():
        build.mkdir(parents=True, exist_ok=True)
        pages = build / f"{bewerbung['id']}-{DOSSIER_PAGES}"
        pages.write_text("{}\n", encoding="utf-8")
    result = dossier_modul.main([str(pages), *cv, "--brief", str(letter), *_design_arguments(bewerbung),
                                 *_pages(daten), "--build-dir", str(build), "--out-dir", str(folder)])
    return {"lebenslauf": result.cv, "anschreiben": result.letter, DOSSIER: result.dossier}


def baue(daten: pathlib.Path, bewerbung: dict, build: pathlib.Path) -> dict[str, pathlib.Path]:
    """Lebenslauf und (falls vorhanden) Anschreiben bauen, mit gewähltem Dossier auch dieses; liefert die Pfade der PDFs."""
    daten = daten.resolve()
    if wants_dossier(bewerbung):
        bewerbungsordner(daten, bewerbung["id"]).mkdir(parents=True, exist_ok=True)
        return _baue_dossier(daten, bewerbung, build)
    pfade_pdf = pdf_pfade(daten, bewerbung["id"])
    pfade_pdf["lebenslauf"].parent.mkdir(parents=True, exist_ok=True)
    eigener = eigener_lebenslauf(daten, bewerbung)
    if not eigener:
        _baue_lebenslauf(daten, bewerbung, build, pfade_pdf["lebenslauf"])
    gebaut = {"lebenslauf": eigener or pfade_pdf["lebenslauf"]}
    eigenes_anschreiben = own_letter(daten, bewerbung)
    if eigenes_anschreiben:
        return {**gebaut, "anschreiben": eigenes_anschreiben}
    brief = letter_source(daten, bewerbung["id"])
    if brief.is_file():
        argumente = [str(brief), "--build-dir", str(build), "-o", str(pfade_pdf["anschreiben"])]
        if (daten / "cv.yaml").is_file():
            argumente += ["--cv", str(daten / "cv.yaml")]
        anschreiben_modul.main(argumente)
        gebaut["anschreiben"] = pfade_pdf["anschreiben"]
    return gebaut
