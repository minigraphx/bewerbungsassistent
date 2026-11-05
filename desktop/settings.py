"""Where the desktop app keeps its own files, and which data folder it uses (MIN-342).

App files (settings, the address of the running instance, the log) live in the user's app folder:
%APPDATA%\\Bewerbungsassistent on Windows, ~/Library/Application Support/Bewerbungsassistent on macOS.
The data folder is the person's own folder (default: Documents\\Bewerbungsbegleiter). Nothing secret is
stored here: the access to the AI is in the system's keychain.
"""
import dataclasses
import json
import os
import pathlib
import sys

APP_NAME = "Bewerbungsassistent"  # the folder of installed apps: stays, whatever the app is called
SUGGESTED_DATA_FOLDER = "Bewerbungsbegleiter"
SETTINGS_FILE = "einstellungen.json"
INSTANCE_FILE = "instanz.json"
LOG_FILE = "protokoll.txt"
CLAUDE_ACCESS = "claude_zugang"
QUESTIONS_PAGE = "fragen_seite"
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


def claude_access(paths: Paths) -> bool:
    """Whether Claude may use the tools of the app (MIN-377); off until the person has read the notes and said yes."""
    return load(paths).get(CLAUDE_ACCESS) is True


def set_claude_access(paths: Paths, allowed: bool) -> dict:
    return save(paths, {**load(paths), CLAUDE_ACCESS: allowed})


def questions_page(paths: Paths) -> bool:
    """Whether the page „Fragen“ is there (MIN-376); off until Andy decides how it should work, on by hand in the settings file."""
    return load(paths).get(QUESTIONS_PAGE) is True


def chosen_data_dir(paths: Paths) -> pathlib.Path | None:
    """The data folder chosen in the setup; None until the person has chosen one."""
    value = load(paths).get("datenordner")
    return pathlib.Path(value) if isinstance(value, str) and value else None


def remember_data_dir(paths: Paths, folder: pathlib.Path) -> dict:
    return save(paths, {**load(paths), "datenordner": str(folder)})


def build_defaults(bundle_dir: pathlib.Path) -> dict:
    """Values fixed at build time, e.g. {"ki_url": "https://…"}; empty when missing."""
    try:
        data = json.loads((bundle_dir / DEFAULTS_FILE).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}
