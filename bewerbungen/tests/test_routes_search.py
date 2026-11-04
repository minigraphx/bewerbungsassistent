"""Routes of the job search (MIN-339): the extension's flow and the page „Treffer“, with a simulated AI."""
import concurrent.futures
import json
import shutil

import pytest
import yaml

import app
import routes_ai
import routes_search
from ai.connection import ACCESS_VARIABLE, KEY_VARIABLE, URL_VARIABLE
from test_ai_tasks import RATING, VORLAGEN, FakeClient
from test_app import get, post, server  # noqa: F401  (server is a fixture)

HIT = {"portal": "jobs.ch", "portal_id": "abc-1", "stelle": "Python Developer", "firma": "Muster GmbH", "ort": "Bern",
       "pensum": "80–100 %", "link": "https://www.jobs.ch/de/stellenangebote/detail/abc-1/", "alter_tage": 2,
       "text": "Python, SQL, Deutsch fliessend."}


@pytest.fixture
def search(server, monkeypatch):  # noqa: F811
    daten = server.kontext.daten
    shutil.copy(VORLAGEN / "suchprofil.md", daten / "suchprofil.md")
    shutil.copytree(VORLAGEN / "anschreiben", daten / "anschreiben", dirs_exist_ok=True)
    for name in (URL_VARIABLE, ACCESS_VARIABLE):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(KEY_VARIABLE, "sk-test")
    return server


def listing(s):
    return json.loads(get(s, "/api/suche/liste")[2])


def test_plan_comes_from_the_profile(search):
    status, _, content = get(search, "/api/suche/plan")
    assert status == 200
    assert json.loads(content)["plan"]["kantone"] == ["BE", "SO"]


def test_plan_without_profile_is_a_clear_error(server):  # noqa: F811
    status, _, content = get(server, "/api/suche/plan")
    assert status == 400
    assert "Einstieg" in json.loads(content)["fehler"]


def test_extension_flow_screen_send_finish(search):
    excluded = {**HIT, "portal_id": "p-2", "stelle": "Praktikum Python", "link": HIT["link"] + "p2"}
    status, screened = post(search, "/api/suche/sichten", {"treffer": [HIT, excluded]})
    assert status == 200
    assert screened["holen"] == ["jobs.ch:abc-1"]
    assert screened["gefiltert"] == [{"stelle": "Praktikum Python", "grund": "Titel: Praktikum"}]
    status, received = post(search, "/api/suche/treffer", {"treffer": [HIT]})
    assert (status, received["neu"]) == (200, 1)
    status, run = post(search, "/api/suche/abschluss", {"portale": {"jobs.ch": {"treffer": 2, "neu": 1, "problem": ""}}})
    assert status == 200
    page = listing(search)
    assert page["treffer"][0]["stelle"] == "Python Developer"
    assert page["letzte_suche"]["portale"]["jobs.ch"]["neu"] == 1
    assert "suche/" in app.GITIGNORE  # hits stay out of the data folder's history


@pytest.mark.parametrize("body", [{}, {"treffer": "x"}, {"portale": {"linkedin": {}}}])
def test_bad_bodies_are_refused(search, body):
    path = "/api/suche/abschluss" if "portale" in body else "/api/suche/treffer"
    assert post(search, path, body)[0] == 400


def test_rate_stores_the_rating(search, monkeypatch):
    client = FakeClient(reply=RATING)
    monkeypatch.setattr(routes_ai, "new_client", lambda: client)
    post(search, "/api/suche/treffer", {"treffer": [HIT]})
    hit_id = listing(search)["treffer"][0]["id"]
    status, rated = post(search, "/api/suche/bewerten", {}, id=hit_id)
    assert status == 200
    assert rated["bewertung"]["note"] == 5
    assert rated["bewertung"]["haken"] == ["Pensum"]
    sent = json.dumps(client.messages.calls[0], ensure_ascii=False)
    assert "Python, SQL, Deutsch fliessend." in sent


def test_rate_without_text_explains(search):
    post(search, "/api/suche/treffer", {"treffer": [{**HIT, "text": ""}]})
    hit_id = listing(search)["treffer"][0]["id"]
    status, answer = post(search, "/api/suche/bewerten", {}, id=hit_id)
    assert status == 400
    assert "Text des Inserats" in answer["fehler"]


def test_take_over_writes_register_and_ad_with_drafts(search):
    post(search, "/api/suche/treffer", {"treffer": [HIT]})
    hit_id = listing(search)["treffer"][0]["id"]
    status, taken = post(search, "/api/suche/uebernehmen", {}, id=hit_id)
    assert status == 200
    assert taken["zustand"] == "uebernommen"
    daten = search.kontext.daten
    entry = next(b for b in yaml.safe_load((daten / "bewerbungen.yaml").read_text(encoding="utf-8"))
                 if b["id"] == taken["bewerbung_id"])
    assert (entry["firma"], entry["status"], entry["portal"], entry["firma_schluessel"]) == (
        "Muster GmbH", "Gemerkt", "jobs.ch", "muster")
    ad = (daten / "bewerbungen" / entry["id"] / "stelle.md").read_text(encoding="utf-8")
    assert ad.startswith("Stelle: Python Developer") and ad.endswith("Deutsch fliessend.")
    assert post(search, "/api/suche/uebernehmen", {}, id=hit_id)[0] == 400


def test_take_over_twice_at_once_gives_one_application(search):
    post(search, "/api/suche/treffer", {"treffer": [HIT]})
    hit_id = listing(search)["treffer"][0]["id"]
    with concurrent.futures.ThreadPoolExecutor(2) as pool:
        statuses = sorted(pool.map(lambda _: post(search, "/api/suche/uebernehmen", {}, id=hit_id)[0], range(2)))
    assert statuses == [200, 400]
    register = yaml.safe_load((search.kontext.daten / "bewerbungen.yaml").read_text(encoding="utf-8"))
    assert sum(b["firma"] == "Muster GmbH" for b in register) == 1


def test_failed_ad_file_does_not_lead_to_a_second_application(search, monkeypatch):
    post(search, "/api/suche/treffer", {"treffer": [HIT]})
    hit_id = listing(search)["treffer"][0]["id"]

    def full_disk(*args):
        raise OSError("Datenträger voll")
    monkeypatch.setattr(routes_search, "schreibe_atomar", full_disk)
    assert post(search, "/api/suche/uebernehmen", {}, id=hit_id)[0] >= 400
    [hit] = listing(search)["treffer"]
    assert hit["zustand"] == "uebernommen" and hit["bewerbung_id"]


def test_discard_and_restore(search):
    post(search, "/api/suche/treffer", {"treffer": [HIT]})
    hit_id = listing(search)["treffer"][0]["id"]
    assert post(search, "/api/suche/verwerfen", {}, id=hit_id)[1]["zustand"] == "verworfen"
    assert post(search, "/api/suche/verwerfen", {"zurueck": True}, id=hit_id)[1]["zustand"] == "neu"


def test_text_of_unknown_hit_is_404(search):
    assert get(search, "/api/suche/text", id="gibt-es-nicht")[0] == 404


def test_overview_names_kind_and_portals_of_the_profile(search):
    first = listing(search)
    assert (first["art"], first["portale"]) == ("stelle", ["job-room", "jobs.ch", "jobscout24", "ictjobs"])
    shutil.copy(VORLAGEN / "suchprofil-lehrstelle.md", search.kontext.daten / "suchprofil.md")
    second = listing(search)
    assert (second["art"], second["portale"]) == ("lehrstelle", ["LENA", "yousty"])


def test_summary_of_an_apprenticeship_search_is_accepted(search):
    shutil.copy(VORLAGEN / "suchprofil-lehrstelle.md", search.kontext.daten / "suchprofil.md")
    status, _ = post(search, "/api/suche/abschluss", {"portale": {"LENA": {"treffer": 3, "neu": 2}, "yousty": {"treffer": 1, "neu": 0}}})
    assert status == 200
    assert set(listing(search)["letzte_suche"]["portale"]) == {"LENA", "yousty"}


def test_unfinished_apprenticeship_profile_keeps_its_kind_next_to_the_error(search):
    (search.kontext.daten / "suchprofil.md").write_text("# Suchprofil Lehrstelle\n\n## Lehrbeginn\n- August 2027\n", encoding="utf-8")
    overview = listing(search)
    assert (overview["art"], overview["portale"]) == ("lehrstelle", ["LENA", "yousty"])
    assert "Berufe" in overview["hinweise"][0]
