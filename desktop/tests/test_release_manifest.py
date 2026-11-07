"""The announcement built while publishing is exactly what the app accepts (MIN-403)."""
import hashlib
import json

import pytest

import release_manifest
import signed_update
import updates
from signed_update import BASE, KEY

EXE, ZIP, IMAGE = b"MZ" + b"x" * 500, b"PK" + b"z" * 500, b"\x7fELF" + b"a" * 500
EXE_NAME, ZIP_NAME = "Bewerbungsbegleiter-Setup-9.2.0.exe", "Bewerbungsbegleiter-9.2.0-macOS.zip"
IMAGE_NAME = "Bewerbungsbegleiter-9.2.0-x86_64.AppImage"


def sum_line(data, name, star=""):
    return f"{hashlib.sha256(data).hexdigest()}  {star}{name}\n"


@pytest.fixture
def folder(tmp_path):
    (tmp_path / EXE_NAME).write_bytes(EXE)
    (tmp_path / ZIP_NAME).write_bytes(ZIP)
    (tmp_path / "SHA256SUMS.txt").write_text(sum_line(EXE, EXE_NAME))
    (tmp_path / "SHA256SUMS-macOS.txt").write_text(sum_line(ZIP, ZIP_NAME))
    (tmp_path / IMAGE_NAME).write_bytes(IMAGE)
    (tmp_path / "SHA256SUMS-Linux.txt").write_text(sum_line(IMAGE, IMAGE_NAME))
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


@pytest.mark.parametrize("missing", [EXE_NAME, ZIP_NAME, IMAGE_NAME, "SHA256SUMS.txt", "SHA256SUMS-macOS.txt", "SHA256SUMS-Linux.txt"])
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
