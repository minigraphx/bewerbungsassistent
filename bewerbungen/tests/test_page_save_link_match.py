"""A saved job is found by its link, whatever its title says (#197); only invented companies."""
import pytest

from test_app import post, server  # noqa: F401  (server is a fixture)
from test_routes_page import rated  # noqa: F401  (rated is a fixture)
from test_routes_search import listing, search  # noqa: F401  (search is a fixture)

LINK = "https://www.jobscout24.ch/de/job/7654321/"
TEXT = "Wir suchen eine Person für Modelle und Datenpipelines. " * 6
PAGE_AD = {"stelle": "AI Engineer (80-100%, f/m/d)", "firma": "Beispiel Analytik AG", "ort": "Bern", "link": LINK, "text": TEXT}
HIT = {"portal": "jobscout24", "portal_id": "7654321", "stelle": "AI Engineer (80-100%, f/m/d)", "firma": "Beispiel Analytik AG",
       "ort": "Bern", "link": LINK, "alter_tage": 1, "text": TEXT}


def saved_job(s, link=LINK, stelle="AI Engineer", status="Gemerkt"):
    register = s.kontext.register()
    return register.neu(firma="Beispiel Analytik AG", stelle=stelle, firma_schluessel="beispiel-analytik", portal="jobscout24",
                        link=link, status=status)


def applications(s):
    return s.kontext.register().alle()


def ad_file(s, entry):
    return s.kontext.daten / "bewerbungen" / entry["id"] / "stelle.md"


def test_saving_the_page_of_a_saved_job_fills_in_its_ad(rated):  # noqa: F811
    s, _ = rated
    entry = saved_job(s)
    count = len(applications(s))

    status, answer = post(s, "/api/seite/speichern", PAGE_AD)

    assert status == 200 and answer["neu"] is False and answer["bewerbung"]["id"] == entry["id"]
    assert len(applications(s)) == count
    assert "Datenpipelines" in ad_file(s, entry).read_text(encoding="utf-8")


@pytest.mark.parametrize("link", [LINK.rstrip("/"), LINK + "?utm_source=newsletter", "http://jobscout24.ch/de/job/7654321"])
def test_the_link_matches_without_slash_tracking_or_scheme(rated, link):  # noqa: F811
    s, _ = rated
    entry = saved_job(s)

    answer = post(s, "/api/seite/speichern", {**PAGE_AD, "link": link})[1]

    assert answer["neu"] is False and answer["bewerbung"]["id"] == entry["id"]


def test_the_check_names_the_saved_job_found_by_its_link(rated):  # noqa: F811
    s, _ = rated
    entry = saved_job(s)

    answer = post(s, "/api/seite/pruefen", PAGE_AD)[1]

    assert answer["vorhanden"]["id"] == entry["id"]


def test_another_job_on_the_same_portal_is_new(rated):  # noqa: F811
    s, _ = rated
    saved_job(s)

    answer = post(s, "/api/seite/speichern", {**PAGE_AD, "stelle": "Buchhalterin", "link": "https://www.jobscout24.ch/de/job/1111111/"})[1]

    assert answer["neu"] is True


def test_a_page_save_names_the_portal_not_the_host(rated):  # noqa: F811
    s, _ = rated

    answer = post(s, "/api/seite/speichern", PAGE_AD)[1]

    assert next(b for b in applications(s) if b["id"] == answer["bewerbung"]["id"])["portal"] == "jobscout24"


def test_on_other_sites_a_close_title_is_the_same_job(rated):  # noqa: F811
    s, _ = rated
    link = "https://karriere.beispiel-analytik.ch/stellen/ai-engineer"
    entry = saved_job(s, link=link)

    answer = post(s, "/api/seite/speichern", {**PAGE_AD, "link": link})[1]

    assert answer["neu"] is False and answer["bewerbung"]["id"] == entry["id"]


def test_on_other_sites_another_title_under_the_same_address_stays_apart(rated):  # noqa: F811
    s, _ = rated
    link = "https://karriere.beispiel-analytik.ch/stellen"
    saved_job(s, link=link)

    answer = post(s, "/api/seite/speichern", {**PAGE_AD, "stelle": "Buchhalterin", "link": link})[1]

    assert answer["neu"] is True


def test_taking_over_a_hit_of_a_saved_job_adds_no_entry(search):  # noqa: F811
    entry = saved_job(search)
    count = len(applications(search))
    post(search, "/api/suche/treffer", {"treffer": [{**HIT, "link": LINK + "?utm_medium=mail"}]})
    hit_id = listing(search)["treffer"][0]["id"]

    status, taken = post(search, "/api/suche/uebernehmen", {}, id=hit_id)

    assert status == 200 and taken["zustand"] == "uebernommen" and taken["bewerbung_id"] == entry["id"]
    assert len(applications(search)) == count
    assert "Datenpipelines" in ad_file(search, entry).read_text(encoding="utf-8")


def test_taking_over_keeps_an_ad_text_that_is_there(search):  # noqa: F811
    entry = saved_job(search)
    path = ad_file(search, entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("Eigene Fassung", encoding="utf-8")
    post(search, "/api/suche/treffer", {"treffer": [{**HIT, "link": LINK + "?utm_medium=mail"}]})
    hit_id = listing(search)["treffer"][0]["id"]

    post(search, "/api/suche/uebernehmen", {}, id=hit_id)

    assert path.read_text(encoding="utf-8") == "Eigene Fassung"


def test_taking_over_ignores_a_closed_entry_with_that_link(search):  # noqa: F811
    entry = saved_job(search, status="Absage")
    post(search, "/api/suche/treffer", {"treffer": [{**HIT, "link": LINK + "?utm_medium=mail"}]})
    hit_id = listing(search)["treffer"][0]["id"]

    taken = post(search, "/api/suche/uebernehmen", {}, id=hit_id)[1]

    assert taken["bewerbung_id"] != entry["id"]


def test_screening_knows_a_saved_job_under_a_slightly_other_link(search):  # noqa: F811
    saved_job(search)

    screened = post(search, "/api/suche/sichten", {"treffer": [{**HIT, "link": LINK.rstrip("/") + "?utm_source=alert"}]})[1]

    assert screened["holen"] == [] and screened["bekannt"] == 1


YOUSTY = "https://www.yousty.ch/de-CH/lehrstellen/beispiel-werk-ag/informatiker-efz"
APPRENTICESHIP_AD = {"stelle": "Informatiker/in EFZ", "firma": "Beispiel Werk AG", "ort": "Bern", "link": YOUSTY, "text": TEXT}
TRIAL_AD = {**APPRENTICESHIP_AD, "stelle": "Schnupperlehre Informatiker/in EFZ", "link": YOUSTY + "#schnupperlehre"}


def saved_on_yousty(s, ad, **fields):
    return s.kontext.register().neu(firma="Beispiel Werk AG", stelle=ad["stelle"], firma_schluessel="beispiel-werk",
                                     portal="yousty", link=ad["link"], status="Gemerkt", **fields)


def test_the_apprenticeship_page_does_not_land_in_the_saved_trial(rated):  # noqa: F811
    s, _ = rated
    trial = saved_on_yousty(s, TRIAL_AD, art="Schnupperlehre")

    status, answer = post(s, "/api/seite/speichern", APPRENTICESHIP_AD)

    assert status == 200 and answer["neu"] is True and answer["bewerbung"]["id"] != trial["id"]
    assert not ad_file(s, trial).exists()


def test_the_trial_page_does_not_land_in_the_saved_apprenticeship(rated):  # noqa: F811
    s, _ = rated
    apprenticeship = saved_on_yousty(s, APPRENTICESHIP_AD)

    status, answer = post(s, "/api/seite/speichern", TRIAL_AD)

    assert status == 200 and answer["neu"] is True and answer["bewerbung"]["id"] != apprenticeship["id"]
    assert not ad_file(s, apprenticeship).exists()


def test_the_trial_page_fills_in_the_saved_trial(rated):  # noqa: F811
    s, _ = rated
    trial = saved_on_yousty(s, TRIAL_AD, art="Schnupperlehre")

    status, answer = post(s, "/api/seite/speichern", {**TRIAL_AD, "stelle": "Informatiker/in EFZ"})

    assert status == 200 and answer["neu"] is False and answer["bewerbung"]["id"] == trial["id"]


JOBS_CH = "https://www.jobs.ch/de/stellenangebote/detail/?jobid="


@pytest.mark.parametrize("stelle", ["Senior AI Engineer", "AI Engineer (80-100%, f/m/d)", "AI Engineer"])
def test_on_a_portal_another_link_is_another_ad(rated, stelle):  # noqa: F811
    s, _ = rated
    entry = saved_job(s, link=JOBS_CH + "111")

    status, answer = post(s, "/api/seite/speichern", {**PAGE_AD, "stelle": stelle, "link": JOBS_CH + "222"})

    assert status == 200 and answer["neu"] is True and answer["bewerbung"]["id"] != entry["id"]
    assert not ad_file(s, entry).exists()


def test_on_a_portal_an_entry_without_a_link_is_found_by_title_and_company(rated):  # noqa: F811
    s, _ = rated
    entry = s.kontext.register().neu(firma="Beispiel Analytik AG", stelle="AI Engineer", firma_schluessel="beispiel-analytik",
                                     status="Gemerkt")

    status, answer = post(s, "/api/seite/speichern", {**PAGE_AD, "link": JOBS_CH + "222"})

    assert status == 200 and answer["neu"] is False and answer["bewerbung"]["id"] == entry["id"]
