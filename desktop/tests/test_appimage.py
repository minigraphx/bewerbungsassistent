"""Building the AppImage from the PyInstaller folder (#73, G5)."""
import os
import pathlib
import subprocess

import pytest

import appimage


@pytest.fixture
def dist(tmp_path):
    folder = tmp_path / "dist" / "Bewerbungsbegleiter"
    (folder / "_internal" / "erweiterung" / "icons").mkdir(parents=True)
    (folder / "Bewerbungsbegleiter").write_bytes(b"\x7fELF")
    (folder / "_internal" / "erweiterung" / "icons" / "icon128.png").write_bytes(b"\x89PNG")
    return folder


def test_appdir_starts_the_program_with_all_arguments(dist, tmp_path):
    appdir = appimage.build_appdir(dist, tmp_path / "AppDir")

    run = appdir / "AppRun"
    assert os.access(run, os.X_OK)
    assert run.read_text(encoding="utf-8").splitlines()[-1] == 'exec "$HERE/usr/lib/bewerbungsbegleiter/Bewerbungsbegleiter" "$@"'
    assert (appdir / "usr" / "lib" / "bewerbungsbegleiter" / "Bewerbungsbegleiter").read_bytes() == b"\x7fELF"


def test_appdir_carries_menu_entry_and_icon_at_its_root(dist, tmp_path):
    appdir = appimage.build_appdir(dist, tmp_path / "AppDir")

    entry = (appdir / "bewerbungsbegleiter.desktop").read_text(encoding="utf-8")
    assert "Icon=bewerbungsbegleiter" in entry and "MimeType=x-scheme-handler/bewerbungsbegleiter;" in entry
    assert (appdir / "bewerbungsbegleiter.png").read_bytes() == b"\x89PNG"


def test_the_program_can_start_after_copying(dist, tmp_path):
    (dist / "Bewerbungsbegleiter").chmod(0o755)

    appdir = appimage.build_appdir(dist, tmp_path / "AppDir")

    assert os.access(appdir / "usr" / "lib" / "bewerbungsbegleiter" / "Bewerbungsbegleiter", os.X_OK)


def test_a_missing_program_stops_the_build(tmp_path):
    (tmp_path / "leer").mkdir()

    with pytest.raises(appimage.BuildError, match="Bewerbungsbegleiter"):
        appimage.build_appdir(tmp_path / "leer", tmp_path / "AppDir")


def test_an_old_appdir_is_replaced(dist, tmp_path):
    old = tmp_path / "AppDir"
    (old / "alt").mkdir(parents=True)

    appimage.build_appdir(dist, old)

    assert not (old / "alt").exists()


def test_the_tool_gets_the_pinned_runtime(dist, tmp_path):
    calls = []

    def run(command, **options):
        calls.append((command, options))
        return subprocess.CompletedProcess(command, 0)

    out = appimage.build(dist, tmp_path / "out" / "B.AppImage", tmp_path / "appimagetool", tmp_path / "runtime", run=run)

    command, options = calls[0]
    assert command[0] == str(tmp_path / "appimagetool")
    assert command[1:3] == ["--runtime-file", str(tmp_path / "runtime")] and command[-1] == str(out)
    assert options["env"]["ARCH"] == "x86_64" and options["check"] is True


def test_build_writes_into_a_fresh_out_folder(dist, tmp_path):
    out = appimage.build(dist, tmp_path / "neu" / "B.AppImage", tmp_path / "tool", tmp_path / "runtime",
                         run=lambda command, **options: subprocess.CompletedProcess(command, 0))

    assert out.parent.is_dir() and out == tmp_path / "neu" / "B.AppImage"
