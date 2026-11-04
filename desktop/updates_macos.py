"""Updates of the macOS app inside the app (MIN-368).

The app downloads the zip of the release, checks its SHA-256 sum, unpacks it in a hidden folder next to itself
and verifies the signature. After the app has quit, a small script swaps old and new and starts the new version.
The old version stays in the hidden folder until the new one confirms its start; without that it comes back.
If it cannot come back, the folder stays, because it then holds the only working version.
The checksum over HTTPS says the package is ours; codesign says it arrived complete (the app is signed ad hoc,
so the signature names no one).
"""
import logging
import os
import pathlib
import shutil
import subprocess
import sys
from typing import Callable

import updates

log = logging.getLogger(__name__)

STAGING = ".Bewerbungsassistent-update"
NEW_APP = "Bewerbungsassistent.app"
INSIDE = pathlib.PurePath("Contents", "MacOS", "Bewerbungsassistent")
STARTED = "gestartet"
SCRIPT = "tausch.sh"
TRANSLOCATED = "/AppTranslocation/"
DITTO = "/usr/bin/ditto"
CODESIGN = "/usr/bin/codesign"
OPEN = "/usr/bin/open"
SHELL = "/bin/sh"
TOOL_TIMEOUT_SECONDS = 300
EXIT_WAIT_SECONDS = 30
START_WAIT_SECONDS = 120
MOVE_FIRST = "Zuerst in den Ordner Programme verschieben, dann geht das Update hier in der App."
NO_APP = "Diese Version lässt sich nicht selbst aktualisieren."

Run = Callable[..., subprocess.CompletedProcess]

# Arguments, not text pasted into the script, so names with spaces or quotes stay harmless.
SWAP_SCRIPT = r'''#!/bin/sh
pid=$1; app=$2; staging=$3; note=$4; version=$5; opener=$6; exit_wait=$7; start_wait=$8
new="$staging/Bewerbungsassistent.app"
old="$staging/Bewerbungsassistent-alt.app"
started="$staging/gestartet"

failed() { printf '%s\n' "$version" > "$note"; }

# mv onto an existing folder would bury the old version inside it, so the place must be free first.
# If anything here does not work, the folder stays: it then holds the only working version.
go_back() {
  failed
  if [ -e "$app" ] && ! mv "$app" "$staging/fehlgeschlagen.app"; then exit 1; fi
  if ! mv "$old" "$app"; then exit 1; fi
  rm -rf "$staging"
  "$opener" "$app"
  exit 1
}

waited=0
while kill -0 "$pid" 2>/dev/null; do
  if [ "$waited" -ge "$exit_wait" ]; then rm -rf "$staging"; exit 1; fi
  sleep 1
  waited=$((waited + 1))
done

if ! mv "$app" "$old"; then failed; rm -rf "$staging"; "$opener" "$app"; exit 1; fi
mv "$new" "$app" || go_back
"$opener" "$app" || go_back

waited=0
while [ ! -e "$started" ]; do
  if [ "$waited" -ge "$start_wait" ]; then go_back; fi
  sleep 1
  waited=$((waited + 1))
done
rm -rf "$staging"
'''


def running_app(executable: str | None = None) -> pathlib.Path | None:
    """The .app around the running program; None when it does not run from such a package."""
    path = pathlib.Path(executable or sys.executable)
    if len(path.parents) < 3 or path.parent.name != "MacOS" or path.parents[1].name != "Contents":
        return None
    return path.parents[2] if path.parents[2].suffix == ".app" else None


def place_problem(app: pathlib.Path | None) -> str | None:
    """Why the app cannot replace itself where it is: a substitute folder of macOS or a folder it may not write."""
    if app is None:
        return NO_APP
    if TRANSLOCATED in str(app):
        return MOVE_FIRST
    return None if os.access(app.parent, os.W_OK | os.X_OK) and os.access(app, os.W_OK) else MOVE_FIRST


def _tool(args: list[str], run: Run, message: str) -> None:
    try:
        result = run(args, capture_output=True, text=True, errors="replace", timeout=TOOL_TIMEOUT_SECONDS)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise updates.UpdateError(message) from error
    if result.returncode != 0:
        log.warning("%s: %s", args[0], (result.stderr or "").strip()[:500])
        raise updates.UpdateError(message)


def _unpack_and_verify(archive: pathlib.Path, staging: pathlib.Path, run: Run) -> None:
    _tool([DITTO, "-x", "-k", str(archive), str(staging)], run, "Die neue Version liess sich nicht entpacken.")
    archive.unlink()
    new = staging / NEW_APP
    if new.is_symlink() or not (new / INSIDE).is_file():
        raise updates.UpdateError("Das Paket ist unvollständig; Update abgebrochen.")
    _tool([CODESIGN, "--verify", "--deep", "--strict", str(new)], run,
          "Die Signatur der neuen Version stimmt nicht; Update abgebrochen.")


def discard(staging: pathlib.Path) -> None:
    shutil.rmtree(staging, ignore_errors=True)


def prepare(update: updates.Update, app: pathlib.Path, fetch: updates.Fetch, run: Run = subprocess.run) -> pathlib.Path:
    """The folder next to the app with the verified new version; nothing stays behind if anything does not match."""
    staging = app.parent / STAGING
    ready = False
    try:
        discard(staging)
        staging.mkdir()
        _unpack_and_verify(updates.download(update, staging, fetch), staging, run)
        ready = True
        return staging
    except OSError as error:
        raise updates.UpdateError("Die neue Version liess sich nicht ablegen. Ist genug Speicherplatz frei?") from error
    finally:
        if not ready:
            discard(staging)


def start_swap(app: pathlib.Path, staging: pathlib.Path, note: pathlib.Path, version: str, pid: int | None = None,
               open_command: str = OPEN, exit_wait: int = EXIT_WAIT_SECONDS, start_wait: int = START_WAIT_SECONDS) -> None:
    """Start the script detached; it outlives this app, which quits right after."""
    script = staging / SCRIPT
    script.write_text(SWAP_SCRIPT, encoding="utf-8")
    subprocess.Popen(  # noqa: S603 (fixed script and tool, values passed as arguments)
        [SHELL, str(script), str(os.getpid() if pid is None else pid), str(app), str(staging), str(note), version,
         open_command, str(exit_wait), str(start_wait)],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True, close_fds=True)


def confirm_started(app: pathlib.Path | None) -> None:
    """Called by each start of the app: tells a waiting swap that this version runs, so the old one can go."""
    if app is None or not (app.parent / STAGING).is_dir():
        return
    try:
        (app.parent / STAGING / STARTED).touch()
    except OSError as error:
        log.warning("Start nach dem Update nicht bestätigt: %s", error)
