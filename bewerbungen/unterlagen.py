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


def bewerbungsordner(daten: pathlib.Path, bewerbung_id: str) -> pathlib.Path:
    if not ID_MUSTER.fullmatch(bewerbung_id or ""):
        raise ValueError(f"Ungültige Bewerbungs-id: {bewerbung_id!r}")
    return daten.resolve() / ORDNER / bewerbung_id


def pdf_pfade(daten: pathlib.Path, bewerbung_id: str) -> dict[str, pathlib.Path]:
    ordner = bewerbungsordner(daten, bewerbung_id)
    return {art: ordner / f"{art}.pdf" for art in ARTEN}


def _baue_lebenslauf(daten: pathlib.Path, bewerbung: dict, build: pathlib.Path, ziel: pathlib.Path) -> None:
    if not bewerbung.get("variante"):
        raise ValueError("Keine Lebenslauf-Variante gewählt (Feld variante)")
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
    _baue_lebenslauf(daten, bewerbung, build, pfade_pdf["lebenslauf"])
    gebaut = {"lebenslauf": pfade_pdf["lebenslauf"]}
    brief = pfade_pdf["anschreiben"].with_suffix(".yaml")
    if brief.is_file():
        argumente = [str(brief), "--build-dir", str(build), "-o", str(pfade_pdf["anschreiben"])]
        if (daten / "cv.yaml").is_file():
            argumente += ["--cv", str(daten / "cv.yaml")]
        anschreiben_modul.main(argumente)
        gebaut["anschreiben"] = pfade_pdf["anschreiben"]
    return gebaut
