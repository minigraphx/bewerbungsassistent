"""The link `bewerbungsbegleiter://einladung?code=…` opens the app and redeems the invitation (MIN-342, MIN-344).

On Windows the scheme is registered for the current user (HKCU, no admin rights); the installer does the
same and removes it again on uninstall. On macOS the app bundle declares it (Info.plist), on Linux the menu
entry that the AppImage writes on every start (linux_desktop.py, #73).
"""
import re
import sys
import urllib.parse

SCHEME = "bewerbungsbegleiter"
CODE = re.compile(r"[A-Za-z0-9 -]{4,40}")
REGISTRY_KEY = rf"Software\Classes\{SCHEME}"
SETUP_REQUEST = "ki=einrichten"  # the page opens the window „KI einrichten“ (G60) for an invitation link


def invitation_code(argument: str | None) -> str | None:
    """The code of an invitation link, or None for anything else."""
    if not argument:
        return None
    parts = urllib.parse.urlsplit(argument.strip())
    if parts.scheme != SCHEME or (parts.netloc or parts.path.strip("/")) != "einladung":
        return None
    code = urllib.parse.parse_qs(parts.query).get("code", [""])[-1].strip()
    return code if CODE.fullmatch(code) else None


def register_windows(executable: str) -> bool:
    """Register the scheme for the current user; False if not on Windows or not possible."""
    if sys.platform != "win32":
        return False
    try:
        import winreg
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY) as key:
            winreg.SetValueEx(key, None, 0, winreg.REG_SZ, "URL:Bewerbungsbegleiter")
            winreg.SetValueEx(key, "URL Protocol", 0, winreg.REG_SZ, "")
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY + r"\shell\open\command") as key:
            winreg.SetValueEx(key, None, 0, winreg.REG_SZ, f'"{executable}" "%1"')
        return True
    except OSError:
        return False
