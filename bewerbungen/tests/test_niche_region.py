"""Niche searches respect the region unless the ad names remote work (G111, #387).

Niches run without a place, so they search the whole country. A hit only they found stays if its place lies in the
chosen cantons or at the places the app counts as home, or if its title or ad text names remote work; the others are
counted with the reason «ausserhalb der Region, kein Remote». The profile is the invented template (Kantone BE, SO;
Orte Bern, Solothurn); every title, company and outside place here is invented or a large town far from it.
"""
import datetime
import json
import pathlib

import pytest

import hits
import niche_region
import place_cantons
import query_log
import required_words
import search_plan
import search_yield
import term_evidence
from test_app import get, post, server  # noqa: F401  (server is a fixture)
from test_routes_search import search  # noqa: F401  (search is a fixture)

TODAY = datetime.date(2026, 11, 22)
VORLAGEN = pathlib.Path(__file__).resolve().parents[2] / "vorlagen"
NICHE = {"stichwort": "EdTech", "ort": ""}
PLACED = {"stichwort": "Python", "ort": "Bern"}
TITLE = "EdTech Produktmanager (m/w/d)"
REASON = "ausserhalb der Region, kein Remote"


def profile(text: str | None = None) -> str:
    base = (VORLAGEN / "suchprofil.md").read_text(encoding="utf-8") if text is None else text
    # the template's title filter would keep the invented titles out before the region is asked
    return base.replace("- Positiv: Python, Software, Entwickler/Developer/Engineer, Daten/Data, Web, Learning, Trainer\n", "", 1)


def region_of(text: str | None = None) -> niche_region.Region:
    return niche_region.of_plan(search_plan.parse(profile(text)))


def hit(number: int, place: str, title: str = TITLE, queries=(NICHE,), text: str = "Wir bauen Lernsoftware.") -> dict:
    return {"portal": "jobs.ch", "portal_id": f"nr-{number}", "stelle": title, "firma": f"Beispiel Lernen {number} AG",
            "ort": place, "link": f"https://www.jobs.ch/de/stellenangebote/detail/nr-{number}/", "text": text,
            "abfragen": list(queries)}


@pytest.fixture
def store(tmp_path):
    return hits.Hits(tmp_path)


def added(store, found: dict, region: niche_region.Region | None = None) -> dict:
    return store.add([found], [], TODAY, region=region_of() if region is None else region)


# The criterion

def test_a_niche_hit_outside_the_region_without_remote_is_screened_out_with_its_reason(store):
    outside = []
    region = region_of()
    assert store.screen([hit(1, "Lugano")], (), 45, [], region=region)["holen"] == ["jobs.ch:nr-1"], \
        "its ad text may still name remote work, so it is loaded"

    result = store.add([hit(1, "Lugano")], [], TODAY, region=region, on_outside=outside.append)

    assert (result["neu"], result["ausserhalb_region"]) == (0, 1)
    assert store.all() == []
    assert [found["stelle"] for found in outside] == [TITLE]
    assert niche_region.REASON == REASON


def test_the_same_hit_with_100_percent_remote_in_the_ad_is_kept(store):
    assert added(store, hit(2, "Lugano", text="Die Stelle ist 100 % remote.")) == {"neu": 1, "zusammengefuehrt": 0, "abgelehnt": []}


def test_a_remote_mention_keeps_the_hit_also_when_the_profile_says_remote_no(store):
    text = profile().replace("- Remote: ja", "- Remote: nein", 1)
    assert "- Remote: nein" in text
    assert added(store, hit(3, "Lugano", text="Die Stelle ist 100 % remote."), region_of(text))["neu"] == 1


def test_a_remote_title_is_enough(store):
    assert added(store, hit(4, "Lugano", title="Remote EdTech Lead"))["neu"] == 1


# What counts as remote

@pytest.mark.parametrize("text", ["Wir arbeiten remote.", "REMOTE-first", "Homeoffice 100 %", "Homeoffice 100%",
                                  "100 % Homeoffice", "100% Home-Office möglich", "Arbeitsort ortsunabhängig",
                                  "Télétravail à 100 %", "teletravail possible", "Homeoffice 100 %"])
def test_remote_words_are_found_in_any_case(text):
    assert niche_region.mentions_remote(text)


@pytest.mark.parametrize("text", ["Homeoffice nach Absprache", "1 Tag Homeoffice", "Büro in Lugano", ""])
def test_a_partial_home_office_is_no_remote_mention(text):
    assert not niche_region.mentions_remote(text)


# Where the hit lies

@pytest.mark.parametrize("place", ["Olten", "4600 Olten", "Bern", "3011 Bern", "Thun", "Köniz BE", "Kanton Solothurn",
                                   "Lugano, Olten", "Homeoffice", "Remote", "Schweiz", "", "Musterhausen", "Buchs",
                                   "Mehrere Standorte", "4512 Bellach"])
def test_places_in_the_region_unknown_or_ambiguous_keep_the_hit(place):
    assert region_of().inside(place), place


@pytest.mark.parametrize("place", ["Lugano", "6900 Lugano", "CH-6900 Lugano", "Lugano TI", "Lugano, Schweiz",
                                   "Lugano, Locarno", "Kanton Tessin", "Genève", "St. Gallen"])
def test_known_places_in_other_cantons_lie_outside(place):
    assert not region_of().inside(place), place


@pytest.mark.parametrize("place", ["6003 Luzern", "Luzern 6003"])
def test_a_place_written_with_its_postcode_is_found_through_its_town_name(store, place):
    outside = []
    result = store.add([hit(12, place)], [], TODAY, region=region_of(), on_outside=outside.append)
    assert (result["neu"], result["ausserhalb_region"], len(outside)) == (0, 1, 1)

    again = store.screen([hit(12, place)], (), 45, [], region=region_of())

    assert again["gefiltert"] == [{"stelle": TITLE, "grund": REASON}]


def test_a_bare_postcode_without_a_town_name_keeps_the_hit(store):
    assert added(store, hit(13, "6003"))["neu"] == 1


def test_the_canton_of_a_place_comes_from_the_shared_table():
    assert place_cantons.canton_in("6900 Lugano") == "TI"
    assert place_cantons.canton_in("Lugano (TI)") == "TI"
    assert place_cantons.canton_in("Kanton Tessin") == "TI"
    assert place_cantons.canton_in("Basel-Stadt") == "BS"
    assert place_cantons.canton_in("Buchs") is None, "a name in several cantons stays unknown"
    assert place_cantons.canton_in("Musterhausen") is None


# When the rule is off

def test_without_chosen_cantons_the_rule_is_off(store):
    text = profile().replace("- Kantone (job-room): BE, SO\n", "", 1)
    region = region_of(text)
    assert not region.active
    assert added(store, hit(5, "Lugano"), region)["neu"] == 1


def test_a_hit_also_found_by_a_place_bound_search_is_not_affected(store):
    assert added(store, hit(6, "Lugano", queries=(NICHE, PLACED)))["neu"] == 1


def test_a_hit_from_an_older_extension_without_queries_is_not_affected(store):
    assert added(store, hit(7, "Lugano", queries=()))["neu"] == 1


def test_a_niche_also_in_the_term_list_counts_as_place_bound():
    text = profile().replace("- Kernliste: Python,", "- Kernliste: EdTech, Python,", 1)
    assert not region_of(text).niche_only([{"portal": "jobs.ch", **NICHE}])


def test_an_apprenticeship_search_has_no_such_rule():
    plan = search_plan.parse((VORLAGEN / "suchprofil-lehrstelle.md").read_text(encoding="utf-8"))
    assert niche_region.of_plan(plan) == niche_region.OFF


# Remembered links

def test_a_screened_link_is_not_loaded_again_until_cantons_or_places_change(store):
    store.add([hit(8, "Lugano")], [], TODAY, region=region_of())
    outs = []

    again = store.screen([hit(8, "Lugano")], (), 45, [], region=region_of(),
                         on_screened_out=lambda found, reason: outs.append((found["stelle"], reason)))

    assert (again["holen"], again["gefiltert"]) == ([], [{"stelle": TITLE, "grund": REASON}])
    assert outs == [(TITLE, REASON)]
    cantons = profile().replace("- Kantone (job-room): BE, SO", "- Kantone (job-room): BE, SO, TI", 1)
    assert store.screen([hit(8, "Lugano")], (), 45, [], region=region_of(cantons))["holen"] == ["jobs.ch:nr-8"]
    places = profile().replace("- Orte (jobs.ch, LinkedIn): Bern, Solothurn", "- Orte (jobs.ch, LinkedIn): Bern, Biel", 1)
    assert store.screen([hit(8, "Lugano")], (), 45, [], region=region_of(places))["holen"] == ["jobs.ch:nr-8"]


def test_a_remembered_link_with_a_remote_title_now_is_loaded(store):
    store.add([hit(9, "Lugano")], [], TODAY, region=region_of())
    assert store.screen([hit(9, "Lugano", title="EdTech Lead (remote)")], (), 45, [], region=region_of())["holen"] \
        == ["jobs.ch:nr-9"]


# Both reasons together

def test_a_hit_without_its_required_word_counts_once_and_only_as_such(store):
    text = profile().replace("- Nischen (ohne Ort suchen): EdTech,", "- Nischen (ohne Ort suchen): EdTech (nur mit Informatik),", 1)
    required = required_words.of_profile(text)
    unrelated, outside = [], []

    result = store.add([hit(10, "Lugano"), hit(11, "Lugano", title="EdTech Informatik Coach")], [], TODAY,
                       required=required, region=region_of(text), on_unrelated=unrelated.append, on_outside=outside.append)

    assert (result["neu"], result["ohne_pflichtbezug"], result["ausserhalb_region"]) == (0, 1, 1)
    assert [found["portal_id"] for found in unrelated] == ["nr-10"]
    assert [found["portal_id"] for found in outside] == ["nr-11"]
    again = store.screen([hit(10, "Lugano"), hit(11, "Lugano", title="EdTech Informatik Coach")], (), 45, [],
                         required=required, region=region_of(text))
    assert [entry["grund"] for entry in again["gefiltert"]] == ["ohne Pflichtbezug", REASON]


# Counting

def test_the_run_counts_hits_outside_per_query_with_their_places(tmp_path):
    log = query_log.QueryLog(tmp_path)
    query = {"portal": "jobs.ch", **NICHE}
    for place in ("6900 Lugano", "Lugano", "St. Gallen"):
        log.note_outside([query], place)
    log.close_run({"jobs.ch": [{**NICHE, "treffer": 5}]}, TODAY)
    [entry] = log.runs()[0]["abfragen"]
    assert entry["ausserhalb_region"] == 3
    assert entry["ausserhalb_orte"] == {"Lugano": 2, "St. Gallen": 1}


def niche_runs(counts: list[int]) -> list[dict]:
    places = {"Lugano": 4, "St. Gallen": 3, "Chur": 2, "Genève": 1}
    return [{"datum": f"2026-11-{10 + day:02d}", "abfragen": [
        {"portal": "jobs.ch", **NICHE, "treffer": count, **({"ausserhalb_region": count, "ausserhalb_orte": places} if count else {})},
        {"portal": "job-room", **NICHE, "treffer": 1},
        {"portal": "jobs.ch", **PLACED, "treffer": 2}]} for day, count in enumerate(counts)]


def test_the_places_name_a_niche_row_with_the_hits_outside_and_where_they_lay():
    rows = search_yield.summary(niche_runs([10, 10, 10]), [], ["Python"], with_places=True, keywords=("EdTech",))["orte"]
    niche = rows[-1]
    assert (niche["nischen"], niche["suchen"], niche["treffer"], niche["ausserhalb_region"]) == (True, 6, 33, 30)
    assert niche["ausserhalb_orte"] == [{"ort": "Lugano", "anzahl": 12}, {"ort": "St. Gallen", "anzahl": 9},
                                        {"ort": "Chur", "anzahl": 6}]
    assert niche["ausserhalb_andere"] == 3
    assert all(row["ort"] for row in rows[:-1]), "the niche searches leave the place-less rows of their portals"


def test_hits_outside_the_region_bring_no_yield():
    only_outside = [{"datum": f"2026-11-{10 + day:02d}", "abfragen": [
        {"portal": "jobs.ch", **NICHE, "treffer": 2, "ausserhalb_region": 2, "ausserhalb_orte": {"Lugano": 2}}]} for day in range(3)]
    result = search_yield.summary(only_outside, [], ["EdTech"], with_places=True, keywords=("EdTech",))
    assert (result["begriffe"][0]["ausserhalb_region"], result["begriffe"][0]["ohne_ertrag"]) == (6, True)


def test_the_term_review_counts_them_with_the_screened_and_names_them_apart():
    counted = term_evidence.keyword_counts(niche_runs([2, 2, 2]), [], ("Python",), ("EdTech",))
    [niche] = counted.as_dict()["nischen"]
    assert (niche["aussortiert"], niche["ausserhalb_region"]) == (6, 6)


# Through the routes

def write_profile(s, text: str) -> None:
    (s.kontext.daten / search_plan.PROFILE).write_text(text, encoding="utf-8")


def test_a_run_screens_out_the_hit_outside_and_the_page_names_it(search):  # noqa: F811
    write_profile(search, profile())
    listing = [hit(1, "Olten"), hit(2, "Lugano")]
    assert post(search, "/api/suche/sichten", {"treffer": listing})[1]["holen"] == ["jobs.ch:nr-1", "jobs.ch:nr-2"]
    received = post(search, "/api/suche/treffer", {"treffer": listing})[1]
    assert (received["neu"], received["ausserhalb_region"]) == (1, 1)
    queries = [{**NICHE, "treffer": 2}, {**PLACED, "treffer": 0}]
    post(search, "/api/suche/abschluss", {"portale": {"jobs.ch": {"treffer": 2, "neu": 1, "problem": "", "abfragen": queries}}})

    page = json.loads(get(search, "/api/suche/liste")[2])
    assert [h["ort"] for h in page["treffer"]] == ["Olten"]
    assert page["region"]["nischen"] == 2
    shown = json.loads(get(search, "/api/suche/ertrag")[2])
    niche = next(row for row in shown["orte"] if row.get("nischen"))
    assert (niche["ausserhalb_region"], niche["ausserhalb_orte"]) == (1, [{"ort": "Lugano", "anzahl": 1}])

    again = post(search, "/api/suche/sichten", {"treffer": [hit(2, "Lugano")]})[1]
    assert (again["holen"], again["gefiltert"]) == ([], [{"stelle": TITLE, "grund": REASON}])
