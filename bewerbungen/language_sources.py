"""Where the app's texts stand in its source (#414, G10), for the scanner `sprachen_pruefen`.

HTML: what page_translation translates: text nodes outside script and style, the attributes aria-label, placeholder,
title and alt, and the text set of an element with data-text. JavaScript: the literal of each `Texte.t(…)`, the key of
each `Texte.text(…)`, and German-looking literals left outside Texte.t. Python: the template of each `T(…)` (#415) and
the literal message of a `raise`, also through a module constant; a message built with an f-string needs `T`.
onboarding/form.json: what Meine Angaben shows of it (#431), never a value it stores. Never a
text: names in INVARIANT, stored data values (DATA_VALUES), comparisons, object keys, code-like literals and lines
marked `kein UI-Text`.
"""
import ast
import dataclasses
import json
import pathlib
import re
from typing import Iterable, Iterator

import page_translation
import register

BASE = pathlib.Path(__file__).resolve().parent
TEXTE_JS = BASE / "seiten" / "texte.js"
# The scripts of Meine Angaben say their texts through their own T (onboarding/src/words.js, #431).
ONBOARDING_SRC = BASE.parent / "onboarding" / "src"
NOT_UI_MARKER = "kein UI-Text"
# Names and units that read the same in every language; a text of nothing else needs no translation.
INVARIANT = ("Bewerbungsbegleiter", "Claude Desktop", "Claude", "Anthropic", "CHF", "USD", "jobs.ch", "Job-Room",
             "job-room", "jobscout24", "ictjobs", "yousty", "kununu", "LinkedIn", "GitHub", "Google Chrome",
             "Microsoft Edge", "Chrome", "Edge", "Firefox", "Safari", "PDF", "ZIP", "JPG", "PNG", "SVG", "km")
# Stored values stay German in every language; the pages word them (texte.js statusName).
DATA_VALUES = frozenset(register.STATUS)
LETTER = re.compile(r"[^\W\d_]")
PLACEHOLDER = re.compile(r"\{\w+\}")
INVARIANT_NAME = re.compile("|".join(rf"(?<![\w.-]){re.escape(name)}(?![\w-])"
                                     for name in sorted(INVARIANT, key=len, reverse=True)))

JS_TOKEN = re.compile(r"""//[^\n]*|/\*.*?\*/|"(?:[^"\\\n]|\\.)*"|'(?:[^'\\\n]|\\.)*'|`(?:[^`\\]|\\.)*`""", re.S)
JS_ESCAPE = re.compile(r"\\(u\{[0-9a-fA-F]+\}|u[0-9a-fA-F]{4}|.)", re.S)
JS_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "b": "\b", "f": "\f", "v": "\v", "0": "\0"}
T_CALL = re.compile(r"\bTexte\.t\(\s*$")
# texte.js calls its own t (#416): there the same catalog lookup has no „Texte.“ before it; the scripts of Meine
# Angaben call T, which is Texte.t in the app and gives the German back in the file for sharing (#431).
OWN_T_CALL = re.compile(r"(?<![\w.$])t\(\s*$")
ONBOARDING_T_CALL = re.compile(r"(?<![\w.$])T\(\s*$")
SET_CALL = re.compile(r"\bTexte\.text\(\s*$")
COMPARED_BEFORE = re.compile(r"(?:[!=]==?|\bcase)\s*$")
# A form of a text set in texte.js; the catalog translates it as "texte:<key>", never as a plain text.
SET_FORM_BEFORE = re.compile(r"\b(?:sie|du|lehrstelle):\s*$")
COMPARED_AFTER = re.compile(r"^\s*[!=]==?")
# A literal before „:“ is an object key, unless „?“ stands before it: then it is the first branch of a ternary (#417).
KEY_AFTER = re.compile(r"^\s*:")
TERNARY_BEFORE = re.compile(r"\?\s*$")
# A leftover is a sentence (with a space) or one capitalised word such as „Speichern“; code rarely looks like either.
TEXT_LIKE = re.compile(r"[A-ZÄÖÜ][^\s]*\s+\S.*|[A-ZÄÖÜ][a-zäöüß]+[.!?:…]?", re.S)
# A bare address is code; a sentence that names one („unter chrome://extensions … klicken“) is still a text (#418).
CODE_LIKE = re.compile(r"^[a-z][\w-]*://\S*$|^[/#.]")
# A template literal is judged by its own words: `Version ${v} ist verfügbar.` is a text, `/treffer?${q}` is not (#416).
INTERPOLATION = re.compile(r"\$\{[^}]*\}")
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
    # "text": German text for the catalog; "set": key of a text set; "leftover": a literal outside Texte.t (JavaScript)
    # or a formatted message outside T (Python)
    kind: str


def needs_translation(text: str, stored: frozenset[str] = DATA_VALUES) -> bool:
    """A text with words of its own: names, stored values and a template of nothing but placeholders such as
    „{hinweis} {adresse}“ are none (#417). Placeholders with punctuation stay a text, since French spaces it."""
    if text in stored or not PLACEHOLDER.sub("", text).strip():
        return False
    return LETTER.search(INVARIANT_NAME.sub("", text)) is not None


def _line(source: str, offset: int) -> int:
    return source.count("\n", 0, offset) + 1


def _marked_lines(source: str) -> frozenset[int]:
    return frozenset(number for number, line in enumerate(source.splitlines(), 1) if NOT_UI_MARKER in line)


def _html_items(path: pathlib.Path, source: str) -> Iterator[Item]:
    for found in page_translation.page_texts(source):
        # A page holds no stored values, only labels: a tab „Gemerkt“ is a word for the person (#420).
        if found.kind == "set" or needs_translation(found.text, stored=frozenset()):
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
    if (T_CALL.search(before) or (path.name == TEXTE_JS.name and OWN_T_CALL.search(before))
            or (path.resolve().parent == ONBOARDING_SRC and ONBOARDING_T_CALL.search(before))):
        return Item(path, line, value, "text")
    # Judged without the spaces around it: " Die Erweiterung …" joins a sentence before it and is a text all the same.
    words = (INTERPOLATION.sub("", value) if found[0][0] == "`" else value).strip()
    is_key = KEY_AFTER.match(after) and not TERNARY_BEFORE.search(before)
    if (COMPARED_BEFORE.search(before) or SET_FORM_BEFORE.search(before) or COMPARED_AFTER.match(after) or is_key
            or CODE_LIKE.search(value) or CODE_LIKE.search(words)):
        return None
    if TEXT_LIKE.fullmatch(words) and needs_translation(words):
        return Item(path, line, value, "leftover")
    return None


def _interpolations(source: str, token: re.Match) -> Iterator[tuple[int, int]]:
    """Start and end of the code of each ${…} in a template token, braces counted and strings skipped."""
    position = token.start() + 1
    while (start := source.find("${", position, token.end())) != -1:
        depth, at = 1, start + 2
        while at < token.end() and depth:
            string = JS_TOKEN.match(source, at) if source[at] in "\"'`" else None
            if string:
                at = string.end()
                continue
            depth += {"{": 1, "}": -1}.get(source[at], 0)
            at += 1
        yield start + 2, at - 1
        position = at


def _tokens(source: str, start: int, end: int) -> Iterator[re.Match]:
    """Every token, also those inside the ${…} of a template: Texte.t there is a text like any other (#416)."""
    for found in JS_TOKEN.finditer(source, start, end):
        yield found
        if found[0][0] == "`":
            for inner_start, inner_end in _interpolations(source, found):
                yield from _tokens(source, inner_start, inner_end)


def _js_items(path: pathlib.Path, source: str) -> Iterator[Item]:
    marked = _marked_lines(source)
    for found in _tokens(source, 0, len(source)):
        if found[0][0] not in "\"'`" or _line(source, found.start()) in marked:
            continue
        item = _js_item(path, source, found)
        if item:
            yield item


def _is_string(node: ast.expr) -> bool:
    return isinstance(node, ast.JoinedStr) or (isinstance(node, ast.Constant) and isinstance(node.value, str))


def _module_constants(tree: ast.Module) -> dict[str, ast.expr]:
    """Strings of the module by name, plain or formatted: a raised f-string constant needs T as much as an inline one
    (#420, routes_apply.TOO_MANY)."""
    return {target.id: node.value for node in tree.body if isinstance(node, ast.Assign) and _is_string(node.value)
            for target in node.targets if isinstance(target, ast.Name)}


def _template(node: ast.JoinedStr) -> str:
    return "".join(part.value if isinstance(part, ast.Constant)
                   else "{" + (part.value.id if isinstance(part.value, ast.Name) else "…") + "}"
                   for part in node.values)


def _resolved(node: ast.expr, constants: dict[str, ast.expr]) -> ast.expr:
    return constants.get(node.id, node) if isinstance(node, ast.Name) else node


def _literal(node: ast.expr, constants: dict[str, ast.expr]) -> str | None:
    found = _resolved(node, constants)
    if isinstance(found, ast.Constant) and isinstance(found.value, str):
        return found.value
    if isinstance(found, ast.JoinedStr):
        return _template(found)
    return None


def _text_or_leftover(node: ast.expr, constants: dict[str, ast.expr]) -> tuple[str, str] | None:
    text = _literal(node, constants)
    return (("leftover" if isinstance(_resolved(node, constants), ast.JoinedStr) else "text"), text) if text else None


def _message(node: ast.AST, constants: dict[str, ast.expr]) -> tuple[str, str] | None:
    """(kind, text) of a message: "text" for the catalog, "leftover" for a formatted one that only T can translate,
    since the server matches a plain message as a whole and the filled-in values are never in the catalog."""
    if isinstance(node, ast.Call) and node.args:
        callee = node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, "attr", "")
        if callee == "T":
            return _text_or_leftover(node.args[0], constants)
    if isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call) and node.exc.args:
        return _text_or_leftover(node.exc.args[0], constants)
    return None


def _python_items(path: pathlib.Path, source: str) -> Iterator[Item]:
    tree = ast.parse(source, filename=str(path))
    constants = _module_constants(tree)
    marked = _marked_lines(source)
    for node in ast.walk(tree):
        message = _message(node, constants)
        lines = range(getattr(node, "lineno", 0), getattr(node, "end_lineno", 0) + 1)
        if message and needs_translation(message[1]) and not marked.intersection(lines):
            yield Item(path, node.lineno, message[1], message[0])


# onboarding/form.json (#431): the keys whose strings Meine Angaben shows. Options show only without labels of their
# own; suggestions and presets go into the field as they are, and like every value the form stores they stay German.
FORM_TEXT_KEYS = frozenset({"title", "intro", "label", "hint", "placeholder", "itemTitle", "emptyLabel", "kindLabel",
                            "kindPlural", "example", "labels", "messages", "optionLabels", "options"})
# A canton (BE) or a level of a language (C2) reads the same in every language; an abbreviation such as PLZ does not.
FORM_CODE = re.compile(r"[A-Z]{2}|[ABC][12]")
JSON_STRING = re.compile(r'"(?:[^"\\\n]|\\.)*"')


def _strings(value) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, (dict, list)):
        for item in (value.values() if isinstance(value, dict) else value):
            yield from _strings(item)


def _form_texts(value) -> Iterator[str]:
    """The strings of form.json the form shows, in the order of the file: the canton names and the strings under
    FORM_TEXT_KEYS, whether one text, one per track or a list."""
    if isinstance(value, list):
        for item in value:
            yield from _form_texts(item)
        return
    if not isinstance(value, dict):
        return
    for name, item in value.items():
        if name == "options" and "optionLabels" in value:
            continue
        if name in FORM_TEXT_KEYS:
            yield from _strings(item)
        elif name == "cantons" and isinstance(item, list):
            yield from (canton["name"] for canton in item if isinstance(canton, dict) and isinstance(canton.get("name"), str))
        else:
            yield from _form_texts(item)


def _is_form_text(text: str) -> bool:
    return needs_translation(text, stored=frozenset()) and not FORM_CODE.fullmatch(text) and not CODE_LIKE.search(text)


def _form_items(path: pathlib.Path, source: str) -> Iterator[Item]:
    lines: dict[str, int] = {}
    for found in JSON_STRING.finditer(source):
        lines.setdefault(json.loads(found[0]), _line(source, found.start()))
    shown = dict.fromkeys(text for text in _form_texts(json.loads(source)) if _is_form_text(text))
    for text in shown:
        yield Item(path, lines.get(text, 1), text, "text")


READERS = {".html": _html_items, ".js": _js_items, ".py": _python_items, ".json": _form_items}


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
