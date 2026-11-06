"""A fake update server with signed announcements, for the tests of the update path (MIN-403)."""
import base64
import hashlib
import json

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

import update_key

SHIPPED_KEY = update_key.PUBLIC_KEY
BASE = "https://updates.example.ch/app"
KEY = Ed25519PrivateKey.generate()
PUBLIC_KEY = base64.b64encode(KEY.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)).decode()
PACKAGE_NAMES = {"win32": "Bewerbungsbegleiter-Setup-{}.exe", "darwin": "Bewerbungsbegleiter-{}-macOS.zip"}


def envelope(payload: bytes, key: Ed25519PrivateKey = KEY) -> bytes:
    return json.dumps({"payload": base64.b64encode(payload).decode(),
                       "signature": base64.b64encode(key.sign(payload)).decode()}).encode()


def announcement(version: str, packages: dict[str, bytes], **extra) -> bytes:
    listed = {platform: {"file": PACKAGE_NAMES[platform].format(version), "sha256": hashlib.sha256(data).hexdigest()}
              for platform, data in packages.items()}
    return json.dumps({"version": version, "notes": "Neu: Updates", "packages": listed, **extra}).encode()


def server(version: str = "9.2.0", packages: dict[str, bytes] | None = None, raw: bytes | None = None):
    """A fetch serving the signed announcement (or `raw` as the file) and the packages."""
    packages = {"win32": b"MZ" + b"x" * 5000} if packages is None else packages
    files = {f"{BASE}/latest.json": envelope(announcement(version, packages)) if raw is None else raw}
    files |= {f"{BASE}/{version}/{PACKAGE_NAMES[platform].format(version)}": data for platform, data in packages.items()}

    def fetch(url: str, limit: int) -> bytes:
        if url not in files:
            raise OSError("not found")
        return files[url]
    return fetch
