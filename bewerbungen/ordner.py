"""Show a folder in the file manager of the system."""
import pathlib
import subprocess
from typing import Callable

COMMANDS = {"darwin": ["open"], "win32": ["explorer"]}
TIMEOUT_SECONDS = 30


def reveal(folder: pathlib.Path, platform: str, run: Callable = subprocess.run) -> None:
    """Show a folder in Finder or Explorer (Explorer ends with code 1 even when it worked)."""
    if not folder.is_dir():
        raise ValueError(f"Der Ordner {folder} wurde nicht gefunden.")
    command = COMMANDS.get(platform, ["xdg-open"]) + [str(folder)]
    try:
        run(command, capture_output=True, timeout=TIMEOUT_SECONDS)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ValueError(f"Der Ordner liess sich nicht öffnen: {folder}") from error
