"""The announcement built while publishing is exactly what the app accepts (MIN-403)."""
import base64
import hashlib
import io
import json
import zipfile

import pytest

import release_manifest
import signed_update
import store_package
import updates
from signed_update import BASE, KEY

EXE, ZIP, IMAGE = b"MZ" + b"x" * 500, b"PK" + b"z" * 500, b"\x7fELF" + b"a" * 500
EXE_NAME, ZIP_NAME = "Bewerbungsbegleiter-Setup-9.2.0.exe", "Bewerbungsbegleiter-9.2.0-macOS.zip"
IMAGE_NAME = "Bewerbungsbegleiter-9.2.0-x86_64.AppImage"
EXTENSION_NAME, EXTENSION_SUMS = "Bewerbungsbegleiter-Erweiterung-9.2.0.zip", "SHA256SUMS-Erweiterung.txt"
# The public key of the developer add-on: it decides the ID an unpacked copy gets.
REAL_KEY = json.loads((store_package.EXTENSION / "manifest.json").read_text(encoding="utf-8"))["key"]


def sum_line(data, name, star=""):
    return f"{hashlib.sha256(data).hexdigest()}  {star}{name}\n"


def invented_extension(**manifest):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("manifest.json", json.dumps({"manifest_version": 3, "name": "Erfunden", **manifest}))
        archive.writestr("background.js", "// erfunden")
    return buffer.getvalue()


def put_extension(folder, data):
    (folder / EXTENSION_NAME).write_bytes(data)
    (folder / EXTENSION_SUMS).write_text(sum_line(data, EXTENSION_NAME))


@pytest.fixture
def folder(tmp_path):
    (tmp_path / EXE_NAME).write_bytes(EXE)
    (tmp_path / ZIP_NAME).write_bytes(ZIP)
    (tmp_path / "SHA256SUMS.txt").write_text(sum_line(EXE, EXE_NAME))
    (tmp_path / "SHA256SUMS-macOS.txt").write_text(sum_line(ZIP, ZIP_NAME))
    (tmp_path / IMAGE_NAME).write_bytes(IMAGE)
    (tmp_path / "SHA256SUMS-Linux.txt").write_text(sum_line(IMAGE, IMAGE_NAME))
    put_extension(tmp_path, invented_extension(version="9.2.0", key=REAL_KEY))
    return tmp_path


def announced_by(payload):
    raw = release_manifest.build_envelope(payload, KEY.sign(payload))
    return signed_update.server(raw=raw, packages={})


@pytest.mark.parametrize("platform, name, data", [("win32", EXE_NAME, EXE), ("darwin", ZIP_NAME, ZIP), ("linux", IMAGE_NAME, IMAGE)],
                         ids=["win32", "darwin", "linux"])
def test_the_app_finds_every_package(folder, platform, name, data):
    payload = release_manifest.build_payload("v9.2.0", folder, "Neu: Updates")

    found = updates.latest(announced_by(payload), platform)

    assert found.version == "9.2.0" and found.notes == "Neu: Updates"
    assert found.installer_url == f"{BASE}/9.2.0/{name}" and found.sha256 == hashlib.sha256(data).hexdigest()


def test_binary_mode_marks_in_the_list_are_understood(folder):
    (folder / "SHA256SUMS.txt").write_text(sum_line(EXE, EXE_NAME, star="*"))

    assert release_manifest.build_payload("v9.2.0", folder, "")


def test_the_announcement_names_the_extension_download_with_its_sum(folder):
    payload = json.loads(release_manifest.build_payload("v9.2.0", folder, ""))

    data = (folder / EXTENSION_NAME).read_bytes()
    assert payload["extension"] == {"file": EXTENSION_NAME, "sha256": hashlib.sha256(data).hexdigest()}
    assert "extension" not in payload["packages"]  # the app never takes it for an update


def test_the_app_still_reads_an_announcement_with_the_extension(folder):
    payload = release_manifest.build_payload("v9.2.0", folder, "")

    assert updates.latest(announced_by(payload), "win32").version == "9.2.0"


@pytest.mark.parametrize("manifest, message", [
    ({"version": "9.2.0"}, "key"),
    ({"version": "9.1.0", "key": REAL_KEY}, "9.1.0"),
    ({"version": "9.2.0", "key": base64.b64encode(b"erfunden").decode()}, "ID"),
], ids=["without key", "other version", "other key"])
def test_an_extension_download_that_would_not_work_is_not_announced(folder, manifest, message):
    put_extension(folder, invented_extension(**manifest))

    with pytest.raises(release_manifest.ReleaseError, match=message):
        release_manifest.build_payload("v9.2.0", folder, "")


def test_an_extension_download_that_differs_from_its_list_is_not_announced(folder):
    (folder / EXTENSION_NAME).write_bytes(invented_extension(version="9.2.0", key=REAL_KEY, name="Anders"))

    with pytest.raises(release_manifest.ReleaseError, match="Prüfsumme"):
        release_manifest.build_payload("v9.2.0", folder, "")


def test_the_command_line_lists_every_file_that_goes_on_the_server(capsys):
    assert release_manifest.main(["files", "v9.2.0"]) == 0

    assert capsys.readouterr().out.split() == [EXE_NAME, ZIP_NAME, IMAGE_NAME, EXTENSION_NAME]
    assert release_manifest.main(["files", "main"]) == 1


@pytest.mark.parametrize("missing", [EXE_NAME, ZIP_NAME, IMAGE_NAME, EXTENSION_NAME, "SHA256SUMS.txt", "SHA256SUMS-macOS.txt",
                                     "SHA256SUMS-Linux.txt", EXTENSION_SUMS])
def test_a_release_with_a_missing_file_is_not_announced(folder, missing):
    (folder / missing).unlink()

    with pytest.raises(release_manifest.ReleaseError, match="Fehlt"):
        release_manifest.build_payload("v9.2.0", folder, "")


def test_a_package_that_differs_from_its_list_is_not_announced(folder):
    (folder / ZIP_NAME).write_bytes(b"PK anders")

    with pytest.raises(release_manifest.ReleaseError, match="Prüfsumme"):
        release_manifest.build_payload("v9.2.0", folder, "")


def test_a_package_of_another_version_does_not_count(folder):
    with pytest.raises(release_manifest.ReleaseError, match="Fehlt"):
        release_manifest.build_payload("v9.3.0", folder, "")


@pytest.mark.parametrize("tag", ["9.2.0", "v9.2", "v9.2.0-rc1", "main", "v9.2.0; rm -rf /"])
def test_only_version_tags_are_announced(folder, tag):
    with pytest.raises(release_manifest.ReleaseError, match="Versions-Tag"):
        release_manifest.build_payload(tag, folder, "")


def test_long_notes_are_cut_and_umlauts_stay(folder):
    payload = release_manifest.build_payload("v9.2.0", folder, "ä" * 5000)

    notes = json.loads(payload)["notes"]
    assert len(notes) == release_manifest.MAX_NOTES and notes[0] == "ä"


@pytest.mark.parametrize("signature", [b"", b"x" * 63, b"x" * 65])
def test_a_signature_of_the_wrong_length_is_refused(signature):
    with pytest.raises(release_manifest.ReleaseError, match="Signatur"):
        release_manifest.build_envelope(b"{}", signature)


def test_the_command_line_writes_a_file_the_app_accepts(folder, tmp_path):
    notes, payload, signature, out = (tmp_path / name for name in ("notes.md", "payload.json", "payload.sig", "latest.json"))
    notes.write_text("Neu", encoding="utf-8")

    assert release_manifest.main(["payload", "v9.2.0", str(folder), str(notes), str(payload)]) == 0
    signature.write_bytes(KEY.sign(payload.read_bytes()))
    assert release_manifest.main(["envelope", str(payload), str(signature), str(out)]) == 0

    assert updates.latest(signed_update.server(raw=out.read_bytes(), packages={}), "win32").version == "9.2.0"


def test_the_command_line_fails_loudly(folder, tmp_path, capsys):
    assert release_manifest.main(["payload", "kaputt", str(folder), str(tmp_path / "fehlt"), str(tmp_path / "out")]) == 1
    assert "Update nicht angekündigt" in capsys.readouterr().err
    assert release_manifest.main(["unbekannt"]) == 2
