"""Hits from the extension (MIN-339): screen, store, merge across portals, duplicate hints."""
import datetime

import pytest

import hits

TODAY = datetime.date(2026, 11, 3)
REGISTER = [
    {"id": "beispiel-ag-entwickler", "firma": "Beispiel AG", "firma_schluessel": "beispiel", "stelle": "Entwickler",
     "status": "Beworben", "link": "https://www.jobs.ch/de/stellenangebote/detail/alt/"},
]


def hit(**fields) -> dict:
    base = {"portal": "jobs.ch", "portal_id": "abc-1", "stelle": "Data Engineer", "firma": "Muster GmbH",
            "ort": "Bern", "pensum": "80–100 %", "link": "https://www.jobs.ch/de/stellenangebote/detail/abc-1/",
            "alter_tage": 3, "text": "Wir suchen eine Person mit Python."}
    return {**base, **fields}


@pytest.fixture
def store(tmp_path):
    return hits.Hits(tmp_path)


def test_new_hit_is_stored_with_text_and_state_neu(store):
    result = store.add([hit()], REGISTER, TODAY)
    assert result["neu"] == 1
    [stored] = store.all()
    assert stored["zustand"] == "neu"
    assert stored["gefunden_am"] == "2026-11-03"
    assert "text" not in stored
    assert store.text(stored["id"]) == "Wir suchen eine Person mit Python."


def test_same_hit_twice_is_not_stored_again(store):
    store.add([hit()], REGISTER, TODAY)
    assert store.add([hit()], REGISTER, TODAY)["neu"] == 0
    assert len(store.all()) == 1


def test_same_job_on_another_portal_is_merged(store):
    store.add([hit()], REGISTER, TODAY)
    other = hit(portal="job-room", portal_id="x-9", firma="Muster GmbH ", stelle="Data  Engineer",
                link="https://www.job-room.ch/job-search/x-9")
    result = store.add([other], REGISTER, TODAY)
    assert result == {"neu": 0, "zusammengefuehrt": 1, "abgelehnt": []}
    [stored] = store.all()
    assert stored["weitere"] == [{"portal": "job-room", "link": "https://www.job-room.ch/job-search/x-9"}]


def test_same_title_twice_on_one_portal_stays_two_hits(store):
    second = hit(portal_id="abc-2", ort="Basel", link="https://www.jobs.ch/de/stellenangebote/detail/abc-2/")
    assert store.add([hit(), second], REGISTER, TODAY)["neu"] == 2


@pytest.mark.parametrize("other", [
    {"ort": "8000 Zürich"},  # another place
    {"firma": ""},  # company unknown on both
])
def test_jobs_that_only_look_alike_are_not_merged(store, other):
    store.add([hit(**({"firma": ""} if "firma" in other else {}))], REGISTER, TODAY)
    twin = hit(portal="job-room", portal_id="x-9", link="https://www.job-room.ch/job-search/x-9", **other)
    assert store.add([twin], REGISTER, TODAY)["neu"] == 1


def test_place_with_postal_code_matches_the_bare_city(store):
    store.add([hit(ort="Bern")], REGISTER, TODAY)
    twin = hit(portal="job-room", portal_id="x-9", ort="3011 Bern", link="https://www.job-room.ch/job-search/x-9")
    assert store.add([twin], REGISTER, TODAY)["zusammengefuehrt"] == 1


def test_screen_adds_the_link_of_a_twin_without_fetching_it(store):
    store.add([hit()], REGISTER, TODAY)
    twin = hit(portal="job-room", portal_id="x-9", link="https://www.job-room.ch/job-search/x-9")
    result = store.screen([twin], (), 45, REGISTER)
    assert result["holen"] == [] and result["zusammengefuehrt"] == 1
    assert store.all()[0]["weitere"] == [{"portal": "job-room", "link": "https://www.job-room.ch/job-search/x-9"}]
    assert store.screen([twin], (), 45, REGISTER)["zusammengefuehrt"] == 0


def test_company_with_a_running_application_gets_a_hint(store):
    store.add([hit(firma="Beispiel AG", stelle="Data Engineer")], REGISTER, TODAY)
    [stored] = store.all()
    assert "Beispiel AG" in stored["hinweis"] and "Beworben" in stored["hinweis"]


def test_invalid_hits_are_rejected_with_a_reason(store):
    bad = [hit(portal="linkedin"), hit(stelle=""), hit(link="https://evil.example/x"), "kein Objekt"]
    result = store.add(bad, REGISTER, TODAY)
    assert result["neu"] == 0
    assert len(result["abgelehnt"]) == 4


def test_link_must_belong_to_the_portal(store):
    with pytest.raises(ValueError, match="Link"):
        hits.validate(hit(link="https://www.jobs.ch.evil.example/x"))


@pytest.mark.parametrize("link", [
    "https://evil.example\\@www.jobs.ch/x",
    "https://user@www.jobs.ch/x",
    "https://www.jobs.ch\\@evil.example/x",
    "https://www.jobs.ch/x y",
    "http://www.jobs.ch/x",
])
def test_links_that_a_browser_reads_differently_are_refused(link):
    with pytest.raises(ValueError, match="Link"):
        hits.validate(hit(link=link))


def test_long_text_is_cut(store):
    store.add([hit(text="x" * (hits.MAX_TEXT + 50))], REGISTER, TODAY)
    assert len(store.text(store.all()[0]["id"])) == hits.MAX_TEXT


def test_screen_sorts_listing_into_fetch_known_and_filtered(store):
    store.add([hit()], REGISTER, TODAY)
    listing = [
        hit(portal_id="abc-1"),  # stored already
        hit(portal_id="neu-2", stelle="Python Developer", link="https://www.jobs.ch/de/stellenangebote/detail/neu-2/"),
        hit(portal_id="alt", link="https://www.jobs.ch/de/stellenangebote/detail/alt/", stelle="X"),  # in register
        hit(portal_id="p-3", stelle="Praktikum Data", link="https://www.jobs.ch/de/stellenangebote/detail/p-3/"),
        hit(portal_id="o-4", stelle="Old", alter_tage=90, link="https://www.jobs.ch/de/stellenangebote/detail/o-4/"),
    ]
    result = store.screen(listing, ("Praktikum",), 45, REGISTER)
    assert result["holen"] == ["jobs.ch:neu-2"]
    assert result["bekannt"] == 2
    assert [f["grund"] for f in result["gefiltert"]] == ["Titel: Praktikum", "älter als 45 Tage"]


def test_title_filter_matches_whole_words_only(store):
    listing = [hit(portal_id="s-1", stelle="Salesforce Developer", link="https://www.jobs.ch/x/s-1")]
    assert store.screen(listing, ("Sales",), 45, [])["holen"] == ["jobs.ch:s-1"]


def test_update_and_state_changes(store):
    store.add([hit()], REGISTER, TODAY)
    hit_id = store.all()[0]["id"]
    store.update(hit_id, zustand="verworfen")
    assert store.get(hit_id)["zustand"] == "verworfen"
    with pytest.raises(ValueError):
        store.update(hit_id, zustand="unbekannt")
    with pytest.raises(KeyError):
        store.get("gibt-es-nicht")


def test_last_run_is_kept(store):
    store.save_run({"portale": {"jobs.ch": {"treffer": 4, "neu": 1, "problem": ""}}}, TODAY)
    assert store.last_run()["datum"] == "2026-11-03"
    assert store.last_run()["portale"]["jobs.ch"]["neu"] == 1


def test_ad_text_has_the_details_first(store):
    store.add([hit()], REGISTER, TODAY)
    text = store.ad_text(store.all()[0]["id"])
    assert text.startswith("Stelle: Data Engineer\nFirma: Muster GmbH")
    assert text.endswith("Wir suchen eine Person mit Python.")
