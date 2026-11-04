"""The browser extension as developer add-on (MIN-339): its folder comes with the app.

Until the extension is in the stores, the person loads it once as unpacked extension („Entpackte
Erweiterung laden“). The packaged app copies the folder to its app folder on every start, so the path stays
the same across updates; after an update the extension reloads itself (`erweiterung/lib/reload.js`). From source,
the repo folder is used.
"""
import json
import pathlib
import shutil

from settings import Paths

FOLDER = "erweiterung"


def source(bundle_dir: pathlib.Path, frozen: bool) -> pathlib.Path:
    """The extension in the package (frozen) or in the repo next to desktop/."""
    return bundle_dir / FOLDER if frozen else bundle_dir.parent / FOLDER


def version(folder: pathlib.Path) -> str | None:
    try:
        data = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data.get("version") if isinstance(data, dict) else None


def install(paths: Paths, origin: pathlib.Path, frozen: bool) -> pathlib.Path:
    """Folder the person loads in the browser; replaced only when the version changed."""
    if not frozen:
        return origin
    target = paths.app_dir / FOLDER
    if version(target) == version(origin) and version(target) is not None:
        return target
    fresh = paths.app_dir / f"{FOLDER}.neu"
    shutil.rmtree(fresh, ignore_errors=True)
    shutil.copytree(origin, fresh)
    shutil.rmtree(target, ignore_errors=True)
    fresh.rename(target)
    return target
