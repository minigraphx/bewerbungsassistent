"""The extension as a ZIP file for the browser stores (MIN-352): python store_package.py [target folder].

The stores assign their own ID, so the manifest loses `key`, which only fixes the ID of the developer add-on. Tests and
notes stay out. A private key never goes along: finding one stops the build.
"""
import json
import pathlib
import sys
import zipfile

REPO = pathlib.Path(__file__).resolve().parent.parent
EXTENSION = REPO / "erweiterung"
LEFT_OUT_FOLDERS = {"tests", "__pycache__"}
LEFT_OUT_FILES = {"README.md", ".DS_Store"}
MAX_DESCRIPTION = 132
REQUIRED_ICON = "128"
FIXED_TIME = (1980, 1, 1, 0, 0, 0)  # the same files give the same bytes


def _store_manifest(source: pathlib.Path) -> dict:
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    if len(manifest.get("description", "")) > MAX_DESCRIPTION:
        raise ValueError(f"Die Beschreibung ist länger als {MAX_DESCRIPTION} Zeichen.")
    if REQUIRED_ICON not in manifest.get("icons", {}):
        raise ValueError("Das Symbol mit 128 Pixeln fehlt im Manifest.")
    for icon in manifest["icons"].values():
        if not (source / icon).is_file():
            raise ValueError(f"Das Symbol {icon} fehlt.")
    return {key: value for key, value in manifest.items() if key != "key"}


def _packed_files(source: pathlib.Path) -> list[pathlib.Path]:
    files = sorted(path for path in source.rglob("*") if path.is_file())
    keys = [path.name for path in files if path.suffix == ".pem"]
    if keys:
        raise ValueError(f"Ein privater Schlüssel liegt im Ordner: {', '.join(keys)}")
    return [path for path in files if path.name not in LEFT_OUT_FILES and path.name != "manifest.json"
            and not LEFT_OUT_FOLDERS.intersection(path.relative_to(source).parts)]


def _add(archive: zipfile.ZipFile, name: str, content: bytes) -> None:
    info = zipfile.ZipInfo(name, FIXED_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    archive.writestr(info, content)


def build(target_dir: pathlib.Path, source: pathlib.Path = EXTENSION) -> pathlib.Path:
    """Writes the ZIP file and gives its path; the manifest lies at the top, as the stores ask."""
    manifest = _store_manifest(source)
    files = _packed_files(source)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"bewerbungsassistent-erweiterung-{manifest['version']}.zip"
    with zipfile.ZipFile(target, "w") as archive:
        _add(archive, "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"))
        for path in files:
            _add(archive, path.relative_to(source).as_posix(), path.read_bytes())
    return target


def main(argv: list[str]) -> int:
    target_dir = pathlib.Path(argv[0]) if argv else REPO / "desktop" / "build"
    sys.stdout.write(f"{build(target_dir)}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
