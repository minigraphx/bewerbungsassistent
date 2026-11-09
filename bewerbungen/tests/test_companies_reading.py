"""What the extension read at kununu, and a value the person enters by hand (G35, #189). Only invented companies."""
import datetime

import pytest
import yaml

import companies
from test_app import post, server  # noqa: F401  (server is a fixture)
from test_companies import add_hits, companies_of, store

LINK = "https://www.kununu.com/ch/muster-industrie"


@pytest.fixture
def muster(server):  # noqa: F811
    add_hits(server, ("Data Engineer", "Muster Industrie AG", "Winterthur"))
    return server


def read(s, reading, firma="muster-industrie"):
    """As the extension sends it: through the host a POST carries no query, so the company is in the body."""
    return post(s, "/api/firmen/kununu", {"firma": firma, **reading} if isinstance(reading, dict) else reading)


def stored(s) -> dict:
    return yaml.safe_load((s.kontext.daten / companies.FILE).read_text(encoding="utf-8"))


def today() -> str:
    return datetime.date.today().isoformat()


def test_a_read_rating_is_stored_with_site_link_and_today(muster):
    status, answer = read(muster, {"zustand": "gefunden", "wert": 3.8, "bewertungen": 214,
                                   "link": LINK + "?utm_source=x", "seite": "ch"})

    assert status == 200
    assert answer == {"zustand": "gefunden", "wert": 3.8, "bewertungen": 214, "link": LINK, "seite": "ch", "geprueft_am": today()}
    assert companies_of(muster)["muster-industrie"]["kununu"] == answer


def test_the_site_follows_the_link_not_what_the_extension_says(muster):
    status, answer = read(muster, {"zustand": "gefunden", "wert": 4.1, "bewertungen": 12,
                                   "link": "https://www.kununu.com/de/muster-industrie", "seite": "ch"})
    assert status == 200 and answer["seite"] == "de"


def test_a_page_without_reviews_and_a_company_not_found(muster):
    status, answer = read(muster, {"zustand": "keine", "link": LINK})
    assert status == 200 and answer == {"zustand": "keine", "link": LINK, "seite": "ch", "geprueft_am": today()}

    status, answer = read(muster, {"zustand": "nicht_gefunden"})
    assert status == 200 and answer == {"zustand": "nicht_gefunden", "geprueft_am": today()}


def test_several_companies_hand_their_candidates_to_the_person(muster):
    candidates = [{"name": "Muster Industrie AG", "ort": "Winterthur", "bewertungen": 214, "link": LINK},
                  {"name": "Muster Industrie Holding", "link": "https://www.kununu.com/ch/muster-holding"},
                  {"name": "Ohne Link"}]

    status, answer = read(muster, {"zustand": "mehrere", "kandidaten": candidates})

    assert status == 200 and answer["zustand"] == "mehrere"
    assert [c["link"] for c in answer["kandidaten"]] == [LINK, "https://www.kununu.com/ch/muster-holding"]
    assert "geprueft_am" in answer


@pytest.mark.parametrize("reading", [
    {"zustand": "gefunden", "wert": 3.8, "bewertungen": 214, "link": "https://www.example.ch/muster"},
    {"zustand": "gefunden", "wert": 3.8, "bewertungen": 214},
    {"zustand": "gefunden", "wert": 7, "bewertungen": 214, "link": LINK},
    {"zustand": "gefunden", "wert": 3.8, "bewertungen": -1, "link": LINK},
    {"zustand": "gefunden", "wert": "3.8", "bewertungen": 214, "link": LINK},
    {"zustand": "zugeordnet", "link": LINK},
    {"zustand": "fehler"},
    {"zustand": "mehrere", "kandidaten": []},
    "kein Objekt",
])
def test_a_reading_that_does_not_fit_is_refused_and_nothing_is_written(muster, reading):
    status, answer = read(muster, reading)

    assert status == 400
    assert not (muster.kontext.daten / companies.FILE).exists()


def test_a_reading_for_an_unknown_company_is_404(muster):
    status, _ = read(muster, {"zustand": "nicht_gefunden"}, "probe-gastro")
    assert status == 404


def test_a_reading_keeps_drafts_and_the_other_companies(muster):
    add_hits(muster, ("Koch", "Probe Gastro GmbH", "Bern"))
    store(muster, {"probe-gastro": {"zustand": "nicht_gefunden", "geprueft_am": "2026-11-01"}})

    read(muster, {"zustand": "gefunden", "wert": 3.8, "bewertungen": 214, "link": LINK})

    assert set(stored(muster)) == {"probe-gastro", "muster-industrie"}
    assert list((muster.kontext.daten / ".entwuerfe").rglob("*"))


def test_the_person_enters_a_value_by_hand_and_the_known_page_stays(muster):
    store(muster, {"muster-industrie": {"zustand": "zugeordnet", "link": LINK, "seite": "ch"}})

    status, answer = post(muster, "/api/firmen/von-hand", {"wert": 3.8, "bewertungen": 214}, firma="muster-industrie")

    assert status == 200
    assert answer == {"zustand": "gefunden", "wert": 3.8, "bewertungen": 214, "link": LINK, "seite": "ch",
                      "geprueft_am": today(), "von_hand": True}
    assert companies_of(muster)["muster-industrie"]["kununu"]["von_hand"] is True


@pytest.mark.parametrize("values", [{"wert": 0.5, "bewertungen": 3}, {"wert": 5.5, "bewertungen": 3}, {"wert": 3.8},
                                    {"wert": 3.8, "bewertungen": 2.5}, {"wert": True, "bewertungen": 3}, {"bewertungen": 3}])
def test_a_value_by_hand_must_be_a_rating_and_a_count(muster, values):
    status, answer = post(muster, "/api/firmen/von-hand", values, firma="muster-industrie")
    assert status == 400 and answer["fehler"]
