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


LENA_HIT = {"portal": "LENA", "portal_id": "3709234", "stelle": "Fachmann/-frau Gesundheit EFZ", "firma": "Spital Muster AG",
            "ort": "Bern (BE)", "link": "https://www.berufsberatung.ch/de/lehrstellen/3709234", "art": "Lehrstelle",
            "beruf": "Fachfrau Gesundheit EFZ", "lehrbeginn": "2027", "text": "Du lernst …"}
YOUSTY_HIT = {"portal": "yousty", "portal_id": "8690204", "stelle": "Fachmann/-frau Gesundheit (FaGe) EFZ",
              "firma": "Spital Muster", "ort": "Bern", "art": "Lehrstelle", "beruf": "Fachfrau Gesundheit EFZ",
              "link": "https://www.yousty.ch/de-CH/lehrstellen/profile/8690204-fage", "lehrbeginn": "2027, 2028",
              "text": "Deine Lehre …"}


def test_apprenticeship_keeps_kind_profession_and_start(store):
    store.add([LENA_HIT], [], TODAY)
    stored = store.all()[0]
    assert (stored["art"], stored["beruf"], stored["lehrbeginn"]) == ("Lehrstelle", "Fachfrau Gesundheit EFZ", "2027")
    assert "Lehrbeginn: 2027" in store.ad_text(stored["id"])


def test_apprenticeship_on_both_portals_is_merged_by_profession_company_and_place(store):
    store.add([LENA_HIT], [], TODAY)
    answer = store.add([YOUSTY_HIT], [], TODAY)
    assert (answer["neu"], answer["zusammengefuehrt"]) == (0, 1)
    assert store.all()[0]["weitere"] == [{"portal": "yousty", "link": YOUSTY_HIT["link"]}]


def test_screening_merges_an_apprenticeship_twin_without_fetching_its_text(store):
    store.add([LENA_HIT], [], TODAY)
    answer = store.screen([YOUSTY_HIT], (), 45, [])
    assert answer["holen"] == []
    assert answer["zusammengefuehrt"] == 1


def test_other_profession_in_the_same_company_stays_a_hit_of_its_own(store):
    store.add([LENA_HIT], [], TODAY)
    other = {**YOUSTY_HIT, "beruf": "Assistentin Gesundheit und Soziales EBA"}
    assert store.add([other], [], TODAY)["neu"] == 1


def test_link_of_an_apprenticeship_must_belong_to_its_portal(store):
    wrong = {**LENA_HIT, "link": "https://www.yousty.ch/de-CH/lehrstellen/profile/1"}
    assert store.add([wrong], [], TODAY)["neu"] == 0


def test_details_name_a_trial_and_leave_others_as_they_are():
    assert hits.ad_with_details({"stelle": "X", "art": "Schnupperlehre"}, "Text").startswith("Art: Schnupperlehre\n")
    assert "Art:" not in hits.ad_with_details({"stelle": "X", "art": "Lehrstelle"}, "Text")


@pytest.mark.parametrize("raw, clean", [
    ("<em>UX</em>/<em>UI</em> <em>Designer</em>", "UX/UI Designer"),
    ("Graphic &amp; Motion Designer:in 100 %", "Graphic & Motion Designer:in 100 %"),
    ("&lt;b&gt;Koch&lt;/b&gt; EFZ", "Koch EFZ"),
    ("Entwickler C++ (m/w) 80% < 100%", "Entwickler C++ (m/w) 80% < 100%"),
])
def test_titles_and_companies_come_without_markup(raw, clean):
    found = hits.validate(hit(stelle=raw, firma=raw))
    assert found["stelle"] == clean and found["firma"] == clean


def test_titles_stored_with_markup_read_clean(store):
    today = datetime.date(2026, 11, 3)
    store.add([hit()], [], today)
    stored = store.all()[0]
    store._write([{**stored, "stelle": "<em>Data</em> &amp; Engineer", "firma": "A &amp; B"}])
    assert (store.all()[0]["stelle"], store.all()[0]["firma"]) == ("Data & Engineer", "A & B")


@pytest.mark.parametrize("place, near", [
    ("Thun", True), ("3600 Thun", True), ("Thun BE", True), ("3604 Hilterfingen", True),
    ("Thunstetten", False), ("8000 Zürich", False), ("", False),
])
def test_near_means_the_home_or_the_same_postal_area(place, near):
    assert hits.is_near(place, ("Thun",), ("3600",)) is near


def test_screen_names_the_hits_near_the_home(store):
    listing = [hit(portal_id="n-1", ort="Thun", link="https://www.jobs.ch/de/stellenangebote/detail/n-1/"),
               hit(portal_id="f-1", ort="Zürich", stelle="Koch", firma="Andere AG",
                   link="https://www.jobs.ch/de/stellenangebote/detail/f-1/")]
    result = store.screen(listing, (), 45, [], near=lambda place: place == "Thun")
    assert result["nah"] == ["jobs.ch:n-1"] and len(result["holen"]) == 2
    assert store.screen(listing, (), 45, [])["nah"] == []
