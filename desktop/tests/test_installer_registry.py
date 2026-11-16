"""The Windows installer removes on uninstall the browser host keys the app writes at runtime (#356)."""
import pathlib
import re

import pytest

import native_messaging

INSTALLER = pathlib.Path(__file__).resolve().parents[1] / "installer.iss"
DEFINE = re.compile(r'^#define\s+(\w+)\s+"([^"]*)"', re.MULTILINE)
PARAMETER = re.compile(r'\s*(\w+):\s*("(?:[^"]|"")*"|[^;]*)\s*(?:;|$)')
# Every name the app has registered its host under: the current one and the one up to 0.2.10.
HOST_NAMES = (native_messaging.HOST_NAME, native_messaging.OLD_HOST_NAME)


def expand(text: str, defines: dict[str, str]) -> str:
    return re.sub(r"\{#(\w+)\}", lambda match: defines[match.group(1)], text)


def registry_entries(script: str) -> list[dict[str, str]]:
    """The [Registry] lines as parameter dicts, with preprocessor constants expanded and quotes removed."""
    defines = dict(DEFINE.findall(script))
    section = re.search(r"^\[Registry\]\n(.*?)(?=^\[|\Z)", script, re.MULTILINE | re.DOTALL).group(1)
    entries = []
    for line in section.splitlines():
        if not line.strip() or line.lstrip().startswith(";"):
            continue
        entry = {}
        for name, value in PARAMETER.findall(line):
            if value.startswith('"'):
                value = value[1:-1].replace('""', '"')
            entry[name.lower()] = expand(value, defines)
        entries.append(entry)
    return entries


def flags(entry: dict[str, str]) -> set[str]:
    return set(entry.get("flags", "").lower().split())


def entries_for(subkey: str) -> list[dict[str, str]]:
    script = INSTALLER.read_text(encoding="utf-8")
    return [entry for entry in registry_entries(script)
            if entry.get("root") == "HKCU" and entry.get("subkey", "").casefold() == subkey.casefold()]


HOST_KEYS = [rf"{parent}\{host}" for parent in native_messaging.WINDOWS_KEYS for host in HOST_NAMES]


@pytest.mark.parametrize("subkey", HOST_KEYS)
def test_every_host_key_the_app_writes_is_deleted_on_uninstall(subkey):
    assert any("uninsdeletekey" in flags(entry) for entry in entries_for(subkey)), subkey


@pytest.mark.parametrize("subkey", HOST_KEYS)
def test_the_installer_itself_writes_nothing_under_a_host_key(subkey):
    for entry in entries_for(subkey):
        assert entry.get("valuetype", "none").lower() == "none"
        assert "dontcreatekey" in flags(entry)
        assert "deletekey" not in flags(entry)


@pytest.mark.parametrize("parent", native_messaging.WINDOWS_KEYS)
def test_the_browsers_own_host_folder_stays(parent):
    for entry in entries_for(parent):
        assert not flags(entry) & {"deletekey", "uninsdeletekey", "uninsdeletekeyifempty"}


def test_the_invitation_link_key_keeps_its_uninstall_deletion():
    entries = entries_for(r"Software\Classes\bewerbungsbegleiter")

    assert any(entry.get("valuename") == "URL Protocol" for entry in entries)
    assert any("uninsdeletekey" in flags(entry) for entry in entries)


def test_the_parser_reads_quoted_values_and_constants():
    script = ('#define Name "app"\n[Registry]\n; comment\n'
              'Root: HKCU; Subkey: "Software\\{#Name}"; ValueType: string; ValueData: """a; b"""; Flags: uninsdeletekey\n'
              '[Run]\n')

    assert registry_entries(script) == [{"root": "HKCU", "subkey": "Software\\app", "valuetype": "string",
                                         "valuedata": '"a; b"', "flags": "uninsdeletekey"}]
