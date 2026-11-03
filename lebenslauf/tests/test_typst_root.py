"""Typst root across drives: on Windows the app and the data can lie on different drives (C: and D:).

Different drives are simulated by letting `os.path.commonpath` fail the way it does on Windows.
"""
import json

import pytest

import anschreiben
import build
import fotoausschnitt
import typst_root
from test_build import FOTO, daten  # noqa: F401  (daten is a fixture)


@pytest.fixture
def different_drives(monkeypatch):
    def fail(paths):
        raise ValueError("Paths don't have the same drive")

    monkeypatch.setattr(typst_root.os.path, "commonpath", fail)


def test_same_drive_uses_the_common_parent(tmp_path):
    (tmp_path / "themes").mkdir()
    root = typst_root.typst_root(tmp_path / "build", [tmp_path / "themes"])

    assert root.path == tmp_path.resolve() and root.moved == {}
    assert root.typst_path(tmp_path / "themes" / "main.typ") == "/themes/main.typ"


def test_different_drives_copy_themes_and_photo_into_the_build_folder(different_drives, tmp_path):
    themes = tmp_path / "app" / "themes"
    (themes / "a").mkdir(parents=True)
    (themes / "a" / "main.typ").write_text("x", encoding="utf-8")
    photo = tmp_path / "daten" / "foto.jpg"
    photo.parent.mkdir()
    photo.write_bytes(b"jpg")
    build_dir = tmp_path / "build"

    root = typst_root.typst_root(build_dir, [themes, photo, build_dir / "cv.json"])

    assert root.path == build_dir.resolve()
    assert root.locate(themes / "a" / "main.typ").read_text(encoding="utf-8") == "x"
    assert root.locate(photo).read_bytes() == b"jpg"
    assert root.typst_path(build_dir / "cv.json") == "/cv.json"
    assert root.typst_path(photo).startswith(f"/{typst_root.STAGE}/")


def test_cv_with_photo_builds_across_drives(different_drives, daten, tmp_path):  # noqa: F811
    build_dir = tmp_path / "zwischenstand"
    out = tmp_path / "cv.pdf"

    build.main([str(daten / "cv.yaml"), "--build-dir", str(build_dir), "-o", str(out)])

    assert out.read_bytes().startswith(b"%PDF")
    cv = json.loads((build_dir / "cv.json").read_text(encoding="utf-8"))
    assert cv["basics"]["image"].startswith(f"/{typst_root.STAGE}/")


def test_letter_builds_across_drives(different_drives, tmp_path):
    out = tmp_path / "anschreiben.pdf"

    anschreiben.main([str(build.ROOT / "data" / "anschreiben-beispiel.yaml"), "--build-dir", str(tmp_path / "b"),
                      "-o", str(out)])

    assert out.read_bytes().startswith(b"%PDF")


def test_photo_preview_renders_across_drives(different_drives, tmp_path):
    preview = fotoausschnitt.Vorschau(FOTO, tmp_path / "b")

    assert preview.png(fotoausschnitt.STANDARD).startswith(b"\x89PNG")
