"""Build the Linux app as AppImage from the PyInstaller folder (#73, G5); run by the CI on Ubuntu.

  python desktop/appimage.py dist/Bewerbungsbegleiter dist-linux/Bewerbungsbegleiter-<v>-x86_64.AppImage \\
      --tool appimagetool-x86_64.AppImage --runtime runtime-x86_64

appimagetool and the runtime are pinned with their checksums in .github/workflows/app.yml; without
--runtime-file the tool would fetch an unpinned runtime while building.
"""
import argparse
import os
import pathlib
import shutil
import subprocess
import sys
from typing import Callable

import linux_desktop

PROGRAM = "Bewerbungsbegleiter"
INSIDE = pathlib.Path("usr") / "lib" / "bewerbungsbegleiter"
ICON = pathlib.Path("_internal") / "erweiterung" / "icons" / "icon128.png"
APP_RUN = f"""#!/bin/sh
# Start of the AppImage: the program sits in {INSIDE}; links and the extension pass their arguments.
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/{INSIDE}/{PROGRAM}" "$@"
"""

Run = Callable[..., subprocess.CompletedProcess]


class BuildError(Exception):
    """Something the AppImage needs is missing."""


def build_appdir(dist: pathlib.Path, appdir: pathlib.Path) -> pathlib.Path:
    """Lay out the AppDir: AppRun, menu entry and icon at the root, the program below usr/lib."""
    if not (dist / PROGRAM).is_file():
        raise BuildError(f"{dist / PROGRAM} fehlt: zuerst PyInstaller laufen lassen")
    if appdir.exists():
        shutil.rmtree(appdir)
    shutil.copytree(dist, appdir / INSIDE, symlinks=True)
    run = appdir / "AppRun"
    run.write_text(APP_RUN, encoding="utf-8")
    run.chmod(0o755)
    entry = linux_desktop.desktop_entry(pathlib.Path(PROGRAM))
    (appdir / linux_desktop.DESKTOP_FILE).write_text(entry, encoding="utf-8")
    icon = dist / ICON
    if icon.is_file():
        shutil.copyfile(icon, appdir / f"{linux_desktop.ICON_NAME}.png")
    return appdir


def build(dist: pathlib.Path, out: pathlib.Path, tool: pathlib.Path, runtime: pathlib.Path,
          run: Run = subprocess.run) -> pathlib.Path:
    appdir = build_appdir(dist, out.parent / "AppDir")
    out.parent.mkdir(parents=True, exist_ok=True)
    run([str(tool), "--runtime-file", str(runtime), "--no-appstream", str(appdir), str(out)],
        check=True, env={**os.environ, "ARCH": "x86_64"})
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Baut das AppImage aus dem Ordner von PyInstaller.")
    parser.add_argument("dist", type=pathlib.Path)
    parser.add_argument("out", type=pathlib.Path)
    parser.add_argument("--tool", type=pathlib.Path, required=True)
    parser.add_argument("--runtime", type=pathlib.Path, required=True)
    args = parser.parse_args(argv)
    try:
        print(build(args.dist, args.out, args.tool, args.runtime))
    except (BuildError, subprocess.CalledProcessError, OSError) as error:
        print(f"AppImage nicht gebaut: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
