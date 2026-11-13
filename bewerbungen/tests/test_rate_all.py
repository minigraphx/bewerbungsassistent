"""„Alle prüfen“ on Stellen (G44, #209): before the run the app names the number of hits, the estimated cost from the
current prices, what stays of the budget and the rough duration; hits without text are loaded first where the portal
allows it, and a run that hits the end of the budget leaves the rest open. All data is invented, the AI is simulated."""
import datetime
import json
import shutil

import pytest

import rate_all
import routes_ai
from ai import usage
from ai.connection import ACCESS_VARIABLE, KEY_VARIABLE, URL_VARIABLE
from ai.errors import BUDGET_USED, AiError
from hits import Hits
from test_ai_tasks import VORLAGEN, PackageClient, rating_entry
from test_app import get, post, server  # noqa: F401  (server is a fixture)

ESTIMATE = "/api/suche/alle-pruefen"
HOLEN, TEXTE = "/api/inserate/holen", "/api/inserate/texte"
HIT = {"portal": "jobs.ch", "portal_id": "abc-1", "stelle": "Python Developer", "firma": "Muster GmbH", "ort": "Bern",
       "pensum": "80–100 %", "link": "https://www.jobs.ch/de/stellenangebote/detail/abc-1/", "alter_tage": 2,
       "text": "Python, SQL, Deutsch fliessend."}
OWN_SITE = "example.ch"  # a site the person named (MIN-348): no adapter, so no automatic loading
OTHER_SITE = {**HIT, "portal": OWN_SITE, "portal_id": "fremd-1", "firma": "Fremd AG", "text": "",
              "link": "https://www.example.ch/stellen/fremd-1"}


@pytest.fixture
def search(server, monkeypatch):  # noqa: F811
    daten = server.kontext.daten
    shutil.copy(VORLAGEN / "suchprofil.md", daten / "suchprofil.md")
    shutil.copytree(VORLAGEN / "anschreiben", daten / "anschreiben", dirs_exist_ok=True)
    for name in (URL_VARIABLE, ACCESS_VARIABLE):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(KEY_VARIABLE, "sk-test")
    return server


def hits(search, count: int, prefix: str = "p", **fields) -> list[str]:
    found = [{**HIT, "portal_id": f"{prefix}-{i}", "firma": f"Firma {prefix} {i}", "link": f"{HIT['link']}{prefix}{i}", "text": f"Inserat Nummer {i}. " * 40,
              **fields} for i in range(count)]
    post(search, "/api/suche/treffer", {"treffer": found})
    return [hit["id"] for hit in listing(search) if hit["portal_id"] in {f["portal_id"] for f in found}]


def listing(search) -> list[dict]:
    return json.loads(get(search, "/api/suche/liste")[2])["treffer"]


def estimate(search) -> dict:
    status, _, content = get(search, ESTIMATE)
    assert status == 200, content
    return json.loads(content)


def mediation(monkeypatch, spent: float, budget: float):
    monkeypatch.delenv(KEY_VARIABLE, raising=False)
    monkeypatch.setenv(URL_VARIABLE, "https://ki.example.ch")
    monkeypatch.setenv(ACCESS_VARIABLE, "bwa_test")
    monkeypatch.setattr(routes_ai.invitation, "account",
                        lambda url, access: {"month": "2026-11", "spent_usd": spent, "budget_usd": budget})


def test_the_estimate_counts_every_new_hit_without_a_grade(search, monkeypatch):
    ids = hits(search, 4)
    rated, discarded, *open_ids = ids
    monkeypatch.setattr(routes_ai, "new_client", lambda: PackageClient(lambda labels: [rating_entry(labels[0], 3)]))
    assert post(search, "/api/suche/bewerten", {}, id=rated)[0] == 200
    assert post(search, "/api/suche/verwerfen", {}, id=discarded)[0] == 200

    answer = estimate(search)

    assert answer["anzahl"] == len(open_ids) == 2
    assert answer["kosten_usd"] > 0
    assert answer["dauer_minuten"] >= 1


def test_the_cost_comes_from_the_current_prices(search, monkeypatch):
    hits(search, 12)
    before = estimate(search)["kosten_usd"]
    model = rate_all.MODEL
    price_in, price_out = usage.PRICES_USD[model]
    monkeypatch.setitem(usage.PRICES_USD, model, (price_in * 2, price_out * 2))

    after = estimate(search)["kosten_usd"]

    assert after == pytest.approx(before * 2, rel=0.05)


def test_more_hits_cost_more_and_take_longer(search):
    hits(search, 2)
    few = estimate(search)
    hits(search, 25, prefix="lang", text="Ein längeres Inserat. " * 80)
    many = estimate(search)

    assert many["anzahl"] == few["anzahl"] + 25
    assert many["kosten_usd"] > few["kosten_usd"]
    assert many["dauer_minuten"] > few["dauer_minuten"]


def test_with_the_mediation_it_names_the_budget_left_now_and_afterwards(search, monkeypatch):
    hits(search, 3)
    mediation(monkeypatch, spent=1.5, budget=20)

    answer = estimate(search)

    assert answer["budget_usd"] == pytest.approx(18.5)
    assert answer["danach_usd"] == pytest.approx(18.5 - answer["kosten_usd"])
    assert answer["reicht_fuer"] is None, "the budget is enough for all"


def test_a_budget_too_small_says_for_how_many_it_is_enough(search, monkeypatch):
    hits(search, 20)
    mediation(monkeypatch, spent=19.99, budget=20)

    answer = estimate(search)

    assert 0 <= answer["reicht_fuer"] < answer["anzahl"]
    assert answer["danach_usd"] == 0


def test_with_an_own_key_there_is_no_budget_to_name(search):
    hits(search, 2)

    answer = estimate(search)

    assert answer["budget_usd"] is None and answer["danach_usd"] is None and answer["reicht_fuer"] is None


def test_hits_without_text_are_loaded_first_unless_the_portal_forbids_it(search):
    loadable = hits(search, 1, text="")[0]
    Hits(search.kontext.daten).add([OTHER_SITE], [], datetime.date(2026, 11, 13), frozenset({OWN_SITE}))
    other = next(hit["id"] for hit in listing(search) if hit["portal_id"] == "fremd-1")

    answer = estimate(search)

    assert answer["laden"] == [loadable]
    assert answer["anzahl"] == 1, "a hit the extension may load counts, one it may not does not"
    assert [entry["id"] for entry in answer["nicht_ladbar"]] == [other]
    assert "automatisches Laden" in answer["nicht_ladbar"][0]["grund"]


def test_the_extension_gets_the_hits_to_load_again_in_the_same_start(search):
    loadable = hits(search, 1, text="")[0]
    assert [job["id"] for job in post(search, HOLEN, {})[1]["laden"]] == [loadable]
    assert post(search, HOLEN, {})[1]["laden"] == [], "the start hands each job out once"

    status, answer = post(search, HOLEN, {"treffer": [loadable, "unbekannt"]})

    assert status == 200 and [job["id"] for job in answer["laden"]] == [loadable]
    status, stored = post(search, TEXTE, {"texte": [{"art": "treffer", "id": loadable, "text": "Der Text des Inserats."}]})
    assert (status, stored["gespeichert"]) == (200, 1)
    assert estimate(search)["laden"] == []


@pytest.mark.parametrize("body", [{"treffer": "x"}, {"treffer": [1]}])
def test_a_bad_list_of_hits_to_load_is_refused(search, body):
    assert post(search, HOLEN, body)[0] == 400


def test_when_the_budget_runs_out_the_rated_stay_and_the_rest_is_named(search, monkeypatch):
    ids = hits(search, 14)
    calls = []

    def client():
        calls.append(1)
        if len(calls) > 1:
            raise AiError(BUDGET_USED)
        return PackageClient(lambda labels: [rating_entry(label, 3) for label in labels])

    monkeypatch.setattr(routes_ai, "new_client", client)
    first, second = ids[:10], ids[10:]
    assert post(search, "/api/suche/bewerten-paket", {"ids": first})[0] == 200

    status, answer = post(search, "/api/suche/bewerten-paket", {"ids": second})

    assert status == 400 and answer["fehler"] == BUDGET_USED
    assert sum(1 for hit in listing(search) if hit.get("bewertung")) == 10
    assert estimate(search)["anzahl"] == 4
