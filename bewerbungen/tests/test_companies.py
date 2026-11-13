"""The page Firmen (G35, #188): one row per company from hits and applications, its kununu page in firmen.yaml.

Only invented companies; nothing here reads kununu itself (#189).
"""
import datetime
import json

import pytest
import yaml

import companies
from hits import Hits
from test_app import get, post, server  # noqa: F401  (server is a fixture)

TODAY = datetime.date(2026, 11, 9)


def add_hits(s, *hits):
    raw = [{"portal": "jobs.ch", "portal_id": f"x{i}", "stelle": stelle, "firma": firma, "ort": ort,
            "link": f"https://www.jobs.ch/de/stellenangebote/detail/x{i}/", "text": "Erfundenes Inserat."}
           for i, (stelle, firma, ort) in enumerate(hits)]
    Hits(s.kontext.daten).add(raw, [], TODAY)


def companies_of(s) -> dict[str, dict]:
    status, _, content = get(s, "/api/firmen")
    assert status == 200
    return {row["schluessel"]: row for row in json.loads(content)["firmen"]}


def store(s, entries: dict):
    (s.kontext.daten / companies.FILE).write_text(yaml.safe_dump(entries, allow_unicode=True), encoding="utf-8")


def test_hits_and_applications_of_one_company_share_a_row(server):  # noqa: F811
    add_hits(server, ("Data Engineer", "Muster Industrie AG", "Winterthur"), ("Analyst", "Muster Industrie", "Winterthur"),
             ("Koch", "Probe Gastro GmbH", "Bern"))
    entry = server.kontext.register().neu(firma="Muster Industrie AG", stelle="Entwickler", status="Beworben")

    rows = companies_of(server)

    muster = rows["muster-industrie"]
    assert muster["name"] == "Muster Industrie AG" and muster["ort"] == "Winterthur"
    assert [h["stelle"] for h in muster["treffer"]] == ["Data Engineer", "Analyst"]
    assert muster["bewerbungen"] == [{"id": entry["id"], "stelle": "Entwickler", "status": "Beworben"}]
    assert muster["kununu"] is None and "probe-gastro" in rows


def test_a_hit_without_a_company_has_no_row(server):  # noqa: F811
    add_hits(server, ("Koch", "", "Bern"))
    assert "unbekannt" not in companies_of(server)


def test_known_kununu_values_come_with_the_row(server):  # noqa: F811
    add_hits(server, ("Data Engineer", "Muster Industrie AG", "Winterthur"))
    store(server, {"muster-industrie": {"zustand": "gefunden", "wert": 3.8, "bewertungen": 214, "empfehlung": 78,
                                        "geprueft_am": "2026-11-05", "seite": "ch",
                                        "link": "https://www.kununu.com/ch/muster-industrie",
                                        "lernende": {"wert": 4.2, "bewertungen": 12}}})

    kununu = companies_of(server)["muster-industrie"]["kununu"]

    assert kununu == {"zustand": "gefunden", "wert": 3.8, "bewertungen": 214, "empfehlung": 78, "geprueft_am": "2026-11-05",
                      "seite": "ch", "link": "https://www.kununu.com/ch/muster-industrie",
                      "lernende": {"wert": 4.2, "bewertungen": 12}}


def test_odd_values_in_the_file_are_left_out(server):  # noqa: F811
    add_hits(server, ("Data Engineer", "Muster Industrie AG", "Winterthur"), ("Koch", "Probe Gastro GmbH", "Bern"))
    store(server, {"muster-industrie": {"zustand": "gefunden", "wert": 9, "bewertungen": "viele", "empfehlung": 140,
                                        "link": "https://boese.example/ch/muster", "geprueft_am": "gestern"},
                   "probe-gastro": {"zustand": "erfunden"}})

    rows = companies_of(server)

    assert rows["muster-industrie"]["kununu"] == {"zustand": "gefunden"}
    assert rows["probe-gastro"]["kununu"] is None


def test_the_search_link_goes_to_kununu_ch_with_the_name(server):  # noqa: F811
    add_hits(server, ("Data Engineer", "Muster & Söhne AG", "Bern"))
    link = companies_of(server)["muster-sohne"]["suche"]
    assert link == "https://www.kununu.com/ch/search?q=Muster%20%26%20S%C3%B6hne%20AG"


@pytest.mark.parametrize("pasted, link, site", [
    ("https://www.kununu.com/ch/muster-industrie", "https://www.kununu.com/ch/muster-industrie", "ch"),
    ("kununu.com/ch/muster-industrie/kommentare?page=2#top", "https://www.kununu.com/ch/muster-industrie/kommentare", "ch"),
    ("https://www.kununu.com/de/muster-industrie1", "https://www.kununu.com/de/muster-industrie1", "de"),
    ("https://www.kununu.de/muster-industrie", "https://www.kununu.com/de/muster-industrie", "de"),
])
def test_a_pasted_kununu_link_is_assigned(server, pasted, link, site):  # noqa: F811
    add_hits(server, ("Data Engineer", "Muster Industrie AG", "Winterthur"))

    status, answer = post(server, "/api/firmen/zuordnen", {"link": pasted}, firma="muster-industrie")

    assert status == 200 and answer == {"zustand": "zugeordnet", "link": link, "seite": site}
    assert companies_of(server)["muster-industrie"]["kununu"] == answer


@pytest.mark.parametrize("pasted", ["https://www.kununu.com/at/muster", "https://www.kununu.com/ch/search?q=Muster",
                                    "https://kununu.com.boese.example/ch/muster", "https://www.example.ch/ch/muster",
                                    "javascript:alert(1)", "https://user@www.kununu.com/ch/muster", "", None, 42,
                                    "https://www.kununu.com/ch"])
def test_other_links_are_refused(server, pasted):  # noqa: F811
    add_hits(server, ("Data Engineer", "Muster Industrie AG", "Winterthur"))

    status, answer = post(server, "/api/firmen/zuordnen", {"link": pasted}, firma="muster-industrie")

    assert status == 400 and companies.BAD_LINK in json.dumps(answer, ensure_ascii=False)
    assert not (server.kontext.daten / companies.FILE).exists()


def test_an_unknown_company_is_404(server):  # noqa: F811
    status, _ = post(server, "/api/firmen/zuordnen", {"link": "https://www.kununu.com/ch/muster"}, firma="gibt-es-nicht")
    assert status == 404


def test_assigning_keeps_drafts_and_the_other_companies(server):  # noqa: F811
    add_hits(server, ("Data Engineer", "Muster Industrie AG", "Winterthur"), ("Koch", "Probe Gastro GmbH", "Bern"))
    store(server, {"probe-gastro": {"zustand": "nicht_gefunden", "geprueft_am": "2026-11-01"}})
    before = len(list((server.kontext.daten / ".entwuerfe").rglob("*"))) if (server.kontext.daten / ".entwuerfe").exists() else 0

    post(server, "/api/firmen/zuordnen", {"link": "https://www.kununu.com/ch/muster-industrie"}, firma="muster-industrie")

    rows = companies_of(server)
    assert rows["probe-gastro"]["kununu"] == {"zustand": "nicht_gefunden", "geprueft_am": "2026-11-01"}
    assert rows["muster-industrie"]["kununu"]["zustand"] == "zugeordnet"
    assert len(list((server.kontext.daten / ".entwuerfe").rglob("*"))) > before


CANDIDATES = [{"name": "Beispiel Holding AG", "ort": "Zürich", "branche": "Finanzen", "bewertungen": 96,
               "link": "https://www.kununu.com/ch/beispiel-holding"},
              {"name": "Beispiel Holding GmbH", "ort": "Stuttgart", "bewertungen": 31,
               "link": "https://www.kununu.com/de/beispiel-holding-gmbh"}]


def several(s):
    add_hits(s, ("Leiter Beschaffung", "Beispiel Holding AG", "Zürich"))
    store(s, {"beispiel-holding": {"zustand": "mehrere", "geprueft_am": "2026-11-09", "kandidaten": CANDIDATES}})


def test_several_companies_list_their_candidates(server):  # noqa: F811
    several(server)
    assert companies_of(server)["beispiel-holding"]["kununu"]["kandidaten"] == CANDIDATES


def test_choosing_a_candidate_assigns_its_page(server):  # noqa: F811
    several(server)

    status, answer = post(server, "/api/firmen/waehlen", {"link": CANDIDATES[1]["link"]}, firma="beispiel-holding")

    assert status == 200 and answer == {"zustand": "zugeordnet", "link": CANDIDATES[1]["link"], "seite": "de"}


def test_only_a_listed_candidate_can_be_chosen(server):  # noqa: F811
    several(server)
    status, _ = post(server, "/api/firmen/waehlen", {"link": "https://www.kununu.com/ch/andere-firma"}, firma="beispiel-holding")
    assert status == 400


def test_none_of_them_means_not_found(server):  # noqa: F811
    several(server)

    status, answer = post(server, "/api/firmen/waehlen", {"keine": True}, firma="beispiel-holding")

    assert status == 200 and answer["zustand"] == "nicht_gefunden" and answer["geprueft_am"]
    assert "kandidaten" not in companies_of(server)["beispiel-holding"]["kununu"]



def test_the_page_is_reached_from_the_search(server):  # noqa: F811
    # The sidebar (G54) has no place for Firmen; until it becomes a tab of Stellen (#262) the search links to it.
    from test_app import anfrage, session_header
    status, _, page, _ = anfrage(server, "GET", "/firmen", headers=session_header(server))
    assert status == 200 and "/firmen.js" in page.decode("utf-8")
    search = anfrage(server, "GET", "/treffer", headers=session_header(server))[2].decode("utf-8")
    assert 'href="/firmen" data-text="suche.firmen">Firmen ansehen</a>' in search
