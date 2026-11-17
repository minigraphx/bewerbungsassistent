"""The routes that take an invitation code or an own key answer 400 only for a value that is wrong in itself (#350).

Einstellungen ties a 400 to its field, so it clears on the first input there (G97); a mediation or an Anthropic that
cannot be reached, a missing consent and a failing keychain are no input error and stay until «×».
"""
import io
import json
import urllib.error

import anthropic
import httpx2 as httpx
import keyring
import pytest

import routes_ai
from ai import connection, consent, invitation, own_key
from ai.connection import ACCESS_VARIABLE, URL_VARIABLE
from test_app import post, server  # noqa: F401  (server is a fixture)
from test_consent import _consented

pytestmark = pytest.mark.real_consent  # the consent decides whether a code waits

MEDIATION = "https://ki.example.ch"
CODE = "TEST-0000-TEST-0000"  # made up
KEY = "erfundener-schluessel-0123456789-abcdefghij"  # made up, only of the form of a key
BAD_REQUEST, CONFLICT, TOO_MANY, SERVER_ERROR, BAD_GATEWAY, UNAVAILABLE = 400, 409, 429, 500, 502, 503


class Answer(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class Keychain:
    """The system's keychain in memory; `broken` refuses everything, as a locked one does."""

    def __init__(self) -> None:
        self.stored: dict[tuple[str, str], str] = {}
        self.broken = False

    def get_password(self, service: str, account: str) -> str | None:
        if self.broken:
            raise RuntimeError("locked")
        return self.stored.get((service, account))

    def set_password(self, service: str, account: str, value: str) -> None:
        if self.broken:
            raise RuntimeError("locked")
        self.stored[(service, account)] = value

    def delete_password(self, service: str, account: str) -> None:
        if self.broken:
            raise RuntimeError("locked")
        self.stored.pop((service, account), None)


@pytest.fixture
def keychain(monkeypatch):
    fake = Keychain()
    monkeypatch.setattr(connection, "_keyring", lambda: fake)
    monkeypatch.setattr(keyring, "set_password", fake.set_password)
    monkeypatch.setattr(connection, "_keyring_access", lambda: None)
    monkeypatch.delenv(ACCESS_VARIABLE, raising=False)
    return fake


@pytest.fixture
def mediation(monkeypatch, keychain):
    """The mediation as the app reaches it over the network: `answer` is what comes back, or what is raised."""
    monkeypatch.setenv(URL_VARIABLE, MEDIATION)
    state = {"answer": {"access": "bwa_erfunden"}}

    def urlopen(request, timeout=None, context=None):
        answer = state["answer"]
        if isinstance(answer, int):
            raise urllib.error.HTTPError(request.full_url, answer, "x", {}, None)
        if isinstance(answer, BaseException):
            raise answer
        return Answer(answer if isinstance(answer, bytes) else json.dumps(answer).encode())

    monkeypatch.setattr(invitation.urllib.request, "urlopen", urlopen)
    return state


def redeem(server, code=CODE):  # noqa: F811
    return post(server, "/api/ki/einladung", {"code": code})


# the invitation code: 400 only for a code that is wrong in itself


@pytest.mark.parametrize("body", [{}, {"code": 1234}])
def test_a_request_without_a_code_is_refused_as_input(server, mediation, body):  # noqa: F811
    _consented(server)
    assert post(server, "/api/ki/einladung", body)[0] == BAD_REQUEST


@pytest.mark.parametrize("code", ["   ", "X" * 65])
def test_a_code_of_the_wrong_form_is_refused_as_input(server, mediation, code):  # noqa: F811
    _consented(server)
    status, answer = redeem(server, code)
    assert status == BAD_REQUEST and answer["fehler"] == invitation.CODE_INVALID


def test_a_code_the_mediation_does_not_know_is_refused_as_input(server, mediation):  # noqa: F811
    _consented(server)
    mediation["answer"] = 400
    status, answer = redeem(server)
    assert status == BAD_REQUEST and answer["fehler"] == invitation.CODE_INVALID


def test_a_code_that_works_is_redeemed(server, mediation):  # noqa: F811
    _consented(server)
    assert redeem(server)[0] == 200


@pytest.mark.parametrize("failure", [urllib.error.URLError("down"), TimeoutError("slow"), ConnectionResetError("reset")])
def test_an_unreachable_mediation_is_no_input_error(server, mediation, failure):  # noqa: F811
    _consented(server)
    mediation["answer"] = failure
    status, answer = redeem(server)
    assert status == BAD_GATEWAY and "Internet" in answer["fehler"]


@pytest.mark.parametrize("code", [401, 500, 502, 503])
def test_an_error_of_the_mediation_is_no_input_error(server, mediation, code):  # noqa: F811
    _consented(server)
    mediation["answer"] = code
    assert redeem(server)[0] == BAD_GATEWAY


def test_too_many_tries_are_no_input_error(server, mediation):  # noqa: F811
    _consented(server)
    mediation["answer"] = TOO_MANY
    status, answer = redeem(server)
    assert status == BAD_GATEWAY and answer["fehler"] == invitation.TOO_MANY


@pytest.mark.parametrize("answer", [b"<html>", [], {"access": ""}])
def test_an_answer_of_the_mediation_that_cannot_be_read_is_no_input_error(server, mediation, answer):  # noqa: F811
    _consented(server)
    mediation["answer"] = answer
    status, answer = redeem(server)
    assert status == BAD_GATEWAY and "Vermittlung" in answer["fehler"]


def test_a_keychain_that_refuses_the_access_is_an_error_of_this_computer(server, mediation, keychain):  # noqa: F811
    _consented(server)
    keychain.broken = True
    status, answer = redeem(server)
    assert status == SERVER_ERROR and "Schlüsselbund" in answer["fehler"]


def test_an_unexpected_failure_is_an_error_of_the_app(server, mediation):  # noqa: F811
    _consented(server)
    mediation["answer"] = RuntimeError("unexpected")
    assert redeem(server)[0] == SERVER_ERROR


def test_without_a_mediation_in_this_app_the_service_is_unavailable(server, keychain, monkeypatch):  # noqa: F811
    monkeypatch.delenv(URL_VARIABLE, raising=False)
    _consented(server)
    status, answer = redeem(server)
    assert status == UNAVAILABLE and "keine KI-Vermittlung" in answer["fehler"]


def test_a_mediation_address_without_https_is_an_error_of_the_app(server, keychain, monkeypatch):  # noqa: F811
    monkeypatch.setenv(URL_VARIABLE, "http://ki.example.ch")
    _consented(server)
    status, answer = redeem(server)
    assert status == SERVER_ERROR and "https://" in answer["fehler"]


def test_a_code_before_the_consent_waits_and_is_no_input_error(server, mediation):  # noqa: F811
    status, answer = redeem(server)
    assert status == CONFLICT and answer["fehler"] == consent.MISSING
    assert server.kontext.cache[routes_ai.WAITING_CODE] == CODE


# the own key: 400 only for a key that is wrong in itself


@pytest.fixture
def check(monkeypatch):
    """The small call that checks a key; `error` is what it raises."""
    state = {"error": None}

    class Client:
        def __init__(self) -> None:
            self.models = self

        def list(self, **options):
            if state["error"]:
                raise state["error"]
            return []

    monkeypatch.setattr(own_key, "check_client", lambda key: Client())
    return state


def save(server, key=KEY, confirmed=True):  # noqa: F811
    return post(server, "/api/schluessel/speichern", {"schluessel": key, "bestaetigt": confirmed})


def api_error(kind, status: int) -> Exception:
    request = httpx.Request("GET", "https://api.anthropic.com/v1/models")
    return kind("refused", response=httpx.Response(status, request=request), body={})


def test_a_key_without_the_confirmation_is_refused_as_input(server, keychain, check):  # noqa: F811
    assert save(server, confirmed=False)[0] == BAD_REQUEST


@pytest.mark.parametrize("key", ["kurz", "sk-ant mit leerzeichen drin 0123456789", "x" * 301])
def test_what_cannot_be_a_key_is_refused_as_input(server, keychain, check, key):  # noqa: F811
    status, answer = save(server, key)
    assert status == BAD_REQUEST and answer["fehler"] == own_key.NOT_A_KEY


@pytest.mark.parametrize("kind,code", [(anthropic.AuthenticationError, 401), (anthropic.PermissionDeniedError, 403)])
def test_a_key_anthropic_refuses_is_refused_as_input(server, keychain, check, kind, code):  # noqa: F811
    check["error"] = api_error(kind, code)
    status, answer = save(server)
    assert status == BAD_REQUEST and answer["fehler"] == own_key.KEY_REJECTED


def test_a_key_that_works_is_saved(server, keychain, check):  # noqa: F811
    status, answer = save(server)
    assert status == 200 and answer["gesetzt"] is True


@pytest.mark.parametrize("error", [
    anthropic.APIConnectionError(message="down", request=httpx.Request("GET", "https://api.anthropic.com")),
    anthropic.APITimeoutError(request=httpx.Request("GET", "https://api.anthropic.com")),
    api_error(anthropic.InternalServerError, 500),
    api_error(anthropic.RateLimitError, 429),
    RuntimeError("unexpected inside the SDK"),
])
def test_an_anthropic_that_cannot_check_the_key_is_no_input_error(server, keychain, check, error):  # noqa: F811
    check["error"] = error
    status, answer = save(server)
    assert status == BAD_GATEWAY and answer["fehler"] not in (own_key.NOT_A_KEY, own_key.KEY_REJECTED)
    assert keychain.stored == {}


def test_a_keychain_that_refuses_the_key_is_an_error_of_this_computer(server, keychain, check):  # noqa: F811
    keychain.broken = True
    status, answer = save(server)
    assert status == SERVER_ERROR and "Schlüsselbund" in answer["fehler"] and KEY not in str(answer)


def test_removing_from_a_locked_keychain_is_an_error_of_this_computer(server, keychain):  # noqa: F811
    keychain.broken = True
    status, answer = post(server, "/api/schluessel/entfernen", {})
    assert status == SERVER_ERROR and "Schlüsselbund" in answer["fehler"]
