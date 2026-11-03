"""Where the desktop app keeps its own files, and which data folder it uses (MIN-342).

App files (settings, the address of the running instance, the log) live in the user's app folder:
%APPDATA%\\Bewerbungsassistent on Windows, ~/Library/Application Support/Bewerbungsassistent on macOS.
The data folder is the person's own folder (default: Documents\\Bewerbungsassistent). Nothing secret is
stored here: the access to the AI is in the system's keychain.
"""
import dataclasses
import json
import os
import pathlib
import sys

APP_NAME = "Bewerbungsassistent"
SETTINGS_FILE = "einstellungen.json"
INSTANCE_FILE = "instanz.json"
LOG_FILE = "protokoll.txt"
DEFAULTS_FILE = "voreinstellungen.json"  # written at build time (e.g. address of the mediation), not secret


@dataclasses.dataclass(frozen=True)
class Paths:
    app_dir: pathlib.Path

    @property
    def settings(self) -> pathlib.Path:
        return self.app_dir / SETTINGS_FILE

    @property
    def instance(self) -> pathlib.Path:
        return self.app_dir / INSTANCE_FILE

    @property
    def log(self) -> pathlib.Path:
        return self.app_dir / LOG_FILE


def app_dir(environ: dict | None = None, platform: str = sys.platform,
            home: pathlib.Path | None = None) -> pathlib.Path:
    env = os.environ if environ is None else environ
    home = home or pathlib.Path.home()
    if platform == "win32":
        return pathlib.Path(env.get("APPDATA") or home / "AppData" / "Roaming") / APP_NAME
    if platform == "darwin":
        return home / "Library" / "Application Support" / APP_NAME
    return pathlib.Path(env.get("XDG_CONFIG_HOME") or home / ".config") / APP_NAME.lower()


def documents_dir(platform: str = sys.platform, home: pathlib.Path | None = None) -> pathlib.Path:
    """The person's Documents folder; on Windows as Windows knows it (also when moved to OneDrive)."""
    home = home or pathlib.Path.home()
    if platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes
            buffer = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
            if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buffer) == 0:  # CSIDL_PERSONAL
                return pathlib.Path(buffer.value)
        except (AttributeError, OSError):
            pass
    return home / "Documents"


def load(paths: Paths) -> dict:
    try:
        data = json.loads(paths.settings.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def save(paths: Paths, values: dict) -> dict:
    paths.app_dir.mkdir(parents=True, exist_ok=True)
    temporary = paths.settings.with_suffix(".tmp")
    temporary.write_text(json.dumps(values, ensure_ascii=False, indent=1), encoding="utf-8")
    temporary.replace(paths.settings)
    return values


def data_dir(paths: Paths, default: pathlib.Path) -> pathlib.Path:
    """The chosen data folder; the first time the default, created and remembered."""
    current = load(paths)
    chosen = pathlib.Path(current["datenordner"]) if current.get("datenordner") else default
    chosen.mkdir(parents=True, exist_ok=True)
    if current.get("datenordner") != str(chosen):
        save(paths, {**current, "datenordner": str(chosen)})
    return chosen


def build_defaults(bundle_dir: pathlib.Path) -> dict:
    """Values fixed at build time, e.g. {"ki_url": "https://…"}; empty when missing."""
    try:
        data = json.loads((bundle_dir / DEFAULTS_FILE).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}
