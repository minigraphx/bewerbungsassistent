"""Where the app's texts stand in its source (#414, G10), for the scanner `sprachen_pruefen`.

HTML: what page_translation translates: text nodes outside script and style, the attributes aria-label, placeholder,
title and alt, and the text set of an element with data-text. JavaScript: the literal of each `Texte.t(…)`, the key of
each `Texte.text(…)`, and German-looking literals left outside Texte.t. Python: the literal of each `T(…)` (#415) and
the literal message of a `raise`, also through a module constant. Never a text: names in INVARIANT, stored data values
(DATA_VALUES), comparisons, object keys, code-like literals and lines marked `kein UI-Text`.
"""
import ast
import dataclasses
import pathlib
import re
from typing import Iterable, Iterator

import page_translation
import register

BASE = pathlib.Path(__file__).resolve().parent
TEXTE_JS = BASE / "seiten" / "texte.js"
NOT_UI_MARKER = "kein UI-Text"
# Names and units that read the same in every language; a text of nothing else needs no translation.
INVARIANT = ("Bewerbungsbegleiter", "Claude Desktop", "Claude", "Anthropic", "CHF", "USD", "jobs.ch", "Job-Room",
             "job-room", "jobscout24", "ictjobs", "yousty", "kununu", "LinkedIn", "GitHub", "Chrome", "Edge", "Firefox",
             "Safari", "PDF", "ZIP", "JPG", "PNG", "SVG")
# Stored values stay German in every language; the pages word them (texte.js statusName).
DATA_VALUES = frozenset(register.STATUS)
LETTER = re.compile(r"[^\W\d_]")
INVARIANT_NAME = re.compile("|".join(rf"(?<![\w.-]){re.escape(name)}(?![\w-])"
                                     for name in sorted(INVARIANT, key=len, reverse=True)))

JS_TOKEN = re.compile(r"""//[^\n]*|/\*.*?\*/|"(?:[^"\\\n]|\\.)*"|'(?:[^'\\\n]|\\.)*'|`(?:[^`\\]|\\.)*`""", re.S)
JS_ESCAPE = re.compile(r"\\(u\{[0-9a-fA-F]+\}|u[0-9a-fA-F]{4}|.)", re.S)
JS_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "b": "\b", "f": "\f", "v": "\v", "0": "\0"}
T_CALL = re.compile(r"\bTexte\.t\(\s*$")
SET_CALL = re.compile(r"\bTexte\.text\(\s*$")
COMPARED_BEFORE = re.compile(r"(?:[!=]==?|\bcase)\s*$")
# A form of a text set in texte.js; the catalog translates it as "texte:<key>", never as a plain text.
SET_FORM_BEFORE = re.compile(r"\b(?:sie|du|lehrstelle):\s*$")
COMPARED_AFTER = re.compile(r"^\s*(?:[!=]==?|:)")
# A leftover is a sentence (with a space) or one capitalised word such as „Speichern“; code rarely looks like either.
TEXT_LIKE = re.compile(r"[A-ZÄÖÜ][^\s]*\s+\S.*|[A-ZÄÖÜ][a-zäöüß]+[.!?:…]?", re.S)
CODE_LIKE = re.compile(r"[a-z][\w-]*://|^[/#.]|\$\{")
CONTEXT = 40

SETS_BLOCK = re.compile(r"const TEXTE = \{\n(.*?)\n  \};", re.S)
SET_KEY = re.compile(r'"([\w.\-]+)":\s*\{')
SET_FORM = re.compile(r'\s*(sie|du|lehrstelle):\s*("(?:[^"\\]|\\.)*")\s*,?')
SET_END = re.compile(r"\s*\}")


@dataclasses.dataclass(frozen=True)
class Item:
    path: pathlib.Path
    line: int
    text: str
    kind: str  # "text": German text for the catalog; "set": key of a text set; "leftover": literal outside Texte.t


def needs_translation(text: str) -> bool:
    return text not in DATA_VALUES and LETTER.search(INVARIANT_NAME.sub("", text)) is not None


def _line(source: str, offset: int) -> int:
    return source.count("\n", 0, offset) + 1


def _marked_lines(source: str) -> frozenset[int]:
    return frozenset(number for number, line in enumerate(source.splitlines(), 1) if NOT_UI_MARKER in line)


def _html_items(path: pathlib.Path, source: str) -> Iterator[Item]:
    for found in page_translation.page_texts(source):
        if found.kind == "set" or needs_translation(found.text):
            yield Item(path, _line(source, found.offset), found.text, found.kind)


def _js_escape(found: re.Match) -> str:
    code = found[1]
    if code.startswith("u{"):
        return chr(int(code[2:-1], 16))
    if code.startswith("u") and len(code) == 5:
        return chr(int(code[1:], 16))
    return JS_ESCAPES.get(code, code)


def js_string(token: str) -> str:
    return JS_ESCAPE.sub(_js_escape, token[1:-1])


def _js_item(path: pathlib.Path, source: str, found: re.Match) -> Item | None:
    before = source[max(0, found.start() - CONTEXT):found.start()]
    after = source[found.end():found.end() + CONTEXT]
    value = js_string(found[0])
    line = _line(source, found.start())
    if SET_CALL.search(before):
        return Item(path, line, value, "set")
    if T_CALL.search(before):
        return Item(path, line, value, "text")
    if (COMPARED_BEFORE.search(before) or SET_FORM_BEFORE.search(before) or COMPARED_AFTER.match(after)
            or CODE_LIKE.search(value)):
        return None
    if TEXT_LIKE.fullmatch(value) and needs_translation(value):
        return Item(path, line, value, "leftover")
    return None


def _js_items(path: pathlib.Path, source: str) -> Iterator[Item]:
    marked = _marked_lines(source)
    for found in JS_TOKEN.finditer(source):
        if found[0][0] not in "\"'`" or _line(source, found.start()) in marked:
            continue
        item = _js_item(path, source, found)
        if item:
            yield item


def _module_constants(tree: ast.Module) -> dict[str, str]:
    return {target.id: node.value.value for node in tree.body if isinstance(node, ast.Assign)
            and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)
            for target in node.targets if isinstance(target, ast.Name)}


def _template(node: ast.JoinedStr) -> str:
    return "".join(part.value if isinstance(part, ast.Constant)
                   else "{" + (part.value.id if isinstance(part.value, ast.Name) else "…") + "}"
                   for part in node.values)


def _literal(node: ast.expr, constants: dict[str, str]) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return _template(node)
    if isinstance(node, ast.Name):
        return constants.get(node.id)
    return None


def _message(node: ast.AST, constants: dict[str, str]) -> str | None:
    if isinstance(node, ast.Call) and node.args:
        callee = node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, "attr", "")
        if callee == "T":
            return _literal(node.args[0], constants)
    if isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call) and node.exc.args:
        return _literal(node.exc.args[0], constants)
    return None


def _python_items(path: pathlib.Path, source: str) -> Iterator[Item]:
    tree = ast.parse(source, filename=str(path))
    constants = _module_constants(tree)
    marked = _marked_lines(source)
    for node in ast.walk(tree):
        text = _message(node, constants)
        lines = range(getattr(node, "lineno", 0), getattr(node, "end_lineno", 0) + 1)
        if text and needs_translation(text) and not marked.intersection(lines):
            yield Item(path, node.lineno, text, "text")


READERS = {".html": _html_items, ".js": _js_items, ".py": _python_items}


def items(paths: Iterable[pathlib.Path]) -> tuple[Item, ...]:
    """Every text of the files, in file and line order; a file of another kind has none."""
    found = (item for path in paths if path.suffix in READERS
             for item in READERS[path.suffix](path, path.read_text(encoding="utf-8")))
    return tuple(sorted(found, key=lambda item: (str(item.path), item.line)))


def _set_forms(block: str, start: int, key: str) -> tuple[dict[str, str], int]:
    forms = {}
    position = start
    while found := SET_FORM.match(block, position):
        forms = {**forms, found[1]: js_string(found[2])}
        position = found.end()
    end = SET_END.match(block, position)
    if not end:
        raise ValueError(f"texte.js: the entry {key} is not plain text forms")
    return forms, end.end()


def text_sets(path: pathlib.Path = TEXTE_JS) -> dict[str, dict[str, str]]:
    """TEXTE of texte.js without running it: key -> {sie, du, lehrstelle?}."""
    block = SETS_BLOCK.search(path.read_text(encoding="utf-8"))
    if not block:
        raise ValueError(f"{path.name}: no TEXTE block")
    sets = {}
    position = 0
    while found := SET_KEY.search(block[1], position):
        forms, position = _set_forms(block[1], found.end(), found[1])
        sets = {**sets, found[1]: forms}
    return sets
