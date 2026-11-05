"""Unterlagen einer Bewerbung bauen: Lebenslauf aus der gewählten Variante, Anschreiben aus
`bewerbungen/<id>/anschreiben.yaml`. Die PDFs liegen in `bewerbungen/<id>/` (nicht in Git, bis zum Versand).
"""
import pathlib
import shutil

import pfade  # noqa: F401  (macht das Modul lebenslauf importierbar)
import anschreiben as anschreiben_modul
import build as lebenslauf_modul
from dateien import im_ordner
from register import ID_MUSTER
from varianten import Varianten

ORDNER = "bewerbungen"
ARTEN = ("lebenslauf", "anschreiben")
CHOOSE_VARIANT = "Keine Lebenslauf-Variante gewählt. Bitte unter „Angaben“ eine wählen und speichern."
NO_CV = "Noch kein Lebenslauf. Bitte unter „Meine Angaben“ erfassen oder unter „Meine Dateien“ als PDF hochladen."
OWN_CV = "dokumente/lebenslauf.pdf"  # uploaded on the page „Meine Dateien“, see own_files.py


def bewerbungsordner(daten: pathlib.Path, bewerbung_id: str) -> pathlib.Path:
    if not ID_MUSTER.fullmatch(bewerbung_id or ""):
        raise ValueError(f"Ungültige Bewerbungs-id: {bewerbung_id!r}")
    return daten.resolve() / ORDNER / bewerbung_id


def pdf_pfade(daten: pathlib.Path, bewerbung_id: str) -> dict[str, pathlib.Path]:
    ordner = bewerbungsordner(daten, bewerbung_id)
    return {art: ordner / f"{art}.pdf" for art in ARTEN}


def eigener_lebenslauf(daten: pathlib.Path, bewerbung: dict) -> pathlib.Path | None:
    """The CV the person uploaded, used as it is. Whoever chooses a variant for an application wants that one."""
    pfad = daten.resolve() / OWN_CV
    return pfad if pfad.is_file() and not bewerbung.get("variante") and not bewerbung.get("versand") else None


def wirksame_pdfs(daten: pathlib.Path, bewerbung: dict) -> dict[str, pathlib.Path]:
    """The files that count for this application: once sent, the CV that went out. Building still writes to `pdf_pfade`."""
    gesendet = ((bewerbung.get("versand") or {}).get("dateien") or {}).get("lebenslauf")
    gilt = im_ordner(daten, gesendet) if gesendet else eigener_lebenslauf(daten, bewerbung)
    pfade_pdf = pdf_pfade(daten, bewerbung["id"])
    return {**pfade_pdf, "lebenslauf": gilt} if gilt and gilt.is_file() else pfade_pdf


def _baue_ganzen_lebenslauf(daten: pathlib.Path, build: pathlib.Path, ziel: pathlib.Path) -> None:
    """Variants come from Claude; whoever works in the app alone has none and still needs a CV. With variants, the person chooses."""
    if Varianten(daten).alle():
        raise ValueError(CHOOSE_VARIANT)
    if not (daten / "cv.yaml").is_file():
        raise ValueError(NO_CV)
    lebenslauf_modul.main([str(daten / "cv.yaml"), "--build-dir", str(build), "-o", str(ziel)])


def _baue_lebenslauf(daten: pathlib.Path, bewerbung: dict, build: pathlib.Path, ziel: pathlib.Path) -> None:
    if not bewerbung.get("variante"):
        return _baue_ganzen_lebenslauf(daten, build, ziel)
    variante = Varianten(daten).hole(bewerbung["variante"])
    if variante.get("quelle"):
        lebenslauf_modul.main([str(daten / "cv.yaml"), "--job", str(im_ordner(daten, variante["quelle"])),
                               "--lang", variante["sprache"], "--build-dir", str(build), "-o", str(ziel)])
    elif variante.get("datei"):
        shutil.copyfile(im_ordner(daten, variante["datei"]), ziel)
    elif not ziel.is_file():
        raise ValueError(
            f"Variante {variante['id']!r} ist extern ({variante['extern']}): "
            f"bitte das PDF als {ziel.relative_to(daten.resolve())} ablegen"
        )


def baue(daten: pathlib.Path, bewerbung: dict, build: pathlib.Path) -> dict[str, pathlib.Path]:
    """Lebenslauf und (falls vorhanden) Anschreiben bauen; liefert die Pfade der PDFs."""
    daten = daten.resolve()
    pfade_pdf = pdf_pfade(daten, bewerbung["id"])
    pfade_pdf["lebenslauf"].parent.mkdir(parents=True, exist_ok=True)
    eigener = eigener_lebenslauf(daten, bewerbung)
    if not eigener:
        _baue_lebenslauf(daten, bewerbung, build, pfade_pdf["lebenslauf"])
    gebaut = {"lebenslauf": eigener or pfade_pdf["lebenslauf"]}
    brief = pfade_pdf["anschreiben"].with_suffix(".yaml")
    if brief.is_file():
        argumente = [str(brief), "--build-dir", str(build), "-o", str(pfade_pdf["anschreiben"])]
        if (daten / "cv.yaml").is_file():
            argumente += ["--cv", str(daten / "cv.yaml")]
        anschreiben_modul.main(argumente)
        gebaut["anschreiben"] = pfade_pdf["anschreiben"]
    return gebaut
