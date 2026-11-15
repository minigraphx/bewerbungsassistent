"""Adopt a point of a hit's AI rating as an exclusion in the search profile (#224, G83); invented hits only.

The app proposes what it would add without AI: a word of the point that the hit's title has goes to the title filter,
anything else to the exclusions the rating reads. The person confirms or edits; drafts before and after, and an undo.
"""
import json
import pathlib
import re
import shutil
import subprocess

import pytest

import search_frame
import search_plan
from ai import tasks
from hits import Hits
from test_ai_tasks import VORLAGEN
from test_app import get, post, server  # noqa: F401  (server is a fixture)
from test_routes_search import HIT, listing, search  # noqa: F401  (search is a fixture)

ROOT = pathlib.Path(__file__).resolve().parents[2]
PAGES = ROOT / "bewerbungen" / "seiten"
ROUTE = "/api/suche/haken-ausschluss"
UNDO = ROUTE + "/rueckgaengig"
POINTS_ROUTE = ROUTE + "/punkte"
POINTS = ["Pikettdienst alle vier Wochen", "Englisch eine Stufe unter dem Verlangten",
          "Python nur am Rand, vor allem Java", "Reisetätigkeit; oft im Ausland"]


@pytest.fixture
def rated(search):  # noqa: F811
    """One hit whose title shares a word with its first point, rated with four points under Was fehlt."""
    raw = {**HIT, "stelle": "Python Systemtechniker mit Pikettdienst"}
    assert post(search, "/api/suche/treffer", {"treffer": [raw]})[0] == 200
    hit_id = listing(search)["treffer"][0]["id"]
    Hits(search.kontext.daten).update(hit_id, bewertung={"note": 4, "zusammenfassung": "Erfunden",
                                                         "passt": ["Python"], "haken": POINTS})
    return hit_id


def profile(s) -> str:
    return (s.kontext.daten / search_plan.PROFILE).read_text(encoding="utf-8")


def drafts(s) -> list:
    return s.kontext.ablage.liste(s.kontext.daten / search_plan.PROFILE)


def preview(s, hit_id, point):
    status, _, content = get(s, ROUTE, id=hit_id, punkt=point)
    return status, json.loads(content)


def adopt(s, hit_id, point, kind, value):
    return post(s, ROUTE, {"id": hit_id, "punkt": point, "art": kind, "wert": value})


def test_a_word_of_the_point_in_the_title_is_proposed_for_the_title_filter(search, rated):  # noqa: F811
    before, kept = profile(search), len(drafts(search))

    status, answer = preview(search, rated, 0)

    assert status == 200
    assert (answer["art"], answer["wert"], answer["text"]) == ("titel_ausschluss", "Pikettdienst", POINTS[0])
    assert answer["werte"]["titel_ausschluss"] == search_frame.values(before)["titel_ausschluss"]
    assert (profile(search), len(drafts(search))) == (before, kept), "the proposal changes nothing"


def test_a_point_without_a_title_word_is_proposed_as_an_exclusion_of_the_ad(search, rated):  # noqa: F811
    answer = preview(search, rated, 1)[1]

    assert (answer["art"], answer["wert"]) == ("ausschluss", "Englisch eine Stufe unter dem Verlangten")


def test_a_word_the_search_looks_for_is_never_proposed_for_the_title_filter(search, rated):  # noqa: F811
    answer = preview(search, rated, 2)[1]

    assert answer["art"] == "ausschluss", "Python is in Titelfilter Positiv"
    assert answer["wert"] == "Python nur am Rand", "a comma would split the entry in the profile"


def test_the_proposal_stops_at_a_semicolon_and_keeps_within_the_field(search, rated):  # noqa: F811
    assert preview(search, rated, 3)[1]["wert"] == "Reisetätigkeit"
    long_point = "Sehr " * 30 + "lange Anforderung"
    Hits(search.kontext.daten).update(rated, bewertung={"note": 4, "zusammenfassung": "x", "haken": [long_point]})

    value = preview(search, rated, 0)[1]["wert"]

    assert len(value) <= 80 and long_point.startswith(value) and not value.endswith(" ")


def test_confirming_an_edited_value_adds_it_to_the_exclusions_with_drafts(search, rated):  # noqa: F811
    kept = len(drafts(search))

    status, answer = adopt(search, rated, 1, "ausschluss", "  Pikettdienst ")

    assert status == 200 and (answer["art"], answer["wert"]) == ("ausschluss", "Pikettdienst")
    assert search_frame.values(profile(search))["ausschluss"] == ["Bildung ohne IT-Bezug", "Recruiting", "Pikettdienst"]
    assert answer["werte"]["ausschluss"][-1] == "Pikettdienst"
    assert len(drafts(search)) == kept + 2, "a draft before and after"


def test_later_ratings_read_the_adopted_exclusion(search, rated):  # noqa: F811
    assert adopt(search, rated, 1, "ausschluss", "Pikettdienst")[0] == 200

    material = tasks.load_material(search.kontext.daten)

    assert "Ausschluss: Bildung ohne IT-Bezug, Recruiting, Pikettdienst" in material.profile
    assert "Pikettdienst" in search_plan.frame(material.profile)["ausschluss"]


def test_later_searches_keep_titles_with_the_adopted_word_away(search, rated):  # noqa: F811
    assert adopt(search, rated, 0, "titel_ausschluss", "Pikettdienst")[0] == 200
    later = {**HIT, "portal_id": "p-9", "stelle": "Netzwerk Pikettdienst Engineer", "link": HIT["link"] + "p9"}

    screened = post(search, "/api/suche/sichten", {"treffer": [later]})[1]

    assert screened["gefiltert"] == [{"stelle": "Netzwerk Pikettdienst Engineer", "grund": "Titel: Pikettdienst"}]
    assert "Pikettdienst" in search_plan.title_terms(profile(search), "ausschluss")


def test_undo_takes_out_exactly_the_adopted_entry_with_drafts(search, rated):  # noqa: F811
    before = search_frame.values(profile(search))
    assert adopt(search, rated, 0, "titel_ausschluss", "Pikettdienst")[0] == 200
    kept = len(drafts(search))

    status, answer = post(search, UNDO, {"art": "titel_ausschluss", "wert": "Pikettdienst"})

    assert status == 200 and answer["werte"]["titel_ausschluss"] == before["titel_ausschluss"]
    assert search_frame.values(profile(search)) == before
    assert len(drafts(search)) == kept + 1, "the state with the entry is saved already; the one after is new"
    status, refused = post(search, UNDO, {"art": "titel_ausschluss", "wert": "Pikettdienst"})
    assert status == 400 and "Rückgängig geht nicht mehr" in refused["fehler"]


def test_an_entry_already_there_is_refused_and_nothing_is_written(search, rated):  # noqa: F811
    before, kept = profile(search), len(drafts(search))

    status, answer = adopt(search, rated, 1, "ausschluss", "recruiting")

    assert status == 400 and answer["fehler"] == "«recruiting» steht schon unter «Im Inserat»."
    assert (profile(search), len(drafts(search))) == (before, kept)


@pytest.mark.parametrize(("point", "kind", "value", "message"), [
    (9, "ausschluss", "Pikettdienst", "Diesen Punkt gibt es in der Einschätzung nicht mehr."),
    ("0", "ausschluss", "Pikettdienst", "Diesen Punkt gibt es in der Einschätzung nicht mehr."),
    (0, "ort", "Pikettdienst", "Bitte «Im Titel» oder «Im Inserat» wählen."),
    (0, "ausschluss", "   ", "Bitte angeben, was nicht mehr kommen soll."),
    (0, "ausschluss", "Pikett, Nacht", "Bitte ohne Komma, ein Ausschluss pro Eintrag."),
    (0, "ausschluss", "x" * 81, "„xxxxxxxxxxxxxxxxxxxx…“ ist zu lang: höchstens 80 Zeichen."),
])
def test_a_bad_confirmation_is_refused_and_nothing_is_written(search, rated, point, kind, value, message):  # noqa: F811
    before, kept = profile(search), len(drafts(search))

    status, answer = adopt(search, rated, point, kind, value)

    assert (status, answer["fehler"]) == (400, message)
    assert (profile(search), len(drafts(search))) == (before, kept)


def test_an_unknown_hit_is_not_found(search, rated):  # noqa: F811
    assert preview(search, "jobs-ch-000000000000", 0)[0] == 404
    assert adopt(search, "jobs-ch-000000000000", 0, "ausschluss", "Pikettdienst")[0] == 404


def test_an_unrated_point_or_a_bad_index_is_refused_in_the_preview(search, rated):  # noqa: F811
    assert preview(search, rated, 4)[0] == 400
    assert preview(search, rated, "eins")[0] == 400


def test_an_apprenticeship_search_has_no_such_exclusions(search, rated):  # noqa: F811
    shutil.copy(VORLAGEN / "suchprofil-lehrstelle.md", search.kontext.daten / search_plan.PROFILE)
    before = profile(search)

    status, answer = preview(search, rated, 0)

    assert status == 400 and answer["fehler"] == "Ausschlüsse aus der Einschätzung gibt es nur bei der Stellensuche."
    assert adopt(search, rated, 0, "ausschluss", "Pikettdienst")[0] == 400
    assert profile(search) == before


def test_neither_the_extension_nor_claude_reach_the_routes():
    for name in ("native_host.py", "mcp_tools.py"):
        assert "/api/suche/haken-ausschluss" not in (ROOT / "desktop" / name).read_text(encoding="utf-8"), name


def test_the_page_offers_each_point_of_the_rating():
    page = (PAGES / "treffer.html").read_text(encoding="utf-8")
    script = (PAGES / "treffer.js").read_text(encoding="utf-8")

    assert page.index('src="/haken-ausschluss-logik.js"') < page.index('src="/haken-ausschluss.js"') < page.index('src="/treffer.js"')
    assert page.index('src="/texte.js"') < page.index('src="/haken-ausschluss.js"')
    assert "HakenAusschluss.liste(" in script


def excluded_points(s, hit_id):
    status, _, content = get(s, POINTS_ROUTE, id=hit_id)
    return status, json.loads(content)


def test_the_page_learns_which_points_are_excluded_already(search, rated):  # noqa: F811
    assert excluded_points(search, rated) == (200, {"ausgeschlossen": [False, False, False, False]})
    assert adopt(search, rated, 0, "titel_ausschluss", "Pikettdienst")[0] == 200
    assert adopt(search, rated, 1, "ausschluss", "englisch")[0] == 200

    assert excluded_points(search, rated)[1] == {"ausgeschlossen": [True, True, False, False]}


def test_a_point_counts_as_excluded_only_for_a_whole_word(search, rated):  # noqa: F811
    assert adopt(search, rated, 1, "ausschluss", "Stufe unter")[0] == 200
    assert adopt(search, rated, 3, "ausschluss", "Reise")[0] == 200

    assert excluded_points(search, rated)[1]["ausgeschlossen"] == [False, True, False, False]


def test_an_apprenticeship_search_names_no_excluded_points(search, rated):  # noqa: F811
    shutil.copy(VORLAGEN / "suchprofil-lehrstelle.md", search.kontext.daten / search_plan.PROFILE)

    assert excluded_points(search, rated)[0] == 400


def test_the_feedback_stays_inside_the_point_on_the_page():
    """Runs the page part with a small stand-in DOM: form in the point, errors inline, confirmation with undo."""
    result = subprocess.run(["node", "--test", "tests/haken_ausschluss_seite.test.cjs"], cwd=ROOT / "bewerbungen",
                            capture_output=True, text=True, timeout=120)

    assert result.returncode == 0, result.stdout + result.stderr


def test_the_buttons_are_big_enough_to_tap_on_a_phone():
    css = (PAGES / "stellen.css").read_text(encoding="utf-8")
    phone = re.search(r"@media \(max-width: 480px\) \{(.*?)\n\}", css, re.S)

    assert phone, "a block for phones"
    rule = re.search(r"\.exclusion-point \.btn[^{]*\{[^}]*min-height: 44px", phone.group(1))
    assert rule, "the buttons of a point are at least 44 px high on a phone"


def test_the_places_in_the_form_have_no_line_between_them():
    css = (PAGES / "stellen.css").read_text(encoding="utf-8")

    assert re.search(r"\.exclusion-adopt \.choice \{[^}]*border-bottom: 0;", css), \
        "the two places read as one choice, not as the list of firmen.css"


def test_the_guide_says_where_the_confirmation_and_undo_appear():
    guide = (ROOT / "docs" / "installation.md").read_text(encoding="utf-8")
    section = guide[guide.index("### Einen Punkt der Einschätzung ausschliessen"):]
    section = section[:section.index("\n### ", 1)]

    assert "Ein Klick zeigt, was die App" in section and "einträgt" in section
    assert "sonst den Punkt bis zum ersten Komma oder Strichpunkt **Im Inserat**" in section
    assert "**Im Inserat** liest die KI bei jeder weiteren Einschätzung als Ausschluss mit; " \
           "die Stelle kommt aber weiter in die Liste" in section
    assert "**Rückgängig** in der Bestätigung, die an Stelle des Formulars erscheint" in section
    assert "«Was Sie nicht sehen wollen»" in section or "**Was Sie nicht sehen wollen**" in section
    assert "**Ausgeschlossen**" in section
    assert re.search(r"!\[[^\]]+\]\(bilder/ausschluss-uebernehmen\.jpg\)", section), "the open form as a picture"
