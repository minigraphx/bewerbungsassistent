"""The move from the old technical name, up to version 0.2.10 (MIN-395).

The app folder keeps settings and the chosen data folder, so the first start under the new name takes it over.
An old app that is still running gets asked to quit first: the installer starts the new app while the old one may
be open, and on Windows its open log would block the move.
"""
import logging
import os
import pathlib
import shutil
import time
from typing import Callable

import instance
from settings import Paths

log = logging.getLogger(__name__)

OLD_APP_NAME = "Bewerbungsassistent"
STOP_WAIT_SECONDS = 10
STOP_POLL_SECONDS = 0.2


def stop_old_app(old_folder: pathlib.Path) -> None:
    """Ask a running old app to quit and wait for it; if it stays, the start goes on anyway."""
    old_paths = Paths(old_folder)
    running = instance.find(old_paths)
    if running is None:
        return
    instance.ask_to_quit(running)
    for _ in range(int(STOP_WAIT_SECONDS / STOP_POLL_SECONDS)):
        if instance.find(old_paths) is None:
            return
        time.sleep(STOP_POLL_SECONDS)


def _move_or_copy(old: pathlib.Path, new: pathlib.Path) -> bool:
    try:
        os.rename(old, new)
        return True
    except OSError:
        pass
    try:
        shutil.copytree(old, new)  # something still holds a file; the old folder then simply stays
        return True
    except OSError:
        shutil.rmtree(new, ignore_errors=True)
        return False


def adopt_app_folder(new: pathlib.Path, stop_old: Callable[[pathlib.Path], None] | None = None) -> bool:
    """Take over the folder of the old name once. True if that happened; a folder under the new name always wins."""
    old = new.with_name(OLD_APP_NAME.lower() if new.name.islower() else OLD_APP_NAME)
    if new.exists() or not old.is_dir():
        return False
    (stop_old or stop_old_app)(old)
    if not _move_or_copy(old, new):
        return False
    Paths(new).instance.unlink(missing_ok=True)  # the address of the old app, not of this one
    return True
