"""The extension as a direct download next to the app packages (#403, G126).

Unlike the store ZIP, the download keeps the manifest `key`: an unpacked copy then gets the ID of the developer add-on,
the one the native host allows. Its version is the app version.
"""
import base64
import hashlib
import json
import shutil
import zipfile

import pytest

import extension_download
import native_messaging
import store_package
import version


@pytest.fixture
def source(tmp_path):
    folder = tmp_path / "ext"
    shutil.copytree(store_package.EXTENSION, folder)
    return folder


def manifest_of(source):
    return json.loads((source / "manifest.json").read_text(encoding="utf-8"))


def change_manifest(source, **change):
    manifest = {key: value for key, value in manifest_of(source).items() if key not in change or change[key] is not None}
    manifest |= {key: value for key, value in change.items() if value is not None}
    (source / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def zipped_manifest(path):
    with zipfile.ZipFile(path) as archive:
        return json.loads(archive.read("manifest.json"))


def test_the_download_keeps_the_key_and_is_named_for_the_app_version(source, tmp_path):
    target = extension_download.build(tmp_path / "out", version.VERSION, source)

    assert target.name == f"Bewerbungsbegleiter-Erweiterung-{version.VERSION}.zip"
    manifest = zipped_manifest(target)
    assert manifest["key"] == manifest_of(source)["key"]
    assert manifest["version"] == version.VERSION


def test_the_key_of_the_real_extension_gives_the_id_the_native_host_allows():
    key = manifest_of(store_package.EXTENSION)["key"]

    assert extension_download.extension_id(key) == extension_download.DEVELOPER_ID
    assert extension_download.DEVELOPER_ID == native_messaging.EXTENSION_IDS[0]


def test_the_download_holds_what_the_extension_needs_and_no_tests(source, tmp_path):
    with zipfile.ZipFile(extension_download.build(tmp_path / "out", version.VERSION, source)) as archive:
        names = archive.namelist()

    assert "background.js" in names and "icons/icon128.png" in names and names.count("manifest.json") == 1
    assert not [name for name in names if name.startswith("tests/") or name.endswith(".md")]


def test_a_source_without_key_is_refused(source, tmp_path):
    change_manifest(source, key=None)

    with pytest.raises(ValueError, match="key"):
        extension_download.build(tmp_path / "out", version.VERSION, source)
    assert not (tmp_path / "out").exists()


def test_a_source_of_another_version_is_refused(source, tmp_path):
    with pytest.raises(ValueError, match="9.9.9"):
        extension_download.build(tmp_path / "out", "9.9.9", source)
    assert not (tmp_path / "out").exists()


def test_a_key_of_another_extension_is_refused(source, tmp_path):
    change_manifest(source, key=base64.b64encode(b"erfundener schluessel").decode())

    with pytest.raises(ValueError, match="ID"):
        extension_download.build(tmp_path / "out", version.VERSION, source)


def test_a_private_key_stops_the_build(source, tmp_path):
    (source / "schluessel.pem").write_text("erfunden", encoding="utf-8")

    with pytest.raises(ValueError, match="privater Schlüssel"):
        extension_download.build(tmp_path / "out", version.VERSION, source)


def test_the_same_files_give_the_same_bytes(source, tmp_path):
    first = extension_download.build(tmp_path / "a", version.VERSION, source).read_bytes()

    assert extension_download.build(tmp_path / "b", version.VERSION, source).read_bytes() == first


def invented_zip(path, manifest):
    with zipfile.ZipFile(path, "w") as archive:
        if manifest is not None:
            archive.writestr("manifest.json", json.dumps(manifest))
        archive.writestr("background.js", "// erfunden")
    return path


REAL_KEY = manifest_of(store_package.EXTENSION)["key"]


@pytest.mark.parametrize("manifest, message", [
    ({"version": "9.2.0"}, "key"),
    ({"version": "9.3.0", "key": REAL_KEY}, "9.3.0"),
    ({"version": "9.2.0", "key": base64.b64encode(b"erfunden").decode()}, "ID"),
    (None, "manifest.json"),
], ids=["without key", "other version", "other key", "no manifest"])
def test_check_package_refuses_a_zip_that_would_not_work(tmp_path, manifest, message):
    package = invented_zip(tmp_path / "erweiterung.zip", manifest)

    with pytest.raises(ValueError, match=message):
        extension_download.check_package(package, "9.2.0")


def test_check_package_refuses_what_is_no_zip(tmp_path):
    package = tmp_path / "erweiterung.zip"
    package.write_bytes(b"kein zip")

    with pytest.raises(ValueError, match="ZIP"):
        extension_download.check_package(package, "9.2.0")


def test_check_package_takes_a_zip_with_key_and_version(tmp_path):
    package = invented_zip(tmp_path / "erweiterung.zip", {"version": "9.2.0", "key": REAL_KEY})

    extension_download.check_package(package, "9.2.0")


def test_the_command_line_writes_the_zip_and_its_checksum_file(tmp_path, capsys):
    assert extension_download.main([str(tmp_path)]) == 0

    package = tmp_path / extension_download.NAME.format(version.VERSION)
    sums = (tmp_path / extension_download.SUMS).read_text(encoding="ascii")
    assert sums == f"{hashlib.sha256(package.read_bytes()).hexdigest()}  {package.name}\n"
    assert package.name in capsys.readouterr().out


GUIDE = store_package.REPO / "docs" / "installation.md"
GUIDE_HEADING = "#### Erweiterung als ZIP-Datei laden"


def guide_part() -> str:
    text = GUIDE.read_text(encoding="utf-8")
    start = text.index(f"\n{GUIDE_HEADING}\n")
    return text[start:text.index("\n#", start + 1)]


def test_the_guide_explains_the_download_in_its_own_part_outside_any_details():
    text = GUIDE.read_text(encoding="utf-8")
    before = text[:text.index(f"\n{GUIDE_HEADING}\n")]
    part = guide_part()

    assert before.count("<details>") == before.count("</details>") and "<details>" not in part
    assert "entpacken" in part and "**Entwicklermodus**" in part and "**Entpackte Erweiterung laden**" in part
    assert "aktualisiert sich nicht von selbst" in part


def test_the_updates_sentence_names_only_the_folder_the_app_opens():
    text = GUIDE.read_text(encoding="utf-8")
    updates = text[text.index("\n### Updates\n"):text.index("\n### Mehrere Personen\n")]

    assert "Haben Sie sie von Hand geladen" not in updates
    assert "Haben Sie den Ordner von Hand geladen, den die App öffnet, bringt die App die neue Version mit" in updates
    assert "(#erweiterung-als-zip-datei-laden)" in updates


def test_the_command_line_fails_loudly(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(extension_download.version, "VERSION", "9.9.9")

    assert extension_download.main([str(tmp_path)]) == 1
    assert "Erweiterung nicht gebaut" in capsys.readouterr().err
    assert not list(tmp_path.iterdir())
