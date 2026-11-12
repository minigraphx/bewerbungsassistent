"""The check script of the MSIX trial (#255): framing like a browser, reading `reg query`, finding the app folder.

The trial itself runs on the CI's Windows runner (.github/workflows/msix-versuch.yml); these parts run anywhere.
Invented paths and values only.
"""
import io
import json
import pathlib
import struct

import pytest

from msix import msix_check


def test_a_message_is_framed_with_its_length_in_four_little_endian_bytes():
    framed = msix_check.frame({"id": 1, "art": "hallo"})
    size = struct.unpack("<I", framed[:4])[0]

    assert size == len(framed) - 4
    assert json.loads(framed[4:]) == {"id": 1, "art": "hallo"}


def test_a_framed_reply_is_read_back_and_a_short_one_is_none():
    reply = {"id": 1, "ok": True, "daten": {"version": "9.9.9", "app": None}}
    framed = msix_check.frame(reply)

    assert msix_check.read_framed(io.BytesIO(framed)) == reply
    assert msix_check.read_framed(io.BytesIO(framed[:3])) is None
    assert msix_check.read_framed(io.BytesIO(framed[:-2])) is None


@pytest.mark.parametrize("output", [
    "\r\nHKEY_CURRENT_USER\\Software\\Google\\Chrome\\NativeMessagingHosts\\bewerbungsbegleiter\r\n"
    "    (Default)    REG_SZ    C:\\Users\\muster\\AppData\\Roaming\\Bewerbungsbegleiter\\native-messaging-host.json\r\n\r\n",
    "HKEY_CURRENT_USER\\Software\\Google\\Chrome\\NativeMessagingHosts\\bewerbungsbegleiter\n"
    "    (Standard)    REG_SZ    C:\\Users\\muster\\AppData\\Roaming\\Bewerbungsbegleiter\\native-messaging-host.json\n",
])
def test_the_default_value_is_read_from_reg_query_in_any_language(output):
    assert msix_check.default_value(output) == (
        "C:\\Users\\muster\\AppData\\Roaming\\Bewerbungsbegleiter\\native-messaging-host.json")


def test_a_key_without_a_value_gives_none():
    assert msix_check.default_value("ERROR: The system was unable to find the specified registry key or value.") is None
    assert msix_check.default_value("HKEY_CURRENT_USER\\Software\\Classes\\x\n    (Default)    REG_SZ    \n") is None


def test_the_command_of_the_link_names_its_program():
    assert msix_check.command_program('"C:\\Programme\\Muster\\Bewerbungsbegleiter.exe" "%1"') == (
        "C:\\Programme\\Muster\\Bewerbungsbegleiter.exe")
    assert msix_check.command_program("C:\\Muster\\app.exe %1") == "C:\\Muster\\app.exe"


def test_the_app_folder_is_looked_for_in_the_real_and_the_package_place(tmp_path):
    roaming, local = tmp_path / "Roaming", tmp_path / "Local"
    places = msix_check.app_places(roaming, local, "Muster_abc123")

    assert places == [roaming / "Bewerbungsbegleiter",
                      local / "Packages" / "Muster_abc123" / "LocalCache" / "Roaming" / "Bewerbungsbegleiter"]


def test_the_running_app_is_found_where_its_instance_file_lies(tmp_path):
    real, packaged = tmp_path / "real", tmp_path / "packaged"
    packaged.mkdir()
    (packaged / "instanz.json").write_text(json.dumps({"port": 4711, "token": "erfunden", "pid": 1}), encoding="utf-8")

    found = msix_check.running_app([real, packaged])

    assert found == (packaged, 4711, "erfunden")
    assert msix_check.running_app([real]) is None


def test_each_result_is_one_line_with_pass_or_fail_and_what_was_seen():
    assert msix_check.Result("registry", True, "Chrome und Edge da").line() == "PASS registry: Chrome und Edge da"
    assert msix_check.Result("host", False, "keine Antwort").line() == "FAIL host: keine Antwort"


def test_the_summary_lists_all_five_checks_in_order():
    results = [msix_check.Result(name, index % 2 == 0, f"seen {index}") for index, name in enumerate(msix_check.CHECKS)]
    summary = msix_check.summary(results)

    assert msix_check.CHECKS == ("registry", "manifest", "host", "link", "claude")
    assert [line.split()[1].rstrip(":") for line in summary.splitlines()[2:]] == list(msix_check.CHECKS)
