"""jobscout24 by region instead of postcodes (G107, #380): «- Regionen (jobscout24): …» under Region.

jobscout24 searches a fixed 20 km around a postcode, so nearby postcodes find the same ads; with regions the extension
sends one search per term with all regions. The postcodes stay in the profile and count again once no region is set.
All data is invented.
"""
import json

import jobscout24_regions
import portal_places
import search_frame
import search_plan
import search_stages
import search_terms
from test_app import get, post, server  # noqa: F401  (server is a fixture)

TERMS = "Kursplaner, Lernbegleiter, Datenpfleger, Ablagehelfer"
PROFILE = f"""# Suchprofil

## Region
- Kantone (job-room): BE
- Orte (jobs.ch): Nordstadt
- PLZ (jobscout24): 1111, 2222, 3333
{{regions}}- Regionen (ictjobs): grossraum-bern

## Keywords
- Kernliste: {TERMS}
"""
WITH_REGION = PROFILE.format(regions="- Regionen (jobscout24): Region Bern (BE/FR/SO)\n")
WITHOUT = PROFILE.format(regions="")


def jobscout24_searches(text: str) -> int:
    return search_stages.size(search_plan.parse(text).as_dict())["pro_portal"]["jobscout24"]


# The search

def test_with_one_region_jobscout24_runs_one_search_per_term_instead_of_one_per_postcode():
    assert jobscout24_searches(WITHOUT) == 3 * 4
    assert jobscout24_searches(WITH_REGION) == 1 * 4
    plan = search_plan.parse(WITH_REGION)
    assert plan.jobscout24_regions == ("3",)
    assert plan.as_dict()["regionen_jobscout24"] == [{"id": "3", "name": "Region Bern (BE/FR/SO)"}]


def test_the_postcodes_stay_in_the_plan_and_count_again_without_a_region():
    plan = search_plan.parse(WITH_REGION)
    assert plan.postal_codes == ("1111", "2222", "3333")
    assert search_plan.parse(WITHOUT).jobscout24_regions == ()


def test_names_as_jobscout24_shows_them_short_names_and_ids_are_all_read():
    line = "- Regionen (jobscout24): region bern, 14, Home Office / Remote Work, Nordwestschweiz (AG/BL/BS/SO)\n"
    plan = search_plan.parse(PROFILE.format(regions=line))
    assert plan.jobscout24_regions == ("3", "14", "1")
    assert [entry["name"] for entry in plan.as_dict()["regionen_jobscout24"]] == [
        "Region Bern (BE/FR/SO)", "Homeoffice / Remote", "Nordwestschweiz (AG/BL/BS/SO)"]


def test_an_unknown_region_is_not_sent_and_the_plan_says_so():
    plan = search_plan.parse(PROFILE.format(regions="- Regionen (jobscout24): Seeland, 99\n"))
    assert plan.jobscout24_regions == ()
    assert jobscout24_searches(PROFILE.format(regions="- Regionen (jobscout24): Seeland\n")) == 12
    assert any("„Seeland“" in hint and "jobscout24" in hint for hint in plan.hints)


def test_the_ictjobs_regions_are_read_from_their_own_line_whatever_comes_first():
    plan = search_plan.parse(WITH_REGION)
    assert plan.regions == ("grossraum-bern",)
    first = WITH_REGION.replace("- Regionen (ictjobs): grossraum-bern\n", "").replace(
        "- Kantone (job-room): BE\n", "- Kantone (job-room): BE\n- Regionen (ictjobs): solothurn\n")
    assert search_plan.parse(first).regions == ("solothurn",)
    assert search_plan.parse(first).jobscout24_regions == ("3",)


def test_the_list_holds_jobscout24s_regions_with_their_ids():
    assert jobscout24_regions.REGIONS[0] == ("1", "Nordwestschweiz (AG/BL/BS/SO)")
    assert dict(jobscout24_regions.REGIONS)["14"] == "Homeoffice / Remote"
    assert len(jobscout24_regions.REGIONS) == 13


# Suche einstellen

def test_the_card_shows_the_regions_and_not_the_postcodes_while_a_region_is_set():
    shown = {entry["portal"]: entry for entry in portal_places.shown(WITH_REGION)}
    assert shown["jobscout24"]["orte"] == ["Region Bern (BE/FR/SO)"]
    assert shown["jobscout24"]["vorsatz"] == "Regionen"
    assert {entry["portal"]: entry["orte"] for entry in portal_places.shown(WITHOUT)}["jobscout24"] == ["1111", "2222", "3333"]


def test_saving_regions_writes_their_names_and_keeps_the_postcodes():
    changed = search_frame.with_values(WITHOUT, {"regionen_jobscout24": ["3", "Homeoffice / Remote"]})
    assert "- Regionen (jobscout24): Region Bern (BE/FR/SO), Homeoffice / Remote\n" in changed
    assert "- PLZ (jobscout24): 1111, 2222, 3333\n" in changed
    assert "- Regionen (ictjobs): grossraum-bern\n" in changed
    assert search_frame.values(changed)["regionen_jobscout24"] == ["Region Bern (BE/FR/SO)", "Homeoffice / Remote"]
    assert search_frame.values(changed)["regionen"] == ["grossraum-bern"]


def test_emptying_the_regions_removes_only_their_line():
    changed = search_frame.with_values(WITH_REGION, {"regionen_jobscout24": []})
    assert changed == WITHOUT


def test_ictjobs_regions_change_without_touching_the_jobscout24_line():
    changed = search_frame.with_values(WITH_REGION, {"regionen": ["solothurn"]})
    assert "- Regionen (jobscout24): Region Bern (BE/FR/SO)\n" in changed
    assert "- Regionen (ictjobs): solothurn\n" in changed


def test_an_unknown_new_region_is_refused_one_the_line_has_stays():
    try:
        search_frame.with_values(WITHOUT, {"regionen_jobscout24": ["Seeland"]})
    except ValueError as error:
        assert "jobscout24" in str(error)
    else:
        raise AssertionError("an unknown region was taken")
    own = PROFILE.format(regions="- Regionen (jobscout24): Seeland\n")
    kept = search_frame.with_values(own, {"regionen_jobscout24": ["Seeland", "3"]})
    assert "- Regionen (jobscout24): Seeland, Region Bern (BE/FR/SO)\n" in kept


def test_the_frame_route_offers_every_region_and_saves_them(server):  # noqa: F811
    (server.kontext.daten / search_plan.PROFILE).write_text(WITHOUT, encoding="utf-8")
    frame = json.loads(get(server, "/api/suche/rahmen")[2])
    names = [choice["name"] for choice in frame["alle_regionen_jobscout24"]]
    assert names[0] == "Nordwestschweiz (AG/BL/BS/SO)" and "Homeoffice / Remote" in names and len(names) == 13
    assert frame["werte"]["regionen_jobscout24"] == []
    status, answer = post(server, "/api/suche/rahmen", {"regionen_jobscout24": ["Region Bern (BE/FR/SO)"]})
    assert status == 200, answer
    assert answer["werte"]["regionen_jobscout24"] == ["Region Bern (BE/FR/SO)"]
    assert answer["werte"]["plz"] == ["1111", "2222", "3333"]


def test_the_line_stays_when_meine_angaben_replaces_the_profile():
    replaced = WITHOUT.replace(TERMS, "Kursplaner")
    text, _ = search_terms.kept_on_replace(WITH_REGION, replaced)
    assert "- Regionen (jobscout24): Region Bern (BE/FR/SO)" in text
    assert search_plan.parse(text).jobscout24_regions == ("3",)
