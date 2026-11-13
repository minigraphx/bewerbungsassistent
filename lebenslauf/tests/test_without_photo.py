"""Builds without the photo (G62): the person turned off „Im Lebenslauf zeigen“, so new documents carry none."""
import json
import shutil

import pytest
import yaml

import build
from dossier_samples import build_dossier, example_cv

PHOTO = build.ROOT / "tests" / "foto.jpg"
CROP = {"mirror": True, "zoom": 1.5}


@pytest.fixture
def cv_with_photo(tmp_path):
    folder = tmp_path / "daten"
    folder.mkdir()
    cv = example_cv()
    cv["basics"] = {**cv["basics"], "image": "foto.jpg", "x-image": CROP}
    (folder / "cv.yaml").write_text(yaml.safe_dump(cv, allow_unicode=True), encoding="utf-8")
    shutil.copyfile(PHOTO, folder / "foto.jpg")
    return folder / "cv.yaml"


def _built_cv(cv_path, tmp_path, *options) -> dict:
    build_dir = tmp_path / "build"
    build.main([str(cv_path), *options, "--build-dir", str(build_dir), "-o", str(tmp_path / "cv.pdf")])
    return json.loads((build_dir / "cv.json").read_text(encoding="utf-8"))


def test_the_cv_carries_the_photo_by_default(cv_with_photo, tmp_path):
    basics = _built_cv(cv_with_photo, tmp_path)["basics"]

    assert basics["image"].endswith("foto.jpg") and basics["x-image"] == CROP


def test_without_photo_the_cv_has_neither_photo_nor_crop(cv_with_photo, tmp_path):
    basics = _built_cv(cv_with_photo, tmp_path, "--ohne-foto")["basics"]

    assert "image" not in basics and "x-image" not in basics
    assert basics["name"] == example_cv()["basics"]["name"]


def test_without_photo_the_cv_file_stays_as_it_is(cv_with_photo, tmp_path):
    before = cv_with_photo.read_text(encoding="utf-8")

    _built_cv(cv_with_photo, tmp_path, "--ohne-foto")

    assert cv_with_photo.read_text(encoding="utf-8") == before


def test_without_photo_helper_returns_a_new_cv():
    cv = {"basics": {"name": "Erika Beispiel", "image": "foto.jpg", "x-image": CROP}, "work": []}

    result = build.without_photo(cv)

    assert result == {"basics": {"name": "Erika Beispiel"}, "work": []}
    assert cv["basics"]["image"] == "foto.jpg", "the given CV is not changed"


def test_the_dossier_without_photo_has_none_in_any_part(tmp_path):
    shutil.copyfile(PHOTO, tmp_path / "foto.jpg")
    cv = {**example_cv(), "basics": {**example_cv()["basics"], "image": "../foto.jpg"}}

    with_photo = build_dossier(tmp_path / "an", cv=cv)
    without = build_dossier(tmp_path / "aus", "--ohne-foto", cv=cv)

    assert json.loads(with_photo.data.read_text(encoding="utf-8"))["person"]["photo"]
    data = json.loads(without.data.read_text(encoding="utf-8"))
    assert data["person"]["photo"] is None and "image" not in data["cv"]["basics"]
