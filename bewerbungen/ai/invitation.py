"""Redeem an invitation of the mediation and keep the access in the system's keychain (MIN-344).

The code comes from the person who runs the pilot. The app sends it once to the mediation and gets an
access back, which goes straight into the keychain (Windows Credential Manager, macOS Keychain) and is
never shown. `account` reads month, spent and budget for the status line.
"""
import json
import logging
import platform
import ssl
import urllib.error
import urllib.request
from typing import Callable

import truststore

from ai.connection import KEYRING_ACCOUNT, KEYRING_SERVICE, keychain_problem
from ai.errors import ACCESS_DENIED, OFFLINE, AiError

TIMEOUT_SECONDS = 30
REDEEM_PATH = "/v1/invitations/redeem"
ACCOUNT_PATH = "/v1/account"
CODE_INVALID = "Der Code gilt nicht (falsch, schon benutzt oder abgelaufen). Bitte um einen neuen Code."
TOO_MANY = "Zu viele Versuche. Bitte in einer Minute nochmals."
NO_KEYCHAIN = "Der Zugang liess sich nicht im Schlüsselbund des Systems ablegen."

Opener = Callable[[urllib.request.Request], object]
log = logging.getLogger("bewerbungsbegleiter")


def _open(request: urllib.request.Request):
    # The packed app has no CA file of its own; the system's trust store verifies, as in the Anthropic SDK.
    context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    return urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS, context=context)  # noqa: S310 (https checked)


def _call(url: str, opener: Opener, body: dict | None = None, access: str | None = None) -> dict:
    headers = {"content-type": "application/json", **({"x-api-key": access} if access else {})}
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(url, data=data, headers=headers, method="POST" if body is not None else "GET")
    try:
        with opener(request) as response:
            answer = json.loads(response.read())
    except urllib.error.HTTPError as error:
        raise _http_error(error.code) from error
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        log.warning("Vermittlung nicht erreicht (%s): %r", url, error)
        raise AiError(OFFLINE) from error
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise AiError("Die Antwort der Vermittlung liess sich nicht lesen.") from error
    if not isinstance(answer, dict):
        raise AiError("Die Antwort der Vermittlung liess sich nicht lesen.")
    return answer


def _http_error(status: int) -> AiError:
    if status == 400:
        return AiError(CODE_INVALID)
    if status == 401:
        return AiError(ACCESS_DENIED)
    if status == 429:
        return AiError(TOO_MANY)
    return AiError("Die Vermittlung ist gerade nicht erreichbar. Bitte später nochmals.")


def _keep(access: str) -> None:
    try:
        import keyring
        keyring.set_password(KEYRING_SERVICE, KEYRING_ACCOUNT, access)
    except Exception as error:  # noqa: BLE001  (no keychain backend, or access denied)
        raise AiError(keychain_problem(NO_KEYCHAIN)) from error


def redeem(base_url: str, code: str, opener: Opener = _open, keep: Callable[[str], None] = _keep,
           receipt: str = "") -> None:
    """`receipt`: version and kind of the consent (MIN-401), so that the operator can show it; no names."""
    code = (code or "").strip()
    if not code or len(code) > 64:
        raise AiError(CODE_INVALID)
    answer = _call(base_url.rstrip("/") + REDEEM_PATH, opener, {"code": code, "device": platform.system() or "Gerät",
                                                                "consent": receipt})
    access = answer.get("access")
    if not isinstance(access, str) or not access:
        raise AiError("Die Antwort der Vermittlung liess sich nicht lesen.")
    keep(access)


def account(base_url: str, access: str, opener: Opener = _open) -> dict:
    """{"month", "spent_usd", "budget_usd"} of the person."""
    return _call(base_url.rstrip("/") + ACCOUNT_PATH, opener, access=access)
