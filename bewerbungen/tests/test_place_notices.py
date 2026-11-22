"""Hints on the places of the region card (G107, #380): a jobs.ch place in a canton another place already covers, and
jobscout24 at several postcodes without a region. Only for a job search; invented terms, places are public towns.
"""
import json

import hits
import place_cantons
import place_notices
import search_plan
from test_app import get, post, server  # noqa: F401  (server is a fixture)

PROFILE = """# Suchprofil

## Region
- Kantone (job-room): AG
- Orte (jobs.ch): {places}
- PLZ (jobscout24): 5000

## Keywords
- Kernliste: Kursplaner, Lernbegleiter, Datenpfleger
- Nischen (ohne Ort suchen): Lernatelier
"""
TWO = PROFILE.format(places="Aarau, Baden")
NOTICE = ("Aarau und Baden liegen beide im Kanton Aargau. jobs.ch sucht bei jedem Ort auch im ganzen Kanton, ein "
          "zweiter Ort im selben Kanton bringt darum kaum neue Stellen. Baden kostet 3 Suchen pro Suchlauf.")


def notices(text: str = TWO, off=(), kept=()) -> dict:
    return place_notices.notices(text, None, list(off), list(kept))


def test_the_later_place_in_the_same_canton_gets_the_notice_with_its_searches():
    [notice] = notices()["orte"]
    assert notice["text"] == NOTICE
    assert (notice["ort"], notice["knopf"], notice["behalten"]) == ("Baden", "Baden entfernen", "Behalten")


def test_the_cost_is_what_the_next_run_saves_with_the_limits_of_the_terms():
    limited = TWO.replace(", Datenpfleger\n", "\n- Nur job-room: Datenpfleger\n")
    [notice] = notices(limited)["orte"]
    assert notice["text"].endswith("Baden kostet 2 Suchen pro Suchlauf.")
    one = TWO.replace("Kursplaner, Lernbegleiter, Datenpfleger", "Kursplaner")
    assert notices(one)["orte"][0]["text"].endswith("Baden kostet 1 Suche pro Suchlauf.")


def test_each_later_place_of_a_canton_names_the_first():
    [baden, brugg] = notices(PROFILE.format(places="Aarau, Bern, Baden, Brugg"))["orte"]
    assert baden["text"].startswith("Aarau und Baden liegen beide im Kanton Aargau.")
    assert brugg["text"].startswith("Aarau und Brugg liegen beide im Kanton Aargau.")


def test_no_notice_for_an_ambiguous_or_unknown_place_or_in_different_cantons():
    assert place_cantons.canton_of("Buchs") is None
    assert place_cantons.canton_of("Nordstadt") is None
    assert place_cantons.canton_of("baden") == "AG"
    for places in ("Aarau, Buchs", "Aarau, Nordstadt", "Aarau, Bern", "Aarau", "Aarau, Wil"):
        assert notices(PROFILE.format(places=places))["orte"] == [], places


def test_no_notice_when_jobs_ch_is_off_kept_or_for_an_apprenticeship():
    assert notices(off=["jobs.ch"])["orte"] == []
    assert notices(kept=["baden"])["orte"] == []
    assert place_notices.notices("## Lehrbeginn\n- 2027\n## Region\n- Wohnort: Aarau\n", None, [], [])["orte"] == []


def test_a_place_with_a_remark_or_inside_a_group_is_not_offered():
    assert notices(PROFILE.format(places="Aarau, Aarau/Baden"))["orte"] == []
    [notice] = notices(PROFILE.format(places="Aarau, Baden (nur Teilzeit)"))["orte"]
    assert notice["ort"] == "Baden"


def test_removal_takes_the_place_out_of_its_line_only():
    removal = place_notices.removal(PROFILE.format(places="Aarau, Baden (nur Teilzeit), Bern"), "Baden", None, [])
    assert "- Orte (jobs.ch): Aarau, Bern\n" in removal.text
    assert removal.done == "Baden entfernt. jobs.ch sucht weiter im ganzen Kanton Aargau, und der nächste Suchlauf spart 3 Suchen."


def test_the_removal_says_what_the_next_run_saves_in_the_singular_too():
    one = TWO.replace("Kursplaner, Lernbegleiter, Datenpfleger", "Kursplaner")
    removal = place_notices.removal(one, "Baden", None, [])
    assert removal.done == "Baden entfernt. jobs.ch sucht weiter im ganzen Kanton Aargau, und der nächste Suchlauf spart 1 Suche."


def test_removal_of_a_place_no_longer_offered_is_refused():
    try:
        place_notices.removal(PROFILE.format(places="Aarau, Bern"), "Bern", None, [])
    except ValueError as error:
        assert str(error) == place_notices.GONE
    else:
        raise AssertionError("a place without notice was removed")


# The nudge towards jobscout24 regions

def test_several_postcodes_without_a_region_get_the_nudge():
    text = TWO.replace("- PLZ (jobscout24): 5000", "- PLZ (jobscout24): 5000, 5400, 5200")
    assert notices(text)["plz"] == {
        "text": ("jobscout24 sucht an 3 PLZ, jede mit 20 km Umkreis; nahe PLZ finden oft dieselben Stellen. "
                 "Mit einer Region sucht jobscout24 einmal pro Begriff."),
        "knopf": "Regionen wählen"}
    assert notices(text, off=["jobscout24"])["plz"] is None
    with_region = text.replace("## Keywords", "- Regionen (jobscout24): Nordwestschweiz\n\n## Keywords")
    assert notices(with_region)["plz"] is None
    assert notices()["plz"] is None


# The routes

def write(server, text: str = TWO) -> None:  # noqa: F811
    (server.kontext.daten / search_plan.PROFILE).write_text(text, encoding="utf-8")


def profile(server) -> str:  # noqa: F811
    return (server.kontext.daten / search_plan.PROFILE).read_text(encoding="utf-8")


def test_the_page_gets_the_notice_and_removes_the_place_on_click_with_undo(server):  # noqa: F811
    write(server)
    status, _, content = get(server, "/api/suche/orte-hinweise")
    assert status == 200 and json.loads(content)["orte"][0]["text"] == NOTICE
    status, answer = post(server, "/api/suche/orte-hinweise/entfernen", {"ort": "Baden"})
    assert status == 200, answer
    assert answer["text"] == "Baden entfernt. jobs.ch sucht weiter im ganzen Kanton Aargau, und der nächste Suchlauf spart 3 Suchen."
    assert "- Orte (jobs.ch): Aarau\n" in profile(server)
    status, back = post(server, "/api/suche/orte-hinweise/rueckgaengig", {"ort": "Baden", "vorher": answer["rueckgaengig"]})
    assert status == 200, back
    assert profile(server) == TWO


def test_undo_after_another_change_puts_the_place_back_at_the_end(server):  # noqa: F811
    write(server, PROFILE.format(places="Aarau, Baden, Bern"))
    _, answer = post(server, "/api/suche/orte-hinweise/entfernen", {"ort": "Baden"})
    write(server, profile(server).replace("Aarau, Bern", "Aarau, Bern, Thun"))
    assert post(server, "/api/suche/orte-hinweise/rueckgaengig", {"ort": "Baden", "vorher": answer["rueckgaengig"]})[0] == 200
    assert "- Orte (jobs.ch): Aarau, Bern, Thun, Baden\n" in profile(server)


def test_keeping_is_remembered_and_the_notice_goes(server):  # noqa: F811
    write(server)
    status, answer = post(server, "/api/suche/orte-hinweise/behalten", {"ort": "Baden"})
    assert status == 200, answer
    assert hits.Hits(server.kontext.daten).settings()[hits.KEPT_PLACES] == ["baden"]
    assert json.loads(get(server, "/api/suche/orte-hinweise")[2])["orte"] == []
    assert profile(server) == TWO


def test_odd_requests_are_refused(server):  # noqa: F811
    write(server)
    for body in ({}, {"ort": 3}, {"ort": "x" * 200}, {"ort": "Bern"}):
        assert post(server, "/api/suche/orte-hinweise/entfernen", body)[0] == 400, body
    assert post(server, "/api/suche/orte-hinweise/rueckgaengig", {"ort": "Baden", "vorher": "nein"})[0] == 400
    assert profile(server) == TWO
