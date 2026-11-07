"""The app on Linux as AppImage (#73, G5): stable path, menu entry and invitation link."""
import pathlib
import subprocess

import pytest

import linux_desktop


def done(code=0):
    return subprocess.CompletedProcess([], code, "", "")


def test_the_appimage_file_is_the_path_to_start(tmp_path):
    image = tmp_path / "Bewerbungsbegleiter-x86_64.AppImage"
    image.write_bytes(b"")
    mounted = pathlib.Path("/tmp/.mount_Bewerb123/Bewerbungsbegleiter")

    assert linux_desktop.launch_path(mounted, {"APPIMAGE": str(image)}) == image


@pytest.mark.parametrize("environ", [{}, {"APPIMAGE": ""}, {"APPIMAGE": "/gibt/es/nicht.AppImage"}])
def test_without_an_appimage_the_program_itself_starts(environ):
    program = pathlib.Path("/opt/bewerbungsbegleiter/Bewerbungsbegleiter")

    assert linux_desktop.launch_path(program, environ) == program


def test_the_entry_opens_invitation_links():
    entry = linux_desktop.desktop_entry(pathlib.Path("/home/test/Apps/Bewerbungsbegleiter.AppImage"))

    assert "MimeType=x-scheme-handler/bewerbungsbegleiter;" in entry.splitlines()
    assert 'Exec="/home/test/Apps/Bewerbungsbegleiter.AppImage" %u' in entry.splitlines()
    assert entry.startswith("[Desktop Entry]\n") and "Type=Application" in entry


def test_odd_characters_in_the_path_stay_one_argument():
    entry = linux_desktop.desktop_entry(pathlib.Path('/home/te st/$HOME/50%/"x"/a\\b.AppImage'))

    exec_line = next(line for line in entry.splitlines() if line.startswith("Exec="))
    assert exec_line == 'Exec="/home/te st/\\\\$HOME/50%%/\\\\"x\\\\"/a\\\\\\\\b.AppImage" %u'


def test_registering_writes_entry_and_icon_and_claims_the_scheme(tmp_path):
    icon = tmp_path / "icon128.png"
    icon.write_bytes(b"\x89PNG")
    calls = []
    data_home = tmp_path / "share"

    ok = linux_desktop.register(pathlib.Path("/apps/B.AppImage"), icon, {"XDG_DATA_HOME": str(data_home)},
                                tmp_path / "home", run=lambda command, **kw: calls.append(command) or done())

    entry = data_home / "applications" / linux_desktop.DESKTOP_FILE
    assert ok and 'Exec="/apps/B.AppImage" %u' in entry.read_text(encoding="utf-8")
    assert (data_home / "icons" / "hicolor" / "128x128" / "apps" / "bewerbungsbegleiter.png").read_bytes() == b"\x89PNG"
    assert ["xdg-mime", "default", linux_desktop.DESKTOP_FILE, "x-scheme-handler/bewerbungsbegleiter"] in calls


def test_without_xdg_data_home_the_entry_goes_to_the_home_folder(tmp_path):
    linux_desktop.register(pathlib.Path("/apps/B.AppImage"), None, {}, tmp_path, run=lambda command, **kw: done())

    assert (tmp_path / ".local" / "share" / "applications" / linux_desktop.DESKTOP_FILE).is_file()


def test_a_moved_appimage_is_found_again(tmp_path):
    environ = {"XDG_DATA_HOME": str(tmp_path)}
    linux_desktop.register(pathlib.Path("/alt/B.AppImage"), None, environ, tmp_path, run=lambda command, **kw: done())
    linux_desktop.register(pathlib.Path("/neu/B.AppImage"), None, environ, tmp_path, run=lambda command, **kw: done())

    text = (tmp_path / "applications" / linux_desktop.DESKTOP_FILE).read_text(encoding="utf-8")
    assert "/neu/B.AppImage" in text and "/alt/" not in text


def test_without_xdg_tools_the_app_still_starts(tmp_path):
    def missing(command, **kw):
        raise FileNotFoundError(command[0])

    ok = linux_desktop.register(pathlib.Path("/apps/B.AppImage"), None, {"XDG_DATA_HOME": str(tmp_path)}, tmp_path, run=missing)

    assert ok is False and (tmp_path / "applications" / linux_desktop.DESKTOP_FILE).is_file()


def test_a_refused_scheme_is_reported(tmp_path):
    ok = linux_desktop.register(pathlib.Path("/apps/B.AppImage"), None, {"XDG_DATA_HOME": str(tmp_path)}, tmp_path,
                                run=lambda command, **kw: done(1 if command[0] == "xdg-mime" else 0))

    assert ok is False
