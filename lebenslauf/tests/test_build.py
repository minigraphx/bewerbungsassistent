"""Tests für build.py: Build-Ordner und Foto ausserhalb des Repos."""
import json
import pathlib
import shutil

import pytest

import build

BEISPIEL = build.ROOT / "data" / "beispiel.yaml"
FOTO = build.ROOT / "tests" / "foto.jpg"


@pytest.fixture
def daten(tmp_path):
    """Beispieldaten mit Foto in einem Ordner ausserhalb des Repos."""
    ordner = tmp_path / "daten"
    ordner.mkdir()
    text = BEISPIEL.read_text(encoding="utf-8")
    (ordner / "cv.yaml").write_text(text.replace("basics:\n", "basics:\n  image: foto.jpg\n", 1), encoding="utf-8")
    shutil.copyfile(FOTO, ordner / "foto.jpg")
    return ordner


def _dateien(ordner):
    return {p for p in ordner.rglob("*") if p.is_file()} if ordner.exists() else set()


def test_build_dir_ausserhalb_des_repos(daten, tmp_path):
    repo_build = build.ROOT / "build"
    vorher = {p: p.stat().st_mtime for p in _dateien(repo_build)}
    build_dir = tmp_path / "zwischenstand"
    out = tmp_path / "out" / "cv.pdf"

    build.main([str(daten / "cv.yaml"), "--build-dir", str(build_dir), "-o", str(out)])

    assert out.read_bytes().startswith(b"%PDF")
    cv = json.loads((build_dir / "cv.json").read_text(encoding="utf-8"))
    assert cv["basics"]["name"] == "Erika Beispiel"
    assert {p: p.stat().st_mtime for p in _dateien(repo_build)} == vorher


def test_foto_wird_nicht_kopiert(daten, tmp_path):
    build_dir = tmp_path / "zwischenstand"

    build.main([str(daten / "cv.yaml"), "--build-dir", str(build_dir), "-o", str(tmp_path / "cv.pdf")])

    assert not list(build_dir.glob("foto*"))


def test_standard_build_dir_im_modul(tmp_path):
    out = tmp_path / "cv.pdf"

    build.main([str(BEISPIEL), "-o", str(out)])

    assert out.read_bytes().startswith(b"%PDF")
    assert (build.ROOT / "build" / "cv.json").exists()
