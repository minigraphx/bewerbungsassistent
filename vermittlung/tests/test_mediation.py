"""The mediation end to end: the app's SDK talks to it, it talks to a simulated Anthropic API."""
import datetime
import json
import pathlib
import sqlite3
import sys
import threading

import anthropic
import httpx2
import pytest

import admin
import config
from limits import ParallelLimiter, RateLimiter
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
        self.message = "busy"
        self.entered = threading.Event()
        self.hold = None  # an Event: the answer waits until it is set

    def __call__(self, request):
        payload = json.loads(request.content)
        self.requests.append(payload)
        self.entered.set()
        if self.hold:
            self.hold.wait(10)
        if self.status != 200:
            kind = "invalid_request_error" if self.status == 400 else "overloaded_error"
            return httpx2.Response(self.status, json={"type": "error", "error": {"type": kind, "message": self.message}})
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
    threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True).start()
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
    ({"model": ["claude-sonnet-5-5"]}, "model not allowed"),
    ({"messages": [{"role": ["user"], "content": "x"}]}, "role and content"),
    ({"messages": [{"role": "user", "content": [
        {"type": "text", "text": "x", "cache_control": {"type": "ephemeral", "ttl": "1h"}}]}]}, "cache_control"),
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


def test_parallel_requests_of_a_person_are_limited(setup):
    setup["server"].mediation.parallel = ParallelLimiter(1)
    setup["fake"].hold = threading.Event()
    client = app_client(setup, access_for(setup))
    running = threading.Thread(target=ask, args=(client,))
    running.start()
    assert setup["fake"].entered.wait(5)

    with pytest.raises(anthropic.RateLimitError) as error:
        ask(client)

    assert int(error.value.response.headers["retry-after"]) > 0
    setup["fake"].hold.set()
    running.join(5)
    assert ask(client).content[0].text == "Hallo"
    assert len(setup["fake"].requests) == 2


def test_a_refused_request_gives_its_parallel_slot_back(setup):
    setup["server"].mediation.parallel = ParallelLimiter(1)
    access = access_for(setup)
    body = {"model": "claude-other", "max_tokens": 100, "messages": [{"role": "user", "content": "x"}]}

    statuses = [raw(setup, "POST", "/v1/messages", body, {"x-api-key": access}).status_code for _ in range(2)]

    assert statuses == [400, 400]


def test_parallel_limit_counts_each_person_alone():
    limiter = ParallelLimiter(1)
    with limiter.slot("T01") as first:
        with limiter.slot("T01") as second, limiter.slot("T02") as other:
            assert (first, second, other) == (True, False, True)
    with limiter.slot("T01") as again:
        assert again


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

    assert "bewerbungsbegleiter://einladung?code=" in invitation
    assert "15.00" in admin.main(["--db", db, "costs"], now)
    assert "PC" in admin.main(["--db", db, "accesses", "T02"], now)
    assert admin.main(["--db", db, "revoke", "T02"], now).startswith("1 ")
    assert "GESPERRT" in admin.main(["--db", db, "accesses", "T02"], now)
    assert "15.00" in admin.main(["--db", db, "costs", "--month", "2026-11"], now)
    with pytest.raises(SystemExit, match="gibt es nicht"):
        admin.main(["--db", db, "budget", "T99", "5"], now)


def test_revoking_a_person_voids_open_invitations(tmp_path):
    db = str(tmp_path / "a.sqlite")
    now = lambda: NOW  # noqa: E731
    open_code = _invited(db, "T04")

    assert "1 offene Einladung" in admin.main(["--db", db, "revoke", "T04"], now)

    with pytest.raises(StoreError):
        Store(db).redeem(open_code, "PC", NOW)
    fresh = Store(db).create_invitation("T04", NOW)
    assert Store(db).redeem(fresh, "PC", NOW).startswith("bwa_")


def test_revoking_one_access_keeps_open_invitations(tmp_path):
    db = str(tmp_path / "a.sqlite")
    now = lambda: NOW  # noqa: E731
    Store(db).redeem(_invited(db, "T05"), "PC", NOW)
    open_code = Store(db).create_invitation("T05", NOW)

    admin.main(["--db", db, "revoke", "T05", "--access", "1"], now)

    assert Store(db).redeem(open_code, "Laptop", NOW).startswith("bwa_")


def test_the_device_name_cannot_carry_control_characters(tmp_path):
    db = str(tmp_path / "a.sqlite")
    Store(db).redeem(_invited(db, "T06"), "PC\x1b[31m\nGESPERRT", NOW)

    assert Store(db).accesses("T06")[0]["device"] == "PC[31mGESPERRT"


def test_config_needs_the_key():
    with pytest.raises(config.ConfigError, match="ANTHROPIC_API_KEY"):
        config.load({})
    assert "sk-x" not in repr(config.load({"ANTHROPIC_API_KEY": "sk-x"}))


def test_refusals_leave_a_reason_for_the_operator_without_contents(setup, caplog):
    caplog.set_level("INFO")
    access = access_for(setup)
    body = {"model": "claude-other", "max_tokens": 100, "messages": [{"role": "user", "content": SECRET_TEXT}]}

    assert raw(setup, "POST", "/v1/messages", body, {"x-api-key": access}).status_code == 400

    assert "model not allowed" in caplog.text and SECRET_TEXT not in caplog.text


def test_a_refusal_cannot_write_extra_lines_into_the_log(setup, caplog):
    caplog.set_level("INFO")
    access = access_for(setup)
    body = {"model": MODEL, "max_tokens": 100, "messages": [{"role": "user", "content": "x"}], "a\nFORGED": 1}

    assert raw(setup, "POST", "/v1/messages", body, {"x-api-key": access}).status_code == 400

    assert "fields not allowed" in caplog.text and "\nFORGED" not in caplog.text


def test_upstream_errors_are_logged_by_type_and_not_by_message(setup, caplog):
    caplog.set_level("INFO")
    setup["fake"].status = 400
    setup["fake"].message = SECRET_TEXT
    access = access_for(setup)
    body = {"model": MODEL, "max_tokens": 100, "messages": [{"role": "user", "content": SECRET_TEXT}]}

    assert raw(setup, "POST", "/v1/messages", body, {"x-api-key": access}).status_code == 400

    assert "invalid_request_error" in caplog.text and SECRET_TEXT not in caplog.text


def _person_with_usage(store, name="T01"):
    from pricing import Usage
    store.add_person(name, 20, NOW)
    token = store.redeem(store.create_invitation(name, NOW), "Mac", NOW)
    store.create_invitation(name, NOW)  # a second code, not redeemed
    access = store.authenticate(token, NOW)
    store.record_usage(access, MODEL, Usage(10, 5, 0, 0), 0.5, 200, "req_1", NOW)
    return access


def _rows(store, table, person):
    column = "name" if table == "people" else "person"
    return store._run(f"SELECT COUNT(*) AS n FROM {table} WHERE {column} = ?", (person,)).fetchone()["n"]


def test_forget_refuses_while_an_access_is_active(tmp_path):
    store = Store(str(tmp_path / "a.sqlite"))
    _person_with_usage(store)
    with pytest.raises(StoreError, match="aktiv"):
        store.forget("T01")
    assert store.spent("T01", "2026-11") == 0.5


def test_forget_removes_everything_of_the_person_and_nobody_else(tmp_path):
    store = Store(str(tmp_path / "a.sqlite"))
    _person_with_usage(store, "T01")
    _person_with_usage(store, "T02")
    store.revoke("T01", NOW)
    removed = store.forget("T01")
    assert removed == {"usage": 1, "accesses": 1, "invitations": 2}
    assert [_rows(store, t, "T01") for t in ("usage", "accesses", "invitations", "people")] == [0, 0, 0, 0]
    assert [_rows(store, t, "T02") for t in ("usage", "accesses", "invitations", "people")] == [1, 1, 2, 1]


def test_forget_unknown_person_is_an_error(tmp_path):
    with pytest.raises(StoreError, match="gibt es nicht"):
        Store(str(tmp_path / "a.sqlite")).forget("T09")


def test_forget_works_for_a_person_who_never_redeemed(tmp_path):
    store = Store(str(tmp_path / "a.sqlite"))
    store.add_person("T01", 20, NOW)
    store.create_invitation("T01", NOW)
    assert store.forget("T01") == {"usage": 0, "accesses": 0, "invitations": 1}


def test_due_lists_people_whose_last_revocation_passed_the_retention(tmp_path):
    store = Store(str(tmp_path / "a.sqlite"))
    for name in ("T01", "T02", "T03"):
        _person_with_usage(store, name)
    store.revoke("T01", NOW)
    store.revoke("T02", NOW + datetime.timedelta(days=5))
    later = NOW + datetime.timedelta(days=30)
    assert [row["person"] for row in store.due_for_deletion(later)] == ["T01"]
    assert [row["person"] for row in store.due_for_deletion(later + datetime.timedelta(days=5))] == ["T01", "T02"]


def test_a_person_with_one_active_access_is_not_due(tmp_path):
    store = Store(str(tmp_path / "a.sqlite"))
    _person_with_usage(store, "T01")
    second = store.create_invitation("T01", NOW)
    store.revoke("T01", NOW)
    store.redeem(second, "Windows", NOW)
    assert store.due_for_deletion(NOW + datetime.timedelta(days=60)) == []


def test_admin_forget_asks_for_yes_before_deleting(tmp_path):
    db, now = str(tmp_path / "a.sqlite"), lambda: NOW
    store = Store(db)
    _person_with_usage(store)
    store.revoke("T01", NOW)
    preview = admin.main(["--db", db, "forget", "T01"], now)
    assert "--yes" in preview and "1 Aufrufe" in preview
    assert store.has_person("T01")
    done = admin.main(["--db", db, "forget", "T01", "--yes"], now)
    assert "gelöscht" in done
    assert not store.has_person("T01")


def test_admin_forget_stops_with_a_message_while_active(tmp_path):
    db = str(tmp_path / "a.sqlite")
    _person_with_usage(Store(db))
    with pytest.raises(SystemExit, match="aktiv"):
        admin.main(["--db", db, "forget", "T01"], lambda: NOW)


def test_admin_due_names_the_people_to_delete(tmp_path):
    db = str(tmp_path / "a.sqlite")
    store = Store(db)
    _person_with_usage(store)
    assert "Niemand" in admin.main(["--db", db, "due"], lambda: NOW)
    store.revoke("T01", NOW)
    assert "T01" in admin.main(["--db", db, "due"], lambda: NOW + datetime.timedelta(days=31))


def test_rate_limiter_lets_go_of_addresses_that_went_quiet():
    moments = iter([0.0, 61.0])
    limiter = RateLimiter(5, clock=lambda: next(moments))
    limiter.acquire("203.0.113.7")
    limiter.acquire("198.51.100.2")
    assert list(limiter._calls) == ["198.51.100.2"]


def _invited(db: str, name: str = "T03") -> str:
    store = Store(db)
    store.add_person(name, 10.0, NOW)
    return store.create_invitation(name, NOW)


def test_the_consent_is_kept_with_the_access_and_shown_to_the_operator(tmp_path):
    db = str(tmp_path / "m.db")
    Store(db).redeem(_invited(db), "PC", NOW, consent="2026-11 lehrstelle")
    assert Store(db).accesses("T03")[0]["consent"] == "2026-11 lehrstelle"
    assert "2026-11 lehrstelle" in admin.main(["--db", db, "accesses", "T03"], lambda: NOW)


@pytest.mark.parametrize("sent", ["<script>", "x" * 41, "Name: Erika Muster"])
def test_only_a_receipt_is_stored_as_consent_never_free_text(tmp_path, sent):
    db = str(tmp_path / "m.db")
    Store(db).redeem(_invited(db), "PC", NOW, consent=sent)
    assert Store(db).accesses("T03")[0]["consent"] == ""


def test_an_existing_database_gets_the_column_and_keeps_its_accesses(tmp_path):
    db = str(tmp_path / "m.db")
    Store(db).redeem(_invited(db), "PC", NOW)
    old = sqlite3.connect(db)
    old.execute("ALTER TABLE accesses DROP COLUMN consent")
    old.commit()
    old.close()
    assert Store(db).accesses("T03")[0]["consent"] == ""
    assert Store(db).accesses("T03")[0]["device"] == "PC"


def test_the_route_passes_the_receipt_on(setup):
    answer = raw(setup, "POST", "/v1/invitations/redeem", {"code": setup["code"], "device": "Laptop", "consent": "2026-11 stelle"})
    assert answer.status_code == 200
    assert setup["store"].accesses("T01")[0]["consent"] == "2026-11 stelle"
