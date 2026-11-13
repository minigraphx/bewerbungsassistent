"""Used and remaining AI budget always visible in the sidebar (#211, G46), with invented amounts.

The view is computed in seiten/sidebar-logic.js without DOM; node evaluates it here for each invented status.
"""
import json
import re
import subprocess
from pathlib import Path

import pytest

import routes_ai
from ai.connection import ACCESS_VARIABLE, URL_VARIABLE
from test_app import get, server  # noqa: F401  (server is a fixture)

PAGES = Path(__file__).resolve().parent.parent / "seiten"
LOGIC = PAGES / "sidebar-logic.js"
MEDIATION = {"monat": "2026-11", "eingerichtet": True, "vermittlung": True, "budget_usd": 10}


def view(status: dict | None) -> dict | None:
    script = ("const s = require(process.argv[1]); "
              "process.stdout.write(JSON.stringify(s.budgetView(JSON.parse(process.argv[2]))));")
    result = subprocess.run(["node", "-e", script, str(LOGIC), json.dumps(status)],
                            capture_output=True, text=True, timeout=60, check=True)
    return json.loads(result.stdout)


def nav_of(name: str) -> str:
    return re.search(r'<nav class="app-nav".*?</nav>', (PAGES / name).read_text(encoding="utf-8"), re.S)[0]


def test_the_sidebar_names_what_is_used_and_what_is_left():
    shown = view({**MEDIATION, "verbraucht_usd": 3.2})

    assert shown["text"] == "USD 3.20 von 10.00 gebraucht"
    assert shown["detail"] == "USD 6.80 frei"
    assert shown["narrow"] == "KI-Budget: USD 6.80 frei"
    assert shown["warning"] == "" and shown["state"] == "ok"


def test_an_unused_budget_says_that_nothing_is_used():
    shown = view({**MEDIATION, "verbraucht_usd": 0})

    assert shown["text"] == "USD 10.00 frei"
    assert shown["detail"] == "Noch nichts gebraucht"
    assert shown["warning"] == ""


@pytest.mark.parametrize("spent", [8, 9.99])
def test_a_nearly_used_budget_says_so_in_words(spent):
    shown = view({**MEDIATION, "verbraucht_usd": spent})

    assert shown["state"] == "low"
    assert shown["warning"] == "Budget fast aufgebraucht"
    assert shown["narrow"].endswith(" · fast aufgebraucht")


def test_below_the_mark_there_is_no_warning():
    assert view({**MEDIATION, "verbraucht_usd": 7.9})["warning"] == ""


@pytest.mark.parametrize("spent", [10, 12.5])
def test_a_used_up_budget_says_so_in_words(spent):
    shown = view({**MEDIATION, "verbraucht_usd": spent})

    assert shown["state"] == "empty"
    assert shown["warning"] == "Budget aufgebraucht"
    assert shown["detail"] == "USD 0.00 frei"
    assert shown["narrow"] == "KI-Budget: USD 0.00 frei · aufgebraucht"


def test_with_an_own_key_no_budget_of_the_mediation_applies():
    shown = view({"monat": "2026-03", "eingerichtet": True, "vermittlung": False, "eigener_schluessel": True,
                  "kosten_usd": 1.5})

    assert shown["text"] == "USD 1.50 mit eigenem Schlüssel"
    assert shown["detail"] == "Kein Budget der Vermittlung"
    assert shown["narrow"] == "KI-Kosten: USD 1.50 · kein Budget der Vermittlung"
    assert shown["warning"] == "" and shown["state"] == "own"


def test_without_ai_or_an_answer_there_is_nothing_to_show():
    assert view(None) is None
    assert view({"monat": "2026-11", "eingerichtet": False}) is None
    assert view({"monat": "2026-11", "eingerichtet": True, "vermittlung": True, "hinweis": "nicht erreichbar"}) is None


def test_every_page_has_room_for_the_rest_and_the_warning_in_words():
    nav = nav_of("uebersicht.html")
    budget = nav[nav.index('id="nav-budget"'):nav.index('id="nav-extension"')]
    assert re.search(r'<span class="num" id="nav-budget-detail"></span>', budget)
    assert re.search(r'<strong class="app-nav__budget-warning" id="nav-budget-warning" hidden>', budget)
    pages = [path.name for path in PAGES.glob("*.html")]
    for name in pages:
        assert nav_of(name) == nav, name


def test_the_status_reads_the_budget_of_the_month_from_the_mediation(server, monkeypatch):  # noqa: F811
    monkeypatch.setenv(URL_VARIABLE, "https://ki.example.ch")
    monkeypatch.setenv(ACCESS_VARIABLE, "bwa_invented")
    asked = []

    def account(url, access):
        asked.append(url)
        return {"month": "2026-11", "spent_usd": 8.4, "budget_usd": 10}

    monkeypatch.setattr(routes_ai.invitation, "account", account)

    status, _, body = get(server, "/api/ki/status")
    answer = json.loads(body)

    assert status == 200 and asked == ["https://ki.example.ch"]
    assert answer["budget_usd"] == 10 and answer["verbraucht_usd"] == 8.4
    assert view(answer)["warning"] == "Budget fast aufgebraucht"
