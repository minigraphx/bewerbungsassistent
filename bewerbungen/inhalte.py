"""Inhalte im Browser bearbeiten (MIN-302, erster Schritt): Datendateien als Text, mit Prüfung je Dateityp.

Bearbeitet wird der Text der Datei, Kommentare und Formatierung bleiben also vollständig erhalten. Vor dem
Speichern wird geprüft; für Lebenslauf, Zuschnitte und Anschreiben mit einem echten Probebau als PDF, das
gleichzeitig als Vorschau dient; Markdown-Dateien werden ebenfalls als PDF gesetzt (textdokument.py).
Gespeichert wird nur Gültiges, mit Entwurf davor und danach (kontext.py).
"""
import fnmatch
import pathlib

import typst
import yaml

import pfade  # noqa: F401  (macht das Modul lebenslauf importierbar)
import anschreiben as anschreiben_modul
import build as lebenslauf_modul
import cv_design
import letter_messages
import photo_shown
from dateien import relativ
import textdokument
from register import pruefe_bewerbung
from ui_message import T
from unterlagen import OWN_LETTER
from varianten import pruefe_variante

MUSTER = ("cv.yaml", "suchprofil.md", "varianten.yaml", "bewerbungen.yaml", "jobs/*.yaml", "anschreiben/*.md",
          "bewerbungen/*/anschreiben.yaml", "bewerbungen/*/stelle.md")

NUR_TEXT = ("bewerbungen.yaml", "varianten.yaml")  # Datenlisten: bearbeiten in der Oberfläche, hier nur als Text
# Titles are messages (#430), so the page shows them in the app language; file and folder names stay
TITEL = {"cv.yaml": T("Lebenslauf"), "suchprofil.md": T("Suchprofil"), "anschreiben/stil.md": T("Anschreiben: Stilprofil"),
         "anschreiben/bausteine.md": T("Anschreiben: Textbausteine"),
         "bewerbungen.yaml": T("Bewerbungsregister (Daten)"), "varianten.yaml": T("Lebenslauf-Varianten (Daten)")}


def _bleibt_im_ordner(rel: str) -> bool:
    """Windows liest den Backslash als Trenner, und „*“ im Muster passt auch auf ihn und auf „..“."""
    return not any(zeichen in rel for zeichen in "\\:") and not any(teil in ("", ".", "..") for teil in rel.split("/"))


def _erlaubt(rel: str) -> bool:
    return _bleibt_im_ordner(rel) and any(fnmatch.fnmatchcase(rel, m) and rel.count("/") == m.count("/") for m in MUSTER)


def hat_pdf_ansicht(rel: str) -> bool:
    return _erlaubt(rel) and rel not in NUR_TEXT


def titel(rel: str) -> str:
    """Verständlicher Name einer Datei für die Oberfläche."""
    if rel in TITEL:
        return TITEL[rel]
    teile = pathlib.PurePosixPath(rel)
    if teile.parts[0] == "jobs":
        return T("Lebenslauf-Zuschnitt {name}", name=teile.stem)
    if teile.parts[0] == "anschreiben":
        return T("Anschreiben: {name}", name=teile.stem)
    if teile.parts[0] == "bewerbungen" and len(teile.parts) == 3:
        art = {"anschreiben.yaml": T("Anschreiben"), OWN_LETTER: T("Eigenes Anschreiben")}.get(teile.name,
                                                                                                 T("Stellenausschreibung"))
        return T("{art} {ordner}", art=art, ordner=teile.parts[1])
    return rel


def bearbeitbare_dateien(daten: pathlib.Path) -> list[str]:
    daten = daten.resolve()
    gefunden = {p.relative_to(daten).as_posix() for m in MUSTER for p in daten.glob(m) if p.is_file()}
    return sorted(r for r in gefunden if _erlaubt(r))


def pruefe_datei(daten: pathlib.Path, rel: str) -> pathlib.Path:
    """Nur Dateien nach MUSTER, nur innerhalb des Datenordners."""
    if not isinstance(rel, str) or rel.startswith("/") or not _erlaubt(rel):
        raise ValueError(T("Datei {datei} ist nicht bearbeitbar", datei=repr(rel)))
    pfad = (daten / rel).resolve()
    relativ(pfad, daten)
    return pfad


def _yaml(text: str):
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as fehler:
        raise ValueError(T("Kein gültiges YAML: {fehler}", fehler=fehler)) from None


def _lebenslauf_fuer_probebau(daten: pathlib.Path, cv: dict, build: pathlib.Path) -> pathlib.Path:
    """Lebenslauf in den Build-Ordner schreiben; das Foto mit absolutem Pfad, damit es gefunden wird."""
    if not isinstance(cv, dict) or not isinstance(cv.get("basics"), dict):
        raise ValueError(T("Der Lebenslauf braucht einen Abschnitt basics"))
    if not photo_shown.load(daten):
        cv = lebenslauf_modul.without_photo(cv)  # the preview as new documents will be (G62)
    bild = cv["basics"].get("image")
    basics = {**cv["basics"], "image": str((daten / bild).resolve())} if bild else cv["basics"]
    ziel = build / "inhalt-probe" / "cv.yaml"
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(yaml.safe_dump({**cv, "basics": basics}, allow_unicode=True), encoding="utf-8")
    return ziel


def _probebau(funktion, argumente: list[str]) -> None:
    """Fehler beim Bauen als verständliche ValueError melden (z.B. falsche Struktur, Typst-Fehler)."""
    try:
        funktion(argumente)
    except ValueError:
        raise
    except (typst.TypstError, KeyError, TypeError, AttributeError, IndexError) as fehler:
        raise ValueError(T("Probebau fehlgeschlagen: {fehler}", fehler=fehler)) from None


def _baue_lebenslauf(cv_pfad: pathlib.Path, job: pathlib.Path | None, build: pathlib.Path, design: str) -> pathlib.Path:
    out = build / "inhalt-probe" / "vorschau.pdf"
    argumente = [str(cv_pfad), *cv_design.theme_arguments(design), "--build-dir", str(build), "-o", str(out)]
    argumente += ["--job", str(job)] if job else []
    _probebau(lebenslauf_modul.main, argumente)
    return out


def _baue_anschreiben(daten: pathlib.Path, wert: object, build: pathlib.Path) -> pathlib.Path:
    brief = anschreiben_modul.pruefe_brief(wert)
    probe = build / "inhalt-probe" / "anschreiben.yaml"
    probe.parent.mkdir(parents=True, exist_ok=True)
    probe.write_text(yaml.safe_dump({k: v for k, v in brief.items() if k != "lebenslauf"}, allow_unicode=True),
                     encoding="utf-8")
    out = build / "inhalt-probe" / "vorschau.pdf"
    _probebau(anschreiben_modul.main, [str(probe), "--cv", str(daten / "cv.yaml"), "--build-dir", str(build), "-o", str(out)])
    return out


def pruefe_inhalt(daten: pathlib.Path, rel: str, text: str, build: pathlib.Path) -> pathlib.Path | None:
    """Text prüfen, ohne zu speichern. Liefert ein Vorschau-PDF, wenn der Dateityp eines hat; Fehler als ValueError."""
    daten = daten.resolve()
    pruefe_datei(daten, rel)
    if rel.endswith(".md"):
        ziel = build / "inhalt-probe" / "vorschau.pdf"
        _probebau(lambda _: textdokument.baue_pdf(text, titel(rel), build / "inhalt-probe", ziel), [])
        return ziel
    wert = _yaml(text)
    if rel == "cv.yaml":
        return _baue_lebenslauf(_lebenslauf_fuer_probebau(daten, wert, build), None, build, cv_design.load(daten))
    if rel.startswith("jobs/"):
        if not isinstance(wert, dict):
            raise ValueError(T("Ein Zuschnitt ist eine Zuordnung (tags, basics, …)"))
        job = build / "inhalt-probe" / "job.yaml"
        cv = _lebenslauf_fuer_probebau(daten, _yaml((daten / "cv.yaml").read_text(encoding="utf-8")), build)
        job.write_text(text, encoding="utf-8")
        return _baue_lebenslauf(cv, job, build, cv_design.load(daten))
    if rel.endswith("anschreiben.yaml"):
        with letter_messages.in_app_language():
            return _baue_anschreiben(daten, wert, build)
    if rel in ("bewerbungen.yaml", "varianten.yaml"):
        if not isinstance(wert, list):
            raise ValueError(T("{datei} ist eine Liste von Einträgen", datei=rel))
        pruefen = pruefe_bewerbung if rel == "bewerbungen.yaml" else (lambda v: pruefe_variante(v, daten))
        ids = [pruefen(e)["id"] for e in wert]
        doppelt = sorted({i for i in ids if ids.count(i) > 1})
        if doppelt:
            raise ValueError(T("IDs doppelt: {ids}", ids=", ".join(doppelt)))
        return None
    return None
