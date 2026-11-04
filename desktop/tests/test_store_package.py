"""The ZIP file for the browser stores (MIN-352)."""
import json
import shutil
import zipfile

import pytest

import store_package


@pytest.fixture
def source(tmp_path):
    folder = tmp_path / "ext"
    shutil.copytree(store_package.EXTENSION, folder)
    return folder


def names_in(path):
    with zipfile.ZipFile(path) as archive:
        return archive.namelist()


def test_the_manifest_lies_at_the_top_and_has_no_key(source, tmp_path):
    target = store_package.build(tmp_path / "out", source)

    with zipfile.ZipFile(target) as archive:
        manifest = json.loads(archive.read("manifest.json"))
    assert "key" not in manifest
    assert manifest["version"] in target.name
    assert "key" in json.loads((source / "manifest.json").read_text(encoding="utf-8"))  # the source stays as it is


def test_only_what_the_extension_needs_goes_along(source, tmp_path):
    names = names_in(store_package.build(tmp_path / "out", source))

    assert "background.js" in names and "form/filler.js" in names and "icons/icon128.png" in names
    assert not [n for n in names if n.startswith("tests/") or n.endswith(".md")]
    assert names.count("manifest.json") == 1


def test_every_file_the_manifest_names_is_inside(source, tmp_path):
    names = names_in(store_package.build(tmp_path / "out", source))
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))

    wanted = [manifest["background"]["service_worker"], manifest["action"]["default_popup"], *manifest["icons"].values(),
              *(js for script in manifest["content_scripts"] for js in script["js"])]
    assert set(wanted) <= set(names)


def test_a_private_key_stops_the_build(source, tmp_path):
    (source / "schluessel.pem").write_text("geheim", encoding="utf-8")

    with pytest.raises(ValueError, match="privater Schlüssel"):
        store_package.build(tmp_path / "out", source)
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("change, message", [
    ({"description": "x" * 133}, "Beschreibung"),
    ({"icons": {}}, "128"),
    ({"icons": {"128": "icons/fehlt.png"}}, "fehlt"),
])
def test_what_the_stores_refuse_stops_the_build(source, tmp_path, change, message):
    path = source / "manifest.json"
    path.write_text(json.dumps({**json.loads(path.read_text(encoding="utf-8")), **change}), encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        store_package.build(tmp_path / "out", source)


def test_the_same_files_give_the_same_bytes(source, tmp_path):
    first = store_package.build(tmp_path / "a", source).read_bytes()
    second = store_package.build(tmp_path / "b", source).read_bytes()

    assert first == second
