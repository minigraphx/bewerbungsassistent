"""The extension as a ZIP file to download next to the app packages (#403, G126): python extension_download.py <folder>.

One ZIP serves Chrome and Edge. Unlike the store ZIP (store_package.py), the manifest keeps `key`: without it an unpacked
copy gets an ID derived from its path, and the native host refuses it. Its version is the app version. Next to it lies
a checksum file, as with the app packages. Standard library only: the rollout job checks the ZIP with it.
"""
import base64
import binascii
import hashlib
import json
import pathlib
import sys
import zipfile

import store_package
import version

NAME = "Bewerbungsbegleiter-Erweiterung-{}.zip"
SUMS = "SHA256SUMS-Erweiterung.txt"
# The ID the key in erweiterung/manifest.json gives; native_messaging.EXTENSION_IDS lets it connect (tested).
DEVELOPER_ID = "ghniboofenadplgmdgddmgjaaeeogejn"
ID_LETTERS = str.maketrans("0123456789abcdef", "abcdefghijklmnop")
ID_LENGTH = 32


def extension_id(key: str) -> str:
    """The ID Chrome and Edge give an unpacked extension with this public key."""
    digest = hashlib.sha256(base64.b64decode(key, validate=True)).hexdigest()
    return digest[:ID_LENGTH].translate(ID_LETTERS)


def _check_manifest(manifest: dict, wanted_version: str) -> None:
    key = manifest.get("key")
    if not isinstance(key, str) or not key:
        raise ValueError("Im Manifest der Erweiterung fehlt `key`: Entpackt bekäme sie eine ID, die die App nicht zulässt.")
    try:
        found_id = extension_id(key)
    except (binascii.Error, ValueError):
        found_id = None
    if found_id != DEVELOPER_ID:
        raise ValueError(f"Der Schlüssel `key` ergibt die ID {found_id}, nicht die der Erweiterung ({DEVELOPER_ID}).")
    if manifest.get("version") != wanted_version:
        raise ValueError(f"Die Erweiterung hat die Version {manifest.get('version')}, die App {wanted_version}.")


def check_package(path: pathlib.Path, wanted_version: str) -> None:
    """Refuses a download ZIP that would not connect to the app or belongs to another version."""
    try:
        with zipfile.ZipFile(path) as archive:
            manifest = json.loads(archive.read("manifest.json"))
    except zipfile.BadZipFile as error:
        raise ValueError(f"Keine ZIP-Datei: {path.name}") from error
    except KeyError as error:
        raise ValueError(f"manifest.json fehlt in {path.name}") from error
    if not isinstance(manifest, dict):
        raise ValueError(f"manifest.json in {path.name} ist kein Objekt")
    _check_manifest(manifest, wanted_version)


def build(target_dir: pathlib.Path, wanted_version: str, source: pathlib.Path = store_package.EXTENSION) -> pathlib.Path:
    """Writes the ZIP with the manifest as it is, `key` included, and gives its path."""
    raw = (source / "manifest.json").read_bytes()
    _check_manifest(json.loads(raw), wanted_version)
    return store_package.write_package(target_dir / NAME.format(wanted_version), raw, source)


def write_sums(package: pathlib.Path) -> pathlib.Path:
    sums = package.parent / SUMS
    sums.write_text(f"{hashlib.sha256(package.read_bytes()).hexdigest()}  {package.name}\n", encoding="ascii")
    return sums


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        sys.stderr.write("usage: extension_download.py <folder>\n")
        return 2
    try:
        package = build(pathlib.Path(argv[0]), version.VERSION)
        sums = write_sums(package)
    except (ValueError, OSError) as error:
        sys.stderr.write(f"Erweiterung nicht gebaut: {error}\n")
        return 1
    sys.stdout.write(f"{package}\n{sums}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
