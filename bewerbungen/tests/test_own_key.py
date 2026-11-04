"""The person's own API key (MIN-348): kept only in the keychain, checked before saving, never shown anywhere."""
import json
import logging
import types

import anthropic
import httpx2 as httpx
import pytest

import routes_own_key
from ai import connection, errors, own_key
from ai.errors import AiError
from test_app import get as get_raw, post, server  # noqa: F401  (fixture)

KEY = "sk-ant-erfunden-0123456789-abcdefghij"  # made up, has never worked anywhere


class FakeKeyring:
    """The keychain of the system, in memory."""

    def __init__(self, broken: bool = False, forgetful: bool = False) -> None:
        self.stored: dict[tuple[str, str], str] = {}
        self.broken = broken
        self.forgetful = forgetful

    def get_password(self, service: str, account: str) -> str | None:
        if self.broken:
            raise RuntimeError(f"locked {service}")
        return self.stored.get((service, account))

    def set_password(self, service: str, account: str, value: str) -> None:
        if self.broken:
            raise RuntimeError(f"cannot store {value}")
        if not self.forgetful:
            self.stored[(service, account)] = value

    def delete_password(self, service: str, account: str) -> None:
        if self.broken:
            raise RuntimeError("locked")
        if (service, account) not in self.stored:
            raise RuntimeError("not found")
        del self.stored[(service, account)]


class FakeClient:
    """Accepts or rejects a key like the API; remembers what was called."""

    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[dict] = []
        self.models = types.SimpleNamespace(list=self._list)

    def _list(self, **options) -> list:
        self.calls.append(options)
        if self.error:
            raise self.error
        return []


def get(s, path: str) -> tuple[int, dict]:
    status, _, content = get_raw(s, path)
    return status, json.loads(content)


def api_error(kind, status: int) -> Exception:
    """An error as the SDK raises it, with the key in its text, to prove it never gets out."""
    request = httpx.Request("GET", "https://api.anthropic.com/v1/models")
    return kind(f"rejected {KEY}", response=httpx.Response(status, request=request), body={"key": KEY})


@pytest.fixture
def keychain(monkeypatch):
    fake = FakeKeyring()
    monkeypatch.setattr(connection, "_keyring", lambda: fake)
    return fake


@pytest.fixture
def api(monkeypatch):
    fake = FakeClient()
    monkeypatch.setattr(own_key, "check_client", lambda key: fake)
    return fake


# connection: which way the calls take


def test_own_key_goes_directly_to_the_api_and_wins_over_the_mediation(keychain):
    own_key.store(KEY)
    found = connection.find_connection({connection.URL_VARIABLE: "https://vermittlung.example"},
                                       keyring_access=lambda: "zugang")
    assert found.base_url is None and found.access == KEY and not found.via_mediation


def test_without_own_key_the_mediation_is_used_again(keychain):
    own_key.store(KEY)
    own_key.remove()
    found = connection.find_connection({connection.URL_VARIABLE: "https://vermittlung.example"},
                                       keyring_access=lambda: "zugang")
    assert found.via_mediation and found.access == "zugang"


def test_a_locked_keychain_means_no_own_key(monkeypatch):
    monkeypatch.setattr(connection, "_keyring", lambda: FakeKeyring(broken=True))
    assert connection.own_key() is None


def test_the_key_is_not_in_the_repr_of_a_connection(keychain):
    own_key.store(KEY)
    assert KEY not in repr(connection.find_connection({}))


# format


@pytest.mark.parametrize("value", ["", "   ", "kurz", "sk-ant mit leerzeichen drin 0123456789", "x" * 301, "sk-ant-äöü-0123456789012345",
                                   None, 12])
def test_what_cannot_be_a_key_is_refused_without_a_call(api, keychain, value):
    with pytest.raises(AiError):
        own_key.save(value)
    assert api.calls == [] and keychain.stored == {}


def test_spaces_around_a_pasted_key_do_not_matter(api, keychain):
    own_key.save(f"  {KEY}\n")
    assert connection.own_key() == KEY


# the check before saving


def test_saving_checks_with_a_small_call_without_content(api, keychain):
    own_key.save(KEY)
    assert api.calls == [{"limit": 1}]
    assert connection.own_key() == KEY


@pytest.mark.parametrize("kind,status,word", [(anthropic.AuthenticationError, 401, "gilt nicht"),
                                              (anthropic.PermissionDeniedError, 403, "gilt nicht"),
                                              (anthropic.RateLimitError, 429, "ausgelastet"),
                                              (anthropic.InternalServerError, 500, "Fehler")])
def test_a_refused_check_saves_nothing_and_says_why(api, keychain, kind, status, word):
    api.error = api_error(kind, status)
    with pytest.raises(AiError) as caught:
        own_key.save(KEY)
    assert word in str(caught.value) and KEY not in str(caught.value)
    assert caught.value.__cause__ is None and caught.value.__suppress_context__
    assert keychain.stored == {}


def test_a_check_without_connection_says_so(api, keychain):
    api.error = anthropic.APIConnectionError(message=KEY, request=httpx.Request("GET", "https://api.anthropic.com"))
    with pytest.raises(AiError, match="Internet") as caught:
        own_key.save(KEY)
    assert KEY not in str(caught.value)


def test_the_real_check_client_does_not_wait_or_repeat():
    client = own_key.check_client(KEY)
    assert client.max_retries == 0 and client.timeout == own_key.CHECK_TIMEOUT_SECONDS


# the keychain


def test_a_keychain_that_fails_says_so_without_the_key(api, monkeypatch):
    monkeypatch.setattr(connection, "_keyring", lambda: FakeKeyring(broken=True))
    with pytest.raises(AiError, match="Schlüsselbund") as caught:
        own_key.save(KEY)
    assert KEY not in str(caught.value) and caught.value.__suppress_context__


def test_a_keychain_that_does_not_keep_it_counts_as_failed(api, monkeypatch):
    monkeypatch.setattr(connection, "_keyring", lambda: FakeKeyring(forgetful=True))
    with pytest.raises(AiError, match="Schlüsselbund"):
        own_key.save(KEY)


def test_no_keyring_module_at_all_counts_as_failed(api, monkeypatch):
    monkeypatch.setattr(connection, "_keyring", lambda: None)
    with pytest.raises(AiError, match="Schlüsselbund"):
        own_key.save(KEY)
    assert connection.own_key() is None


def test_removing_twice_is_fine(keychain):
    own_key.store(KEY)
    own_key.remove()
    own_key.remove()
    assert keychain.stored == {}


def test_removing_from_a_locked_keychain_does_not_claim_success(keychain, monkeypatch):
    own_key.store(KEY)
    monkeypatch.setattr(connection, "_keyring", lambda: FakeKeyring(broken=True))
    with pytest.raises(AiError, match="Schlüsselbund"):
        own_key.remove()


def test_the_access_of_the_mediation_stays_when_the_own_key_goes(keychain):
    keychain.stored[(connection.KEYRING_SERVICE, connection.KEYRING_ACCOUNT)] = "zugang"
    own_key.store(KEY)
    own_key.remove()
    assert keychain.stored == {(connection.KEYRING_SERVICE, connection.KEYRING_ACCOUNT): "zugang"}


# routes


def test_status_without_key(server, keychain):
    status, answer = get(server, "/api/schluessel")
    assert status == 200 and answer["gesetzt"] is False
    assert answer["kosten"] == {"monat_usd": 0, "gesamt_usd": 0, "aufrufe": 0}


def test_saving_needs_the_confirmation(server, keychain, api):
    status, answer = post(server, "/api/schluessel/speichern", {"schluessel": KEY})
    assert status == 400 and "bestätigen" in answer["fehler"]
    assert api.calls == [] and keychain.stored == {}


def test_saving_needs_a_real_confirmation(server, keychain, api):
    status, _ = post(server, "/api/schluessel/speichern", {"schluessel": KEY, "bestaetigt": "ja"})
    assert status == 400 and keychain.stored == {}


def test_save_and_remove_through_the_routes(server, keychain, api):
    status, answer = post(server, "/api/schluessel/speichern", {"schluessel": KEY, "bestaetigt": True})
    assert status == 200 and answer["gesetzt"] is True
    assert KEY not in str(answer)
    assert get(server, "/api/schluessel")[1]["gesetzt"] is True
    status, answer = post(server, "/api/schluessel/entfernen", {})
    assert status == 200 and answer["gesetzt"] is False and keychain.stored == {}


def test_costs_come_from_the_local_log(server, keychain):
    log = routes_own_key.UsageLog(server.kontext.daten)
    log.path.parent.mkdir(parents=True, exist_ok=True)
    this_month = server.kontext.heute().strftime("%Y-%m")
    log.path.write_text(f'{{"time":"{this_month}-02T10:00:00","cost_usd":0.5}}\n'
                        '{"time":"2020-01-02T10:00:00","cost_usd":1.25}\n{"time":"2020-01-03T10:00:00","cost_usd":null}\n',
                        encoding="utf-8")
    assert get(server, "/api/schluessel")[1]["kosten"] == {"monat_usd": 0.5, "gesamt_usd": 1.75, "aufrufe": 3}


def test_the_key_appears_in_no_file_answer_or_log(server, keychain, api, caplog, tmp_path):
    caplog.set_level(logging.DEBUG)
    answers = [post(server, "/api/schluessel/speichern", {"schluessel": KEY, "bestaetigt": True}),
               get(server, "/api/schluessel"), get(server, "/api/ki/status")]
    api.error = api_error(anthropic.AuthenticationError, 401)
    answers.append(post(server, "/api/schluessel/speichern", {"schluessel": KEY, "bestaetigt": True}))
    keychain.broken = True
    answers.append(post(server, "/api/schluessel/entfernen", {}))
    assert answers[-2][0] == 400 and answers[-1][0] == 400
    assert KEY not in str(answers)
    assert KEY not in caplog.text
    files = [p for p in tmp_path.rglob("*") if p.is_file()]
    assert all(KEY.encode() not in p.read_bytes() for p in files)


def test_the_extension_cannot_reach_the_key():
    import pathlib
    host = pathlib.Path(__file__).resolve().parents[2] / "desktop" / "native_host.py"
    assert "/api/schluessel" not in host.read_text(encoding="utf-8")


def test_the_page_is_served_and_never_prefills_the_key(server):
    import urllib.request
    url = f"{server.url.rstrip('/')}/einstellungen?t={server.token}"
    with urllib.request.urlopen(url, timeout=10) as response:
        page = response.read().decode()
    assert 'type="password"' in page and 'autocomplete="off"' in page


def test_a_key_without_credit_is_named_as_such():
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    error = anthropic.BadRequestError("Your credit balance is too low to access the Anthropic API.",
                                      response=httpx.Response(400, request=request), body=None)
    assert str(errors.from_sdk(error)) == errors.NO_CREDIT
