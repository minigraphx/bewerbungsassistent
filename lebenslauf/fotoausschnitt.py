"""Fotoausschnitt (`basics.x-image`) lesen, als Vorschau rendern und in die Datendatei schreiben.

Die Vorschau rendert Typst mit derselben Funktion `foto-rund` wie das Theme, damit sie exakt dem PDF entspricht.
Beim Speichern bleiben Kommentare, Reihenfolge und Formatierung der YAML-Datei erhalten (ruamel.yaml).
"""
import io
import os
import pathlib
import tempfile
import threading

import typst
import yaml
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

from build import ROOT, pruefe_foto_optionen, typst_pfad

STANDARD = {"mirror": False, "zoom": 1, "x": 0.5, "y": 0.5}
NACHKOMMASTELLEN = 3
VORSCHAU_GROESSE_PT = 132  # entspricht der Fotogrösse 4.65cm im Theme zweispaltig
VORSCHAU_PPI = 250  # rund 460 px, etwa 60 ms pro Bild
_SPEICHERN = threading.Lock()  # Lesen, Ändern und Schreiben nicht überlappen lassen


def lies_foto(daten: pathlib.Path) -> tuple[pathlib.Path, dict]:
    """Pfad des Fotos und die vollständigen Optionen (fehlende mit Standardwerten ergänzt)."""
    cv = yaml.safe_load(daten.read_text(encoding="utf-8")) or {}
    basics = cv.get("basics") or {}
    bild = basics.get("image")
    if not bild:
        raise ValueError(f"{daten}: basics.image fehlt, es gibt kein Foto zum Zuschneiden")
    foto = (daten.parent / bild).resolve()
    if not foto.is_file():
        raise ValueError(f"Foto nicht gefunden: {foto}")
    return foto, {**STANDARD, **pruefe_foto_optionen(basics.get("x-image") or {})}


def optionen_aus_anfrage(werte: dict[str, str]) -> dict:
    """Optionen aus Textwerten (z.B. URL-Parametern) lesen und prüfen; alle vier Werte sind Pflicht."""
    fehlend = [key for key in STANDARD if key not in werte]
    if fehlend:
        raise ValueError(f"Es fehlen Werte: {', '.join(fehlend)}")
    if werte["mirror"] not in ("true", "false"):
        raise ValueError("mirror muss true oder false sein")
    zahlen = {}
    for key in ("zoom", "x", "y"):
        try:
            zahlen[key] = float(werte[key])
        except ValueError:
            raise ValueError(f"{key} muss eine Zahl sein, nicht {werte[key]!r}") from None
    return pruefe_foto_optionen({"mirror": werte["mirror"] == "true", **zahlen})


def typst_optionen(optionen: dict) -> str:
    zahlen = ", ".join(f"{key}: {float(optionen[key]):.6f}" for key in ("zoom", "x", "y"))
    return f"(mirror: {'true' if optionen['mirror'] else 'false'}, {zahlen})"


class Vorschau:
    """Rendert den runden Fotoausschnitt als PNG; der Typst-Compiler wird wiederverwendet (rund 35 ms pro Bild)."""

    def __init__(self, foto: pathlib.Path, build: pathlib.Path) -> None:
        build.mkdir(parents=True, exist_ok=True)
        self._wurzel = pathlib.Path(os.path.commonpath([ROOT, build, foto]))
        self._foto = typst_pfad(foto, self._wurzel)
        self._common = typst_pfad(ROOT / "themes" / "common.typ", self._wurzel)
        self._datei = build / "foto-vorschau.typ"
        self._schreibe(STANDARD)
        self._compiler = typst.Compiler(str(self._datei), root=str(self._wurzel))
        self._sperre = threading.Lock()

    def _schreibe(self, optionen: dict) -> None:
        self._datei.write_text(
            f'#import "{self._common}": foto-rund\n'
            f"#set page(width: {VORSCHAU_GROESSE_PT}pt, height: {VORSCHAU_GROESSE_PT}pt, margin: 0pt, fill: none)\n"
            f'#foto-rund("{self._foto}", {VORSCHAU_GROESSE_PT}pt, {typst_optionen(optionen)})\n',
            encoding="utf-8",
        )

    def png(self, optionen: dict) -> bytes:
        geprueft = {**STANDARD, **pruefe_foto_optionen(optionen)}
        with self._sperre:
            self._schreibe(geprueft)
            return self._compiler.compile(format="png", ppi=VORSCHAU_PPI)


def _yaml() -> YAML:
    """Round-Trip-YAML mit den Einstellungen, unter denen die Daten unverändert zurückgeschrieben werden."""
    y = YAML()
    y.preserve_quotes = True
    y.width = 4096
    y.indent(mapping=2, sequence=4, offset=2)
    y.representer.add_representer(type(None), lambda r, _: r.represent_scalar("tag:yaml.org,2002:null", "null"))
    return y


def _gerundet(optionen: dict) -> CommentedMap:
    werte = CommentedMap(
        (key, optionen[key] if key == "mirror" else round(optionen[key], NACHKOMMASTELLEN)) for key in STANDARD
    )
    werte.fa.set_flow_style()
    return werte


def speichere_optionen(daten: pathlib.Path, optionen: dict) -> None:
    """`basics.x-image` setzen; geschrieben wird atomar. Entwürfe davor und danach legt der Aufrufer an
    (bewerbungen/kontext.py, MIN-303)."""
    geprueft = {**STANDARD, **pruefe_foto_optionen(optionen)}
    with _SPEICHERN:
        _schreibe_optionen(daten, geprueft)


def _schreibe_optionen(daten: pathlib.Path, geprueft: dict) -> None:
    text = daten.read_text(encoding="utf-8")
    y = _yaml()
    dokument = y.load(text)  # frisch geladenes Dokument, nur hier verändert
    basics = dokument["basics"]
    neu = _gerundet(geprueft)
    if "x-image" in basics:
        basics["x-image"] = neu
    else:
        position = list(basics).index("image") + 1 if "image" in basics else len(basics)
        basics.insert(position, "x-image", neu)
    ausgabe = io.StringIO()
    y.dump(dokument, ausgabe)

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=daten.parent, delete=False, suffix=".tmp") as tmp:
        tmp.write(ausgabe.getvalue())
    os.replace(tmp.name, daten)
