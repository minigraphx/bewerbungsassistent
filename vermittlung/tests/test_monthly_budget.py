"""Each access has a budget per calendar month in Swiss time, CHF 5 by default, raisable per person (G98)."""
import datetime
import pathlib
import sqlite3
import sys

import anthropic
import pytest

import admin
import months
import pricing
from pricing import Usage
from store import MAX_BUDGET_CHF, MONTHLY_BUDGET_CHF, Store, StoreError
from test_mediation import MODEL, NOW, access_for, app_client, ask, raw, setup  # noqa: F401  (setup is a fixture)

UTC = datetime.timezone.utc
# 30 November 23:30 in Zurich (UTC+1) is 22:30 UTC; 1 December 00:30 in Zurich is still 30 November in UTC
LAST_HOUR_OF_NOVEMBER = datetime.datetime(2026, 11, 30, 22, 30, tzinfo=UTC)
FIRST_HOUR_OF_DECEMBER = datetime.datetime(2026, 11, 30, 23, 30, tzinfo=UTC)
NEXT_MONTH = NOW + datetime.timedelta(days=40)
MESSAGE = {"model": MODEL, "max_tokens": 10, "messages": [{"role": "user", "content": "Hallo"}]}


def _redeemed(store: Store, name: str = "T05", budget: float | None = None):
    if not store.has_person(name):
        store.add_person(name, NOW)
    code = (store.create_invitation(name, NOW, budget_chf=budget) if budget is not None
            else store.create_invitation(name, NOW))
    return store.authenticate(store.redeem(code, "PC", NOW), NOW)


def _account(setup, token: str) -> dict:
    return raw(setup, "GET", "/v1/account", headers={"authorization": f"Bearer {token}"}).json()


def _call(setup, token: str) -> int:
    return raw(setup, "POST", "/v1/messages", MESSAGE, headers={"x-api-key": token}).status_code


# the month in Swiss time

def test_an_access_has_five_francs_a_month_by_default():
    assert MONTHLY_BUDGET_CHF == 5.0


def test_the_month_turns_at_midnight_in_zurich_not_in_utc():
    assert months.month_of(LAST_HOUR_OF_NOVEMBER) == "2026-11"
    assert months.month_of(FIRST_HOUR_OF_DECEMBER) == "2026-12"
    assert FIRST_HOUR_OF_DECEMBER.strftime("%Y-%m") == "2026-11", "UTC is still in November"


def test_the_month_turns_at_midnight_in_zurich_in_summer_time():
    assert months.month_of(datetime.datetime(2026, 6, 30, 21, 59, tzinfo=UTC)) == "2026-06"
    assert months.month_of(datetime.datetime(2026, 6, 30, 22, 0, tzinfo=UTC)) == "2026-07"


@pytest.mark.parametrize("moment, renewal", [
    (NOW, datetime.date(2026, 12, 1)),
    (FIRST_HOUR_OF_DECEMBER, datetime.date(2027, 1, 1)),
    (datetime.datetime(2027, 2, 14, 12, 0, tzinfo=UTC), datetime.date(2027, 3, 1)),
])
def test_the_budget_renews_on_the_first_of_the_next_month(moment, renewal):
    assert months.renews_on(moment) == renewal


@pytest.mark.parametrize("month", ["2026-13", "2026-1", "26-11", "2026-11%", ""])
def test_a_month_must_be_year_and_month(month):
    with pytest.raises(ValueError):
        months.bounds(month)


def test_spend_counts_only_the_current_month_in_swiss_time(tmp_path):
    store = Store(str(tmp_path / "b.sqlite"))
    access = _redeemed(store)
    store.record_usage(access, MODEL, Usage(10, 5), 3.0, 200, "req_1", LAST_HOUR_OF_NOVEMBER)
    store.record_usage(access, MODEL, Usage(10, 5), 0.5, 200, "req_2", FIRST_HOUR_OF_DECEMBER)

    assert store.spent_chf(access, LAST_HOUR_OF_NOVEMBER) == pytest.approx(3.0)
    assert store.spent_chf(access, FIRST_HOUR_OF_DECEMBER) == pytest.approx(0.5)


def test_nothing_carries_over_into_the_next_month(tmp_path):
    store = Store(str(tmp_path / "b.sqlite"))
    access = _redeemed(store)
    store.record_usage(access, MODEL, Usage(10, 5), 1.0, 200, "req_1", NOW)

    assert store.spent_chf(access, NEXT_MONTH) == 0
    assert store.accesses("T05", NEXT_MONTH)[0]["budget_chf"] == MONTHLY_BUDGET_CHF


# refusing and renewing

def test_a_used_up_month_answers_402_with_its_reason(setup):
    token = access_for(setup)
    access = setup["store"].authenticate(token, NOW)
    setup["store"].record_usage(access, MODEL, Usage(10, 5), MONTHLY_BUDGET_CHF, 200, "req_1", NOW)

    answer = raw(setup, "POST", "/v1/messages", MESSAGE, headers={"x-api-key": token})

    assert answer.status_code == 402
    assert answer.json()["error"]["type"] == "credit_used_up"
    assert setup["fake"].requests == [], "nothing reaches Anthropic"


def test_the_budget_renews_at_midnight_in_zurich(setup):
    token = access_for(setup)
    access = setup["store"].authenticate(token, NOW)
    setup["store"].record_usage(access, MODEL, Usage(10, 5), MONTHLY_BUDGET_CHF, 200, "req_1", LAST_HOUR_OF_NOVEMBER)

    setup["clock"]["now"] = LAST_HOUR_OF_NOVEMBER + datetime.timedelta(minutes=29)
    assert _call(setup, token) == 402, "23:59 in Zurich is still November"

    setup["clock"]["now"] = FIRST_HOUR_OF_DECEMBER
    ask(app_client(setup, token))
    assert len(setup["fake"].requests) == 1


def test_a_used_up_person_may_redeem_another_code_with_its_own_budget(setup):
    first = access_for(setup)
    access = setup["store"].authenticate(first, NOW)
    setup["store"].record_usage(access, MODEL, Usage(10, 5), MONTHLY_BUDGET_CHF, 200, "req_1", NOW)
    setup["code"] = setup["store"].create_invitation("T01", NOW)

    second = access_for(setup)

    assert _call(setup, first) == 402
    assert _call(setup, second) == 200
    assert _account(setup, second)["credit_chf"] == MONTHLY_BUDGET_CHF


# the account endpoint

def test_the_account_shows_budget_spend_month_and_renewal_of_this_month(setup):
    token = access_for(setup)
    access = setup["store"].authenticate(token, NOW)
    setup["store"].record_usage(access, MODEL, Usage(10, 5), 1.25, 200, "req_1", NOW)

    assert _account(setup, token) == {"credit_chf": MONTHLY_BUDGET_CHF, "spent_chf": 1.25,
                                      "monat": "2026-11", "erneuert_am": "2026-12-01"}


def test_the_account_counts_the_month_in_swiss_time(setup):
    token = access_for(setup)
    access = setup["store"].authenticate(token, NOW)
    setup["store"].record_usage(access, MODEL, Usage(10, 5), 2.0, 200, "req_1", LAST_HOUR_OF_NOVEMBER)
    setup["clock"]["now"] = FIRST_HOUR_OF_DECEMBER

    assert _account(setup, token) == {"credit_chf": MONTHLY_BUDGET_CHF, "spent_chf": 0,
                                      "monat": "2026-12", "erneuert_am": "2027-01-01"}


# raising the budget of a person

def test_the_access_takes_the_budget_of_its_code(tmp_path):
    store = Store(str(tmp_path / "b.sqlite"))
    assert _redeemed(store, budget=2.5).budget_chf == 2.5
    assert _redeemed(store, "T06").budget_chf == MONTHLY_BUDGET_CHF


def test_a_raised_budget_lets_the_person_go_on_this_month(setup):
    token = access_for(setup)
    access = setup["store"].authenticate(token, NOW)
    setup["store"].record_usage(access, MODEL, Usage(10, 5), 6.0, 200, "req_1", NOW)
    assert _call(setup, token) == 402

    assert setup["store"].set_budget("T01", 20.0) == {"accesses": 1, "invitations": 0}

    assert _call(setup, token) == 200
    assert _account(setup, token)["credit_chf"] == 20.0


def test_a_raise_reaches_all_active_accesses_and_open_codes_of_the_person_only(tmp_path):
    store = Store(str(tmp_path / "b.sqlite"))
    first, second = _redeemed(store), _redeemed(store)
    _redeemed(store, "T06")
    store.revoke("T05", NOW, first.id)
    code = store.create_invitation("T05", NOW)

    assert store.set_budget("T05", 12.0) == {"accesses": 1, "invitations": 1}

    budgets = {row["id"]: row["budget_chf"] for row in store.accesses("T05", NOW)}
    assert budgets == {first.id: MONTHLY_BUDGET_CHF, second.id: 12.0}
    assert store.authenticate(store.redeem(code, "Mac", NOW), NOW).budget_chf == 12.0
    assert store.accesses("T06", NOW)[0]["budget_chf"] == MONTHLY_BUDGET_CHF


def test_a_raise_for_one_access_leaves_the_others(tmp_path):
    store = Store(str(tmp_path / "b.sqlite"))
    _redeemed(store)
    second = _redeemed(store)

    assert store.set_budget("T05", 8.0, second.id) == {"accesses": 1, "invitations": 0}

    assert [row["budget_chf"] for row in store.accesses("T05", NOW)] == [MONTHLY_BUDGET_CHF, 8.0]


@pytest.mark.parametrize("budget", [-1.0, 0.0, MAX_BUDGET_CHF + 0.01, 1000.0])
def test_odd_budgets_are_refused(tmp_path, budget):
    store = Store(str(tmp_path / "b.sqlite"))
    store.add_person("T05", NOW)
    with pytest.raises(StoreError, match="Budget"):
        store.create_invitation("T05", NOW, budget_chf=budget)
    with pytest.raises(StoreError, match="Budget"):
        store.set_budget("T05", budget)


def test_the_budget_of_an_unknown_person_is_an_error(tmp_path):
    with pytest.raises(StoreError, match="gibt es nicht"):
        Store(str(tmp_path / "b.sqlite")).set_budget("T09", 10.0)


# admin

def test_admin_invites_with_a_monthly_budget(tmp_path):
    db = str(tmp_path / "a.sqlite")
    now = lambda: NOW  # noqa: E731

    default = admin.main(["--db", db, "invite", "T07"], now)
    smaller = admin.main(["--db", db, "invite", "T08", "--budget", "2"], now)

    assert "Budget CHF 5.00 pro Monat" in default
    assert "Budget CHF 2.00 pro Monat" in smaller
    for text in (default, smaller):
        assert "einmalig" not in text and "neuen Code" not in text and "USD" not in text


def test_admin_raises_the_budget_of_a_person(tmp_path):
    db = str(tmp_path / "a.sqlite")
    now = lambda: NOW  # noqa: E731
    invitation = admin.main(["--db", db, "invite", "T07"], now)
    code = invitation.split("Code für T07: ")[1].split("\n")[0]
    Store(db).redeem(code, "PC", NOW)

    answer = admin.main(["--db", db, "budget", "T07", "30"], now)

    assert "CHF 30.00 pro Monat" in answer and "1 Zugang" in answer
    assert "Budget CHF 30.00 pro Monat" in admin.main(["--db", db, "accesses", "T07"], now)
    with pytest.raises(SystemExit, match="Budget"):
        admin.main(["--db", db, "budget", "T07", "500"], now)


def test_admin_lists_budget_and_spend_of_the_month_per_access(tmp_path):
    db = str(tmp_path / "a.sqlite")
    invitation = admin.main(["--db", db, "invite", "T07"], lambda: NOW)
    code = invitation.split("Code für T07: ")[1].split("\n")[0]
    store = Store(db)
    access = store.authenticate(store.redeem(code, "PC", NOW), NOW)
    store.record_usage(access, MODEL, Usage(10, 5), 1.2, 200, "req_1", NOW)

    this_month = admin.main(["--db", db, "accesses", "T07"], lambda: NOW)
    next_month = admin.main(["--db", db, "accesses", "T07"], lambda: NEXT_MONTH)
    costs = admin.main(["--db", db, "costs", "--month", "2026-11"], lambda: NOW)

    assert "Budget CHF 5.00 pro Monat, 2026-11 verbraucht CHF 1.20" in this_month
    assert "2026-12 verbraucht CHF 0.00" in next_month
    assert "1.20 CHF" in costs and "USD" not in costs
    with pytest.raises(SystemExit, match="JJJJ-MM"):
        admin.main(["--db", db, "costs", "--month", "2026-11%"], lambda: NOW)


def test_admin_costs_count_the_month_in_swiss_time(tmp_path):
    db = str(tmp_path / "a.sqlite")
    store = Store(db)
    access = _redeemed(store)
    store.record_usage(access, MODEL, Usage(10, 5), 0.7, 200, "req_1", FIRST_HOUR_OF_DECEMBER)

    assert store.costs("2026-11")[0]["cost_chf"] == 0
    assert store.costs("2026-12")[0]["cost_chf"] == pytest.approx(0.7)
    assert store.spent("T05", "2026-12") == pytest.approx(0.7)


# francs

def test_one_usd_billed_counts_as_one_franc():
    assert pricing.CHF_PER_USD == 1.0
    assert pricing.cost_chf(0.42) == pytest.approx(0.42)


def test_the_app_counts_with_the_same_rate():
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "bewerbungen"))
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lebenslauf"))
    from ai.usage import CHF_PER_USD as APP_RATE

    assert pricing.CHF_PER_USD == APP_RATE


# existing databases

def _g80_database(path: str) -> None:
    """A database as the mediation kept it with the one-time credit of G80: credit and start per access."""
    db = sqlite3.connect(path)
    db.executescript("""
        CREATE TABLE people (name TEXT PRIMARY KEY, created TEXT NOT NULL);
        CREATE TABLE invitations (code_hash TEXT PRIMARY KEY, person TEXT NOT NULL REFERENCES people(name),
            created TEXT NOT NULL, expires TEXT NOT NULL, used TEXT, credit_chf REAL NOT NULL DEFAULT 5.0);
        CREATE TABLE accesses (id INTEGER PRIMARY KEY, token_hash TEXT UNIQUE NOT NULL,
            person TEXT NOT NULL REFERENCES people(name), device TEXT NOT NULL, created TEXT NOT NULL,
            last_used TEXT, revoked TEXT, consent TEXT NOT NULL DEFAULT '',
            credit_chf REAL NOT NULL DEFAULT 5.0, credit_since TEXT NOT NULL DEFAULT '');
        CREATE TABLE usage (id INTEGER PRIMARY KEY, time TEXT NOT NULL, person TEXT NOT NULL,
            access_id INTEGER NOT NULL, model TEXT NOT NULL, input_tokens INTEGER NOT NULL, output_tokens INTEGER NOT NULL,
            cache_creation_input_tokens INTEGER NOT NULL, cache_read_input_tokens INTEGER NOT NULL,
            cost_usd REAL NOT NULL, status INTEGER NOT NULL, request_id TEXT);
        INSERT INTO people VALUES ('T09', '2026-10-01T00:00:00+00:00');
        INSERT INTO accesses (token_hash, person, device, created, credit_chf, credit_since) VALUES
            ('8b4f0d1c', 'T09', 'Mac', '2026-10-01T00:00:00+00:00', 5.0, '2026-10-01T00:00:00+00:00');
        INSERT INTO usage (time, person, access_id, model, input_tokens, output_tokens, cache_creation_input_tokens,
            cache_read_input_tokens, cost_usd, status, request_id)
            VALUES ('2026-10-20T00:00:00+00:00', 'T09', 1, 'claude-sonnet-5-5', 10, 5, 0, 0, 5.0, 200, 'req_old');
    """)
    db.commit()
    db.close()


def _legacy_database(path: str) -> None:
    """A database as the mediation kept it before G80: a monthly budget per person, no credit anywhere."""
    db = sqlite3.connect(path)
    db.executescript("""
        CREATE TABLE people (name TEXT PRIMARY KEY, budget_usd REAL NOT NULL, created TEXT NOT NULL);
        CREATE TABLE invitations (code_hash TEXT PRIMARY KEY, person TEXT NOT NULL REFERENCES people(name),
            created TEXT NOT NULL, expires TEXT NOT NULL, used TEXT);
        CREATE TABLE accesses (id INTEGER PRIMARY KEY, token_hash TEXT UNIQUE NOT NULL,
            person TEXT NOT NULL REFERENCES people(name), device TEXT NOT NULL, created TEXT NOT NULL,
            last_used TEXT, revoked TEXT, consent TEXT NOT NULL DEFAULT '');
        CREATE TABLE usage (id INTEGER PRIMARY KEY, time TEXT NOT NULL, person TEXT NOT NULL,
            access_id INTEGER NOT NULL, model TEXT NOT NULL, input_tokens INTEGER NOT NULL, output_tokens INTEGER NOT NULL,
            cache_creation_input_tokens INTEGER NOT NULL, cache_read_input_tokens INTEGER NOT NULL,
            cost_usd REAL NOT NULL, status INTEGER NOT NULL, request_id TEXT);
        INSERT INTO people VALUES ('T09', 20.0, '2026-10-01T00:00:00+00:00');
        INSERT INTO accesses (token_hash, person, device, created) VALUES
            ('8b4f0d1c', 'T09', 'Mac', '2026-10-01T00:00:00+00:00');
        INSERT INTO usage (time, person, access_id, model, input_tokens, output_tokens, cache_creation_input_tokens,
            cache_read_input_tokens, cost_usd, status, request_id)
            VALUES ('2026-10-20T00:00:00+00:00', 'T09', 1, 'claude-sonnet-5-5', 10, 5, 0, 0, 12.0, 200, 'req_old');
    """)
    db.commit()
    db.close()


@pytest.mark.parametrize("build", [_g80_database, _legacy_database])
def test_an_existing_access_keeps_working_with_the_default_budget(tmp_path, build):
    db = str(tmp_path / "old.sqlite")
    build(db)

    row = Store(db).accesses("T09", NOW)[0]

    assert row["budget_chf"] == MONTHLY_BUDGET_CHF and row["spent_chf"] == 0, "October's spend stays in October"
    assert Store(db).costs("2026-10")[0]["cost_chf"] > 0, "the cost logs stay"


@pytest.mark.parametrize("build", [_g80_database, _legacy_database])
def test_an_existing_database_takes_new_people_codes_and_raises(tmp_path, build):
    db = str(tmp_path / "old.sqlite")
    build(db)
    store = Store(db)
    store.add_person("T10", NOW)

    access = store.authenticate(store.redeem(store.create_invitation("T10", NOW), "PC", NOW), NOW)

    assert access.budget_chf == MONTHLY_BUDGET_CHF
    assert store.set_budget("T09", 15.0) == {"accesses": 1, "invitations": 0}
    assert [person["name"] for person in store.people()] == ["T09", "T10"]
