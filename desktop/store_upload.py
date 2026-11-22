"""Checks before a published release uploads the extension to the browser stores (#365).

Step `ready <store>` tells the store's job whether its secrets and variables are set; without them the job ends green
with a notice that names what is missing, never a value. Step `version <tag> <zip>` stops the upload unless the
manifest in the ZIP carries the version of the tag, and prints that version.
Standard library only: the job runs it with the runner's own python3.
"""
import json
import os
import pathlib
import sys
import zipfile
from collections.abc import Mapping
from dataclasses import dataclass

from release_manifest import TAG

SETUP_DOC = "docs/design/erweiterung-einreichen.md"
USAGE = "usage: store_upload.py ready <chrome|edge> | version <tag> <zip>"


@dataclass(frozen=True)
class Store:
    title: str
    secrets: tuple[str, ...]
    variables: tuple[str, ...]

    @property
    def settings(self) -> tuple[str, ...]:
        return (*self.secrets, *self.variables)


STORES = {
    "chrome": Store("Chrome Web Store", ("CHROME_CLIENT_ID", "CHROME_CLIENT_SECRET", "CHROME_REFRESH_TOKEN"),
                    ("CHROME_PUBLISHER_ID", "CHROME_EXTENSION_ID")),
    "edge": Store("Microsoft Edge Add-ons", ("EDGE_CLIENT_ID", "EDGE_API_KEY"), ("EDGE_PRODUCT_ID",)),
}


class UploadError(Exception):
    """The extension must not go to the store as it is."""


def missing_settings(store: Store, environ: Mapping[str, str]) -> list[str]:
    return [name for name in store.settings if not environ.get(name)]


def readiness_notice(store: Store, missing: list[str]) -> str:
    return (f"::notice::Nicht in {store.title} hochgeladen, es fehlt: {' '.join(missing)}. "
            f"Einrichtung in {SETUP_DOC}; danach diesen Lauf neu starten.")


def manifest_version(package: pathlib.Path) -> str:
    try:
        with zipfile.ZipFile(package) as archive:
            manifest = json.loads(archive.read("manifest.json"))
    except KeyError as error:
        raise UploadError(f"manifest.json fehlt in {package.name}") from error
    except (OSError, zipfile.BadZipFile, ValueError) as error:
        raise UploadError(f"{package.name} ist nicht lesbar: {error}") from error
    version = manifest.get("version") if isinstance(manifest, dict) else None
    if not isinstance(version, str):
        raise UploadError(f"manifest.json in {package.name} nennt keine Version")
    return version


def checked_version(tag: str, package: pathlib.Path) -> str:
    found = TAG.match(tag)
    if not found:
        raise UploadError(f"Kein Versions-Tag: '{tag}'")
    version = manifest_version(package)
    if version != found.group(1):
        raise UploadError(f"Das Manifest nennt Version {version}, der Tag {tag}; erweiterung/manifest.json und "
                          "desktop/version.py gemeinsam erhöhen")
    return version


def _ready(store_name: str, environ: Mapping[str, str]) -> int:
    store = STORES[store_name]
    output = environ.get("GITHUB_OUTPUT")
    if not output:
        raise UploadError("GITHUB_OUTPUT fehlt")
    missing = missing_settings(store, environ)
    if missing:
        print(readiness_notice(store, missing))
    with open(output, "a", encoding="utf-8") as file:
        file.write(f"ready={'false' if missing else 'true'}\n")
    return 0


def main(args: list[str], environ: Mapping[str, str] = os.environ) -> int:
    try:
        match args:
            case ["ready", store] if store in STORES:
                return _ready(store, environ)
            case ["version", tag, package]:
                print(checked_version(tag, pathlib.Path(package)))
                return 0
            case _:
                print(USAGE, file=sys.stderr)
                return 2
    except (UploadError, OSError) as error:
        print(f"::error::Erweiterung nicht hochgeladen: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
