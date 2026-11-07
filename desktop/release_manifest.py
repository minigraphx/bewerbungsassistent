"""Builds the announcement of a release for the update server (MIN-403).

Step `payload` lists version, notes and the SHA-256 sums of the packages; openssl signs the result in the workflow;
step `envelope` joins payload and signature into latest.json, which `updates.py` reads.
Standard library only: the job with the signing key installs nothing of its own.
"""
import base64
import hashlib
import json
import pathlib
import re
import sys

TAG = re.compile(r"^v(\d+\.\d+\.\d+)$")
PACKAGES = {
    "win32": ("Bewerbungsbegleiter-Setup-{}.exe", "SHA256SUMS.txt"),
    "darwin": ("Bewerbungsbegleiter-{}-macOS.zip", "SHA256SUMS-macOS.txt"),
    "linux": ("Bewerbungsbegleiter-{}-x86_64.AppImage", "SHA256SUMS-Linux.txt"),
}
MAX_NOTES = 2000
SIGNATURE_BYTES = 64
USAGE = "usage: release_manifest.py payload <tag> <folder> <notes file> <out> | envelope <payload> <signature> <out>"


class ReleaseError(Exception):
    """The release cannot be announced as it is."""


def _version(tag: str) -> str:
    found = TAG.match(tag)
    if not found:
        raise ReleaseError(f"Kein Versions-Tag: {tag}")
    return found.group(1)


def _listed_sum(sums_file: pathlib.Path, name: str) -> str | None:
    lines = (line.split() for line in sums_file.read_text(encoding="ascii").splitlines())
    return next((parts[0].lower() for parts in lines if len(parts) == 2 and parts[1].lstrip("*") == name), None)


def _package_entry(folder: pathlib.Path, name: str, sums_name: str) -> dict:
    package, sums_file = folder / name, folder / sums_name
    if not package.is_file() or not sums_file.is_file():
        raise ReleaseError(f"Fehlt im Release: {name if not package.is_file() else sums_name}")
    digest = hashlib.sha256(package.read_bytes()).hexdigest()
    if _listed_sum(sums_file, name) != digest:
        raise ReleaseError(f"Prüfsumme passt nicht zu {sums_name}: {name}")
    return {"file": name, "sha256": digest}


def build_payload(tag: str, folder: pathlib.Path, notes: str) -> bytes:
    version = _version(tag)
    packages = {platform: _package_entry(folder, name.format(version), sums_name)
                for platform, (name, sums_name) in PACKAGES.items()}
    return json.dumps({"version": version, "notes": notes[:MAX_NOTES], "packages": packages},
                      ensure_ascii=False, indent=1).encode("utf-8")


def build_envelope(payload: bytes, signature: bytes) -> bytes:
    if len(signature) != SIGNATURE_BYTES:
        raise ReleaseError(f"Signatur hat {len(signature)} statt {SIGNATURE_BYTES} Bytes")
    return json.dumps({"payload": base64.b64encode(payload).decode(), "signature": base64.b64encode(signature).decode()}).encode()


def main(args: list[str]) -> int:
    try:
        match args:
            case ["payload", tag, folder, notes_file, out]:
                notes = pathlib.Path(notes_file).read_text(encoding="utf-8")
                pathlib.Path(out).write_bytes(build_payload(tag, pathlib.Path(folder), notes))
            case ["envelope", payload, signature, out]:
                pathlib.Path(out).write_bytes(build_envelope(pathlib.Path(payload).read_bytes(), pathlib.Path(signature).read_bytes()))
            case _:
                print(USAGE, file=sys.stderr)
                return 2
    except (ReleaseError, OSError, ValueError) as error:
        print(f"Update nicht angekündigt: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
