"""G43: the search reads every term and place without a fixed maximum, and the app announces a long run.

The searches per portal come from the same invented plans the extension's tests read (erweiterung/tests/fixtures).
"""
import json
import pathlib

import search_plan
import search_stages
from test_app import get, server  # noqa: F401  (server is a fixture)

CASES = json.loads((pathlib.Path(__file__).resolve().parents[2] / "erweiterung" / "tests" / "fixtures" / "run-size.json")
                   .read_text(encoding="utf-8"))["cases"]
TERMS = tuple(f"Begriff{n}" for n in range(1, 25))
PLACES = ("Nordstadt", "Südstadt", "Oststadt", "Weststadt", "Mittelstadt", "Bergdorf", "Seedorf", "Talstadt")


def profile(terms: tuple[str, ...] = TERMS, places: tuple[str, ...] = PLACES) -> str:
    return f"""# Suchprofil

## Region
- Kantone (job-room): BE
- Orte (jobs.ch): {", ".join(places)}
- PLZ (jobscout24): 1111

## Keywords
- Kernliste: {", ".join(terms)}
- Nischen (ohne Ort suchen): Nische1
"""


def test_every_term_and_place_of_the_profile_is_searched():
    plan = search_plan.parse(profile())
    assert plan.keywords == TERMS
    assert plan.places == PLACES
    assert not any("Nicht gesucht" in hint or "reichen nicht" in hint for hint in plan.hints)


def test_the_app_counts_the_same_searches_per_portal_as_the_extension():
    for case in CASES:
        assert search_stages.searches_per_portal(case["plan"]) == case["searches"], case["name"]


def test_a_long_run_names_searches_stages_and_the_rough_duration():
    plan = search_plan.chosen(search_plan.parse(profile()), ["job-room", "jobscout24", "ictjobs"]).as_dict()
    size = search_stages.size(plan)
    # jobs.ch: 24 terms in 8 places and one niche, 193 searches in 7 stages; the other portals are switched off.
    assert (size["suchen"], size["etappen"], size["lang"]) == (193, 7, True)
    seconds = 193 * search_stages.SECONDS_PER_SEARCH + 6 * search_stages.STAGE_PAUSE_SECONDS
    assert size["minuten"] == -(-seconds // 60) == 23
    assert size["text"] == ("Diese Suche dauert etwa 23 Minuten: 193 Suchen in 7 Etappen, mit je einer Minute Pause "
                            "dazwischen. Viele neue Inserate machen sie länger.")


def test_a_short_run_is_not_announced():
    plan = search_plan.parse(profile(TERMS[:3], PLACES[:2])).as_dict()
    size = search_stages.size(plan)
    assert size["lang"] is False and size["text"] == ""
    assert size["suchen"] == 4 + 7 + 3 + 3  # job-room, jobs.ch, jobscout24, ictjobs
    assert size["etappen"] == 4


def test_the_extension_gets_the_stage_size_the_pause_and_the_announcement(server):  # noqa: F811
    (server.kontext.daten / "suchprofil.md").write_text(profile(), encoding="utf-8")
    plan = json.loads(get(server, "/api/suche/plan")[2])["plan"]
    assert (plan["etappe_abfragen"], plan["etappe_pause_sekunden"]) == (30, 60)
    assert plan["umfang"]["lang"] and "Etappen" in plan["umfang"]["text"]
    assert plan["max_abfragen"] == search_plan.MAX_QUERIES, "an older extension still stops there instead of running all at once"


def test_the_page_stellen_gets_the_announcement(server):  # noqa: F811
    (server.kontext.daten / "suchprofil.md").write_text(profile(), encoding="utf-8")
    answer = json.loads(get(server, "/api/suche/liste")[2])
    assert answer["umfang"]["lang"] and answer["umfang"]["suchen"] > search_stages.STAGE_SIZE
