"""How the app reaches the AI: through the mediation with the person's access, or directly for development.

Pilot (MIN-344): `BEWERBUNGSASSISTENT_KI_URL` is the mediation (same interface as the Messages API) and the
access comes from the system's keychain (`keyring`, service below) or `BEWERBUNGSASSISTENT_KI_ZUGANG`.
Development: without a mediation URL, the SDK's own `ANTHROPIC_API_KEY` is used. The access is never
logged or shown; it only goes to the SDK.
"""
import dataclasses
import os
import urllib.parse

import anthropic

from ai.errors import NOT_SET_UP, AiError

URL_VARIABLE = "BEWERBUNGSASSISTENT_KI_URL"
ACCESS_VARIABLE = "BEWERBUNGSASSISTENT_KI_ZUGANG"
KEY_VARIABLE = "ANTHROPIC_API_KEY"
KEYRING_SERVICE = "bewerbungsassistent-ki"
KEYRING_ACCOUNT = "zugang"
TIMEOUT_SECONDS = 300.0  # Opus thinks before it writes a letter
MAX_RETRIES = 2
LOCAL_HOST = "127.0.0.1"


@dataclasses.dataclass(frozen=True)
class Connection:
    base_url: str | None
    access: str = dataclasses.field(repr=False)  # never printed, also not in tracebacks of the dataclass

    @property
    def via_mediation(self) -> bool:
        return self.base_url is not None


def _keyring_access() -> str | None:
    try:
        import keyring  # optional; the packaged app brings it (MIN-342)
    except ImportError:
        return None
    try:
        return keyring.get_password(KEYRING_SERVICE, KEYRING_ACCOUNT)
    except Exception:  # noqa: BLE001  (a locked or missing keychain means: not set up)
        return None


def _secure(url: str) -> bool:
    """https, or plain http only to this computer (for tests of the mediation)."""
    try:
        parts = urllib.parse.urlsplit(url)
    except ValueError:
        return False
    if parts.username or parts.password or not parts.hostname:
        return False
    return parts.scheme == "https" or (parts.scheme == "http" and parts.hostname == LOCAL_HOST)


def mediation_url(environ: dict | None = None) -> str | None:
    """Address of the mediation, if one is configured; AiError if it is not safe."""
    env = os.environ if environ is None else environ
    url = (env.get(URL_VARIABLE) or "").strip()
    if not url:
        return None
    if not _secure(url):
        raise AiError("Die Adresse der KI-Vermittlung muss mit https:// beginnen.")
    return url.rstrip("/")


def find_connection(environ: dict | None = None, keyring_access=None) -> Connection:
    """The configured connection; AiError with a German hint if there is none."""
    env = os.environ if environ is None else environ
    url = mediation_url(env)
    if url:
        access = (env.get(ACCESS_VARIABLE) or "").strip() or (keyring_access or _keyring_access)()
        if not access:
            raise AiError(NOT_SET_UP)
        return Connection(url, access)
    key = (env.get(KEY_VARIABLE) or "").strip()
    if not key:
        raise AiError(NOT_SET_UP)
    return Connection(None, key)


def make_client(connection: Connection) -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=connection.access, base_url=connection.base_url,
                               timeout=TIMEOUT_SECONDS, max_retries=MAX_RETRIES)
