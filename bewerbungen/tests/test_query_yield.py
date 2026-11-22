"""Which query found each hit, and what each term and place brought (G103, #375). Invented terms and places only."""
import datetime
import json

import pytest
import yaml

import hits
import query_log
import search_yield
from test_routes_search import HIT, listing, search  # noqa: F401  (search is a fixture)
from test_app import get, post, server  # noqa: F401  (server is a fixture)

TODAY = datetime.date(2026, 11, 20)
AARAU = {"stichwort": "Lernbegleiter", "ort": "Aarau"}
OLTEN = {"stichwort": "Kursleiter", "ort": "Olten"}


def hit(**fields) -> dict:
    base = {"portal": "jobs.ch", "portal_id": "q-1", "stelle": "Lernbegleiter Primarstufe", "firma": "Muster Schule AG",
            "ort": "Aarau", "link": "https://www.jobs.ch/de/stellenangebote/detail/q-1/", "text": "Begleitung im Lernatelier."}
    return {**base, **fields}


@pytest.fixture
def store(tmp_path):
    return hits.Hits(tmp_path)


# What a hit keeps

def test_a_hit_keeps_every_query_that_found_it(store):
    store.add([hit(abfragen=[AARAU, OLTEN])], [], TODAY)
    [stored] = store.all()
    assert stored["abfragen"] == [{"portal": "jobs.ch", **AARAU}, {"portal": "jobs.ch", **OLTEN}]


def test_a_twin_from_another_portal_adds_its_queries(store):
    store.add([hit(abfragen=[AARAU])], [], TODAY)
    twin = hit(portal="job-room", portal_id="jr-1", link="https://www.job-room.ch/job-search/jr-1",
               abfragen=[{"stichwort": "Lernbegleiter", "ort": "AG, SO"}])
    assert store.add([twin], [], TODAY)["zusammengefuehrt"] == 1
    [stored] = store.all()
    assert stored["abfragen"] == [{"portal": "jobs.ch", **AARAU}, {"portal": "job-room", "stichwort": "Lernbegleiter", "ort": "AG, SO"}]


def test_a_twin_met_while_screening_adds_its_queries_too(store):
    store.add([hit(abfragen=[AARAU])], [], TODAY)
    twin = hit(portal="jobscout24", portal_id="js-1", link="https://www.jobscout24.ch/de/job/js-1/",
               abfragen=[{"stichwort": "Lernbegleiter", "ort": "5000"}])
    store.screen([twin], (), 45, [])
    [stored] = store.all()
    assert {"portal": "jobscout24", "stichwort": "Lernbegleiter", "ort": "5000"} in stored["abfragen"]


@pytest.mark.parametrize("queries", ["Aarau", [{"ort": "Aarau"}], ["Lernbegleiter"], [{"stichwort": ["x"], "ort": ""}]])
def test_queries_in_another_form_are_refused(queries):
    with pytest.raises(ValueError):
        hits.validate(hit(abfragen=queries))


def test_a_hit_from_an_older_extension_has_no_queries(store):
    store.add([hit()], [], TODAY)
    assert "abfragen" not in store.all()[0]


def test_screening_names_each_title_screen_out_with_its_queries(store):
    outs = []
    listing_ = [hit(portal_id="q-2", stelle="Praktikum Lernbegleitung", link=hit()["link"] + "2", abfragen=[AARAU]),
                hit(portal_id="q-3", stelle="Kursleiter Yoga", link=hit()["link"] + "3", abfragen=[OLTEN]),
                hit(portal_id="q-4", stelle="Lernbegleiter alt", link=hit()["link"] + "4", alter_tage=90, abfragen=[AARAU])]
    store.screen(listing_, ("Praktikum",), 45, [], title_positive=("Lernbegleiter",),
                 on_screened_out=lambda found, reason: outs.append((found["abfragen"], found["stelle"], reason)))
    assert outs == [([{"portal": "jobs.ch", **AARAU}], "Praktikum Lernbegleitung", "Titel: Praktikum"),
                    ([{"portal": "jobs.ch", **OLTEN}], "Kursleiter Yoga", hits.NO_POSITIVE_TERM)], "an old ad is no title screen-out"


# The log of the runs

def test_a_run_records_each_query_with_its_count_screen_outs_and_date(tmp_path):
    log = query_log.QueryLog(tmp_path)
    for number in range(4):
        log.note_screened([{"portal": "jobs.ch", **AARAU}], f"Praktikum {number}", "Titel: Praktikum")
    log.close_run({"jobs.ch": [{**AARAU, "treffer": 5}, {**OLTEN, "treffer": 0}]}, TODAY)
    [run] = log.runs()
    assert run["datum"] == "2026-11-20"
    first, empty = run["abfragen"]
    assert (first["portal"], first["stichwort"], first["ort"], first["treffer"], first["aussortiert"]) == ("jobs.ch", "Lernbegleiter", "Aarau", 5, 4)
    assert first["beispiele"] == [{"stelle": f"Praktikum {n}", "grund": "Titel: Praktikum"} for n in range(3)]
    assert empty == {"portal": "jobs.ch", **OLTEN, "treffer": 0}, "a query without hits is recorded too"


def test_only_the_last_three_runs_are_kept_and_screen_outs_belong_to_one_run(tmp_path):
    log = query_log.QueryLog(tmp_path)
    log.note_screened([{"portal": "jobs.ch", **AARAU}], "Praktikum", "Titel: Praktikum")
    for day in range(1, 5):
        log.close_run({"jobs.ch": [{**AARAU, "treffer": day}]}, datetime.date(2026, 11, day))
    assert [run["datum"] for run in log.runs()] == ["2026-11-02", "2026-11-03", "2026-11-04"]
    assert all("aussortiert" not in run["abfragen"][0] for run in log.runs())


def test_a_run_of_an_older_extension_records_nothing(tmp_path):
    log = query_log.QueryLog(tmp_path)
    assert log.close_run({"jobs.ch": []}, TODAY) is None
    assert log.runs() == []


@pytest.mark.parametrize("queries", ["x", [{"ort": "Aarau", "treffer": 1}], [{**AARAU, "treffer": -1}], [{**AARAU, "treffer": True}]])
def test_queries_of_a_summary_in_another_form_are_refused(queries):
    with pytest.raises(ValueError):
        query_log.checked_queries(queries)


# The yield

def run(day: int, *queries) -> dict:
    return {"datum": f"2026-11-{day:02d}", "abfragen": [{"portal": p, "stichwort": s, "ort": o, "treffer": t, **extra}
                                                        for p, s, o, t, extra in queries]}


def stored(found: str, grade=None, queries=None, portal="jobs.ch") -> dict:
    entry = {"id": f"h-{found}-{grade}", "portal": portal, "stelle": "Stelle", "firma": "Muster AG", "gefunden_am": found}
    if grade is not None:
        entry["bewertung"] = {"note": grade}
    return {**entry, "abfragen": queries} if queries is not None else entry


RUNS = [run(day, ("jobs.ch", "Lernbegleiter", "Aarau", 4, {"aussortiert": 1}), ("jobs.ch", "Lernbegleiter", "Olten", 0, {}),
            ("ictjobs", "Kursleiter", "aargau", 0, {}), ("job-room", "Lernbegleiter", "AG, SO", 2, {}))
        for day in (10, 14, 18)]
FOUND = [{"portal": "jobs.ch", "stichwort": "Lernbegleiter", "ort": "Aarau"}]
HITS = [stored("2026-11-14", 4.5, FOUND), stored("2026-11-18", 3, FOUND),
        stored("2026-11-02", 5, FOUND), stored("2026-10-01"), stored("2026-11-18", portal="weitere.example.ch")]


def test_the_yield_per_term_counts_searches_hits_new_good_and_screened_out():
    result = search_yield.summary(RUNS, HITS, ["Lernbegleiter", "Kursleiter", "Lehrperson"], with_places=True)
    assert result["laeufe"] == 3
    assert result["begriffe"] == [
        {"begriff": "Lernbegleiter", "suchen": 9, "treffer": 18, "neu": 2, "ab_note_4": 1, "aussortiert": 3, "ohne_ertrag": False},
        {"begriff": "Kursleiter", "suchen": 3, "treffer": 0, "neu": 0, "ab_note_4": 0, "aussortiert": 0, "ohne_ertrag": True},
        {"begriff": "Lehrperson", "suchen": 0, "treffer": 0, "neu": 0, "ab_note_4": 0, "aussortiert": 0, "ohne_ertrag": False}]


def test_a_term_whose_hits_the_title_filter_all_screened_out_is_without_yield_too():
    runs = [run(day, ("jobs.ch", "Kursleiter", "Aarau", 2, {"aussortiert": 2}), ("jobs.ch", "Lernbegleiter", "Aarau", 2, {"aussortiert": 1}))
            for day in (10, 14, 18)]
    result = search_yield.summary(runs, [], ["Kursleiter", "Lernbegleiter"], with_places=True)
    assert [(entry["begriff"], entry["treffer"], entry["aussortiert"], entry["ohne_ertrag"]) for entry in result["begriffe"]] \
        == [("Kursleiter", 6, 6, True), ("Lernbegleiter", 6, 3, False)], "a hit past the title filter is yield"
    assert result["leer"] == [], "«Wo ein Begriff nichts findet» still lists only searches without a single hit"


def test_searches_that_found_nothing_stand_per_term_and_portal():
    result = search_yield.summary(RUNS, HITS, ["Lernbegleiter", "Kursleiter"], with_places=True)
    assert result["leer"] == [{"begriff": "Kursleiter", "portal": "ictjobs", "suchen": 3, "laeufe": 3, "nische": False}], \
        "Lernbegleiter found something on jobs.ch in Aarau, so its empty searches in Olten are no empty portal"


def test_an_empty_niche_is_marked_as_one():
    runs = [run(10, ("jobs.ch", "Lernatelier", "", 0, {}), ("jobs.ch", "Kursleiter", "Aarau", 0, {}))]
    empty = search_yield.summary(runs, [], ["Kursleiter"], with_places=True, keywords=("Lernatelier",))["leer"]
    assert [(entry["begriff"], entry["nische"]) for entry in empty] == [("Lernatelier", True), ("Kursleiter", False)]


def test_the_yield_per_place_follows_portal_and_place():
    places = search_yield.summary(RUNS, HITS, ["Lernbegleiter"], with_places=True)["orte"]
    assert places == [
        {"portal": "job-room", "ort": "AG, SO", "ort_name": "AG, SO", "suchen": 3, "treffer": 6, "neu": 0, "ab_note_4": 0,
         "aussortiert": 0, "ohne_ertrag": False},
        {"portal": "jobs.ch", "ort": "Aarau", "ort_name": "Aarau", "suchen": 3, "treffer": 12, "neu": 2, "ab_note_4": 1,
         "aussortiert": 3, "ohne_ertrag": False},
        {"portal": "jobs.ch", "ort": "Olten", "ort_name": "Olten", "suchen": 3, "treffer": 0, "neu": 0, "ab_note_4": 0,
         "aussortiert": 0, "ohne_ertrag": True},
        {"portal": "ictjobs", "ort": "aargau", "ort_name": "Aargau", "suchen": 3, "treffer": 0, "neu": 0, "ab_note_4": 0,
         "aussortiert": 0, "ohne_ertrag": True}], "the portals in their order, the places as they came; ictjobs by the name of its region"


def test_a_search_without_place_comes_last_in_its_portal():
    runs = [run(10, ("jobs.ch", "Lernbegleiter", "Aarau", 1, {}), ("jobs.ch", "Lernatelier", "", 0, {}), ("jobs.ch", "Lernbegleiter", "Olten", 2, {}))]
    places = search_yield.summary(runs, [], [], with_places=True)["orte"]
    assert [place["ort"] for place in places] == ["Aarau", "Olten", ""]


def test_hits_of_the_portals_from_before_count_without_a_query():
    assert search_yield.summary(RUNS, HITS, [], with_places=True)["ohne_angabe"] == 1, "a site the person named never had queries"


def test_no_mark_until_three_runs_have_data():
    result = search_yield.summary(RUNS[:2], HITS, ["Kursleiter"], with_places=True)
    assert result["laeufe"] == 2
    assert result["begriffe"][0]["ohne_ertrag"] is False
    assert all(not place["ohne_ertrag"] for place in result["orte"])


def test_an_apprenticeship_search_shows_the_yield_per_profession_only():
    result = search_yield.summary(RUNS, HITS, ["Lernbegleiter"], with_places=False)
    assert result["orte"] == []
    assert result["begriffe"][0]["suchen"] == 9


def test_before_the_first_run_there_is_nothing_to_count():
    result = search_yield.summary([], HITS, ["Lernbegleiter"], with_places=True)
    assert (result["laeufe"], result["begriffe"][0]["suchen"], result["leer"], result["orte"]) == (0, 0, [], [])


# The run through the routes

def test_after_a_run_every_new_hit_names_its_query_and_the_page_has_the_yield(search):
    found = {**HIT, "abfragen": [{"stichwort": "Python", "ort": "Bern"}]}
    out = {**HIT, "portal_id": "p-2", "stelle": "Praktikum Python", "link": HIT["link"] + "p2",
           "abfragen": [{"stichwort": "Python", "ort": "Bern"}]}
    assert post(search, "/api/suche/sichten", {"treffer": [found, out]})[0] == 200
    assert post(search, "/api/suche/treffer", {"treffer": [found]})[1]["neu"] == 1
    queries = [{"stichwort": "Python", "ort": "Bern", "treffer": 2}, {"stichwort": "E-Learning", "ort": "Bern", "treffer": 0}]
    status, run_ = post(search, "/api/suche/abschluss", {"portale": {"jobs.ch": {"treffer": 2, "neu": 1, "problem": "", "abfragen": queries}}})
    assert status == 200
    assert "abfragen" not in run_["portale"]["jobs.ch"], "the last run stays a summary"

    assert all(h.get("abfragen") for h in listing(search)["treffer"])
    status, _, content = get(search, "/api/suche/ertrag")
    assert status == 200
    shown = json.loads(content)
    python = next(term for term in shown["begriffe"] if term["begriff"] == "Python")
    assert python == {"begriff": "Python", "suchen": 1, "treffer": 2, "neu": 1, "ab_note_4": 0, "aussortiert": 1, "ohne_ertrag": False}
    assert {"portal": "jobs.ch", "ort": "Bern", "ort_name": "Bern", "suchen": 2, "treffer": 2, "neu": 1, "ab_note_4": 0, "aussortiert": 1,
            "ohne_ertrag": False} in shown["orte"]
    assert shown["leer"] == [{"begriff": "E-Learning", "portal": "jobs.ch", "suchen": 1, "laeufe": 1, "nische": False}]
    assert (shown["laeufe"], shown["art"]) == (1, "stelle")
    logged = yaml.safe_load((search.kontext.daten / "suche" / query_log.RUNS_FILE).read_text(encoding="utf-8"))
    assert {"portal": "jobs.ch", "stichwort": "E-Learning", "ort": "Bern", "treffer": 0} in logged[0]["abfragen"]
    assert logged[0]["datum"]


def test_a_summary_with_queries_in_another_form_is_refused(search):
    body = {"portale": {"jobs.ch": {"treffer": 1, "neu": 0, "abfragen": [{"ort": "Bern", "treffer": 1}]}}}
    assert post(search, "/api/suche/abschluss", body)[0] == 400
