"""Excluded companies (#226, G65): their hits leave the search and the list, the person sees and edits the list.

Only invented companies. The list lives in the data folder, names match like the company register (hits.company_key).
"""
import json
import pathlib

import yaml

import excluded_companies
from test_app import get, post  # noqa: F401
from test_routes_search import HIT, listing, search, server  # noqa: F401  (fixtures)

BUILDER = {**HIT, "portal_id": "bau-1", "stelle": "Software Engineer", "firma": "Muster Bau AG",
           "link": "https://www.jobs.ch/de/stellenangebote/detail/bau-1/"}
CARPENTER = {**HIT, "portal_id": "holz-1", "stelle": "Data Engineer", "firma": "Beispiel Holz GmbH",
             "link": "https://www.jobs.ch/de/stellenangebote/detail/holz-1/"}


def excluded(s, **parameter) -> dict:
    status, _, content = get(s, "/api/firmen/ausgeschlossen", **parameter)
    assert status == 200
    return json.loads(content)


def names(s) -> list[str]:
    return [entry["name"] for entry in excluded(s)["firmen"]]


def exclude(s, name: str) -> dict:
    status, answer = post(s, "/api/firmen/ausschliessen", {"name": name})
    assert status == 200, answer
    return answer


def listed_companies(s) -> list[str]:
    return [hit["firma"] for hit in listing(s)["treffer"]]


# The search


def test_hits_of_an_excluded_company_are_screened_out_before_their_text_is_loaded(search):  # noqa: F811
    exclude(search, "Muster Bau")

    status, screened = post(search, "/api/suche/sichten", {"treffer": [BUILDER, CARPENTER]})

    assert status == 200
    assert screened["holen"] == ["jobs.ch:holz-1"]
    assert screened["ausgeschlossen"] == 1


def test_names_match_like_the_company_register(search):  # noqa: F811
    exclude(search, "MUSTER BAU GmbH")
    other_form = {**BUILDER, "portal_id": "bau-2", "firma": "Muster Bau", "link": BUILDER["link"] + "2"}

    screened = post(search, "/api/suche/sichten", {"treffer": [BUILDER, other_form]})[1]

    assert screened["holen"] == []


def test_hits_of_an_excluded_company_are_not_stored(search):  # noqa: F811
    exclude(search, "Muster Bau")

    received = post(search, "/api/suche/treffer", {"treffer": [BUILDER, CARPENTER]})[1]

    assert received["neu"] == 1
    assert listed_companies(search) == ["Beispiel Holz GmbH"]


def test_listed_hits_are_hidden_and_come_back_when_the_company_is_taken_back(search):  # noqa: F811
    post(search, "/api/suche/treffer", {"treffer": [BUILDER, CARPENTER]})

    answer = exclude(search, "Muster Bau AG")

    assert listed_companies(search) == ["Beispiel Holz GmbH"]
    status, _ = post(search, "/api/firmen/wieder-zeigen", {"schluessel": answer["firma"]["schluessel"]})
    assert status == 200
    assert sorted(listed_companies(search)) == ["Beispiel Holz GmbH", "Muster Bau AG"]
    assert names(search) == []


def test_hidden_hits_are_neither_rated_nor_loaded(search):  # noqa: F811
    without_text = [{key: value for key, value in hit.items() if key != "text"} for hit in (BUILDER, CARPENTER)]
    post(search, "/api/suche/treffer", {"treffer": without_text})
    exclude(search, "Muster Bau")

    status, _, content = get(search, "/api/suche/alle-pruefen")
    loaded = post(search, "/api/inserate/holen", {})[1]["laden"]

    assert status == 200 and json.loads(content)["anzahl"] == 1
    assert [job["portal_id"] for job in loaded if job["art"] == "treffer"] == ["holz-1"]


# From a hit, from Firmen and from an application


def test_the_page_firmen_marks_an_excluded_company(search):  # noqa: F811
    post(search, "/api/suche/treffer", {"treffer": [BUILDER, CARPENTER]})
    exclude(search, "Muster Bau AG")

    rows = {row["schluessel"]: row for row in json.loads(get(search, "/api/firmen")[2])["firmen"]}

    assert rows["muster-bau"]["ausgeschlossen"] is True
    assert rows["beispiel-holz"]["ausgeschlossen"] is False


def test_the_company_of_an_application_can_be_excluded(search):  # noqa: F811
    post(search, "/api/suche/treffer", {"treffer": [BUILDER]})
    entry = search.kontext.register().neu(firma="Muster Bau AG", stelle="Bauführer", status="Absage")

    before = excluded(search, firma=entry["firma"])["firma"]
    exclude(search, entry["firma"])
    after = excluded(search, firma=entry["firma"])["firma"]

    assert (before["ausgeschlossen"], after["ausgeschlossen"]) == (False, True)
    assert before["schluessel"] == "muster-bau"
    assert listed_companies(search) == []


# The list on Suche einstellen


def test_the_list_lives_in_the_data_folder_with_drafts(search):  # noqa: F811
    exclude(search, "Muster Bau AG")
    exclude(search, "Beispiel Holz GmbH")
    path = search.kontext.daten / excluded_companies.FILE

    stored = yaml.safe_load(path.read_text(encoding="utf-8"))
    drafts = [yaml.safe_load(search.kontext.ablage.inhalt(entry.id)) for entry in search.kontext.ablage.liste(path)]

    assert stored == ["Muster Bau AG", "Beispiel Holz GmbH"]
    assert ["Muster Bau AG"] in drafts and stored in drafts
    assert not (pathlib.Path(__file__).resolve().parents[1] / excluded_companies.FILE).exists()


def test_the_person_edits_the_whole_list(search):  # noqa: F811
    exclude(search, "Muster Bau AG")

    status, answer = post(search, "/api/firmen/ausgeschlossen", {"firmen": ["Beispiel Holz GmbH", " ", "beispiel holz"]})

    assert status == 200
    assert [entry["name"] for entry in answer["firmen"]] == ["Beispiel Holz GmbH"]
    assert names(search) == ["Beispiel Holz GmbH"]


def test_excluding_twice_keeps_one_entry(search):  # noqa: F811
    exclude(search, "Muster Bau AG")
    exclude(search, "Muster Bau")

    assert names(search) == ["Muster Bau AG"]


def test_odd_input_is_refused(search):  # noqa: F811
    assert post(search, "/api/firmen/ausschliessen", {"name": "  "})[0] == 400
    assert post(search, "/api/firmen/ausschliessen", {"name": "AG"})[0] == 400
    assert post(search, "/api/firmen/ausgeschlossen", {"firmen": "Muster Bau"})[0] == 400
    too_many = [f"Muster Firma {n}" for n in range(excluded_companies.MAX_COMPANIES + 1)]
    assert post(search, "/api/firmen/ausgeschlossen", {"firmen": too_many})[0] == 400
    assert post(search, "/api/firmen/wieder-zeigen", {"schluessel": "nicht-da"})[0] == 404


def test_odd_values_in_the_file_are_left_out(search):  # noqa: F811
    (search.kontext.daten / excluded_companies.FILE).write_text("- Muster Bau AG\n- 42\n- {x: 1}\n- ''\n", encoding="utf-8")

    assert names(search) == ["Muster Bau AG"]


def test_neither_the_extension_nor_claude_reach_the_list():
    desktop = pathlib.Path(__file__).resolve().parents[2] / "desktop"
    for name in ("native_host.py", "mcp_tools.py"):
        text = (desktop / name).read_text(encoding="utf-8")
        assert "/api/firmen/ausgeschlossen" not in text and "/api/firmen/ausschliessen" not in text
        assert "/api/firmen/wieder-zeigen" not in text
