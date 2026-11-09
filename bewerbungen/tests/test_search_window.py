"""How far back the search looks (G32): a window from the profile, shortened per portal after a successful run."""
import datetime
import json

import pytest

import hits
import search_plan
from test_app import get, post, server  # noqa: F401  (server is a fixture)

PROFILE = """# Suchprofil

## Portale und Rhythmus
- Zeitfenster: {window}

| Portal | Modus |
|---|---|
| job-room | automatisch |

## Region
- Kantone (job-room): BE
- Orte (jobs.ch): Bern
- PLZ (jobscout24): 3000

## Keywords
- Kernliste: Python
"""
TODAY = datetime.date(2026, 11, 9)


def profile(window: str = "") -> str:
    text = PROFILE.format(window=window)
    return text if window else text.replace("- Zeitfenster: \n", "")


def test_the_window_is_21_days_by_default():
    plan = search_plan.parse(profile())
    assert (search_plan.MAX_AGE_DAYS, plan.max_age_days, plan.as_dict()["max_alter_tage"]) == (21, 21, 21)
    assert not any("Zeitfenster" in hint for hint in plan.hints)


@pytest.mark.parametrize(("value", "days"), [("14 Tage", 14), ("1 Tag", 1), ("60", 60)])
def test_the_profile_sets_the_window(value, days):
    plan = search_plan.parse(profile(value))
    assert (plan.max_age_days, plan.as_dict()["max_alter_tage"]) == (days, days)


@pytest.mark.parametrize("value", ["0 Tage", "90 Tage", "bald"])
def test_an_invalid_window_falls_back_to_21_with_a_hint(value):
    plan = search_plan.parse(profile(value))
    assert plan.max_age_days == 21
    assert any(hint.startswith("Zeitfenster") and "21 Tage" in hint for hint in plan.hints)


def test_each_portal_searches_since_its_last_successful_run_within_the_window():
    last = {"jobs.ch": "2026-11-06", "job-room": "2026-09-01", "jobscout24": "2026-11-09", "ictjobs": "kaputt"}
    days = search_plan.portal_days(21, ("job-room", "jobs.ch", "jobscout24", "ictjobs"), last, TODAY)
    assert days == {"job-room": 21, "jobs.ch": 4, "jobscout24": 1, "ictjobs": 21}


def test_the_run_state_keeps_the_last_success_of_each_portal(tmp_path):
    store = hits.Hits(tmp_path)
    store.save_run({"portale": {"jobs.ch": {"treffer": 3, "neu": 1, "problem": ""},
                                "job-room": {"treffer": 0, "neu": 0, "problem": "Seite nicht geladen"}}}, TODAY)
    store.save_run({"portale": {"jobscout24": {"treffer": 1, "neu": 1, "problem": ""}}}, TODAY + datetime.timedelta(days=2))
    assert store.last_success() == {"jobs.ch": "2026-11-09", "jobscout24": "2026-11-11"}


def test_screening_cuts_by_the_days_of_the_hits_portal(tmp_path):
    ad = {"portal": "jobs.ch", "portal_id": "w-1", "stelle": "Python Developer", "firma": "Beispiel AG",
          "link": "https://www.jobs.ch/de/stellenangebote/detail/w-1/", "alter_tage": 5}
    result = hits.Hits(tmp_path).screen([ad], (), 21, [], max_age_by_portal={"jobs.ch": 3})
    assert result["gefiltert"] == [{"stelle": "Python Developer", "grund": "älter als 3 Tage"}]


def test_the_plan_sends_the_days_per_portal_after_a_run(server):  # noqa: F811
    (server.kontext.daten / "suchprofil.md").write_text(profile("14 Tage"), encoding="utf-8")
    before = json.loads(get(server, "/api/suche/plan")[2])["plan"]
    assert before["max_alter_tage"] == 14
    assert set(before["max_alter_tage_portale"].values()) == {14}
    status, _ = post(server, "/api/suche/abschluss", {"portale": {"jobs.ch": {"treffer": 2, "neu": 1, "problem": ""}}})
    assert status == 200
    after = json.loads(get(server, "/api/suche/plan")[2])["plan"]
    assert (after["max_alter_tage"], after["max_alter_tage_portale"]["jobs.ch"], after["max_alter_tage_portale"]["job-room"]) == (14, 1, 14)
    old = {"portal": "jobs.ch", "portal_id": "w-2", "stelle": "Python Developer", "firma": "Beispiel AG",
           "link": "https://www.jobs.ch/de/stellenangebote/detail/w-2/", "alter_tage": 3}
    assert post(server, "/api/suche/sichten", {"treffer": [old]})[1]["gefiltert"] == [{"stelle": "Python Developer", "grund": "älter als 1 Tag"}]
