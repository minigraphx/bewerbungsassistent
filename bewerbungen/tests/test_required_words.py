"""Required context words of a broad keyword (G110, #386): «Berufsbildner (nur mit Informatik, ICT, Plattform)».

A hit found only through such a keyword stays only if its title, or its ad text when that is loaded anyway, names one
of the words; the others are counted with the reason «ohne Pflichtbezug». Invented profiles, titles and companies only.
"""
import datetime
import json
import pathlib

import pytest

import hits
import query_log
import required_words
import search_plan
import search_yield
from test_app import get, post, server  # noqa: F401  (server is a fixture)
from test_routes_search import search  # noqa: F401  (search is a fixture)

TODAY = datetime.date(2026, 11, 22)
VORLAGEN = pathlib.Path(__file__).resolve().parents[2] / "vorlagen"
BROAD = "Berufsbildner (nur mit Informatik, ICT, Plattform)"
CORE = f"- Kernliste: Lernbegleiter, {BROAD}, Kursplaner"
TEMPLATE_CORE = "- Kernliste: Python, TypeScript, Softwareentwickler, Data Engineer, E-Learning, Kursleiter (nur mit Informatik, ICT)"
COACH = {"stichwort": "Berufsbildner", "ort": "Bern"}
GUIDE = {"stichwort": "Lernbegleiter", "ort": "Bern"}
PASSES = "Berufsbildner Plattformentwickler (a)"
UNRELATED = "Koch/Köchin EFZ – Berufsbildner/in"


def profile(core: str = CORE) -> str:
    text = (VORLAGEN / "suchprofil.md").read_text(encoding="utf-8")
    changed = text.replace(TEMPLATE_CORE, core, 1)
    assert changed != text
    # the template's title filter would keep these invented titles out before the required words are asked
    return changed.replace("- Positiv: Python, Software, Entwickler/Developer/Engineer, Daten/Data, Web, Learning, Trainer\n", "", 1)


def hit(number: int, title: str, queries=(COACH,), text: str = "Wir bilden Lernende aus.") -> dict:
    return {"portal": "jobs.ch", "portal_id": f"pb-{number}", "stelle": title, "firma": f"Beispiel Betrieb {number} AG",
            "ort": "Bern", "link": f"https://www.jobs.ch/de/stellenangebote/detail/pb-{number}/", "text": text,
            "abfragen": list(queries)}


# Reading the remark

def test_a_remark_names_the_required_words_of_its_term_only():
    required = required_words.of_profile(profile())
    assert required.of_term("Berufsbildner") == ("Informatik", "ICT", "Plattform")
    assert required.of_term("Lernbegleiter") == ()
    assert required.of_term("Berufsbildnerin") == ("Informatik", "ICT", "Plattform"), "the gender form is one term"


def test_the_plan_and_the_portal_query_carry_only_the_term():
    plan = search_plan.parse(profile())
    assert plan.keywords == ("Lernbegleiter", "Berufsbildner", "Kursplaner")
    assert all("nur mit" not in term for term in plan.as_dict()["stichworte"])


def test_a_remark_holds_for_every_alternative_of_its_slash_group():
    required = required_words.of_profile(profile("- Kernliste: Ausbilder/Berufsbildner (nur mit ICT), Lernbegleiter"))
    assert required.of_term("Ausbilder") == required.of_term("Berufsbildner") == ("ICT",)


@pytest.mark.parametrize("line", ["- Nischen (ohne Ort suchen): Berufsbildner (nur mit ICT)",
                                  "- Nur jobs.ch, job-room: Berufsbildner (nur mit ICT)",
                                  "- Weiterbildung: Berufsbildner (nur mit ICT)"])
def test_a_remark_counts_on_every_searched_line_under_keywords(line):
    text = profile("- Kernliste: Lernbegleiter").replace("- Nischen (ohne Ort suchen): EdTech, Remote Python", line, 1)
    assert required_words.of_profile(text).of_term("Berufsbildner") == ("ICT",)


def test_a_term_listed_once_more_without_a_remark_has_no_required_words():
    text = profile().replace("- Nischen (ohne Ort suchen): EdTech, Remote Python", "- Nischen (ohne Ort suchen): Berufsbildner", 1)
    assert required_words.of_profile(text).of_term("Berufsbildner") == ()


def test_search_directions_and_apprenticeship_profiles_have_no_required_words():
    directions = "## Suchrichtungen\n1. Berufsbildner (nur mit ICT)\n\n## Region\n- Kantone (job-room): BE\n"
    assert required_words.of_profile(directions).of_term("Berufsbildner") == ()
    apprenticeship = (VORLAGEN / "suchprofil-lehrstelle.md").read_text(encoding="utf-8")
    assert required_words.of_profile(apprenticeship + "\n## Keywords\n- Kernliste: Koch (nur mit ICT)\n").of_term("Koch") == ()


def test_the_words_match_like_the_title_filter():
    words = ("Informatik", "ICT", "Plattform")
    assert required_words.fits(words, PASSES)
    assert not required_words.fits(words, UNRELATED)
    assert not required_words.fits(words, "Berufsbildner Strictly"), "a short word matches only as a whole word"
    assert required_words.fits(words, UNRELATED, "Lernende in der Wirtschaftsinformatik begleiten")


# Screening and adding hits

@pytest.fixture
def store(tmp_path):
    return hits.Hits(tmp_path)


def test_a_title_with_a_required_word_is_fetched_and_stored(store):
    required = required_words.of_profile(profile())
    screened = store.screen([hit(1, PASSES)], (), 45, [], required=required)
    assert screened["holen"] == ["jobs.ch:pb-1"]
    assert store.add([hit(1, PASSES)], [], TODAY, required=required)["neu"] == 1


def test_a_hit_found_only_through_the_term_without_any_required_word_is_not_stored(store):
    required = required_words.of_profile(profile())
    unrelated = []
    assert store.screen([hit(2, UNRELATED)], (), 45, [], required=required)["holen"] == ["jobs.ch:pb-2"], \
        "its ad text may still name a word, and it is loaded anyway"

    added = store.add([hit(2, UNRELATED)], [], TODAY, required=required, on_unrelated=unrelated.append)

    assert (added["neu"], added["ohne_pflichtbezug"]) == (0, 1)
    assert store.all() == []
    assert [found["stelle"] for found in unrelated] == [UNRELATED]


def test_the_ad_text_loaded_anyway_can_name_the_word(store):
    required = required_words.of_profile(profile())
    found = hit(3, "Berufsbildner/in Logistik", text="Du begleitest Lernende in der Informatik.")
    assert store.add([found], [], TODAY, required=required)["neu"] == 1


def test_a_hit_also_found_through_another_keyword_is_not_screened(store):
    required = required_words.of_profile(profile())
    both = hit(4, UNRELATED, queries=(COACH, GUIDE))
    assert store.add([both], [], TODAY, required=required)["neu"] == 1


def test_a_hit_from_an_older_extension_without_queries_is_not_screened(store):
    required = required_words.of_profile(profile())
    assert store.add([hit(5, UNRELATED, queries=())], [], TODAY, required=required)["neu"] == 1


def test_a_screened_link_is_not_fetched_again_until_the_remark_changes(store):
    required = required_words.of_profile(profile())
    store.add([hit(6, UNRELATED)], [], TODAY, required=required)
    outs = []

    again = store.screen([hit(6, UNRELATED)], (), 45, [], required=required,
                         on_screened_out=lambda found, reason: outs.append((found["stelle"], reason)))

    assert again["holen"] == []
    assert again["gefiltert"] == [{"stelle": UNRELATED, "grund": "ohne Pflichtbezug"}]
    assert outs == [(UNRELATED, "ohne Pflichtbezug")]
    changed = required_words.of_profile(profile(CORE.replace("Informatik, ICT, Plattform", "Informatik, Koch")))
    assert store.screen([hit(6, UNRELATED)], (), 45, [], required=changed)["holen"] == ["jobs.ch:pb-6"]
    without = required_words.of_profile(profile(CORE.replace(f"{BROAD}", "Berufsbildner")))
    assert store.screen([hit(6, UNRELATED)], (), 45, [], required=without)["holen"] == ["jobs.ch:pb-6"]


# Counting

def test_the_run_counts_hits_without_required_word_per_query_with_examples(tmp_path):
    log = query_log.QueryLog(tmp_path)
    for number in range(4):
        log.note_unrelated([{"portal": "jobs.ch", **COACH}], f"Koch {number} – Berufsbildner/in")
    log.note_screened([{"portal": "jobs.ch", **COACH}], "Praktikum Berufsbildung", "Titel: Praktikum")
    log.close_run({"jobs.ch": [{**COACH, "treffer": 6}]}, TODAY)
    [entry] = log.runs()[0]["abfragen"]
    assert (entry["aussortiert"], entry["ohne_pflichtbezug"]) == (1, 4)
    assert entry["pflicht_beispiele"] == [f"Koch {n} – Berufsbildner/in" for n in range(3)]


def runs_with(counts: list[int]) -> list[dict]:
    return [{"datum": f"2026-11-{10 + day:02d}", "abfragen": [
        {"portal": "jobs.ch", **COACH, "treffer": count,
         **({"ohne_pflichtbezug": count, "pflicht_beispiele": [f"Koch {day}", f"Maler {day}"]} if count else {})},
        {"portal": "jobs.ch", **GUIDE, "treffer": 2}]} for day, count in enumerate(counts)]


def test_the_yield_names_hits_without_required_word_and_they_bring_no_yield():
    result = search_yield.summary(runs_with([6, 7, 5]), [], ["Lernbegleiter", "Berufsbildner"], with_places=False)
    coach = result["begriffe"][1]
    assert (coach["treffer"], coach["aussortiert"], coach["ohne_pflichtbezug"], coach["ohne_ertrag"]) == (18, 0, 18, True)
    assert "ohne_pflichtbezug" not in result["begriffe"][0]


def test_the_details_name_each_term_with_examples_of_its_own_last_run():
    details = search_yield.unrelated(runs_with([6, 7, 0]), ["Lernbegleiter", "Berufsbildner"])
    assert details == [{"begriff": "Berufsbildner", "anzahl": 13, "beispiele": ["Koch 1", "Maler 1"]}]
    assert search_yield.unrelated(runs_with([0, 0, 0]), ["Berufsbildner"]) == []


# Through the routes

def write_profile(s, text: str) -> None:
    (s.kontext.daten / search_plan.PROFILE).write_text(text, encoding="utf-8")


def test_a_run_screens_out_the_unrelated_ad_and_the_page_names_it(search):  # noqa: F811
    write_profile(search, profile())
    listing = [hit(1, PASSES), hit(2, UNRELATED)]
    assert post(search, "/api/suche/sichten", {"treffer": listing})[1]["holen"] == ["jobs.ch:pb-1", "jobs.ch:pb-2"]
    received = post(search, "/api/suche/treffer", {"treffer": listing})[1]
    assert (received["neu"], received["ohne_pflichtbezug"]) == (1, 1)
    queries = [{**COACH, "treffer": 2}, {**GUIDE, "treffer": 0}]
    post(search, "/api/suche/abschluss", {"portale": {"jobs.ch": {"treffer": 2, "neu": 1, "problem": "", "abfragen": queries}}})

    page = json.loads(get(search, "/api/suche/liste")[2])
    assert [h["stelle"] for h in page["treffer"]] == [PASSES]
    assert {"begriff": "Berufsbildner", "woerter": ["Informatik", "ICT", "Plattform"]} in page["begriff_pflicht"]
    shown = json.loads(get(search, "/api/suche/ertrag")[2])
    coach = next(term for term in shown["begriffe"] if term["begriff"] == "Berufsbildner")
    assert coach["ohne_pflichtbezug"] == 1
    assert shown["ohne_pflichtbezug"] == [{"begriff": "Berufsbildner", "anzahl": 1, "beispiele": [UNRELATED]}]

    again = post(search, "/api/suche/sichten", {"treffer": [hit(2, UNRELATED)]})[1]
    assert (again["holen"], again["gefiltert"]) == ([], [{"stelle": UNRELATED, "grund": "ohne Pflichtbezug"}])


def test_an_apprenticeship_page_has_no_required_words(search):  # noqa: F811
    write_profile(search, (VORLAGEN / "suchprofil-lehrstelle.md").read_text(encoding="utf-8"))
    assert json.loads(get(search, "/api/suche/ertrag")[2])["ohne_pflichtbezug"] == []
