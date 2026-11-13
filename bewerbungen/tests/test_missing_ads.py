"""Missing ad texts at the start of the app (G37, G38, #275): what the extension may load, what it hands back,
and what the app names with reason and way. All data is invented."""
import json
import shutil

import pytest

import missing_ads
import routes_ai
import unterlagen
from hits import ad_with_details
from test_ai_tasks import VORLAGEN
from test_app import get, post, server  # noqa: F401  (server is a fixture)

HOLEN, TEXTE = "/api/inserate/holen", "/api/inserate/texte"
HIT = {"portal": "jobs.ch", "portal_id": "abc-1", "stelle": "Python Developer", "firma": "Muster GmbH", "ort": "Bern",
       "link": "https://www.jobs.ch/de/stellenangebote/detail/abc-1/", "text": ""}
JOBROOM = "https://www.job-room.ch/job-search/0f1e2d3c-aaaa-bbbb-cccc-123456789abc"
LINKEDIN = "https://www.linkedin.com/jobs/view/123456"


@pytest.fixture
def k(server, monkeypatch):  # noqa: F811
    shutil.copy(VORLAGEN / "suchprofil.md", server.kontext.daten / "suchprofil.md")

    def no_ai(*args, **kwargs):
        raise AssertionError("nothing about missing ad texts goes to the AI")

    monkeypatch.setattr(routes_ai, "new_client", no_ai)
    return server


def saved(s, firma, link, status="Gemerkt", ad=None):
    entry = s.kontext.register().neu(firma=firma, stelle="Data Analyst", link=link, status=status)
    if ad is not None:
        folder = unterlagen.bewerbungsordner(s.kontext.daten, entry["id"])
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "stelle.md").write_text(ad, encoding="utf-8")
    return entry


def ad_of(s, entry_id):
    path = unterlagen.bewerbungsordner(s.kontext.daten, entry_id) / "stelle.md"
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def details(s, entry_id):
    return json.loads(get(s, "/api/bewerbung", id=entry_id)[2])


def test_only_the_head_of_an_ad_is_no_ad_text():
    head = ad_with_details({"stelle": "Data Analyst", "firma": "Muster AG", "link": JOBROOM}, "")
    assert missing_ads.has_ad(head) is False
    assert missing_ads.has_ad("") is False
    assert missing_ads.has_ad(ad_with_details({"stelle": "Data Analyst"}, "Wir suchen Verstärkung.")) is True
    assert missing_ads.has_ad("Stelle: Data Analyst\nWir suchen Verstärkung.") is True


def test_the_app_hands_out_jobs_without_text_on_portals_that_allow_loading(k):
    assert post(k, "/api/suche/treffer", {"treffer": [HIT, {**HIT, "portal_id": "abc-2", "link": HIT["link"] + "2", "text": "Da."}]})[0] == 200
    from_portal = saved(k, "Muster AG", JOBROOM)
    head_only = saved(k, "Beispiel GmbH", "https://www.jobscout24.ch/de/job/77/", status="Bewerben",
                      ad=ad_with_details({"stelle": "Data Analyst", "firma": "Beispiel GmbH"}, ""))
    saved(k, "Fantasie AG", LINKEDIN)
    saved(k, "Gesendet AG", "https://www.ictjobs.ch/job/9", status="Beworben")
    saved(k, "Mit Text AG", "https://www.ictjobs.ch/job/10", ad="Ein ganzes Inserat.")

    status, answer = post(k, HOLEN, {})

    assert status == 200
    handed = {(job["art"], job["portal"], job["portal_id"]) for job in answer["laden"]}
    assert handed == {("treffer", "jobs.ch", "abc-1"), ("bewerbung", "job-room", "0f1e2d3c-aaaa-bbbb-cccc-123456789abc"),
                      ("bewerbung", "jobscout24", "")}
    assert {job["id"] for job in answer["laden"] if job["art"] == "bewerbung"} == {from_portal["id"], head_only["id"]}
    assert post(k, HOLEN, {})[1]["laden"] == [], "once per start of the app"


def test_fetched_texts_land_in_the_hit_and_the_saved_job(k):
    post(k, "/api/suche/treffer", {"treffer": [HIT]})
    entry = saved(k, "Muster AG", JOBROOM)
    handed = post(k, HOLEN, {})[1]["laden"]
    hit_id = next(job["id"] for job in handed if job["art"] == "treffer")

    status, answer = post(k, TEXTE, {"texte": [{"art": "treffer", "id": hit_id, "text": "Python und SQL."},
                                               {"art": "bewerbung", "id": entry["id"], "text": "Daten auswerten."}]})

    assert (status, answer["gespeichert"]) == (200, 2)
    assert json.loads(get(k, "/api/suche/text", id=hit_id)[2])["text"] == "Python und SQL."
    listed = json.loads(get(k, "/api/suche/liste")[2])["treffer"][0]
    assert listed["ohne_text"] is False and listed.get("text_fehlt") is None
    ad = ad_of(k, entry["id"])
    assert ad.startswith("Stelle: Data Analyst\nFirma: Muster AG") and ad.endswith("Daten auswerten.")
    assert details(k, entry["id"])["text_fehlt"] is None, "the pass over saved jobs shows the fetched text (G38)"


def test_only_handed_out_jobs_take_a_text_and_a_text_never_replaces_one(k):
    entry = saved(k, "Muster AG", JOBROOM)
    other = saved(k, "Fantasie AG", LINKEDIN)
    post(k, HOLEN, {})

    answer = post(k, TEXTE, {"texte": [{"art": "bewerbung", "id": other["id"], "text": "Untergeschoben."}]})[1]
    assert answer["gespeichert"] == 0 and ad_of(k, other["id"]) == ""

    (unterlagen.bewerbungsordner(k.kontext.daten, entry["id"])).mkdir(parents=True, exist_ok=True)
    (unterlagen.bewerbungsordner(k.kontext.daten, entry["id"]) / "stelle.md").write_text("Von Hand eingefügt.", encoding="utf-8")
    assert post(k, TEXTE, {"texte": [{"art": "bewerbung", "id": entry["id"], "text": "Neu geladen."}]})[1]["gespeichert"] == 0
    assert ad_of(k, entry["id"]) == "Von Hand eingefügt."


@pytest.mark.parametrize("body", [{}, {"texte": "x"}, {"texte": [{"art": "rav", "id": "a", "text": ""}]},
                                  {"texte": [{"art": "treffer", "id": "a", "text": 3}]}])
def test_bad_bodies_are_refused(k, body):
    assert post(k, TEXTE, body)[0] == 400


def test_a_portal_that_forbids_automatic_loading_is_named_with_reason_and_way(k):
    entry = saved(k, "Fantasie AG", LINKEDIN)
    without_link = saved(k, "Ohne Link AG", "")

    named = details(k, entry["id"])["text_fehlt"]
    assert "linkedin.com" in named["grund"] and "automatisches Laden" in named["grund"]
    assert "Erweiterung speichern" in named["weg"] and "Stellentext" in named["weg"]
    assert "Link" in details(k, without_link["id"])["text_fehlt"]["grund"]


def test_what_did_not_load_is_named_with_the_reason(k):
    post(k, "/api/suche/treffer", {"treffer": [HIT]})
    entry = saved(k, "Muster AG", JOBROOM)
    pending = details(k, entry["id"])["text_fehlt"]
    assert "nächsten Start" in pending["grund"]
    handed = post(k, HOLEN, {})[1]["laden"]
    hit_id = next(job["id"] for job in handed if job["art"] == "treffer")

    post(k, TEXTE, {"texte": [{"art": "bewerbung", "id": entry["id"], "text": "", "fehler": "Antwort 429"},
                              {"art": "treffer", "id": hit_id, "text": ""}]})

    assert "Antwort 429" in details(k, entry["id"])["text_fehlt"]["grund"]
    listed = json.loads(get(k, "/api/suche/liste")[2])["treffer"][0]
    assert "keinen lesbaren Text" in listed["text_fehlt"]["grund"]


def test_saving_the_page_fills_a_saved_job_that_has_only_the_head(k):
    entry = saved(k, "Muster AG", JOBROOM, ad=ad_with_details({"stelle": "Data Analyst", "firma": "Muster AG"}, ""))

    status, _ = post(k, "/api/seite/speichern", {"stelle": "Data Analyst", "firma": "Muster AG", "link": JOBROOM,
                                                  "text": "Das ganze Inserat."})

    assert status == 200
    assert ad_of(k, entry["id"]).endswith("Das ganze Inserat.")
