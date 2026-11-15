"""Portals with their own place lines follow what Suche einstellen shows and saves (#301, G64).

Orte (jobs.ch), PLZ (jobscout24) and Regionen (ictjobs) take priority over Wohnort and Kantone, so the region card
shows them and lets the person change or empty them; an empty line goes, and the portal follows Wohnort and Kantone.
"""
import json

import pytest

import portal_places
import search_frame
import search_plan
from test_ai_tasks import VORLAGEN
from test_app import get, post, server  # noqa: F401  (server is a fixture)
from test_search_frame import APPRENTICESHIP, JOB, SEITEN, changed_lines


def test_the_card_holds_the_place_lines_as_written():
    values = search_frame.values(JOB)
    assert values["orte"] == ["Bern", "Solothurn"]
    assert values["plz"] == ["3000", "4500"]
    assert values["regionen"] == ["grossraum-bern", "solothurn"]


def test_a_profile_without_place_lines_has_empty_fields():
    profile = "# Suchprofil\n\n## Region\n- Wohnort: Bern\n- Kantone (job-room): BE\n\n## Keywords\n- Kernliste: Python\n"
    values = search_frame.values(profile)
    assert (values["orte"], values["plz"], values["regionen"]) == ([], [], [])
    assert portal_places.shown(profile) == []


def test_a_new_home_reaches_jobs_ch_once_its_own_places_are_emptied():
    before = search_plan.parse(JOB)
    assert before.places == ("Bern", "Solothurn")  # the Orte line wins over any Wohnort
    changed = search_frame.with_values(JOB, {"wohnort": "Thun", "orte": []})
    assert "- Orte (jobs.ch, LinkedIn):" not in changed
    assert search_plan.parse(changed).places == ("Thun",)


def test_new_cantons_reach_ictjobs_once_its_own_regions_are_emptied():
    changed = search_frame.with_values(JOB, {"kantone": ["ZH", "AG"], "regionen": []})
    assert search_plan.parse(changed).regions == ("grossraum-zuerich", "aargau")


def test_changed_place_lines_keep_their_labels_and_reach_the_plan():
    change = {"orte": ["Thun", "Biel"], "plz": ["3600"], "regionen": ["grossraum-zuerich"]}
    changed = search_frame.with_values(JOB, change)
    assert changed_lines(JOB, changed) == [
        ("- Orte (jobs.ch, LinkedIn): Bern, Solothurn", "- Orte (jobs.ch, LinkedIn): Thun, Biel"),
        ("- PLZ (jobscout24): 3000, 4500", "- PLZ (jobscout24): 3600"),
        ("- Regionen (ictjobs): grossraum-bern, solothurn", "- Regionen (ictjobs): grossraum-zuerich")]
    plan = search_plan.parse(changed)
    assert (plan.places, plan.postal_codes, plan.regions) == (("Thun", "Biel"), ("3600",), ("grossraum-zuerich",))


def test_the_card_shows_per_portal_where_the_search_looks():
    assert portal_places.shown(JOB) == [
        {"portal": "jobs.ch", "orte": ["Bern", "Solothurn"]},
        {"portal": "jobscout24", "orte": ["3000", "4500"]},
        {"portal": "ictjobs", "orte": ["Grossraum Bern", "Solothurn"]}]
    plan = search_plan.parse(JOB)
    shown = {entry["portal"]: entry["orte"] for entry in portal_places.shown(JOB)}
    assert (tuple(shown["jobs.ch"]), tuple(shown["jobscout24"])) == (plan.places, plan.postal_codes)


def test_the_places_are_shown_as_the_search_reads_them():
    profile = JOB.replace("Bern, Solothurn\n- PLZ", "Bern (Stadt)/Thun, Solothurn\n- PLZ")
    assert portal_places.shown(profile)[0] == {"portal": "jobs.ch", "orte": ["Bern", "Thun", "Solothurn"]}
    assert search_plan.parse(profile).places == ("Bern", "Thun", "Solothurn")


def test_every_ictjobs_region_is_offered_with_its_cantons():
    choices = portal_places.region_choices([])
    assert [choice["wert"] for choice in choices] == list(dict.fromkeys(search_plan.ICTJOBS_REGIONS.values()))
    assert {"wert": "grossraum-basel", "name": "Grossraum Basel (BS, BL)"} in choices


def test_a_region_the_profile_already_has_stays_offered_even_if_unknown():
    choices = portal_places.region_choices(["grossraum-bern", "seeland"])
    assert choices[-1] == {"wert": "seeland", "name": "seeland"}
    assert search_frame.with_values(JOB.replace("solothurn\n", "seeland\n", 1),
                                    {"regionen": ["seeland"]}).count("- Regionen (ictjobs): seeland") == 1


@pytest.mark.parametrize("change, message", [
    ({"plz": ["30000"]}, "Postleitzahl"),
    ({"plz": ["Bern"]}, "Postleitzahl"),
    ({"regionen": ["bern"]}, "Region"),
    ({"orte": [f"Ort{n}" for n in range(7)]}, "höchstens 6"),
    ({"orte": ["Bern/Thun/Biel/Olten/Aarau/Baden/Brugg"]}, "höchstens 6"),  # the search reads seven places
    ({"plz": [str(3000 + n) for n in range(7)]}, "höchstens 6"),
    ({"orte": ["x" * 81]}, "80 Zeichen"),
    ({"orte": "Bern"}, "Liste"),
])
def test_a_place_the_portal_cannot_take_is_refused(change, message):
    with pytest.raises(ValueError, match=message):
        search_frame.with_values(JOB, change)


def test_a_postal_code_the_profile_already_has_stays_allowed():
    profile = JOB.replace("3000, 4500", "3000 Bern, 4500")
    changed = search_frame.with_values(profile, {"plz": ["3000 Bern", "3600"]})
    assert "- PLZ (jobscout24): 3000 Bern, 3600" in changed


@pytest.mark.parametrize("key", ["orte", "plz", "regionen"])
def test_an_apprenticeship_has_no_place_lines(key):
    with pytest.raises(ValueError, match="Stellensuche"):
        search_frame.with_values(APPRENTICESHIP, {key: []})
    assert portal_places.shown(APPRENTICESHIP) == []


def test_the_page_saves_the_place_lines_and_the_next_plan_uses_them(server):  # noqa: F811
    path = server.kontext.daten / "suchprofil.md"
    path.write_text(JOB, encoding="utf-8")
    frame = json.loads(get(server, "/api/suche/rahmen")[2])
    assert frame["orte_pro_portal"][0] == {"portal": "jobs.ch", "orte": ["Bern", "Solothurn"]}
    assert frame["werte"]["regionen"] == ["grossraum-bern", "solothurn"] and len(frame["alle_regionen"]) == 11
    status, answer = post(server, "/api/suche/rahmen", {"wohnort": "Thun", "kantone": ["BE"], "orte": [],
                                                        "plz": ["3600"], "regionen": []})
    assert status == 200, answer
    assert [entry["portal"] for entry in answer["orte_pro_portal"]] == ["jobscout24"]
    plan = json.loads(get(server, "/api/suche/plan")[2])["plan"]
    assert (plan["orte"], plan["plz"], plan["regionen"]) == (["Thun"], ["3600"], ["grossraum-bern"])
    contents = [server.kontext.ablage.inhalt(eintrag.id) for eintrag in server.kontext.ablage.liste(path)]
    assert JOB.encode("utf-8") in contents  # the earlier state stays as a draft


def test_the_card_has_a_field_for_each_place_line():
    html = (SEITEN / "suche-einstellen.html").read_text(encoding="utf-8")
    for element in ("region-portale", "region-orte", "region-plz", "region-regionen", "portale-orte-text"):
        assert f'id="{element}"' in html, element


def test_the_template_place_lines_are_the_ones_the_card_edits():
    template = (VORLAGEN / "suchprofil.md").read_text(encoding="utf-8")
    assert all(search_frame.values(template)[key] for key in portal_places.KEYS)
