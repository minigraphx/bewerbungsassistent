"""Show a folder in the file manager of the system."""
import pathlib
import subprocess
from typing import Callable

COMMANDS = {"darwin": ["open"], "win32": ["explorer"]}
TIMEOUT_SECONDS = 30


def reveal(folder: pathlib.Path, platform: str, run: Callable = subprocess.run) -> None:
    """Show a folder in Finder or Explorer (Explorer ends with code 1 even when it worked)."""
    # Imported late: the desktop app imports this module at its start, before it needs the catalog (#418).
    from ui_texts import T
    if not folder.is_dir():
        raise ValueError(T("Der Ordner {ordner} wurde nicht gefunden.", ordner=folder))
    command = COMMANDS.get(platform, ["xdg-open"]) + [str(folder)]
    try:
        run(command, capture_output=True, timeout=TIMEOUT_SECONDS)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ValueError(T("Der Ordner liess sich nicht öffnen: {ordner}", ordner=folder)) from error
