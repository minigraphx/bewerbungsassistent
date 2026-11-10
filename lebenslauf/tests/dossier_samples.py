"""Shared helpers for the dossier design tests: invented inputs, building, and reading the PDFs.

Imported by name, not from conftest (#93), like cv_samples.
"""
import pathlib
import shutil
import subprocess

import yaml
from pypdf import PdfReader

import build
import dossier

DATA = build.ROOT / "data"
EXAMPLE = DATA / "dossier-beispiel.yaml"


def pdftotext(pdf) -> str:
    tool = shutil.which("pdftotext")
    assert tool, "pdftotext (poppler) is needed to check the reading order"
    return subprocess.run([tool, "-enc", "UTF-8", str(pdf), "-"], capture_output=True, text=True, check=True).stdout


def page_texts(pdf) -> list[str]:
    return pdftotext(pdf).split("\f")[: len(PdfReader(pdf).pages)]


def flat(text: str) -> str:
    return " ".join(text.split())


def assert_in_order(text: str, parts: list[str]) -> None:
    text = flat(text)
    position = 0
    for part in parts:
        found = text.find(part, position)
        assert found >= 0, f"{part!r} missing or out of order after position {position} in: {text[:600]}"
        position = found + len(part)


def example_cv() -> dict:
    return yaml.safe_load((DATA / "beispiel.yaml").read_text(encoding="utf-8"))


def example_letter() -> dict:
    return yaml.safe_load((DATA / "anschreiben-beispiel.yaml").read_text(encoding="utf-8"))


def example_dossier() -> dict:
    return yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))


def build_dossier(folder: pathlib.Path, *options: str, cv: dict | None = None, dossier_file: dict | None = None,
                  letter: dict | None = None) -> dossier.Result:
    """Writes CV, letter and dossier file to folder and builds all three PDFs."""
    folder.mkdir(parents=True)
    (folder / "cv.yaml").write_text(yaml.safe_dump(cv or example_cv(), allow_unicode=True), encoding="utf-8")
    letter_data = {**(letter or example_letter()), "lebenslauf": "cv.yaml"}
    (folder / "brief.yaml").write_text(yaml.safe_dump(letter_data, allow_unicode=True), encoding="utf-8")
    file_data = {**(example_dossier() if dossier_file is None else dossier_file),
                 "lebenslauf": "cv.yaml", "anschreiben": "brief.yaml"}
    file_path = folder / "dossier.yaml"
    file_path.write_text(yaml.safe_dump(file_data, allow_unicode=True), encoding="utf-8")
    return dossier.main([str(file_path), "--build-dir", str(folder / "build"), "--out-dir", str(folder / "out"),
                         *options])
