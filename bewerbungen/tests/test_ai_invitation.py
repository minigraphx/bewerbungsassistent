"""Redeeming an invitation of the mediation: the access goes to the keychain, errors are German (MIN-344)."""
import io
import json
import sys
import urllib.error
import urllib.request

import pytest

from ai import invitation
from ai.errors import AiError

URL = "https://ki.example.ch"


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def opener(answer=None, status=None, error=None):
    requests = []

    def open_(request):
        requests.append(request)
        if error is not None:
            raise error
        if status is not None:
            raise urllib.error.HTTPError(request.full_url, status, "x", {}, None)
        return FakeResponse(json.dumps(answer).encode())
    open_.requests = requests
    return open_


def test_redeem_keeps_the_access_and_sends_only_code_system_and_receipt():
    kept = []
    fake = opener({"access": "bwa_geheim"})

    invitation.redeem(URL + "/", " ABCD-EFGH-JKLM-NPQR ", opener=fake, keep=kept.append)

    request = fake.requests[0]
    assert request.full_url == URL + "/v1/invitations/redeem"
    assert set(json.loads(request.data)) == {"code", "device", "consent"} and json.loads(request.data)["code"] == "ABCD-EFGH-JKLM-NPQR"
    assert kept == ["bwa_geheim"]


@pytest.mark.parametrize("status, message", [(400, "Code gilt nicht"), (429, "Zu viele"), (503, "nicht erreichbar")])
def test_redeem_errors(status, message):
    with pytest.raises(AiError, match=message):
        invitation.redeem(URL, "ABCD", opener=opener(status=status), keep=lambda a: None)


def test_offline_and_empty_code(caplog):
    with pytest.raises(AiError, match="Internet"):
        invitation.redeem(URL, "ABCD", opener=opener(error=urllib.error.URLError("down")), keep=lambda a: None)
    assert "down" in caplog.text  # the real cause lands in the log
    with pytest.raises(AiError, match="Code gilt nicht"):
        invitation.redeem(URL, "  ", opener=opener({}), keep=lambda a: None)


def test_keychain_failure_is_explained(monkeypatch):
    import keyring

    def fail(*args):
        raise keyring.errors.NoKeyringError("none")
    monkeypatch.setattr(keyring, "set_password", fail)

    with pytest.raises(AiError, match="Schlüsselbund"):
        invitation.redeem(URL, "ABCD", opener=opener({"access": "bwa_x"}))


def test_on_linux_the_message_names_the_missing_keychain_service(monkeypatch):
    import keyring

    def fail(*args):
        raise keyring.errors.NoKeyringError("none")
    monkeypatch.setattr(keyring, "set_password", fail)
    monkeypatch.setattr(sys, "platform", "linux")

    with pytest.raises(AiError, match="GNOME-Schlüsselbund oder KWallet"):
        invitation.redeem(URL, "ABCD", opener=opener({"access": "bwa_x"}))


def test_own_key_on_linux_names_the_missing_keychain_service(monkeypatch):
    from ai import connection, own_key
    monkeypatch.setattr(connection, "_keyring", lambda: None)
    monkeypatch.setattr(sys, "platform", "linux")

    with pytest.raises(AiError, match="KWallet"):
        own_key.store("sk-ant-api03-" + "x" * 90)


def test_account_sends_the_access():
    fake = opener({"month": "2026-11", "spent_usd": 0.5, "budget_usd": 20})

    assert invitation.account(URL, "bwa_x", opener=fake)["budget_usd"] == 20
    assert fake.requests[0].get_header("X-api-key") == "bwa_x"


def test_https_uses_the_certificates_of_the_system(monkeypatch):
    """The packed app has no CA file of its own (macOS build): the system's trust store must verify."""
    import truststore

    seen = {}

    def urlopen(request, timeout, context=None):
        seen["context"] = context
        return FakeResponse(b"{}")
    monkeypatch.setattr(invitation.urllib.request, "urlopen", urlopen)

    invitation._open(urllib.request.Request(URL))

    assert isinstance(seen["context"], truststore.SSLContext)
