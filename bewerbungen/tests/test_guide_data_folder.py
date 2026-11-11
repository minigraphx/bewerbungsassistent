"""The guide names every file and folder the app keeps in the data folder (#172).

The names come from the code: module constants that name a file or folder, and paths built as `folder / "name.ext"`.
A new one fails here until the section „Was im Datenordner liegt“ of docs/installation.md explains it.
"""
import ast
import fnmatch
import json
import pathlib
import re

import pytest

import unterlagen

ROOT = pathlib.Path(__file__).resolve().parents[2]
GUIDE = ROOT / "docs" / "installation.md"
HEADING = "#### Was im Datenordner liegt"  # under „Für Geübte“ since #223
SOURCES = ("bewerbungen/*.py", "bewerbungen/ai/*.py", "onboarding/*.py", "desktop/routes_angaben.py", "desktop/setup.py",
           "desktop/routes_setup.py", "desktop/mcp_tools.py")
PATH = re.compile(r"[\w.\-/*]+\.(?:yaml|md|json|jsonl|pdf|zip|txt)")
FOLDER_NAME = re.compile(r"(?:FOLDER|ORDNER|_DIR|TEXTS)$")
NOT_IN_THE_DATA_FOLDER = {
    ("app.py", "GITIGNORE"): "patterns of the entries below, written into .gitignore",
    ("routen_inhalte.py", "VORSCHAU"): "inside .build/",
    ("routen_inhalte.py", "GET"): "routes",
    ("validation.py", "FORM_PATH"): "part of the app",
    ("mcp_tools.py", "TEMPLATES"): "templates that come with the app",
    ("setup.py", "TEXTS"): "texts for the page",
    ("known_tags.py", "JOB_FILES"): "jobs/*.yaml, read relative to jobs/",
}
MUST_HAVE = ("cv.yaml", "suchprofil.md", "anschreiben/stil.md", "anschreiben/bausteine.md", "bewerbungen.yaml", "jobs/*.yaml")


def _strings(node: ast.AST, constants: dict[str, str]) -> list[str]:
    if isinstance(node, ast.JoinedStr):
        parts = [part.value if isinstance(part, ast.Constant) else constants.get(getattr(part.value, "id", ""), "")
                 for part in node.values]
        return ["".join(str(part) for part in parts)]
    if isinstance(node, ast.Constant):
        return [node.value] if isinstance(node.value, str) else []
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        return [text for element in node.elts for text in _strings(element, constants)]
    if isinstance(node, ast.Dict):
        return [text for element in [*node.keys, *node.values] if element is not None for text in _strings(element, constants)]
    return []


def _outside_the_data_folder(node: ast.AST) -> bool:
    """Paths under the build folder (.build/) or next to the code of the app."""
    names = {getattr(sub, "id", "") or getattr(sub, "attr", "") for sub in ast.walk(node) if isinstance(sub, (ast.Name, ast.Attribute))}
    return any("build" in name or name in ("ROOT", "HERE", "__file__") for name in names)


def _sources() -> list[pathlib.Path]:
    return sorted(path for pattern in SOURCES for path in ROOT.glob(pattern))


def _names_in(path: pathlib.Path, constants: dict[str, str]) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in tree.body:
        if not (isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)):
            continue
        name = node.targets[0].id
        if not name.isupper() or (path.name, name) in NOT_IN_THE_DATA_FOLDER:
            continue
        for text in _strings(node.value, constants):
            if PATH.fullmatch(text.strip("/")) or (FOLDER_NAME.search(name) and re.fullmatch(r"[\w.\-/]+", text)):
                names.add(text.strip("/"))
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div) and isinstance(node.right, ast.Constant) \
                and isinstance(node.right.value, str) and not _outside_the_data_folder(node.left):
            if PATH.fullmatch(node.right.value) or node.right.value.startswith("."):
                names.add(node.right.value)
    return names


def written_by_the_app() -> set[str]:
    trees = [ast.parse(path.read_text(encoding="utf-8")) for path in _sources()]
    constants = {node.targets[0].id: node.value.value for tree in trees for node in tree.body
                 if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
                 and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)}
    names = set().union(*(_names_in(path, constants) for path in _sources()))
    documents = json.loads((ROOT / "onboarding" / "form.json").read_text(encoding="utf-8"))["documents"]["categories"]
    built = {f"{kind}.pdf" for kind in unterlagen.ARTEN}
    return names | {f"dokumente/{category['id']}" for category in documents} | built | {".build", ".git"}


def section() -> str:
    text = GUIDE.read_text(encoding="utf-8")
    assert HEADING in text, f"{HEADING} fehlt in docs/installation.md"
    rest = text.split(HEADING, 1)[1]
    return re.split(r"\n#{2,3} ", rest, maxsplit=1)[0]


def _covered(name: str, spans: list[str]) -> bool:
    wanted = name.strip("/").split("/")
    for span in spans:
        parts = span.strip("/").split("/")
        for start in range(len(parts) - len(wanted) + 1):
            if all(fnmatch.fnmatchcase(part, pattern) or fnmatch.fnmatchcase(pattern, part)
                   for part, pattern in zip(parts[start:start + len(wanted)], wanted)):
                return True
    return False


def test_the_scan_finds_the_basic_files():
    found = written_by_the_app()

    assert set(MUST_HAVE) <= found
    assert {"suche", "versendet", ".entwuerfe", "dokumente/zeugnisse", "lebenslauf.pdf", ".gitignore"} <= found


@pytest.mark.parametrize("name", sorted(written_by_the_app()))
def test_the_guide_explains_each_file_of_the_data_folder(name):
    spans = re.findall(r"`([^`]+)`", section())

    assert _covered(name, spans), f"{name} fehlt im Abschnitt „Was im Datenordner liegt“"


def test_the_section_warns_to_keep_a_copy_before_editing_by_hand():
    text = section()

    assert "Sicherung" in text and "von Hand" in text
    assert "Inhalte als Text" in text and "Meine Angaben" in text
