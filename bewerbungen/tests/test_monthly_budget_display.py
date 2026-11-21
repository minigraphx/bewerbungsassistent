"""The monthly AI budget of the mediation (G98) as the server hands it to the pages, with invented amounts.

The mediation names the month and the day the budget renews (`monat`, `erneuert_am`); the app passes them on and words
them, it never takes them from its own clock. A mediation that names no renewal yet keeps the words of G80.
"""
import json
from pathlib import Path

import anthropic
import pytest

import routes_ai
from ai import budget, errors, tasks
from ai.connection import ACCESS_VARIABLE, KEY_VARIABLE, URL_VARIABLE
from ai.usage import UsageLog
from test_ai_tasks import AD, FakeClient, daten, gateway_for, response  # noqa: F401  (daten is a fixture)
from test_app import get, server  # noqa: F401  (server is a fixture)
from test_rate_all import estimate, hits, search  # noqa: F401  (search is a fixture)

ROOT = Path(__file__).resolve().parents[2]
MONTHLY = {"credit_chf": 5.0, "spent_chf": 1.2, "monat": "2026-11", "erneuert_am": "2026-12-01"}
OLD_MEDIATION = {"credit_chf": 5.0, "spent_chf": 1.2}
USED_UP_IN_NOVEMBER = ("Das KI-Budget für November ist aufgebraucht. Die KI geht wieder ab 1.\u00a0Dezember; "
                       "alles andere funktioniert weiterhin.")


def via_mediation(monkeypatch, account: dict) -> None:
    monkeypatch.delenv(KEY_VARIABLE, raising=False)
    monkeypatch.setenv(URL_VARIABLE, "https://ki.example.ch")
    monkeypatch.setenv(ACCESS_VARIABLE, "bwa_invented")
    monkeypatch.setattr(routes_ai.invitation, "account", lambda url, access: account)


# words

@pytest.mark.parametrize("account, month, renews", [
    (MONTHLY, "November", "1.\u00a0Dezember"),
    ({"monat": "2026-12", "erneuert_am": "2027-01-01"}, "Dezember", "1.\u00a0Januar"),
    ({"monat": "2026-03", "erneuert_am": "2026-04-01"}, "März", "1.\u00a0April"),
])
def test_month_and_renewal_are_named_in_german_from_what_the_mediation_says(account, month, renews):
    assert budget.month_of(account) == (month, renews)


@pytest.mark.parametrize("account", [
    OLD_MEDIATION, {"monat": "2026-11"}, {"erneuert_am": "2026-12-01"}, {"monat": "2026-13", "erneuert_am": "2026-12-01"},
    {"monat": "2026-11", "erneuert_am": "1. Dezember"}, {"monat": 202611, "erneuert_am": "2026-12-01"},
    {"monat": "2026-11", "erneuert_am": "2026-02-30"}, None,
])
def test_a_missing_or_unreadable_renewal_names_no_month(account):
    assert budget.month_of(account) is None
    assert budget.renewal_fields(account) == {}


def test_day_and_month_stay_together_with_an_escaped_no_break_space():
    source = (ROOT / "bewerbungen" / "ai" / "budget.py").read_text(encoding="utf-8")
    assert "\u00a0" not in source and "\\u00a0" in source


# the status of the AI

def test_the_status_passes_on_the_month_and_renewal_of_the_mediation(server, monkeypatch):  # noqa: F811
    via_mediation(monkeypatch, {**MONTHLY, "monat": "2026-09", "erneuert_am": "2026-10-01"})

    answer = json.loads(get(server, "/api/ki/status")[2])

    # the app's own clock says 26 October 2026: the month shown is the mediation's
    assert answer["monat"] == "2026-09" and answer["erneuert_am"] == "2026-10-01"
    assert answer["guthaben_chf"] == 5.0 and answer["verbraucht_chf"] == 1.2


def test_an_old_mediation_without_renewal_keeps_the_status_of_g80(server, monkeypatch):  # noqa: F811
    via_mediation(monkeypatch, OLD_MEDIATION)

    answer = json.loads(get(server, "/api/ki/status")[2])

    assert "erneuert_am" not in answer and answer["monat"] == "2026-10"
    assert answer["guthaben_chf"] == 5.0


def test_an_unreadable_renewal_is_not_passed_on(server, monkeypatch):  # noqa: F811
    via_mediation(monkeypatch, {**MONTHLY, "erneuert_am": "<b>bald</b>"})

    answer = json.loads(get(server, "/api/ki/status")[2])

    assert "erneuert_am" not in answer and answer["monat"] == "2026-10"


# the refusal of the mediation

def test_a_used_up_budget_names_the_month_and_the_day_the_ai_works_again(daten, monkeypatch):  # noqa: F811
    via_mediation(monkeypatch, {**MONTHLY, "spent_chf": 5.0})
    refused = anthropic.APIStatusError("x", response=response(402), body=None)
    gateway, material = gateway_for(daten, FakeClient(error=refused))

    with pytest.raises(errors.AiError) as raised:
        tasks.rate_match(gateway, material, AD)

    assert str(raised.value) == USED_UP_IN_NOVEMBER
    assert "anfordern" not in str(raised.value)


def test_an_old_mediation_still_says_a_new_code_can_be_asked_for(daten, monkeypatch):  # noqa: F811
    via_mediation(monkeypatch, {**OLD_MEDIATION, "spent_chf": 5.0})
    refused = anthropic.APIStatusError("x", response=response(402), body=None)
    gateway, material = gateway_for(daten, FakeClient(error=refused))

    with pytest.raises(errors.AiError) as raised:
        tasks.rate_match(gateway, material, AD)

    assert str(raised.value) == errors.CREDIT_USED_ONCE
    assert "neuen Code anfordern" in str(raised.value) and "KI und Budget" in str(raised.value)


def test_without_an_answer_of_the_mediation_the_refusal_keeps_the_words_of_g80(daten, monkeypatch):  # noqa: F811
    via_mediation(monkeypatch, {})

    def unreachable(url, access):
        raise errors.AiError(errors.OFFLINE)

    monkeypatch.setattr(routes_ai.invitation, "account", unreachable)
    refused = anthropic.APIStatusError("x", response=response(402), body=None)
    gateway, material = gateway_for(daten, FakeClient(error=refused))

    with pytest.raises(errors.AiError, match="Einladungscodes ist aufgebraucht"):
        tasks.rate_match(gateway, material, AD)


# estimates before a run

def test_an_estimate_carries_the_month_and_renewal_of_the_mediation(search, monkeypatch):  # noqa: F811
    hits(search, 2)
    via_mediation(monkeypatch, MONTHLY)

    answer = estimate(search)

    assert answer["monat"] == "2026-11" and answer["erneuert_am"] == "2026-12-01"
    assert answer["guthaben"] == pytest.approx(3.8)


def test_an_estimate_of_an_old_mediation_names_no_renewal(search, monkeypatch):  # noqa: F811
    hits(search, 2)
    via_mediation(monkeypatch, OLD_MEDIATION)

    answer = estimate(search)

    assert "erneuert_am" not in answer and "monat" not in answer


# the rows per task in Einstellungen

def test_the_rows_per_task_follow_the_month_of_the_mediation(server):  # noqa: F811
    log = UsageLog(server.kontext.daten)
    for when, task in (("2026-09-30T23:00:00+02:00", "rate"), ("2026-10-02T09:00:00+02:00", "draft")):
        log.path.parent.mkdir(parents=True, exist_ok=True)
        with log.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps({"time": when, "task": task, "cost_usd": 0.5}) + "\n")

    september = json.loads(get(server, "/api/schluessel", monat="2026-09")[2])["kosten"]
    own_clock = json.loads(get(server, "/api/schluessel")[2])["kosten"]

    assert list(september["aufgaben"]) == ["rate"] and september["monat_usd"] == pytest.approx(0.5)
    assert list(own_clock["aufgaben"]) == ["draft"]


def test_a_month_that_is_no_month_is_refused(server):  # noqa: F811
    assert get(server, "/api/schluessel", monat="2026-9")[0] == 400
    assert get(server, "/api/schluessel", monat="../x")[0] == 400


# the guide

def test_the_guide_no_longer_calls_the_code_a_one_time_credit():
    guide = (ROOT / "docs" / "installation.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for words in ("einmalig", "Probeguthaben", "erneuert sich nicht", "neuen Code an"):
        assert words not in guide, words
    assert "einmalig" not in readme
    assert "CHF 5 pro Monat" in guide and "Monatsersten" in guide
