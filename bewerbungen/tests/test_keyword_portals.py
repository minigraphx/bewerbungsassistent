"""G105, #376: a line «- Nur <Portal>, <Portal>: <Begriff>, …» under Keywords limits its terms to those portals.

Without the line every term runs on every portal (G68). The estimate before the run, search_stages.size and the
extension count the same searches (erweiterung/tests/fixtures/run-size.json). All data is invented.
"""
import json

import search_plan
import search_stages
import search_terms
import term_changes
from hits import Hits
from test_app import get, server  # noqa: F401  (server is a fixture)

ALL_ON: list[str] = []


def profile(keywords: str) -> str:
    return f"""# Suchprofil

## Region
- Kantone (job-room): BE
- Orte (jobs.ch): Nordstadt, Südstadt
- PLZ (jobscout24): 1111
- Regionen (ictjobs): grossraum-bern

## Keywords
{keywords}
- Nischen (ohne Ort suchen): Nische1

## Titelfilter
- Positiv: Kurs
"""


LIMITED = profile("- Kernliste: Kursplaner, Lernbetreuer\n- Nur job-room: Lernbegleiter")
EVERYWHERE = profile("- Kernliste: Kursplaner, Lernbetreuer, Lernbegleiter")


def size_of(text: str, off: list[str] = ALL_ON) -> dict:
    return search_stages.size(search_plan.chosen(search_plan.parse(text), off).as_dict())


def test_a_term_marked_nur_job_room_creates_no_searches_on_the_other_portals():
    limited, everywhere = size_of(LIMITED), size_of(EVERYWHERE)

    assert limited["pro_portal"]["job-room"] == everywhere["pro_portal"]["job-room"] == 4
    # On the other portals the term would run once per place: two towns, one postcode, one region.
    dropped = {"jobs.ch": 2, "jobscout24": 1, "ictjobs": 1}
    assert {p: everywhere["pro_portal"][p] - limited["pro_portal"][p] for p in dropped} == dropped
    assert everywhere["suchen"] - limited["suchen"] == sum(dropped.values()) == 4


def test_the_plan_names_the_portals_of_each_limited_term_only():
    plan = search_plan.parse(LIMITED)

    assert plan.keywords == ("Kursplaner", "Lernbetreuer", "Lernbegleiter")
    assert plan.as_dict()["nur_portale"] == {"Lernbegleiter": ["job-room"]}
    assert search_plan.parse(EVERYWHERE).as_dict()["nur_portale"] == {}


def test_portal_names_are_read_ignoring_case_and_several_lines_count():
    plan = search_plan.parse(profile("- Kernliste: Kursplaner\n- Nur JOBS.CH, Job-Room: Lernbegleiter, Kursleiter\n"
                                     "- nur ictjobs: Lernplattform\n- Nur jobs.ch, job-room: Moderator"))

    assert plan.keywords == ("Kursplaner", "Lernbegleiter", "Kursleiter", "Lernplattform", "Moderator")
    assert plan.as_dict()["nur_portale"] == {"Lernbegleiter": ["jobs.ch", "job-room"], "Kursleiter": ["jobs.ch", "job-room"],
                                             "Lernplattform": ["ictjobs"], "Moderator": ["jobs.ch", "job-room"]}


def test_a_line_naming_a_portal_the_app_does_not_know_is_no_limit_and_the_page_says_so():
    for line in ("- Nur Aarau: Lernbegleiter", "- Nur jobs.ch, Aarau: Lernbegleiter", "- Nur: Lernbegleiter"):
        plan = search_plan.parse(profile(f"- Kernliste: Kursplaner\n{line}"))
        assert plan.keywords == ("Kursplaner", "Lernbegleiter"), line
        assert plan.as_dict()["nur_portale"] == {}, line
        assert size_of(profile(f"- Kernliste: Kursplaner\n{line}")) == size_of(profile("- Kernliste: Kursplaner, Lernbegleiter"))

    plan = search_plan.parse(profile("- Kernliste: Kursplaner\n- Nur Aarau: Lernbegleiter"))
    assert search_plan.portal_limit_notes(plan, ALL_ON)["hinweise"] == [
        "Die Zeile „Nur Aarau: …“ nennt kein Portal, das die App kennt. Die Begriffe darin sucht sie darum auf allen Portalen."]


def test_niches_cannot_be_limited_and_a_term_also_in_the_core_list_runs_everywhere():
    plan = search_plan.parse(LIMITED)

    assert plan.niche_keywords == ("Nische1",)
    assert "Nische1" not in plan.as_dict()["nur_portale"]
    # jobs.ch: two terms in two towns, and the niche without a place as before
    assert size_of(LIMITED)["pro_portal"]["jobs.ch"] == 2 * 2 + 1
    assert size_of(profile("- Kernliste: Kursplaner, Lernbegleiter\n- Nur job-room: Lernbegleiter"))["suchen"] == \
        size_of(profile("- Kernliste: Kursplaner, Lernbegleiter"))["suchen"]


def test_a_term_whose_portals_are_all_switched_off_runs_in_no_search():
    text = profile("- Kernliste: Kursplaner\n- Nur ictjobs: Lernbegleiter")
    plan = search_plan.parse(text)

    notes = search_plan.portal_limit_notes(plan, ["ictjobs"])

    assert notes["begriffe"] == [{"begriff": "Lernbegleiter", "portale": ["ictjobs"], "aus": True}]
    assert notes["hinweise"] == ["„Lernbegleiter“ sucht nur auf ictjobs, und ictjobs ist ausgeschaltet. "
                                 "Der Begriff läuft darum in keiner Suche."]
    assert size_of(text, ["ictjobs"]) == size_of(profile("- Kernliste: Kursplaner"), ["ictjobs"])
    on = search_plan.portal_limit_notes(plan, ALL_ON)
    assert on == {"begriffe": [{"begriff": "Lernbegleiter", "portale": ["ictjobs"], "aus": False}], "hinweise": []}


def test_removing_a_term_also_removes_it_from_its_nur_line():
    changed = search_terms.removed(profile("- Kernliste: Kursplaner\n- Nur job-room: Lernbegleiter, Kursleiter"),
                                   "Lernbegleiter")

    assert "- Nur job-room: Kursleiter\n" in changed
    assert search_plan.parse(changed).as_dict()["nur_portale"] == {"Kursleiter": ["job-room"]}


def test_a_new_term_goes_to_the_core_list_never_into_a_nur_line():
    changed = search_terms.added(LIMITED, "Lerncoach")
    assert "- Kernliste: Kursplaner, Lernbetreuer, Lerncoach\n- Nur job-room: Lernbegleiter\n" in changed

    only_limited = profile("- Nur job-room: Lernbegleiter")
    changed = search_terms.added(only_limited, "Lerncoach")
    assert "- Nur job-room: Lernbegleiter\n" in changed
    assert search_plan.parse(changed).as_dict()["nur_portale"] == {"Lernbegleiter": ["job-room"]}
    assert "Lerncoach" in search_plan.parse(changed).keywords

    empty_core = profile("- Kernliste:\n- Nur job-room: Lernbegleiter")
    assert "- Kernliste: Lerncoach\n- Nur job-room: Lernbegleiter\n" in search_terms.added(empty_core, "Lerncoach")


def test_reordering_keeps_the_limit():
    changed = search_terms.reordered(LIMITED, ["Lernbegleiter", "Kursplaner", "Lernbetreuer"])

    plan = search_plan.parse(changed)
    assert plan.keywords == ("Lernbegleiter", "Kursplaner", "Lernbetreuer")
    assert plan.as_dict()["nur_portale"] == {"Lernbegleiter": ["job-room"]}


def test_a_profile_from_meine_angaben_keeps_the_nur_line():
    replaced = profile("- Kernliste: Kursplaner")

    kept, terms = search_terms.kept_on_replace(LIMITED, replaced)

    assert "- Nur job-room: Lernbegleiter\n" in kept
    assert "Lernbegleiter" not in search_plan.section_lines(kept, "## Keywords")[0]
    assert search_plan.parse(kept).as_dict()["nur_portale"] == {"Lernbegleiter": ["job-room"]}
    assert terms == ("Lernbetreuer",)


def test_switching_terms_in_a_proposal_keeps_the_nur_line():
    current = term_changes.terms_of(LIMITED)
    change = term_changes.Change(term_changes.KEYWORDS, ("Kursplaner",), ("Kursleiter",), "")

    changed = term_changes.applied(LIMITED, (change,))

    assert "- Kernliste: Lernbetreuer, Kursleiter\n- Nur job-room: Lernbegleiter\n" in changed
    assert current.keywords == ("Kursplaner", "Lernbetreuer", "Lernbegleiter")


def test_the_page_and_the_extension_get_the_limit(server):  # noqa: F811
    folder = server.kontext.daten
    (folder / "suchprofil.md").write_text(profile("- Kernliste: Kursplaner\n- Nur ictjobs: Lernbegleiter\n"
                                                  "- Nur Aarau: Lernbetreuer"), encoding="utf-8")
    Hits(folder).set_portals_off(["ictjobs"])

    page = json.loads(get(server, "/api/suche/liste")[2])
    plan = json.loads(get(server, "/api/suche/plan")[2])["plan"]

    assert page["begriff_portale"] == [{"begriff": "Lernbegleiter", "portale": ["ictjobs"], "aus": True}]
    assert page["portal_hinweise"] == [
        "Die Zeile „Nur Aarau: …“ nennt kein Portal, das die App kennt. Die Begriffe darin sucht sie darum auf allen Portalen.",
        "„Lernbegleiter“ sucht nur auf ictjobs, und ictjobs ist ausgeschaltet. Der Begriff läuft darum in keiner Suche."]
    assert plan["nur_portale"] == {"Lernbegleiter": ["ictjobs"]}
    # Kursplaner and Lernbetreuer: job-room 2 and the niche, jobs.ch 2 × 2 and the niche, jobscout24 2.
    assert page["umfang"]["pro_portal"] == plan["umfang"]["pro_portal"] == {"job-room": 3, "jobs.ch": 5, "jobscout24": 2}
