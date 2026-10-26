"""Markdown-Dateien als PDF ansehen (Stilprofil, Bausteine, Suchprofil, Stellentext).

Der Markdown-Text wird mit markdown-it (CommonMark plus Tabellen) in eine Struktur zerlegt und als JSON an
`typst/dokument.typ` übergeben. Typst setzt alle Texte als Text ein, nie als Markup; HTML bleibt Text,
Bilder werden nicht geladen, Links nur für Web- und Mail-Adressen.
"""
import json
import os
import pathlib

import typst
from markdown_it import MarkdownIt
from markdown_it.tree import SyntaxTreeNode

import pfade  # noqa: F401  (macht das Modul lebenslauf importierbar)
import build as lebenslauf_modul

VORLAGE = pathlib.Path(__file__).resolve().parent / "typst" / "dokument.typ"
LINK_SCHEMAS = ("http://", "https://", "mailto:")
MIT_TEXT = ("text", "code_inline", "fence", "code_block")
DURCHREICHEN = ("inline", "thead", "tbody")

_markdown = MarkdownIt("commonmark", {"html": False}).enable("table")


def _kinder(knoten: SyntaxTreeNode) -> list[dict]:
    return [teil for kind in knoten.children for teil in _umwandeln(kind)]


def _tabelle(knoten: SyntaxTreeNode) -> dict:
    zeilen = [[_kinder(zelle) for zelle in zeile.children]
              for teil in knoten.children for zeile in teil.children]
    spalten = max((len(z) for z in zeilen), default=1)
    gleich = [z + [[] for _ in range(spalten - len(z))] for z in zeilen]
    return {"t": "table", "spalten": spalten, "kopf": gleich[0] if gleich else [], "zeilen": gleich[1:]}


def _umwandeln(knoten: SyntaxTreeNode) -> list[dict]:
    """Ein Knoten wird zu null oder mehr Einträgen (Hüllen wie `inline` werden aufgelöst)."""
    typ = knoten.type
    if typ in DURCHREICHEN:
        return _kinder(knoten)
    if typ == "paragraph" and knoten.hidden:  # Absatz in einer engen Liste
        return _kinder(knoten)
    if typ == "table":
        return [_tabelle(knoten)]
    if typ in MIT_TEXT:
        return [{"t": typ, "text": knoten.content}]
    eintrag = {"t": typ}
    if typ == "heading":
        eintrag["stufe"] = int(knoten.tag[1:])
    if typ == "ordered_list":
        eintrag["start"] = int(knoten.attrs.get("start", 1))
    if typ == "link":
        href = str(knoten.attrs.get("href", ""))
        eintrag["href"] = href if href.lower().startswith(LINK_SCHEMAS) else None
    if knoten.children:
        eintrag["k"] = _kinder(knoten)
    return [eintrag]


def als_struktur(text: str) -> list[dict]:
    return _kinder(SyntaxTreeNode(_markdown.parse(text)))


def baue_pdf(text: str, titel: str, build: pathlib.Path, ziel: pathlib.Path) -> pathlib.Path:
    build = build.resolve()
    build.mkdir(parents=True, exist_ok=True)
    daten = build / "dokument.json"
    daten.write_text(json.dumps({"titel": titel, "bloecke": als_struktur(text)}, ensure_ascii=False), encoding="utf-8")
    wurzel = pathlib.Path(os.path.commonpath([VORLAGE.parent, build]))
    ziel = ziel.resolve()
    ziel.parent.mkdir(parents=True, exist_ok=True)
    typst.compile(str(VORLAGE), output=str(ziel), root=str(wurzel),
                  font_paths=[str(lebenslauf_modul.ROOT / "fonts")],
                  sys_inputs={"data": lebenslauf_modul.typst_pfad(daten, wurzel)})
    return ziel
