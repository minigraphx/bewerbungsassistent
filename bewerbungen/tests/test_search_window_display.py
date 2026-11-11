"""What Stellen suchen says about the search window (#208, option A of docs/design/suchzeitraum.md, G32).

The line under the title names the last search; a second line comes only when the next search starts elsewhere than
the last one did. Invented runs, today is Tuesday 10.11.2026.
"""
import datetime
import json

import pytest

import search_plan
import search_window
from test_app import get, post, server  # noqa: F401  (server is a fixture)

TODAY = datetime.date(2026, 11, 10)
JOBS = ("job-room", "jobs.ch", "jobscout24")
PROBLEM = "Die Seite von jobs.ch hat sich verändert. Die Suche dort braucht ein Update der Erweiterung."


def run(day: str, portals: dict, success: dict) -> dict:
    return {"datum": day, "portale": portals, "erfolgreich_am": success}


def ok(*names: str) -> dict:
    return {name: {"treffer": 5, "neu": 2, "problem": ""} for name in names}


def show(last_run, portals=JOBS, window=21, kind=search_plan.KIND_JOB) -> dict:
    return search_window.display(kind, window, portals, last_run, TODAY)


NORMAL = run("2026-11-09", ok(*JOBS), dict.fromkeys(JOBS, "2026-11-09"))


@pytest.mark.parametrize(("day", "said"), [("2026-11-10", "heute"), ("2026-11-09", "gestern"), ("2026-10-24", "am 24.10.2026")])
def test_the_last_search_is_named_by_its_day(day, said):
    assert search_window.when(day, TODAY) == said


def test_the_first_search_says_how_far_back_it_looks():
    assert show(None)["zeile"] == "Die erste Suche nimmt Inserate der letzten 21 Tage."
    assert show(None, window=14)["zeile"] == "Die erste Suche nimmt Inserate der letzten 14 Tage."


def test_nothing_more_when_every_portal_starts_where_the_last_search_did():
    shown = show(NORMAL)
    assert (shown["zeile"], shown["zeitfenster_aendern"], shown["nachholen"], shown["letzte"]) == ("", False, {}, "gestern")


def test_a_portal_that_was_off_catches_up():
    last = run("2026-11-09", ok("job-room", "jobs.ch"), {"job-room": "2026-11-09", "jobs.ch": "2026-11-09", "jobscout24": "2026-11-03"})
    assert show(last)["zeile"] == "jobscout24 holt ab 03.11.2026 nach."


def test_two_and_more_portals_catching_up():
    portals = ("job-room", "jobs.ch", "jobscout24", "ictjobs")
    same = {"job-room": "2026-11-09", "jobs.ch": "2026-11-09", "jobscout24": "2026-11-03", "ictjobs": "2026-11-03"}
    assert show(run("2026-11-09", ok("job-room", "jobs.ch"), same), portals)["zeile"] == "jobscout24 und ictjobs holen ab 03.11.2026 nach."
    apart = {**same, "ictjobs": "2026-11-06"}
    assert show(run("2026-11-09", ok("job-room", "jobs.ch"), apart), portals)["zeile"] == \
        "jobscout24 holt ab 03.11.2026 nach, ictjobs ab 06.11.2026."
    three = {**apart, "jobs.ch": "2026-11-05"}
    assert show(run("2026-11-09", ok("job-room"), three), portals)["zeile"] == "3 Portale holen nach, ab 03.11.2026."


def test_a_portal_that_never_searched_says_so():
    last = run("2026-11-09", ok(*JOBS), dict.fromkeys(JOBS, "2026-11-09"))
    assert show(last, (*JOBS, "ictjobs"))["zeile"] == "ictjobs sucht zum ersten Mal, die letzten 21 Tage."


def test_a_portal_with_a_problem_says_it_in_its_problem_line():
    last = run("2026-11-09", {**ok("job-room", "jobscout24"), "jobs.ch": {"treffer": 0, "neu": 0, "problem": PROBLEM}},
               {"job-room": "2026-11-09", "jobs.ch": "2026-11-06", "jobscout24": "2026-11-09"})
    shown = show(last)
    assert shown["zeile"] == ""
    assert shown["nachholen"] == {"jobs.ch": "Sobald die Suche dort wieder geht, holt sie die Inserate ab 06.11.2026 nach."}
    never = run("2026-11-09", last["portale"], {"job-room": "2026-11-09", "jobscout24": "2026-11-09"})
    assert show(never)["nachholen"] == {"jobs.ch": "Sobald die Suche dort wieder geht, holt sie die Inserate der letzten 21 Tage nach."}


def test_a_pause_longer_than_the_window_leaves_a_gap():
    last = run("2026-10-24", ok(*JOBS), dict.fromkeys(JOBS, "2026-10-24"))
    shown = show(last, window=14)
    assert shown["zeile"] == "Die nächste Suche nimmt nur die letzten 14 Tage, ab 28.10.2026."
    assert shown["zeitfenster_aendern"] is True
    assert show(last)["zeile"] == ""  # 21 days still reach back to 24.10


def test_the_change_link_comes_only_when_a_larger_window_closes_the_gap():
    long_ago = run("2026-08-01", ok(*JOBS), dict.fromkeys(JOBS, "2026-08-01"))
    assert show(long_ago)["zeile"] == "Die nächste Suche nimmt nur die letzten 21 Tage, ab 21.10.2026."
    assert show(long_ago)["zeitfenster_aendern"] is False
    at_most = run("2026-09-01", ok(*JOBS), dict.fromkeys(JOBS, "2026-09-01"))
    assert show(at_most, window=60)["zeitfenster_aendern"] is False


def test_the_gap_counts_before_catching_up():
    last = run("2026-10-01", ok("job-room", "jobs.ch"), {"job-room": "2026-10-01", "jobs.ch": "2026-10-01", "jobscout24": "2026-09-20"})
    assert show(last)["zeile"] == "Die nächste Suche nimmt nur die letzten 21 Tage, ab 21.10.2026."


def test_apprenticeships_and_further_sites_never_show_a_start_date():
    for last in (None, run("2026-08-01", ok("LENA", "yousty"), {"LENA": "2026-08-01"})):
        shown = show(last, search_plan.APPRENTICESHIP_PORTALS, kind=search_plan.KIND_APPRENTICESHIP)
        assert (shown["zeile"], shown["nachholen"], shown["portale"]) == ("", {}, [])
    site = run("2026-11-09", {**ok(*JOBS), "beispiel.ch": {"treffer": 0, "neu": 0, "problem": "Seite nicht geladen"}},
               dict.fromkeys(JOBS, "2026-11-09"))
    shown = show(site)
    assert (shown["zeile"], shown["nachholen"]) == ("", {})
    assert [p["portal"] for p in shown["portale"]] == list(JOBS)


def test_each_portal_with_its_last_success_and_its_start_for_the_settings():
    last = run("2026-11-09", {**ok("job-room"), "jobs.ch": {"treffer": 0, "neu": 0, "problem": PROBLEM}},
               {"job-room": "2026-11-09", "jobs.ch": "2026-11-06"})
    assert show(last)["portale"] == [
        {"portal": "job-room", "zuletzt": "gestern", "ab": "09.11.2026", "problem": False},
        {"portal": "jobs.ch", "zuletzt": "am 06.11.2026", "ab": "06.11.2026", "problem": True},
        {"portal": "jobscout24", "zuletzt": "", "ab": "21.10.2026", "problem": False}]


PROFILE = """# Suchprofil

## Portale und Rhythmus
Wochentag: Montag
- Zeitfenster: 14 Tage

| Portal | Modus |
|---|---|
| job-room | automatisch |

## Keywords
- Kernliste: Python
"""


def test_the_list_carries_the_window_display(server):  # noqa: F811
    (server.kontext.daten / "suchprofil.md").write_text(PROFILE, encoding="utf-8")
    shown = json.loads(get(server, "/api/suche/liste")[2])["zeitraum"]
    assert (shown["zeitfenster"], shown["zeile"]) == (14, "Die erste Suche nimmt Inserate der letzten 14 Tage.")


def test_the_settings_change_the_window_in_the_profile_with_a_draft(server):  # noqa: F811
    path = server.kontext.daten / "suchprofil.md"
    path.write_text(PROFILE, encoding="utf-8")
    status, answer = post(server, "/api/suche/zeitfenster", {"tage": 30})
    assert (status, answer["zeitfenster"]) == (200, 30)
    assert "- Zeitfenster: 30 Tage" in path.read_text(encoding="utf-8")
    assert "- Zeitfenster: 14 Tage" not in path.read_text(encoding="utf-8")
    assert len(server.kontext.ablage.liste(path)) >= 2  # before and after
    assert json.loads(get(server, "/api/suche/zeitfenster")[2])["zeitfenster"] == 30


def test_a_profile_without_the_line_gets_it_in_its_section(server):  # noqa: F811
    path = server.kontext.daten / "suchprofil.md"
    path.write_text(PROFILE.replace("- Zeitfenster: 14 Tage\n", ""), encoding="utf-8")
    assert post(server, "/api/suche/zeitfenster", {"tage": 7})[0] == 200
    section = search_plan.section_lines(path.read_text(encoding="utf-8"), "## Portale und Rhythmus")
    assert "- Zeitfenster: 7 Tage" in section


@pytest.mark.parametrize("days", [0, 61, "21", None, 2.5])
def test_the_window_stays_within_its_bounds(server, days):  # noqa: F811
    path = server.kontext.daten / "suchprofil.md"
    path.write_text(PROFILE, encoding="utf-8")
    status, answer = post(server, "/api/suche/zeitfenster", {"tage": days})
    assert status == 400 and "1 bis 60 Tage" in answer["fehler"]
    assert path.read_text(encoding="utf-8") == PROFILE
