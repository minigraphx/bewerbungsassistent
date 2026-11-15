"""An invitation code is a one-time trial credit of CHF 5 (G80): never renewed, refused once used up, all in CHF."""
import datetime
import pathlib
import sqlite3
import sys

import anthropic
import pytest

import admin
import pricing
from pricing import Usage
from store import TRIAL_CREDIT_CHF, Store, StoreError
from test_mediation import MODEL, NOW, access_for, app_client, ask, raw, setup  # noqa: F401  (setup is a fixture)

NEXT_MONTH = NOW + datetime.timedelta(days=40)


def _redeemed(store: Store, name: str = "T05", credit: float | None = None):
    store.add_person(name, NOW)
    code = store.create_invitation(name, NOW, credit_chf=credit) if credit is not None else store.create_invitation(name, NOW)
    return store.authenticate(store.redeem(code, "PC", NOW), NOW)


def test_a_code_carries_five_francs_by_default():
    assert TRIAL_CREDIT_CHF == 5.0


def test_one_usd_billed_counts_as_one_franc():
    assert pricing.CHF_PER_USD == 1.0
    assert pricing.cost_chf(0.42) == pytest.approx(0.42)


def test_the_app_counts_with_the_same_rate():
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "bewerbungen"))
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lebenslauf"))
    from ai.usage import CHF_PER_USD as APP_RATE

    assert pricing.CHF_PER_USD == APP_RATE


def test_the_access_takes_the_credit_of_its_code(tmp_path):
    store = Store(str(tmp_path / "c.sqlite"))
    access = _redeemed(store, credit=2.5)
    assert access.credit_chf == 2.5
    assert _redeemed(store, "T06").credit_chf == TRIAL_CREDIT_CHF


def test_the_credit_is_not_renewed_in_a_new_month(tmp_path):
    store = Store(str(tmp_path / "c.sqlite"))
    access = _redeemed(store)
    store.record_usage(access, MODEL, Usage(10, 5), 3.0, 200, "req_1", NOW)
    store.record_usage(access, MODEL, Usage(10, 5), 1.5, 200, "req_2", NEXT_MONTH)
    assert store.spent_chf(access) == pytest.approx(4.5)


def test_a_new_code_brings_a_new_credit(tmp_path):
    store = Store(str(tmp_path / "c.sqlite"))
    first = _redeemed(store)
    store.record_usage(first, MODEL, Usage(10, 5), 5.0, 200, "req_1", NOW)
    second = store.authenticate(store.redeem(store.create_invitation("T05", NOW), "PC", NOW), NOW)
    assert store.spent_chf(first) == pytest.approx(5.0)
    assert store.spent_chf(second) == 0


@pytest.mark.parametrize("credit", [-1.0, 0.0, 1000.0])
def test_odd_credits_are_refused(tmp_path, credit):
    store = Store(str(tmp_path / "c.sqlite"))
    store.add_person("T05", NOW)
    with pytest.raises(StoreError, match="Guthaben"):
        store.create_invitation("T05", NOW, credit_chf=credit)


def test_a_used_up_credit_answers_402_with_its_reason(setup):
    token = access_for(setup)
    access = setup["store"].authenticate(token, NOW)
    setup["store"].record_usage(access, MODEL, Usage(10, 5), TRIAL_CREDIT_CHF, 200, "req_1", NOW)

    answer = raw(setup, "POST", "/v1/messages", {"model": MODEL, "max_tokens": 10,
                                                 "messages": [{"role": "user", "content": "Hallo"}]},
                 headers={"x-api-key": token})

    assert answer.status_code == 402
    assert answer.json()["error"] == {"type": "credit_used_up", "message": "trial credit used up"}
    assert setup["fake"].requests == [], "nothing reaches Anthropic"


def test_the_refusal_stays_in_the_next_month(setup):
    token = access_for(setup)
    access = setup["store"].authenticate(token, NOW)
    setup["store"].record_usage(access, MODEL, Usage(10, 5), TRIAL_CREDIT_CHF, 200, "req_1", NOW)
    setup["clock"]["now"] = NEXT_MONTH

    with pytest.raises(anthropic.APIStatusError) as error:
        ask(app_client(setup, token))
    assert error.value.status_code == 402


def test_the_account_shows_the_credit_in_francs_without_a_month(setup):
    token = access_for(setup)
    access = setup["store"].authenticate(token, NOW)
    setup["store"].record_usage(access, MODEL, Usage(10, 5), 1.25, 200, "req_1", NOW)

    answer = raw(setup, "GET", "/v1/account", headers={"authorization": f"Bearer {token}"})

    assert answer.json() == {"credit_chf": TRIAL_CREDIT_CHF, "spent_chf": 1.25}


def test_admin_invites_with_a_credit_in_francs(tmp_path):
    db = str(tmp_path / "a.sqlite")
    now = lambda: NOW  # noqa: E731

    default = admin.main(["--db", db, "invite", "T07"], now)
    smaller = admin.main(["--db", db, "invite", "T08", "--credit", "2"], now)

    assert "Guthaben CHF 5.00, einmalig" in default
    assert "Guthaben CHF 2.00, einmalig" in smaller
    assert "Monat" not in default and "USD" not in default


def test_admin_states_credit_and_costs_in_francs(tmp_path):
    db = str(tmp_path / "a.sqlite")
    now = lambda: NOW  # noqa: E731
    invitation = admin.main(["--db", db, "invite", "T07"], now)
    code = invitation.split("Code für T07: ")[1].split("\n")[0]
    store = Store(db)
    access = store.authenticate(store.redeem(code, "PC", NOW), NOW)
    store.record_usage(access, MODEL, Usage(10, 5), 1.2, 200, "req_1", NOW)

    listed = admin.main(["--db", db, "accesses", "T07"], now)
    costs = admin.main(["--db", db, "costs", "--month", "2026-11"], now)

    assert "Guthaben CHF 1.20 von 5.00" in listed
    assert "1.20 CHF" in costs and "USD" not in costs
    with pytest.raises(SystemExit):
        admin.main(["--db", db, "budget", "T07", "30"], now)


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


def test_an_existing_access_keeps_working_with_a_fresh_credit_from_the_migration(tmp_path):
    db = str(tmp_path / "old.sqlite")
    _legacy_database(db)

    store = Store(db, now=NOW)
    row = store.accesses("T09")[0]

    assert row["credit_chf"] == TRIAL_CREDIT_CHF and row["spent_chf"] == 0
    assert store.costs("2026-10")[0]["cost_chf"] == pytest.approx(12.0), "the cost logs stay"


def test_the_migration_runs_once(tmp_path):
    db = str(tmp_path / "old.sqlite")
    _legacy_database(db)
    Store(db, now=NOW)
    later = Store(db, now=NEXT_MONTH)
    assert later.accesses("T09")[0]["credit_since"] == NOW.isoformat(timespec="seconds")


def test_an_old_database_takes_new_people_and_codes(tmp_path):
    db = str(tmp_path / "old.sqlite")
    _legacy_database(db)
    store = Store(db, now=NOW)
    store.add_person("T10", NOW)
    access = store.authenticate(store.redeem(store.create_invitation("T10", NOW), "PC", NOW), NOW)
    assert access.credit_chf == TRIAL_CREDIT_CHF
    assert [person["name"] for person in store.people()] == ["T09", "T10"]
