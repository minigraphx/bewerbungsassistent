"""Known jobs by content (G109, #385): reposts, recruiter reposts, discarded jobs and one ad sent five times.

All data is invented. Each case runs the flow of the extension: screen, send what the app asked for, finish."""
import pytest

import unterlagen
from test_app import post, server  # noqa: F401  (server is a fixture)
from test_routes_search import listing, search  # noqa: F401  (search is a fixture)

DAY = "2026-10-26"  # the date of the test server
FIRST_LINK = "https://www.jobs.ch/de/stellenangebote/detail/kw-0/"
ORIGINAL_AD = "Stelle: Data Engineer\n\nDas ursprüngliche Inserat.\n"


def ad(number: str, **fields) -> dict:
    base = {"portal": "jobs.ch", "portal_id": f"kw-{number}", "stelle": "Data Engineer (m/w/d) 80–100 %",
            "firma": "Kieswerk Beispiel AG", "ort": "3011 Bern", "pensum": "80–100 %",
            "link": f"https://www.jobs.ch/de/stellenangebote/detail/kw-{number}/", "alter_tage": 1,
            "text": "Prozesse, Qualität, Deutsch."}
    return {**base, **fields}


def run(s, ads: list[dict]) -> dict:
    """What the extension does in one run: screen, then send only the ads the app asked for."""
    status, screened = post(s, "/api/suche/sichten", {"treffer": ads})
    assert status == 200
    wanted = [a for a in ads if f"{a['portal']}:{a['portal_id']}" in screened["holen"]]
    if wanted:
        assert post(s, "/api/suche/treffer", {"treffer": wanted})[0] == 200
    assert post(s, "/api/suche/abschluss", {"portale": {"jobs.ch": {"treffer": len(ads), "neu": len(wanted), "problem": ""}}})[0] == 200
    return screened


def saved_entry(s, **fields) -> dict:
    k = s.kontext
    entry = k.register().neu(**{"firma": "Kieswerk Beispiel AG", "stelle": "Data Engineer", "ort": "Bern",
                                "pensum": "80–100 %", "portal": "jobs.ch", "link": FIRST_LINK, "status": "Beworben", **fields})
    path = unterlagen.bewerbungsordner(k.daten, entry["id"]) / "stelle.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(ORIGINAL_AD, encoding="utf-8")
    return entry


def new_hits(s) -> list[dict]:
    return [hit for hit in listing(s)["treffer"] if hit["zustand"] == "neu"]


def test_a_reposted_ad_with_a_new_id_and_link_is_not_new_and_the_entry_carries_it(search):
    entry = saved_entry(search)
    screened = run(search, [ad("2")])
    assert screened["holen"] == [], "a known job needs no text and no AI"
    assert new_hits(search) == []
    stored = search.kontext.register().hole(entry["id"])
    assert stored["link"] == FIRST_LINK and stored["stelle"] == "Data Engineer"
    assert stored["wieder_ausgeschrieben"] == [{"datum": DAY, "portal": "jobs.ch", "link": ad("2")["link"]}]
    folder = unterlagen.bewerbungsordner(search.kontext.daten, entry["id"])
    assert (folder / "stelle.md").read_text(encoding="utf-8") == ORIGINAL_AD
    drafts = [d.beschreibung for d in search.kontext.ablage.liste(search.kontext.register().pfad)]
    assert drafts[:2] == ["Wieder ausgeschriebene Stellen vermerkt", "Stand vor: Wieder ausgeschriebene Stellen vermerkt"]


def test_the_new_link_is_known_at_once_and_noted_once(search):
    entry = saved_entry(search)
    screened = run(search, [ad("2"), ad("2", portal_id="kw-2-copy")])
    assert screened["holen"] == [] and screened["bekannt"] == 1
    assert run(search, [ad("2")])["bekannt"] == 1
    assert len(search.kontext.register().hole(entry["id"])["wieder_ausgeschrieben"]) == 1


def test_a_recruiter_reposting_its_own_ad_is_not_new(search):
    entry = saved_entry(search, firma="Adecco", stelle="Software Tester 100 %", ort="Zürich", pensum="100 %",
                        link="https://www.jobs.ch/de/stellenangebote/detail/ad-1/")
    repost = ad("ad-2", firma="Adecco", stelle="Software Tester 100 %", ort="8000 Zürich", pensum="100 %")
    assert run(search, [repost])["holen"] == []
    assert new_hits(search) == []
    assert search.kontext.register().hole(entry["id"])["wieder_ausgeschrieben"][0]["link"] == repost["link"]


def test_a_recruiter_ad_of_a_saved_job_is_only_suggested(search):
    entry = saved_entry(search)
    agency = ad("ad-3", firma="Adecco", stelle="Data Engineer 80–100 %")
    assert run(search, [agency])["holen"] == ["jobs.ch:kw-ad-3"], "a recruiter ad never matches for sure"
    [listed] = new_hits(search)
    assert {"id": entry["id"], "stelle": "Data Engineer"} in listed["vielleicht_dieselbe"]["bewerbungen"]
    assert "Könnte dieselbe Stelle sein" in listed["vielleicht_dieselbe"]["satz"]
    assert "wieder_ausgeschrieben" not in search.kontext.register().hole(entry["id"])


def test_a_discarded_job_reposted_stays_discarded_with_grade_and_reason(search):
    run(search, [ad("1")])
    [first] = listing(search)["treffer"]
    rating = {"note": 2.5, "zusammenfassung": "Zu weit weg vom Profil.", "passt": [], "haken": ["Schichtarbeit"],
              "neue_luecken": [], "auffaellig": []}
    assert post(search, "/api/suche/bewertung", rating, id=first["id"])[0] == 200
    assert post(search, "/api/suche/verwerfen", {}, id=first["id"])[0] == 200
    screened = run(search, [ad("5")])
    assert screened["holen"] == []
    [stored] = listing(search)["treffer"]
    assert stored["zustand"] == "verworfen"
    assert (stored["bewertung"]["note"], stored["bewertung"]["haken"]) == (2.5, ["Schichtarbeit"])
    assert stored["link"] == ad("1")["link"]
    assert stored["wieder_ausgeschrieben"] == [{"datum": DAY, "portal": "jobs.ch", "link": ad("5")["link"]}]
    assert run(search, [ad("5")])["bekannt"] == 1


def test_one_portal_sending_the_same_ad_five_times_lists_one_job(search):
    five = [ad(str(n)) for n in range(1, 6)]
    screened = run(search, five)
    assert screened["holen"] == ["jobs.ch:kw-1"]
    [job] = listing(search)["treffer"]
    assert [w["link"] for w in job["weitere"]] == [a["link"] for a in five[1:]]
    assert {w["portal"] for w in job["weitere"]} == {"jobs.ch"}
    assert all(w["datum"] == "2026-10-25" for w in job["weitere"]), "the day of the ad: one day online"
    assert run(search, five)["bekannt"] == 5


def test_the_run_counts_what_the_app_knew_already(search):
    saved_entry(search)
    run(search, [ad("1", firma="Sägerei Muster GmbH", stelle="Python Entwickler")])
    [first] = listing(search)["treffer"]
    assert post(search, "/api/suche/verwerfen", {}, id=first["id"])[0] == 200
    run(search, [ad("2"), ad("3", firma="Sägerei Muster GmbH", stelle="Python Entwickler")])
    assert listing(search)["letzte_suche"]["wieder_ausgeschrieben"] == {"bewerbungen": 1, "verworfen": 1}


def test_the_page_cannot_write_the_reposts(search):
    entry = saved_entry(search)
    run(search, [ad("2")])
    forged = [{"datum": DAY, "portal": "jobs.ch", "link": "https://www.jobs.ch/x"}]
    assert post(search, "/api/bewerbung", {"id": entry["id"], "wieder_ausgeschrieben": forged, "notiz": "neu"})[0] == 200
    stored = search.kontext.register().hole(entry["id"])
    assert stored["wieder_ausgeschrieben"][0]["link"] == ad("2")["link"] and stored["notiz"] == "neu"


@pytest.mark.parametrize("changed", [
    {"firma": ""},  # no company name: «unbekannt» never matches
    {"pensum": "40 %", "stelle": "Data Engineer 40 %"},  # another pensum
    {"ort": "Genève"},  # another place
    {"stelle": "Software Architekt"},  # another job at the same company
])
def test_what_only_looks_alike_stays_new(search, changed):
    saved_entry(search, **({"firma": "unbekannt"} if "firma" in changed else {}))
    assert run(search, [ad("2", **changed)])["holen"] == ["jobs.ch:kw-2"]
    assert len(new_hits(search)) == 1
