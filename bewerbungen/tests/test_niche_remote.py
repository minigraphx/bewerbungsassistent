"""Whether a remote mention keeps a niche hit outside the region is the person's choice (G125, #390, extends G111).

The switch sits on Suche einstellen under Erweitert, Nischen, and in the search profile as the line
«- Nischen mit Remote ausserhalb der Region: aussortieren» directly under «- Remote: …». Without the line, or with any
other value, the hit stays as in 0.3.3; the app writes the line only when the switch is off. The profile is the
invented template (Kantone BE, SO; Orte Bern, Solothurn); titles, companies and outside places are invented or large
towns far from it, as in test_niche_region.py.
"""
import json

import pytest

import hits  # noqa: F401  (before niche_region, which hits imports while it loads)
import niche_region
import routes_window
import search_frame
import search_plan
import search_terms
from test_app import get, post, server  # noqa: F401  (server is a fixture)
from test_niche_region import NICHE, PLACED, TITLE, TODAY, hit, profile, store  # noqa: F401  (store is a fixture)
from test_routes_search import search  # noqa: F401  (search is a fixture)

OFF_LINE = "- Nischen mit Remote ausserhalb der Region: aussortieren"
REMOTE_LINE = "- Remote: ja"
REASON_ON = "ausserhalb der Region, kein Remote"
REASON_OFF = "ausserhalb der Region"
REMOTE_AD = "Die Stelle ist 100 % remote."


def switched_off(text: str | None = None) -> str:
    base = profile(text)
    changed = base.replace(f"{REMOTE_LINE}\n", f"{REMOTE_LINE}\n{OFF_LINE}\n", 1)
    assert changed != base
    return changed


def region_of(text: str) -> niche_region.Region:
    return niche_region.of_plan(search_plan.parse(text))


ON, OFF = region_of(profile()), region_of(switched_off())


# The line in the profile

def test_without_the_line_a_remote_mention_keeps_the_hit_as_before():
    assert search_plan.parse(profile()).niche_remote_kept is True
    assert ON.keeps(hit(1, "Lugano"), REMOTE_AD)


@pytest.mark.parametrize("value, kept", [("aussortieren", False), ("Aussortieren", False), (" aussortieren ", False),
                                         ("behalten", True), ("vielleicht", True), ("", True)])
def test_only_aussortieren_switches_the_remote_rule_off(value, kept):
    text = profile().replace(f"{REMOTE_LINE}\n", f"{REMOTE_LINE}\n- Nischen mit Remote ausserhalb der Region: {value}\n", 1)
    assert search_plan.parse(text).niche_remote_kept is kept


# Screening with the switch off

def test_switched_off_a_remote_ad_outside_the_region_is_screened_out_with_the_plain_reason(store):
    outside = []
    result = store.add([hit(1, "Lugano", text=REMOTE_AD)], [], TODAY, region=OFF, on_outside=outside.append)

    assert (result["neu"], result["ausserhalb_region"]) == (0, 1)
    assert [found["portal_id"] for found in outside] == ["nr-1"]
    assert niche_region.REASON_OFF == REASON_OFF
    assert OFF.reason == REASON_OFF and ON.reason == REASON_ON


def test_switched_off_a_remote_title_does_not_keep_the_hit_either(store):
    assert store.add([hit(2, "Lugano", title="Remote EdTech Lead")], [], TODAY, region=OFF)["neu"] == 0


def test_switched_off_places_in_the_region_unknown_places_and_place_bound_searches_still_keep_the_hit(store):
    found = [hit(3, "Olten", text=REMOTE_AD), hit(4, "Musterhausen"), hit(5, "Lugano", queries=(NICHE, PLACED))]
    assert store.add(found, [], TODAY, region=OFF)["neu"] == 3


def test_switched_off_without_cantons_the_rule_stays_off(store):
    text = switched_off().replace("- Kantone (job-room): BE, SO\n", "", 1)
    assert store.add([hit(6, "Lugano")], [], TODAY, region=region_of(text))["neu"] == 1


def test_switched_off_the_screening_counts_a_remembered_link_without_loading_it_even_with_a_remote_title(store):
    store.add([hit(7, "Lugano", text=REMOTE_AD)], [], TODAY, region=OFF)
    reasons = []

    again = store.screen([hit(7, "Lugano", title="Remote EdTech Lead")], (), 45, [], region=OFF,
                         on_screened_out=lambda found, reason: reasons.append(reason))

    assert (again["holen"], again["gefiltert"]) == ([], [{"stelle": "Remote EdTech Lead", "grund": REASON_OFF}])
    assert reasons == [REASON_OFF]


# Switching

def test_turning_the_switch_back_on_asks_again_for_the_ads_screened_out_while_off(store):
    store.add([hit(8, "Lugano", text=REMOTE_AD)], [], TODAY, region=OFF)

    assert store.screen([hit(8, "Lugano")], (), 45, [], region=ON)["holen"] == ["jobs.ch:nr-8"]
    assert store.add([hit(8, "Lugano", text=REMOTE_AD)], [], TODAY, region=ON)["neu"] == 1


def test_turning_it_off_keeps_out_what_was_screened_out_while_on_without_loading_it(store):
    store.add([hit(9, "Lugano")], [], TODAY, region=ON)

    again = store.screen([hit(9, "Lugano")], (), 45, [], region=OFF)

    assert (again["holen"], again["gefiltert"]) == ([], [{"stelle": TITLE, "grund": REASON_OFF}])


# Writing the switch

def test_switching_off_writes_the_line_directly_under_remote_and_switching_on_removes_it():
    text = profile()
    off = search_frame.with_values(text, {"nischen_remote": False})

    assert f"{REMOTE_LINE}\n{OFF_LINE}\n" in off
    assert search_frame.values(off)["nischen_remote"] is False
    assert search_frame.with_values(off, {"nischen_remote": True}) == text
    assert search_frame.values(text)["nischen_remote"] is True


def test_switching_on_a_profile_without_the_line_changes_nothing():
    assert search_frame.with_values(profile(), {"nischen_remote": True}) == profile()


def test_a_line_with_another_value_is_replaced_in_place():
    text = profile().replace(f"{REMOTE_LINE}\n", f"{REMOTE_LINE}\n- Pendelgrenze: 45 Minuten\n- Nischen mit Remote ausserhalb der Region: behalten\n", 1)
    off = search_frame.with_values(text, {"nischen_remote": False})
    assert f"- Pendelgrenze: 45 Minuten\n{OFF_LINE}\n" in off
    assert off.count("Nischen mit Remote") == 1


def test_without_a_remote_line_the_line_goes_after_the_last_line_of_the_region():
    text = profile().replace(f"{REMOTE_LINE}\n", "", 1)
    off = search_frame.with_values(text, {"nischen_remote": False})
    last = [line for line in search_plan.section_lines(text, "## Region") if line.startswith("- ")][-1]
    assert f"{last}\n{OFF_LINE}\n" in off
    assert search_plan.parse(off).niche_remote_kept is False


def test_without_any_line_in_the_region_the_line_starts_the_section():
    text = "# Suchprofil\n\n## Region\n\n## Keywords\n- Kernliste: Lernbegleiter\n- Nischen (ohne Ort suchen): EdTech\n"
    off = search_frame.with_values(text, {"nischen_remote": False})
    assert search_plan.section_lines(off, "## Region") == [OFF_LINE]


@pytest.mark.parametrize("value", ["nein", 0, None, "aussortieren"])
def test_only_true_or_false_is_taken(value):
    with pytest.raises(ValueError):
        search_frame.with_values(profile(), {"nischen_remote": value})


def test_an_apprenticeship_profile_has_no_such_switch():
    from test_niche_region import VORLAGEN
    text = (VORLAGEN / "suchprofil-lehrstelle.md").read_text(encoding="utf-8")
    with pytest.raises(ValueError):
        search_frame.with_values(text, {"nischen_remote": False})


# The choice survives every save of the app

def test_the_choice_survives_the_cards_of_suche_einstellen():
    text = switched_off()
    for change in ({"kantone": ["BE", "SO", "FR"]}, {"wohnort": "Bern"}, {"pensum": "80 %"},
                   {"titel_positiv": ["Lernen"]}, {"ausschluss": ["Vertrieb"]}, {"orte": ["Bern"]}):
        text = search_frame.with_values(text, change)
        assert search_plan.parse(text).niche_remote_kept is False, change


def test_the_choice_survives_changes_to_the_terms_and_the_window():
    text = search_terms.added(switched_off(), "Lernbegleiter")
    text = search_terms.removed(text, "TypeScript")
    text = search_terms.moved_to_niches(text, "Data Engineer")
    text = routes_window.with_window(text, 14)
    assert f"{REMOTE_LINE}\n{OFF_LINE}\n" in text


def test_the_choice_survives_a_profile_from_meine_angaben_that_does_not_name_it():
    replaced, _ = search_terms.kept_on_replace(switched_off(), profile())

    assert f"{REMOTE_LINE}\n{OFF_LINE}\n" in replaced
    assert search_plan.parse(replaced).niche_remote_kept is False


def test_a_profile_from_meine_angaben_without_the_line_stays_without_it():
    replaced, _ = search_terms.kept_on_replace(profile(), profile())
    assert "Nischen mit Remote" not in replaced


# Through the routes

def write_profile(s, text: str) -> None:
    (s.kontext.daten / search_plan.PROFILE).write_text(text, encoding="utf-8")


def read_profile(s) -> str:
    return (s.kontext.daten / search_plan.PROFILE).read_text(encoding="utf-8")


def test_the_card_route_saves_the_switch_and_the_pages_read_it(search):  # noqa: F811
    write_profile(search, profile())
    assert json.loads(get(search, "/api/suche/rahmen")[2])["werte"]["nischen_remote"] is True
    assert json.loads(get(search, "/api/suche/liste")[2])["region"]["nischen_remote"] is True

    status, answer = post(search, "/api/suche/rahmen", {"nischen_remote": False})

    assert (status, answer["werte"]["nischen_remote"]) == (200, False)
    assert f"{REMOTE_LINE}\n{OFF_LINE}\n" in read_profile(search)
    assert json.loads(get(search, "/api/suche/liste")[2])["region"]["nischen_remote"] is False
    assert json.loads(get(search, "/api/suche/ertrag")[2])["nischen_remote"] is False
    assert post(search, "/api/suche/rahmen", {"nischen_remote": "nein"})[0] == 400

    post(search, "/api/suche/rahmen", {"nischen_remote": True})
    assert read_profile(search) == profile()


def test_a_run_with_the_switch_off_counts_the_remote_ad_outside_and_does_not_load_it_again(search):  # noqa: F811
    write_profile(search, switched_off())
    listing = [hit(1, "Olten"), hit(2, "Lugano", text=REMOTE_AD)]
    post(search, "/api/suche/sichten", {"treffer": listing})
    received = post(search, "/api/suche/treffer", {"treffer": listing})[1]
    assert (received["neu"], received["ausserhalb_region"]) == (1, 1)
    queries = [{**NICHE, "treffer": 2}, {**PLACED, "treffer": 0}]
    post(search, "/api/suche/abschluss", {"portale": {"jobs.ch": {"treffer": 2, "neu": 1, "problem": "", "abfragen": queries}}})

    shown = json.loads(get(search, "/api/suche/ertrag")[2])
    niche = next(row for row in shown["orte"] if row.get("nischen"))
    assert (niche["ausserhalb_region"], niche["ausserhalb_orte"]) == (1, [{"ort": "Lugano", "anzahl": 1}])
    again = post(search, "/api/suche/sichten", {"treffer": [hit(2, "Lugano", text=REMOTE_AD)]})[1]
    assert (again["holen"], again["gefiltert"]) == ([], [{"stelle": TITLE, "grund": REASON_OFF}])

    post(search, "/api/suche/rahmen", {"nischen_remote": True})
    assert post(search, "/api/suche/sichten", {"treffer": [hit(2, "Lugano")]})[1]["holen"] == ["jobs.ch:nr-2"]
