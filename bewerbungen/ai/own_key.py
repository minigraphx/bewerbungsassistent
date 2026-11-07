"""The person's own Claude API key (MIN-348): checked with a small call, kept only in the system's keychain.

Nothing here may let the key out: errors of the SDK and of the keychain can carry it, so they are replaced by
fixed German messages and not chained (`from None`).
"""
import re

import anthropic

from ai import connection
from ai.errors import OFFLINE, AiError, from_sdk

MIN_LENGTH = 20
MAX_LENGTH = 300
KEY_SHAPE = re.compile(r"[!-~]+")  # printable ASCII without spaces: anything else cannot go into a header
CHECK_TIMEOUT_SECONDS = 20.0
NOT_A_KEY = "Das sieht nicht wie ein API-Schlüssel aus. Bitte den ganzen Schlüssel aus der Anthropic Console einfügen."
KEY_REJECTED = "Dieser Schlüssel gilt nicht. Bitte in der Anthropic Console prüfen. Gespeichert wurde nichts."
NO_KEYCHAIN = "Der Schlüsselbund dieses Computers lässt sich gerade nicht nutzen. Bitte nochmals versuchen."


def check_client(key: str) -> anthropic.Anthropic:
    """Client for the check only; replaced in tests."""
    return anthropic.Anthropic(api_key=key, timeout=CHECK_TIMEOUT_SECONDS, max_retries=0)


def _cleaned(value) -> str:
    key = value.strip() if isinstance(value, str) else ""
    if not MIN_LENGTH <= len(key) <= MAX_LENGTH or not KEY_SHAPE.fullmatch(key):
        raise AiError(NOT_A_KEY)
    return key


def _check(key: str) -> None:
    """Listing the models costs nothing and carries no content. It says nothing about the remaining credit."""
    message = None
    try:
        check_client(key).models.list(limit=1)
    except (anthropic.AuthenticationError, anthropic.PermissionDeniedError):
        message = KEY_REJECTED
    except anthropic.APIError as error:
        message = str(from_sdk(error))
    except Exception:  # noqa: BLE001  (whatever it was, its text may hold the key)
        message = OFFLINE
    if message:
        raise AiError(message) from None


def _keychain():
    library = connection._keyring()
    if library is None:
        raise AiError(connection.keychain_problem(NO_KEYCHAIN))
    return library


def store(key: str) -> None:
    """Into the keychain, read back: some keychains accept everything and keep nothing."""
    library = _keychain()
    kept = None
    try:
        library.set_password(connection.KEYRING_SERVICE, connection.OWN_KEY_ACCOUNT, key)
        kept = library.get_password(connection.KEYRING_SERVICE, connection.OWN_KEY_ACCOUNT)
    except Exception:  # noqa: BLE001  (its text may hold the key)
        kept = None
    if kept != key:
        raise AiError(connection.keychain_problem(NO_KEYCHAIN)) from None


def save(value) -> None:
    """Check, then keep. AiError with a message for the person if not."""
    key = _cleaned(value)
    _check(key)
    store(key)


def remove() -> None:
    """Gone for sure afterwards, or AiError: a locked keychain must not look like success."""
    library = _keychain()
    try:
        library.delete_password(connection.KEYRING_SERVICE, connection.OWN_KEY_ACCOUNT)
    except Exception:  # noqa: BLE001  (also raised when there is nothing to delete; the reading below decides)
        pass
    try:
        left = library.get_password(connection.KEYRING_SERVICE, connection.OWN_KEY_ACCOUNT)
    except Exception:  # noqa: BLE001
        raise AiError(connection.keychain_problem(NO_KEYCHAIN)) from None
    if left:
        raise AiError(connection.keychain_problem(NO_KEYCHAIN))
