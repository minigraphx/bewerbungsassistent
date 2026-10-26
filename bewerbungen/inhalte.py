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
from dateien import relativ
import textdokument
from register import pruefe_bewerbung
from varianten import pruefe_variante

MUSTER = ("cv.yaml", "suchprofil.md", "varianten.yaml", "bewerbungen.yaml", "jobs/*.yaml", "anschreiben/*.md",
          "bewerbungen/*/anschreiben.yaml", "bewerbungen/*/stelle.md")

NUR_TEXT = ("bewerbungen.yaml", "varianten.yaml")  # Datenlisten: bearbeiten in der Oberfläche, hier nur als Text
TITEL = {"cv.yaml": "Lebenslauf", "suchprofil.md": "Suchprofil", "anschreiben/stil.md": "Anschreiben: Stilprofil",
         "anschreiben/bausteine.md": "Anschreiben: Textbausteine",
         "bewerbungen.yaml": "Bewerbungsregister (Daten)", "varianten.yaml": "Lebenslauf-Varianten (Daten)"}


def _erlaubt(rel: str) -> bool:
    return any(fnmatch.fnmatchcase(rel, m) and rel.count("/") == m.count("/") for m in MUSTER)


def hat_pdf_ansicht(rel: str) -> bool:
    return _erlaubt(rel) and rel not in NUR_TEXT


def titel(rel: str) -> str:
    """Verständlicher Name einer Datei für die Oberfläche."""
    if rel in TITEL:
        return TITEL[rel]
    teile = pathlib.PurePosixPath(rel)
    if teile.parts[0] == "jobs":
        return f"Lebenslauf-Zuschnitt {teile.stem}"
    if teile.parts[0] == "anschreiben":
        return f"Anschreiben: {teile.stem}"
    if teile.parts[0] == "bewerbungen" and len(teile.parts) == 3:
        art = "Anschreiben" if teile.name == "anschreiben.yaml" else "Stellenausschreibung"
        return f"{art} {teile.parts[1]}"
    return rel


def bearbeitbare_dateien(daten: pathlib.Path) -> list[str]:
    daten = daten.resolve()
    gefunden = {p.relative_to(daten).as_posix() for m in MUSTER for p in daten.glob(m) if p.is_file()}
    return sorted(r for r in gefunden if _erlaubt(r))


def pruefe_datei(daten: pathlib.Path, rel: str) -> pathlib.Path:
    """Nur Dateien nach MUSTER, nur innerhalb des Datenordners."""
    if not isinstance(rel, str) or rel.startswith("/") or not _erlaubt(rel):
        raise ValueError(f"Datei {rel!r} ist nicht bearbeitbar")
    pfad = (daten / rel).resolve()
    relativ(pfad, daten)
    return pfad


def _yaml(text: str):
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as fehler:
        raise ValueError(f"Kein gültiges YAML: {fehler}") from None


def _lebenslauf_fuer_probebau(daten: pathlib.Path, cv: dict, build: pathlib.Path) -> pathlib.Path:
    """Lebenslauf in den Build-Ordner schreiben; das Foto mit absolutem Pfad, damit es gefunden wird."""
    if not isinstance(cv, dict) or not isinstance(cv.get("basics"), dict):
        raise ValueError("Der Lebenslauf braucht einen Abschnitt basics")
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
        raise ValueError(f"Probebau fehlgeschlagen: {fehler}") from None


def _baue_lebenslauf(cv_pfad: pathlib.Path, job: pathlib.Path | None, build: pathlib.Path) -> pathlib.Path:
    out = build / "inhalt-probe" / "vorschau.pdf"
    argumente = [str(cv_pfad), "--build-dir", str(build), "-o", str(out)] + (["--job", str(job)] if job else [])
    _probebau(lebenslauf_modul.main, argumente)
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
        return _baue_lebenslauf(_lebenslauf_fuer_probebau(daten, wert, build), None, build)
    if rel.startswith("jobs/"):
        if not isinstance(wert, dict):
            raise ValueError("Ein Zuschnitt ist eine Zuordnung (tags, basics, …)")
        job = build / "inhalt-probe" / "job.yaml"
        cv = _lebenslauf_fuer_probebau(daten, _yaml((daten / "cv.yaml").read_text(encoding="utf-8")), build)
        job.write_text(text, encoding="utf-8")
        return _baue_lebenslauf(cv, job, build)
    if rel.endswith("anschreiben.yaml"):
        brief = anschreiben_modul.pruefe_brief(wert)
        probe = build / "inhalt-probe" / "anschreiben.yaml"
        probe.parent.mkdir(parents=True, exist_ok=True)
        probe.write_text(yaml.safe_dump({k: v for k, v in brief.items() if k != "lebenslauf"}, allow_unicode=True),
                         encoding="utf-8")
        out = build / "inhalt-probe" / "vorschau.pdf"
        _probebau(anschreiben_modul.main, [str(probe), "--cv", str(daten / "cv.yaml"), "--build-dir", str(build), "-o", str(out)])
        return out
    if rel in ("bewerbungen.yaml", "varianten.yaml"):
        if not isinstance(wert, list):
            raise ValueError(f"{rel} ist eine Liste von Einträgen")
        pruefen = pruefe_bewerbung if rel == "bewerbungen.yaml" else (lambda v: pruefe_variante(v, daten))
        ids = [pruefen(e)["id"] for e in wert]
        doppelt = sorted({i for i in ids if ids.count(i) > 1})
        if doppelt:
            raise ValueError(f"IDs doppelt: {', '.join(doppelt)}")
        return None
    return None
