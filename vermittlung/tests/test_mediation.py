"""The mediation end to end: the app's SDK talks to it, it talks to a simulated Anthropic API."""
import datetime
import json
import pathlib
import sys
import threading

import anthropic
import httpx2
import pytest

import admin
import config
from limits import RateLimiter
from policy import Policy
from pricing import PRICES_USD
from service import Mediation, Server
from store import Store, StoreError
from upstream import Upstream

NOW = datetime.datetime(2026, 11, 3, 10, 0, tzinfo=datetime.timezone.utc)
SECRET_TEXT = "Erika Beispiel bewirbt sich"
MODEL = "claude-sonnet-5-5"
SSE = "".join(f"event: {e['type']}\ndata: {json.dumps(e)}\n\n" for e in [
    {"type": "message_start", "message": {"id": "msg_1", "type": "message", "role": "assistant", "model": MODEL,
                                          "content": [], "stop_reason": None, "stop_sequence": None,
                                          "usage": {"input_tokens": 100, "output_tokens": 1}}},
    {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
    {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Hallo"}},
    {"type": "content_block_stop", "index": 0},
    {"type": "message_delta", "delta": {"stop_reason": "end_turn", "stop_sequence": None}, "usage": {"output_tokens": 50}},
    {"type": "message_stop"},
]).encode()


class FakeAnthropic:
    def __init__(self):
        self.requests = []
        self.status = 200

    def __call__(self, request):
        payload = json.loads(request.content)
        self.requests.append(payload)
        if self.status != 200:
            return httpx2.Response(self.status, json={"type": "error", "error": {"type": "overloaded_error",
                                                                                  "message": "busy"}})
        if payload.get("stream"):
            return httpx2.Response(200, headers={"content-type": "text/event-stream", "request-id": "req_s"},
                                   content=SSE)
        return httpx2.Response(200, headers={"request-id": "req_j"}, json={
            "id": "msg_1", "type": "message", "role": "assistant", "model": payload["model"],
            "content": [{"type": "text", "text": "Hallo"}], "stop_reason": "end_turn", "stop_sequence": None,
            "usage": {"input_tokens": 1000, "output_tokens": 200, "cache_creation_input_tokens": 0,
                      "cache_read_input_tokens": 0}})


@pytest.fixture
def setup(tmp_path):
    fake = FakeAnthropic()
    upstream = Upstream(anthropic.Anthropic(api_key="sk-upstream", max_retries=0,
                                            http_client=httpx2.Client(transport=httpx2.MockTransport(fake))))
    db = tmp_path / "v.sqlite"
    store = Store(str(db))
    clock = {"now": NOW}
    mediation = Mediation(store=store, upstream=upstream, policy=Policy(max_output_tokens=4000),
                          calls=RateLimiter(3), redeems=RateLimiter(5), now=lambda: clock["now"])
    server = Server(("127.0.0.1", 0), mediation)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    store.add_person("T01", 1.0, NOW)
    code = store.create_invitation("T01", NOW)
    yield {"server": server, "store": store, "fake": fake, "db": db, "code": code, "clock": clock,
           "url": f"http://127.0.0.1:{server.server_address[1]}"}
    server.shutdown()
    server.server_close()


def raw(setup, method, path, body=None, headers=None):
    client = httpx2.Client(base_url=setup["url"])
    return client.request(method, path, json=body, headers=headers or {})


def redeem(setup, code=None):
    return raw(setup, "POST", "/v1/invitations/redeem", {"code": code or setup["code"], "device": "Laptop"})


def app_client(setup, access):
    return anthropic.Anthropic(api_key=access, base_url=setup["url"], max_retries=0)


def ask(client, **extra):
    return client.messages.create(model=MODEL, max_tokens=100, messages=[{"role": "user", "content": SECRET_TEXT}],
                                  **extra)


def access_for(setup):
    return redeem(setup).json()["access"]


def test_invitation_gives_an_access_once(setup):
    first = redeem(setup, setup["code"].lower().replace("-", " "))
    again = redeem(setup)

    assert first.status_code == 200 and first.json()["access"].startswith("bwa_")
    assert again.status_code == 400 and "schon benutzt" in again.json()["error"]["message"]


def test_invitation_holds_45_days_by_default(setup):
    setup["clock"]["now"] = NOW + datetime.timedelta(days=44)

    assert redeem(setup).status_code == 200


def test_old_invitation_is_refused(setup):
    setup["clock"]["now"] = NOW + datetime.timedelta(days=46)

    answer = redeem(setup)
    assert answer.status_code == 400 and "abgelaufen" in answer.json()["error"]["message"]


def invite(db, *options):
    output = admin.main(["--db", db, "invite", "T03", *options], lambda: NOW)
    return output, output.split("Code für T03: ")[1].split("\n")[0]


def test_admin_sets_how_long_a_code_holds_in_days(tmp_path):
    db = str(tmp_path / "a.sqlite")
    output, code = invite(db, "--days", "10")

    assert "Gültig bis 13.11.2026" in output
    with pytest.raises(StoreError):
        Store(db).redeem(code, "PC", NOW + datetime.timedelta(days=11))
    assert Store(db).redeem(code, "PC", NOW + datetime.timedelta(days=9)).startswith("bwa_")


@pytest.mark.parametrize("options, until", [
    ([], "18.12.2026"),                   # 45 days by default
    (["--weeks", "2"], "17.11.2026"),
    (["--months", "2"], "03.01.2027"),    # calendar months
])
def test_admin_validity_in_weeks_and_months(tmp_path, options, until):
    output, _ = invite(str(tmp_path / "a.sqlite"), *options)

    assert f"Gültig bis {until}" in output


def test_month_end_is_kept_in_shorter_months():
    start = datetime.datetime(2027, 1, 31, 12, 0, tzinfo=datetime.timezone.utc)

    assert admin.add_months(start, 1).date() == datetime.date(2027, 2, 28)


@pytest.mark.parametrize("options", [["--days", "0"], ["--days", "-3"], ["--days", "400"], ["--months", "13"]])
def test_admin_refuses_odd_validity(tmp_path, options):
    with pytest.raises(SystemExit, match="Gültigkeit"):
        admin.main(["--db", str(tmp_path / "a.sqlite"), "invite", "T04", *options], lambda: NOW)


def test_only_one_unit_of_validity(tmp_path):
    with pytest.raises(SystemExit):
        admin.main(["--db", str(tmp_path / "a.sqlite"), "invite", "T04", "--days", "3", "--weeks", "1"], lambda: NOW)


def test_app_sdk_works_through_the_mediation_and_costs_are_logged_without_content(setup):
    client = app_client(setup, access_for(setup))

    message = ask(client, system=[{"type": "text", "text": "Kontext", "cache_control": {"type": "ephemeral"}}])

    assert message.content[0].text == "Hallo"
    assert setup["fake"].requests[0]["messages"][0]["content"] == SECRET_TEXT
    assert setup["store"].spent("T01", "2026-11") == pytest.approx((1000 * 2 + 200 * 10) / 1_000_000)
    setup["store"]._db.commit()
    assert SECRET_TEXT.encode() not in setup["db"].read_bytes() and b"Kontext" not in setup["db"].read_bytes()


def test_streaming_passes_through_and_counts_usage(setup):
    client = app_client(setup, access_for(setup))

    with client.messages.stream(model=MODEL, max_tokens=100, messages=[{"role": "user", "content": "x"}]) as stream:
        final = stream.get_final_message()

    assert final.content[0].text == "Hallo" and final.usage.output_tokens == 50
    assert setup["store"].spent("T01", "2026-11") == pytest.approx((100 * 2 + 50 * 10) / 1_000_000)


def test_revoked_access_is_refused(setup):
    client = app_client(setup, access_for(setup))
    setup["store"].revoke("T01", NOW)

    with pytest.raises(anthropic.AuthenticationError):
        ask(client)


def test_used_budget_answers_402(setup):
    client = app_client(setup, access_for(setup))
    setup["store"].set_budget("T01", 0.003)
    ask(client)

    with pytest.raises(anthropic.APIStatusError) as error:
        ask(client)
    assert error.value.status_code == 402


@pytest.mark.parametrize("extra, message", [
    ({"model": "claude-fable-5-1"}, "model not allowed"),
    ({"max_tokens": 4001}, "max_tokens"),
    ({"tools": [{"type": "web_search_20260209", "name": "web_search"}]}, "fields not allowed"),
    ({"messages": [{"role": "user", "content": [{"type": "image", "source": {}}]}]}, "only text"),
])
def test_policy_blocks_other_uses(setup, extra, message):
    access = access_for(setup)
    body = {"model": MODEL, "max_tokens": 100, "messages": [{"role": "user", "content": "x"}], **extra}

    answer = raw(setup, "POST", "/v1/messages", body, {"x-api-key": access})

    assert answer.status_code == 400 and message in answer.json()["error"]["message"]
    assert setup["fake"].requests == []


def test_rate_limit_per_person(setup):
    client = app_client(setup, access_for(setup))
    for _ in range(3):
        ask(client)

    with pytest.raises(anthropic.RateLimitError) as error:
        ask(client)
    assert int(error.value.response.headers["retry-after"]) > 0


def test_upstream_errors_pass_through_without_cost(setup):
    client = app_client(setup, access_for(setup))
    setup["fake"].status = 529

    with pytest.raises(anthropic.APIStatusError) as error:
        ask(client)
    assert error.value.status_code == 529 and setup["store"].spent("T01", "2026-11") == 0


def test_account_shows_month_and_budget(setup):
    access = access_for(setup)

    answer = raw(setup, "GET", "/v1/account", headers={"authorization": f"Bearer {access}"})

    assert answer.json() == {"month": "2026-11", "spent_usd": 0, "budget_usd": 1.0}
    assert raw(setup, "GET", "/v1/account").status_code == 401


def test_redeem_attempts_are_limited(setup):
    statuses = [redeem(setup, "AAAA-BBBB-CCCC-DDDD").status_code for _ in range(6)]

    assert statuses[:5] == [400] * 5 and statuses[5] == 429


def test_invalid_bodies(setup):
    access = access_for(setup)
    client = httpx2.Client(base_url=setup["url"])

    assert client.post("/v1/messages", content=b"{kaputt", headers={"x-api-key": access}).status_code == 400
    assert client.get("/nirgends").status_code == 404
    assert client.get("/health").json() == {"ok": True}


def test_prices_match_the_app():
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "bewerbungen"))
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lebenslauf"))
    from ai.usage import PRICES_USD as APP_PRICES

    assert PRICES_USD == APP_PRICES


def test_admin_commands(tmp_path):
    db = str(tmp_path / "a.sqlite")
    now = lambda: NOW  # noqa: E731

    invitation = admin.main(["--db", db, "invite", "T02", "--budget", "15"], now)
    code = invitation.split("Code für T02: ")[1].split("\n")[0]
    Store(db).redeem(code, "PC", NOW)

    assert "bewerbungsassistent://einladung?code=" in invitation
    assert "15.00" in admin.main(["--db", db, "costs"], now)
    assert "PC" in admin.main(["--db", db, "accesses", "T02"], now)
    assert admin.main(["--db", db, "revoke", "T02"], now).startswith("1 ")
    assert "GESPERRT" in admin.main(["--db", db, "accesses", "T02"], now)
    assert "15.00" in admin.main(["--db", db, "costs", "--month", "2026-11"], now)
    with pytest.raises(SystemExit, match="gibt es nicht"):
        admin.main(["--db", db, "budget", "T99", "5"], now)


def test_config_needs_the_key():
    with pytest.raises(config.ConfigError, match="ANTHROPIC_API_KEY"):
        config.load({})
    assert "sk-x" not in repr(config.load({"ANTHROPIC_API_KEY": "sk-x"}))
