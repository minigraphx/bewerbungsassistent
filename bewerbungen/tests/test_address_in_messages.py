"""Texts from the server reach people who chose du as well, so they do not use the formal address."""
import ast
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
FOLDERS = (ROOT / "bewerbungen", ROOT / "bewerbungen" / "ai", ROOT / "desktop")
ADDRESS = re.compile(r"\b(Sie|Ihr|Ihre|Ihrem|Ihren|Ihrer|Ihnen)\b")
# prompts and the check of letters are about the letter to the firm or the AI's instructions; the setup names the choice
NOT_MESSAGES = {"prompts.py", "pruefung.py", "preferences.py"}
# „Sie“ here means the texts, not the reader
PLURAL_OF_THINGS = "Sie können indirekt auf"


def _strings(path: pathlib.Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    docstrings = {id(node.body[0].value) for node in ast.walk(tree)
                  if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
                  and node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant)}
    return [node.value for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings]


def _sources() -> list[pathlib.Path]:
    return [path for folder in FOLDERS for path in sorted(folder.glob("*.py")) if path.name not in NOT_MESSAGES]


@pytest.mark.parametrize("path", _sources(), ids=lambda path: path.name)
def test_messages_leave_out_the_formal_address(path):
    found = [text for text in _strings(path) if ADDRESS.search(text) and PLURAL_OF_THINGS not in text]
    assert found == []


def test_the_check_sees_a_formal_text(tmp_path):
    sample = tmp_path / "sample.py"
    sample.write_text('"""Docstring mit Sie bleibt erlaubt."""\nMESSAGE = "Bitte prüfen Sie das."\n', encoding="utf-8")
    assert _strings(sample) == ["Bitte prüfen Sie das."]
