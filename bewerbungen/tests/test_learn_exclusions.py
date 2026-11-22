"""A title word many dismissed hits share, proposed as an exclusion on Suche einstellen (#225, G66).

The app counts without AI; nothing changes in the profile without the person's click. Invented hits only.
"""
import json
import pathlib
import re

import dismissed_words
import search_plan
from hits import Hits
from test_ai_tasks import VORLAGEN
from test_app import get, post, server  # noqa: F401  (server is a fixture)

ROOT = pathlib.Path(__file__).resolve().parents[2]
SEITEN = ROOT / "bewerbungen" / "seiten"
JOB = (VORLAGEN / "suchprofil.md").read_text(encoding="utf-8")
APPRENTICESHIP = (VORLAGEN / "suchprofil-lehrstelle.md").read_text(encoding="utf-8")
POSITIVE = search_plan.title_terms(JOB, "positiv")
EXCLUDED = search_plan.title_terms(JOB, "ausschluss")
ROUTE = "/api/suche/verworfen-woerter"


def hit(number: int, title: str, state: str = "verworfen", company: str = "Beispiel AG") -> dict:
    return {"id": f"t{number}", "stelle": title, "firma": company, "zustand": state, "portal": "jobs.ch"}


FIELD_SERVICE = [hit(1, "Aussendienst Software Berater"), hit(2, "Software Engineer im Aussendienst"),
                 hit(3, "Aussendienst-Techniker Software")]
OTHERS = [hit(4, "Python Entwickler Banking"), hit(5, "Data Engineer Banking"),
          hit(6, "Software Entwickler Aussendienst", "neu"), hit(7, "Python Developer", "uebernommen")]
HITS = FIELD_SERVICE + OTHERS


def proposals(hits: list[dict], hidden: dict | None = None) -> list[dismissed_words.Proposal]:
    return dismissed_words.proposals(hits, POSITIVE, EXCLUDED, hidden or {})


def test_three_dismissed_hits_with_one_title_word_make_a_proposal():
    found = proposals(HITS)
    assert [p.as_dict() for p in found] == [{"wort": "Aussendienst", "ids": ["t1", "t2", "t3"], "verworfen": 3, "andere": 1}]


def test_two_dismissed_hits_are_not_enough():
    assert proposals(FIELD_SERVICE[:2] + OTHERS) == []


def test_hits_that_are_not_dismissed_never_make_a_proposal():
    kept = [{**h, "zustand": "neu"} for h in FIELD_SERVICE]
    assert proposals(kept + OTHERS) == []


def test_a_word_of_the_positive_filter_is_never_proposed():
    # "Software" is in all three titles, but excluding it would end the search the person set up.
    assert "software" not in {p.word.casefold() for p in proposals(HITS)}


def test_hits_the_title_exclusion_already_catches_do_not_count():
    sales = [hit(10 + n, f"Senior Sales Manager Software {n}") for n in range(3)]
    assert {p.word for p in proposals(HITS + sales)} == {"Aussendienst"}


def test_short_words_fillers_and_numbers_are_no_proposal():
    titles = ["IT Support für Software 2027", "IT Support für Software 2026", "IT Support für Python 2025"]
    found = {p.word for p in proposals([hit(20 + n, title) for n, title in enumerate(titles)])}
    assert found == {"Support"}


def test_the_word_most_dismissed_hits_share_comes_first():
    more = [hit(30 + n, f"Web Entwickler Schichtbetrieb {n}") for n in range(4)]
    assert [p.word for p in proposals(HITS + more)] == ["Schichtbetrieb", "Aussendienst"]


def test_a_word_put_aside_comes_back_only_when_more_hits_have_it():
    hidden = {"aussendienst": 3}
    assert proposals(HITS, hidden) == []
    fourth = hit(40, "Aussendienst Web Verkauf")
    assert [p.word for p in proposals(HITS + [fourth], hidden)] == ["Aussendienst"]


def test_the_count_matches_how_the_search_screens_titles():
    # G104: the search catches the word at the start or end of a longer word, never in its middle.
    compound = [hit(50 + n, f"Aussendienstmitarbeiter Software {n}") for n in range(2)]
    inside = [hit(60 + n, f"Teamaussendienstleiter Software {n}") for n in range(2)]
    found = {p.word: p.ids for p in proposals(HITS + compound + inside)}
    assert found["Aussendienst"] == ("t1", "t2", "t3", "t50", "t51")


def write_hits(server, hits: list[dict]) -> None:  # noqa: F811
    Hits(server.kontext.daten)._write(hits)


def job_profile(server) -> pathlib.Path:  # noqa: F811
    path = server.kontext.daten / search_plan.PROFILE
    path.write_text(JOB, encoding="utf-8")
    return path


def listed(server) -> list[dict]:  # noqa: F811
    return json.loads(get(server, ROUTE)[2])["vorschlaege"]


def test_the_page_gets_the_proposal_counted_by_the_app(server):  # noqa: F811
    job_profile(server)
    write_hits(server, HITS)
    assert listed(server) == [{"wort": "Aussendienst", "ids": ["t1", "t2", "t3"], "verworfen": 3, "andere": 1}]


def test_an_apprenticeship_and_a_folder_without_profile_get_no_proposal(server):  # noqa: F811
    write_hits(server, HITS)
    assert listed(server) == []
    (server.kontext.daten / search_plan.PROFILE).write_text(APPRENTICESHIP, encoding="utf-8")
    assert listed(server) == []


def test_adopting_puts_the_word_into_the_title_exclusion_with_drafts(server):  # noqa: F811
    path = job_profile(server)
    write_hits(server, HITS)
    status, answer = post(server, f"{ROUTE}/ausschliessen", {"wort": "aussendienst"})
    assert status == 200 and answer["titel_ausschluss"][-1] == "Aussendienst"
    assert search_plan.parse(path.read_text(encoding="utf-8")).title_exclude == (*EXCLUDED, "Aussendienst")
    contents = [server.kontext.ablage.inhalt(entry.id) for entry in server.kontext.ablage.liste(path)]
    assert JOB.encode("utf-8") in contents and path.read_bytes() in contents
    assert listed(server) == []  # the hits are caught by the exclusion now


def test_a_word_that_is_no_proposal_changes_nothing(server):  # noqa: F811
    path = job_profile(server)
    write_hits(server, HITS)
    for word in ("Banking", "Software", "", None):
        status, answer = post(server, f"{ROUTE}/ausschliessen", {"wort": word})
        assert status == 400 and answer["fehler"], word
    assert path.read_text(encoding="utf-8") == JOB
    assert server.kontext.ablage.liste(path) == []


def test_not_now_puts_the_proposal_aside_without_touching_the_profile(server):  # noqa: F811
    path = job_profile(server)
    write_hits(server, HITS)
    assert post(server, f"{ROUTE}/nicht-jetzt", {"wort": "Aussendienst"})[0] == 200
    assert listed(server) == []
    assert path.read_text(encoding="utf-8") == JOB
    write_hits(server, HITS + [hit(40, "Aussendienst Web Verkauf")])
    assert [p["wort"] for p in listed(server)] == ["Aussendienst"]


def test_the_link_shows_exactly_the_dismissed_hits_with_the_word(server):  # noqa: F811
    job_profile(server)
    write_hits(server, HITS)
    status, _, body = get(server, f"{ROUTE}/beleg", wort="Aussendienst")
    assert status == 200 and json.loads(body) == {"wort": "Aussendienst", "ids": ["t1", "t2", "t3"]}


def test_the_app_serves_the_scripts_of_the_proposal(server):  # noqa: F811
    for script in ("/verworfen-woerter.js", "/verworfen-woerter-logik.js"):
        assert get(server, script)[0] == 200, script


def test_no_ai_is_involved_and_neither_the_extension_nor_claude_reach_the_routes():
    for name in ("dismissed_words.py", "routes_dismissed_words.py"):
        source = (ROOT / "bewerbungen" / name).read_text(encoding="utf-8")
        assert not re.search(r"^(from ai\b|import ai\b|import routes_ai)", source, re.MULTILINE), name
    for name in ("native_host.py", "mcp_tools.py"):
        assert ROUTE not in (ROOT / "desktop" / name).read_text(encoding="utf-8"), name


def test_the_proposal_sits_in_the_card_what_you_do_not_want_to_see():
    html = (SEITEN / "suche-einstellen.html").read_text(encoding="utf-8")
    card = html[html.index('id="karte-nicht"'):html.index('id="karte-wo"')]
    assert 'id="wort-vorschlag"' in card
    script = (SEITEN / "verworfen-woerter.js").read_text(encoding="utf-8")
    ids = set(re.findall(r'id="([^"]+)"', html))
    assert set(re.findall(r'\$\("([^"$]+)"\)', script)) - ids == set()
    for page in ("suche-einstellen.html", "treffer.html"):
        assert '<script src="/verworfen-woerter-logik.js"></script>' in (SEITEN / page).read_text(encoding="utf-8"), page
    assert '<script src="/verworfen-woerter.js"></script>' in html
