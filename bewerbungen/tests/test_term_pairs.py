"""Terms searched twice, or covered by a broader term, on «Suche einstellen» (G106, #377). Invented terms and places only."""
import json

import pytest

import hits
import search_plan
import search_stages
import term_pairs
from test_routes_search import search  # noqa: F401  (search is a fixture)
from test_app import get, post, server  # noqa: F401  (server is a fixture)

REGION = "## Region\n- Kantone: AG\n- Orte: Aarau, Olten\n- PLZ: 5000\n\n"
PROFILE = (f"# Suchprofil\n\n{REGION}## Keywords\n- Kernliste: Kursleiter, Lernbegleiter, Kursleiter Informatik\n"
           "- Nischen (ohne Ort suchen): Kursleiter, Lernatelier\n")
# job-room 3 + 2, jobs.ch 2 × 3 + 2, jobscout24 1 × 3, ictjobs off: 16 searches. A keyword costs 4, a niche 2.
OFF = ["ictjobs"]
DUPLICATE = ("„Kursleiter“ steht zweimal: in der Kernliste und bei den Nischen. Bei den Nischen sucht die App ohne Ort, "
             "also auch alles, was die Kernliste findet. In der Kernliste kostet er 4 Suchen pro Suchlauf, bei den Nischen 2.")
OVERLAP = ("„Kursleiter Informatik“ steckt ganz in „Kursleiter“: Die Suche nach „Kursleiter“ findet diese Stellen meist "
           "schon. „Kursleiter Informatik“ kostet 4 Suchen pro Suchlauf.")
# The setup of screenshot 4: no choice of portals yet, so ictjobs runs only while a computing term may run there.
WITH_LIMIT = (f"{REGION}## Keywords\n- Kernliste: Kursleiter, Lernbegleiter, Kursleiter Informatik, Lerncoach\n"
              "- Nischen (ohne Ort suchen): Kursleiter, Lernatelier\n- Nur jobs.ch, job-room: Lerncoach\n")
GOES_OFF = "das ist in der Zahl schon eingerechnet."
NARROW_QUERY = {"portal": "jobs.ch", "stichwort": "Kursleiter Informatik", "ort": "Aarau"}
BROAD_QUERY = {"portal": "jobs.ch", "stichwort": "Kursleiter", "ort": "Aarau"}


def found(text: str = PROFILE, off=OFF, kept=(), shown=()) -> list[dict]:
    return term_pairs.pairs(text, None, off, kept, list(shown))


def texts(pairs: list[dict]) -> list[str]:
    return [pair["text"] for pair in pairs]


# What the notice shows

def test_a_term_in_both_lists_and_a_narrower_variant_show_with_their_searches():
    pairs = found()
    assert texts(pairs) == [DUPLICATE, OVERLAP]
    duplicate, overlap = pairs
    assert [(option["knopf"], option["spart"]) for option in duplicate["optionen"]] == [
        ("Aus der Kernliste entfernen", 4), ("Bei den Nischen entfernen", 2)]
    assert [(option["knopf"], option["spart"]) for option in overlap["optionen"]] == [("„Kursleiter Informatik“ entfernen", 4)]
    assert duplicate["behalten"] == overlap["behalten"] == "Beide behalten"


def test_the_costs_follow_the_estimate_of_the_page():
    plan = search_plan.chosen(search_plan.parse(PROFILE), OFF)
    assert term_pairs.searches(PROFILE, None, OFF) == 16 == search_stages.size(plan.as_dict())["suchen"]


def test_without_duplicates_or_overlaps_there_is_nothing_to_show():
    text = f"{REGION}## Keywords\n- Kernliste: Kursleiter, Lernbegleiter\n- Nischen: Lernatelier\n"
    assert found(text) == []


def test_two_forms_of_the_same_words_are_the_same_term():
    text = f"{REGION}## Keywords\n- Kernliste: Kursleiterin Informatik, Lernbegleiter\n- Nischen: Informatik Kursleiter\n"
    [pair] = found(text)
    assert pair["art"] == term_pairs.DUPLICATE
    assert pair["text"].startswith("„Kursleiterin Informatik“ steht zweimal: in der Kernliste und bei den Nischen.")


def test_a_term_in_a_limit_line_and_the_core_list_is_a_duplicate_named_as_in_the_profile():
    text = f"{REGION}## Keywords\n- Kernliste: Kursleiter, Lernbegleiter\n- Nur jobs.ch, job-room: Kursleiter\n"
    [pair] = found(text)
    assert pair["text"] == ("„Kursleiter“ steht zweimal: in der Kernliste und in der Zeile „Nur jobs.ch, job-room“. "
                            "Weil er auch in der Kernliste steht, sucht die App ihn auf allen Portalen, nicht nur auf "
                            "jobs.ch und job-room. In der Kernliste kostet er 1 Suche pro Suchlauf, in der Zeile "
                            "„Nur jobs.ch, job-room“ keine zusätzliche.")
    assert [(option["knopf"], option["spart"]) for option in pair["optionen"]] == [
        ("Aus der Kernliste entfernen", 1), ("Aus der Zeile „Nur jobs.ch, job-room“ entfernen", 0)]


def test_a_broader_term_limited_to_fewer_portals_does_not_cover_the_narrower_one():
    text = f"{REGION}## Keywords\n- Kernliste: Kursleiter Informatik, Lernbegleiter\n- Nur jobs.ch: Kursleiter\n"
    assert found(text) == []


def test_a_kept_pair_is_not_shown_again():
    first = found()
    assert texts(found(kept=[first[0]["id"]])) == [OVERLAP]


def queried(both: int, total: int = 14) -> list[dict]:
    """Hits of the narrower term, `both` of them found by the broader term too, and one of the broader term only."""
    mine = [{"id": f"h-{n}", "abfragen": [NARROW_QUERY, BROAD_QUERY] if n < both else [NARROW_QUERY]} for n in range(total)]
    return [*mine, {"id": "h-x", "abfragen": [BROAD_QUERY]}]


def test_the_overlap_says_how_many_of_its_postings_the_broader_term_found_too():
    overlap = found(shown=queried(13))[1]
    assert overlap["text"] == f"{OVERLAP} Von seinen 14 Stellen kamen 13 auch über „Kursleiter“."


@pytest.mark.parametrize(("both", "total", "sentence"), [
    (1, 1, "Seine einzige Stelle kam auch über „Kursleiter“."),
    (0, 1, "Seine einzige Stelle kam nicht über „Kursleiter“."),
    (4, 4, "Alle seine 4 Stellen kamen auch über „Kursleiter“."),
    (0, 4, "Von seinen 4 Stellen kam keine über „Kursleiter“."),
    (1, 4, "Von seinen 4 Stellen kam eine auch über „Kursleiter“."),
    (3, 4, "Von seinen 4 Stellen kamen 3 auch über „Kursleiter“.")])
def test_the_overlap_counts_each_posting_once_in_stellen(both, total, sentence):
    assert found(shown=queried(both, total))[1]["text"].endswith(f" {sentence}")


def test_when_less_than_half_came_through_the_broader_term_it_only_should_find_them():
    overlap = found(shown=queried(6))[1]
    assert overlap["text"] == ("„Kursleiter Informatik“ steckt ganz in „Kursleiter“: Die Suche nach „Kursleiter“ sollte "
                               "diese Stellen auch finden. „Kursleiter Informatik“ kostet 4 Suchen pro Suchlauf. Von "
                               "seinen 14 Stellen kamen 6 auch über „Kursleiter“.")


def test_a_duplicate_the_plan_searches_once_anyway_has_no_cost_sentence():
    text = f"{REGION}## Keywords\n- Kernliste: Kursleiter, Lernbegleiter\n- Weitere: Kursleiter\n"
    [pair] = found(text)
    assert pair["text"] == ("„Kursleiter“ steht zweimal: in der Kernliste und in der Zeile „Weitere“. Die App sucht ihn "
                            "trotzdem nur einmal.")


def test_removing_the_only_term_ictjobs_runs_for_says_the_portal_goes_off():
    pairs = found(WITH_LIMIT, off=None)
    assert pairs[-1]["text"] == ("„Kursleiter Informatik“ steckt ganz in „Kursleiter“: Die Suche nach „Kursleiter“ findet "
                                 "diese Stellen meist schon. „Kursleiter Informatik“ kostet 8 Suchen pro Suchlauf. Ohne "
                                 "ihn sucht die App nicht mehr auf ictjobs; das ist in der Zahl schon eingerechnet.")
    assert not any(GOES_OFF in pair["text"] for pair in pairs[:-1])


def test_a_duplicate_names_the_entry_without_which_a_portal_goes_off():
    text = f"{REGION}## Keywords\n- Kernliste: Kursleiter Informatik, Lernbegleiter\n- Nur jobs.ch: Kursleiter Informatik\n"
    [pair] = found(text, off=None)
    assert pair["text"].endswith("In der Kernliste kostet er 4 Suchen pro Suchlauf, in der Zeile „Nur jobs.ch“ keine "
                                 "zusätzliche. Ohne den Eintrag in der Kernliste sucht die App nicht mehr auf ictjobs; das "
                                 "ist in der Zahl schon eingerechnet.")


@pytest.mark.parametrize("text, off", [
    (WITH_LIMIT, []),
    (WITH_LIMIT.replace("Lerncoach\n- Nischen", "Lerncoach, Informatiklehrer\n- Nischen"), None),
], ids=["switched-on-by-the-person", "another-term-keeps-it"])
def test_a_portal_that_stays_on_is_not_named(text, off):
    assert not any(GOES_OFF in pair["text"] for pair in found(text, off=off))


def test_removing_the_last_core_term_is_not_offered():
    text = f"{REGION}## Keywords\n- Kernliste: Kursleiter\n- Nischen: Kursleiter\n"
    [pair] = found(text)
    assert [option["knopf"] for option in pair["optionen"]] == ["Bei den Nischen entfernen"]


def test_an_apprenticeship_profile_shows_nothing():
    text = "## Lehrbeginn\n- 2027\n\n## Berufe (mit Priorität)\n1. Koch/Köchin EFZ\n2. Koch EFZ\n"
    assert found(text, off=None) == []


# Removing one, through the routes

def write(search, text: str = PROFILE) -> None:  # noqa: F811
    daten = search.kontext.daten
    (daten / search_plan.PROFILE).write_text(text, encoding="utf-8")
    hits.Hits(daten).set_portals_off(OFF)


def shown(search) -> list[dict]:  # noqa: F811
    status, _, content = get(search, "/api/suche/doppelt")
    assert status == 200
    return json.loads(content)["paare"]


def test_the_page_gets_the_pairs_and_looking_changes_nothing(search):  # noqa: F811
    write(search)
    path = search.kontext.daten / search_plan.PROFILE
    assert texts(shown(search)) == [DUPLICATE, OVERLAP]
    assert path.read_text(encoding="utf-8") == PROFILE, "the app only proposes"


def test_removing_at_the_niches_keeps_the_core_list_and_can_be_undone(search):  # noqa: F811
    write(search)
    path = search.kontext.daten / search_plan.PROFILE
    pair = shown(search)[0]
    status, answer = post(search, "/api/suche/doppelt/entfernen", {"paar": pair["id"], "seite": pair["optionen"][1]["seite"]})
    assert status == 200
    assert answer["text"] == "„Kursleiter“ bei den Nischen entfernt. Der nächste Suchlauf spart 2 Suchen."
    after = path.read_text(encoding="utf-8")
    assert "- Nischen (ohne Ort suchen): Lernatelier\n" in after
    assert "- Kernliste: Kursleiter, Lernbegleiter, Kursleiter Informatik\n" in after
    assert len(search.kontext.ablage.liste(path)) >= 2, "drafts before and after"
    undo = {"beruf": answer["beruf"], "vorher": answer["rueckgaengig"], "zeile": answer["zeile"]}
    assert post(search, "/api/beruf/rueckgaengig", undo)[0] == 200
    assert path.read_text(encoding="utf-8") == PROFILE


def test_undo_after_another_change_puts_the_term_back_into_its_line(search):  # noqa: F811
    write(search)
    path = search.kontext.daten / search_plan.PROFILE
    pair = shown(search)[0]
    _, answer = post(search, "/api/suche/doppelt/entfernen", {"paar": pair["id"], "seite": "b"})
    assert post(search, "/api/beruf/aufnehmen", {"beruf": "Lerncoach"})[0] == 200
    undo = {"beruf": answer["beruf"], "vorher": answer["rueckgaengig"], "zeile": answer["zeile"]}
    status, back = post(search, "/api/beruf/rueckgaengig", undo)
    assert status == 200 and back["am_ende"]
    assert "- Nischen (ohne Ort suchen): Lernatelier, Kursleiter\n" in path.read_text(encoding="utf-8")


def test_removing_the_narrower_term_says_what_the_next_search_saves(search):  # noqa: F811
    write(search)
    path = search.kontext.daten / search_plan.PROFILE
    pair = shown(search)[1]
    status, answer = post(search, "/api/suche/doppelt/entfernen", {"paar": pair["id"], "seite": pair["optionen"][0]["seite"]})
    assert status == 200
    assert answer["text"] == "„Kursleiter Informatik“ entfernt. Der nächste Suchlauf spart 4 Suchen."
    assert "Kursleiter Informatik" not in path.read_text(encoding="utf-8")
    assert post(search, "/api/beruf/rueckgaengig", {"beruf": answer["beruf"], "vorher": answer["rueckgaengig"]})[0] == 200
    assert path.read_text(encoding="utf-8") == PROFILE


def test_removing_the_only_term_ictjobs_runs_for_says_the_run_leaves_it_out(search):  # noqa: F811
    path = search.kontext.daten / search_plan.PROFILE
    path.write_text(WITH_LIMIT, encoding="utf-8")  # no choice of portals stored
    pair = shown(search)[-1]
    status, answer = post(search, "/api/suche/doppelt/entfernen", {"paar": pair["id"], "seite": pair["optionen"][0]["seite"]})
    assert status == 200
    assert answer["text"] == ("„Kursleiter Informatik“ entfernt. Der nächste Suchlauf spart 8 Suchen und sucht nicht mehr "
                              "auf ictjobs.")


def test_keeping_both_is_remembered_for_that_pair(search):  # noqa: F811
    write(search)
    pair = shown(search)[0]
    status, answer = post(search, "/api/suche/doppelt/behalten", {"paar": pair["id"]})
    assert status == 200 and answer["text"] == "Beide bleiben. Die App fragt bei diesem Paar nicht wieder."
    assert texts(shown(search)) == [OVERLAP]
    assert (search.kontext.daten / search_plan.PROFILE).read_text(encoding="utf-8") == PROFILE


@pytest.mark.parametrize("body", [{}, {"paar": "doppelt:x", "seite": "a"}, {"paar": 5, "seite": "a"}, {"paar": "x" * 900},
                                  {"paar": "doppelt:x", "seite": "c"}], ids=["none", "unknown", "number", "long", "side"])
def test_a_pair_that_is_not_there_is_refused(search, body):  # noqa: F811
    write(search)
    assert post(search, "/api/suche/doppelt/entfernen", {"seite": "a", **body})[0] == 400
    assert (search.kontext.daten / search_plan.PROFILE).read_text(encoding="utf-8") == PROFILE


@pytest.mark.parametrize("pair", [None, 5, "", "doppelt:" + "x" * 900, "anderes:x"], ids=["none", "number", "empty", "long", "other"])
def test_keeping_refuses_what_is_no_pair(search, pair):  # noqa: F811
    write(search)
    assert post(search, "/api/suche/doppelt/behalten", {"paar": pair})[0] == 400
