"""The invitation code as a one-time trial credit of CHF 5 (G80) as the app shows it, in CHF (G46), with invented data.

The page logic runs in node without DOM; the routes run against a simulated mediation.
"""
import json
import re
import subprocess
from pathlib import Path

import anthropic
import httpx2
import pytest

import routes_ai
from ai import errors, usage
from ai.connection import ACCESS_VARIABLE, KEY_VARIABLE, URL_VARIABLE
from test_app import get, server  # noqa: F401  (server is a fixture)
from test_rate_all import estimate, hits, search  # noqa: F401  (search is a fixture)

ROOT = Path(__file__).resolve().parents[2]
PAGES = ROOT / "bewerbungen" / "seiten"
CREDIT = {"eingerichtet": True, "vermittlung": True, "waehrung": "CHF", "guthaben_chf": 5, "verbraucht_chf": 3.2}
USED_UP = {**CREDIT, "verbraucht_chf": 5}


def node(logic: str, call: str, *values) -> object:
    """`call` uses `L` for the module and `a[0]`, `a[1]` … for the values."""
    script = (f"const L = require(process.argv[1]); const a = JSON.parse(process.argv[2]); "
              f"process.stdout.write(JSON.stringify({call}));")
    result = subprocess.run(["node", "-e", script, str(PAGES / logic), json.dumps(list(values))],
                            capture_output=True, text=True, timeout=60, check=True)
    return json.loads(result.stdout)


def via_mediation(monkeypatch, account: dict) -> None:
    monkeypatch.delenv(KEY_VARIABLE, raising=False)
    monkeypatch.setenv(URL_VARIABLE, "https://ki.example.ch")
    monkeypatch.setenv(ACCESS_VARIABLE, "bwa_invented")
    monkeypatch.setattr(routes_ai.invitation, "account", lambda url, access: account)


# the refusal and its words

def _refusal(status: int) -> anthropic.APIStatusError:
    request = httpx2.Request("POST", "https://ki.example.ch/v1/messages")
    body = {"type": "error", "error": {"type": "credit_used_up", "message": "trial credit used up"}}
    return anthropic.APIStatusError("trial credit used up", response=httpx2.Response(status, request=request, json=body),
                                    body=body)


def test_a_used_up_credit_says_so_and_that_a_new_code_can_be_asked_for():
    message = str(errors.from_sdk(_refusal(402)))

    assert message == errors.CREDIT_USED
    assert "Guthaben" in message and "aufgebraucht" in message and "neuen Code anfordern" in message
    assert "Monat" not in message


def test_no_message_names_the_begleitperson_as_the_source_of_access():
    for message in (errors.ACCESS_DENIED, errors.NO_CREDIT, errors.CREDIT_USED):
        assert "Begleitperson" not in message


def test_the_setup_does_not_say_the_code_comes_from_the_begleitperson():
    texts = (PAGES / "texte.js").read_text(encoding="utf-8")
    entry = re.search(r'"einrichtung\.ki\.code": \{.*?\n    \}', texts, re.S)[0]
    assert "Begleitperson" not in entry and "CHF 5" in entry


def test_no_text_of_the_app_says_the_budget_is_used_up_for_this_month():
    files = [*PAGES.glob("*.js"), *PAGES.glob("*.html"), *(ROOT / "bewerbungen" / "ai").glob("*.py"),
             ROOT / "docs" / "installation.md"]
    for path in files:
        text = path.read_text(encoding="utf-8")
        assert "für diesen Monat aufgebraucht" not in text, path.name
        assert "Budget pro Monat" not in text, path.name


@pytest.mark.parametrize("name", ["einstellungen-logik.js", "einstellungen.html", "einstellungen.js", "ki-zugang.js",
                                  "ki.js", "ki-fenster.js", "sidebar-logic.js", "treffer-logik.js"])
def test_the_texts_say_guthaben_and_not_budget(name):
    text = (PAGES / name).read_text(encoding="utf-8")
    assert not re.search(r"(?<![\w-])Budget", text), name


def test_one_usd_counts_as_one_franc():
    assert usage.CHF_PER_USD == 1.0
    assert usage.currency(True) == "CHF" and usage.currency(False) == "USD"


# the status of the AI

def test_the_status_reads_the_credit_from_the_mediation(server, monkeypatch):  # noqa: F811
    via_mediation(monkeypatch, {"credit_chf": 5.0, "spent_chf": 1.25})

    answer = json.loads(get(server, "/api/ki/status")[2])

    assert answer["guthaben_chf"] == 5.0 and answer["verbraucht_chf"] == 1.25 and answer["waehrung"] == "CHF"
    assert "budget_usd" not in answer and "verbraucht_usd" not in answer


def test_with_an_own_key_the_costs_stay_in_usd(server, monkeypatch):  # noqa: F811
    for name in (URL_VARIABLE, ACCESS_VARIABLE):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(KEY_VARIABLE, "sk-test")

    answer = json.loads(get(server, "/api/ki/status")[2])

    assert answer["waehrung"] == "USD" and "guthaben_chf" not in answer


# the sidebar and the narrow header (#211)

def test_the_sidebar_shows_used_and_free_credit_in_francs_without_a_month():
    shown = node("sidebar-logic.js", "L.budgetView(a[0])", {**CREDIT, "monat": "2026-11"})

    assert shown["title"] == "KI-Guthaben"
    assert shown["text"] == "CHF\u00a03.20 von 5.00 gebraucht"
    assert shown["detail"] == "CHF\u00a01.80 frei"
    assert shown["narrow"] == "KI-Guthaben: CHF\u00a01.80 frei"
    assert shown["label"] == "64 Prozent des Guthabens gebraucht"


def test_the_sidebar_warns_in_words_about_a_credit_nearly_or_wholly_used():
    low = node("sidebar-logic.js", "L.budgetView(a[0])", {**CREDIT, "verbraucht_chf": 4})
    empty = node("sidebar-logic.js", "L.budgetView(a[0])", USED_UP)

    assert low["warning"] == "Guthaben fast aufgebraucht" and low["narrow"] == "KI-Guthaben: CHF\u00a01.00 frei · fast aufgebraucht"
    assert empty["warning"] == "Guthaben aufgebraucht: neuen Code anfordern"
    assert empty["narrow"] == "KI-Guthaben: CHF\u00a00.00 frei · aufgebraucht"


def test_with_an_own_key_the_sidebar_names_no_credit_of_the_mediation():
    shown = node("sidebar-logic.js", "L.budgetView(a[0])",
                 {"monat": "2026-03", "eingerichtet": True, "vermittlung": False, "eigener_schluessel": True,
                  "kosten_usd": 1.5})
    assert shown["narrow"] == "KI-Kosten: USD\u00a01.50 · kein Guthaben der Vermittlung"


def test_the_pages_learn_the_currency_from_the_status():
    assert node("sidebar-logic.js", "[L.currencyOf(a[0]), L.currencyOf(a[1]), L.currencyOf(null)]",
                CREDIT, {"eingerichtet": True, "vermittlung": False}) == ["CHF", "USD", "USD"]


# Einstellungen

def test_the_settings_card_shows_the_credit_once_without_renewal():
    view = node("einstellungen-logik.js", "L.budgetView(a[0], a[1])", {**CREDIT, "monat": "2026-11"},
                {"monat_usd": 3.2, "gesamt_usd": 3.2, "aufrufe": 9, "aufgaben": {"rate": {"aufrufe": 9, "usd": 3.2}}})

    assert view["title"] == "Guthaben"
    assert view["headline"] == "CHF\u00a03.20 von 5.00 gebraucht"
    assert view["renewal"] is None
    assert view["rows"] == [{"label": "Stellen einschätzen", "count": 9, "usd": "CHF\u00a03.20"}]
    assert view["total"] == "Seit Beginn CHF\u00a03.20 in 9 Aufrufen"
    assert "einmal" in view["note"] and "neuer Einladungscode" in view["note"]


def test_the_settings_offer_a_new_code_once_the_credit_is_used_up():
    assert node("einstellungen-logik.js", "[L.invitationState(a[0]), L.invitationState(a[1])]", CREDIT, USED_UP) \
        == ["aktiv", "aufgebraucht"]
    page = (PAGES / "einstellungen.html").read_text(encoding="utf-8")
    assert re.search(r'<p id="einladung-aufgebraucht" hidden>[^<]*neuen Einladungscode[^<]*</p>', page)
    assert "KI und Guthaben" in page


# the window „KI einrichten“ and the choice of the way

def test_the_choice_names_the_one_time_credit():
    text = (PAGES / "ki-zugang.js").read_text(encoding="utf-8")
    assert "einmaligen Guthaben von CHF 5" in text


# „Alle prüfen“ on Stellen (#209)

def test_the_estimate_of_alle_pruefen_is_in_francs_with_the_mediation(search, monkeypatch):  # noqa: F811
    hits(search, 3)
    via_mediation(monkeypatch, {"credit_chf": 5.0, "spent_chf": 1.5})

    answer = estimate(search)

    assert answer["waehrung"] == "CHF"
    assert answer["guthaben"] == pytest.approx(3.5)
    assert answer["danach"] == pytest.approx(3.5 - answer["kosten"])


def test_the_estimate_with_an_own_key_stays_in_usd(search):  # noqa: F811
    hits(search, 2)
    answer = estimate(search)
    assert answer["waehrung"] == "USD" and answer["guthaben"] is None


def test_the_words_of_alle_pruefen_are_in_francs_and_say_guthaben():
    s = {"anzahl": 2, "kosten": 0.06, "dauer_minuten": 1, "laden": [], "nicht_ladbar": [], "guthaben": 3.5,
         "danach": 3.44, "reicht_fuer": None, "waehrung": "CHF"}
    line = node("treffer-logik.js", "L.estimateLine(a[0])", s)
    question = node("treffer-logik.js", "L.confirmation(a[0], false, true)", {**s, "guthaben": 0.1, "reicht_fuer": 1})
    after = node("treffer-logik.js", "L.schlussText(a[0], 0, 'CHF')",
                 {"bewertet": 2, "von": 2, "offen": [], "ohneText": 0, "kosten": 0.06, "gestoppt": False})

    assert line == "Etwa CHF\u00a00.06 und 1\u00a0Minute. Danach bleiben CHF\u00a03.44 im Guthaben."
    assert "Im Guthaben sind noch CHF\u00a00.10, danach etwa CHF\u00a03.44." in question["sentences"]
    assert question["warning"].startswith("Das Guthaben von CHF\u00a00.10 reicht für etwa 1 von 2 Stellen.")
    assert after == "2 von 2 Treffern bewertet. Kosten: 0.06\u00a0CHF."


# the other amounts of the mediation

def test_a_charged_check_of_the_terms_names_francs_with_the_mediation(monkeypatch):
    import routes_terms
    via_mediation(monkeypatch, {"credit_chf": 5.0, "spent_chf": 0})
    assert routes_terms.charged(0.05) == "Berechnet: 0.05 CHF."


def test_a_used_up_credit_is_named_before_alle_pruefen_and_not_counted_as_enough_for_none():
    s = {"anzahl": 3, "kosten": 0.12, "dauer_minuten": 2, "laden": [], "nicht_ladbar": [], "guthaben": 0,
         "danach": 0, "reicht_fuer": 0, "waehrung": "CHF"}
    line = node("treffer-logik.js", "L.estimateLine(a[0])", s)
    question = node("treffer-logik.js", "L.confirmation(a[0], false, true)", s)

    assert line == "Etwa CHF\u00a00.12 und 2\u00a0Minuten. Das Guthaben ist aufgebraucht: neuen Code anfordern."
    assert question["warning"] == ("Das Guthaben ist aufgebraucht. Mit einem neuen Einladungscode geht es weiter; "
                                   "ohne prüft die KI keine Stelle.")



def _ki_page_status(status: dict) -> str:
    """Runs `statusText` of the page „KI“ as written, without the rest of the page."""
    script = (PAGES / "ki.js").read_text(encoding="utf-8")
    function = re.search(r"\n  function statusText\(s\) \{.*?\n  \}\n", script, re.S)[0]
    code = f"const kosten = x => x; {function}; process.stdout.write(statusText(JSON.parse(process.argv[1])));"
    return subprocess.run(["node", "-e", code, json.dumps(status)], capture_output=True, text=True, timeout=60,
                          check=True).stdout


def test_the_ki_page_names_the_way_to_a_new_code_once_the_credit_is_used_up():
    assert _ki_page_status(CREDIT) == "KI eingerichtet (über die Vermittlung). Guthaben: CHF\u00a03.20 von 5.00 verbraucht."
    assert _ki_page_status(USED_UP) == ("KI eingerichtet (über die Vermittlung). Guthaben: CHF\u00a05.00 von 5.00 verbraucht. "
                                        "Das Guthaben ist aufgebraucht: einen neuen Code anfordern und unter "
                                        "Einstellungen, KI und Guthaben einlösen.")
