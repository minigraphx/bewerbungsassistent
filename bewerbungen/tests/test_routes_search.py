"""Routes of the job search (MIN-339): the extension's flow and the page „Suche“, with a simulated AI."""
import concurrent.futures
import json
import shutil

import pytest
import yaml

import app
import routes_ai
import routes_search
import search_plan
from ai.connection import ACCESS_VARIABLE, KEY_VARIABLE, URL_VARIABLE
from ai.errors import BUDGET_USED, AiError
from test_ai_tasks import VORLAGEN, FakeClient, PackageClient, rating_entry
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
    assert screened["nah"] == ["jobs.ch:abc-1"], "Bern is a place of the profile"
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
    client = PackageClient(lambda labels: [rating_entry(labels[0], hooks=["Pensum"])])
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


def test_the_person_chooses_the_portals_and_the_search_follows(search):
    offer = listing(search)["portale_wahl"]
    assert {item["name"] for item in offer} == set(search_plan.PORTALS)
    status, saved = post(search, "/api/suche/einstellungen", {"portale_aus": ["ictjobs", "jobscout24"]})
    assert status == 200 and saved["portale_aus"] == ["ictjobs", "jobscout24"]
    assert listing(search)["portale"] == ["job-room", "jobs.ch"]
    plan_now = json.loads(get(search, "/api/suche/plan")[2])["plan"]
    assert plan_now["portale"] == ["job-room", "jobs.ch"]
    assert post(search, "/api/suche/einstellungen", {"auto_bewerten": False})[0] == 200
    assert listing(search)["einstellungen"]["portale_aus"] == ["ictjobs", "jobscout24"], "other settings leave it alone"


def test_a_broken_choice_of_portals_in_the_file_does_not_break_the_plan(search):
    folder = search.kontext.daten / "suche"
    folder.mkdir(exist_ok=True)
    (folder / "einstellungen.yaml").write_text("portale_aus:\n- jobs.ch\n- {a: b}\n- 3\n", encoding="utf-8")
    status, _, content = get(search, "/api/suche/plan")
    assert status == 200 and "jobs.ch" not in json.loads(content)["plan"]["portale"]


def test_all_portals_off_is_refused_with_a_message(search):
    status, answer = post(search, "/api/suche/einstellungen", {"portale_aus": list(search_plan.PORTALS)})
    assert status == 400 and "Portal" in answer["fehler"]
    assert listing(search)["einstellungen"]["portale_aus"] is None


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


# Rating in packages (MIN-372)

def many_hits(search, count: int) -> list[str]:
    hits = [{**HIT, "portal_id": f"p-{i}", "firma": f"Firma {i}", "link": f"{HIT['link']}{i}", "text": f"Inserat Nummer {i}."}
            for i in range(count)]
    post(search, "/api/suche/treffer", {"treffer": hits})
    return [hit["id"] for hit in listing(search)["treffer"]]


def use_client(monkeypatch, client):
    monkeypatch.setattr(routes_ai, "new_client", lambda: client)
    return client


def test_package_stores_each_grade_at_its_hit(search, monkeypatch):
    def build(labels):
        return [rating_entry(label, 1 + index) for index, label in reversed(list(enumerate(labels)))]

    client = use_client(monkeypatch, PackageClient(build))
    ids = many_hits(search, 3)
    status, answer = post(search, "/api/suche/bewerten-paket", {"ids": ids})
    assert status == 200 and answer["offen"] == [] and answer["kosten_usd"] > 0
    prompt = client.messages.calls[0]["messages"][0]["content"]
    by_grade = sorted(listing(search)["treffer"], key=lambda hit: hit["bewertung"]["note"])
    numbers = [int(hit["firma"].split()[1]) for hit in by_grade]
    assert [prompt.index(f"Nummer {n}") for n in numbers] == sorted(prompt.index(f"Nummer {n}") for n in numbers)
    assert len(client.messages.calls) == 1
    shares = [hit["bewertung"]["kosten_usd"] for hit in by_grade]
    assert sum(shares) == pytest.approx(answer["kosten_usd"])


def test_package_keeps_what_it_got_when_labels_are_missing(search, monkeypatch):
    use_client(monkeypatch, PackageClient(lambda labels: [rating_entry(labels[0])]))
    ids = many_hits(search, 3)
    status, answer = post(search, "/api/suche/bewerten-paket", {"ids": ids})
    assert status == 200 and len(answer["bewertet"]) == 1 and len(answer["offen"]) == 2
    assert sum("bewertung" in hit for hit in listing(search)["treffer"]) == 1


def test_package_with_an_unusable_answer_tells_the_page_to_go_one_by_one(search, monkeypatch):
    use_client(monkeypatch, FakeClient(reply="kein json"))
    ids = many_hits(search, 2)
    status, answer = post(search, "/api/suche/bewerten-paket", {"ids": ids})
    assert status == 200 and answer["bewertet"] == [] and sorted(answer["offen"]) == sorted(ids) and answer["meldung"]


def test_package_stops_on_errors_of_access_or_budget(search, monkeypatch):
    def refuse():
        raise AiError(BUDGET_USED)

    monkeypatch.setattr(routes_ai, "new_client", refuse)
    ids = many_hits(search, 2)
    status, answer = post(search, "/api/suche/bewerten-paket", {"ids": ids})
    assert status == 400 and answer["fehler"] == BUDGET_USED


def test_package_leaves_out_hits_without_text(search, monkeypatch):
    client = use_client(monkeypatch, PackageClient(lambda labels: [rating_entry(label) for label in labels]))
    post(search, "/api/suche/treffer", {"treffer": [{**HIT, "text": ""}]})
    page = listing(search)["treffer"]
    assert page[0]["ohne_text"] is True
    status, answer = post(search, "/api/suche/bewerten-paket", {"ids": [page[0]["id"]]})
    assert status == 200 and answer["ohne_text"] == [page[0]["id"]] and client.messages.calls == []


@pytest.mark.parametrize("body", [{}, {"ids": []}, {"ids": "x"}, {"ids": [1]}, {"ids": ["a", "a"]}, {"ids": [f"a{i}" for i in range(11)]}])
def test_package_refuses_wrong_requests(search, body):
    assert post(search, "/api/suche/bewerten-paket", body)[0] == 400


def test_package_with_an_unknown_hit_is_not_found(search):
    assert post(search, "/api/suche/bewerten-paket", {"ids": ["jobs-ch-000000000000"]})[0] == 404


def test_an_uncertain_grade_and_the_profession_grade_are_kept(search, monkeypatch):
    use_client(monkeypatch, PackageClient(lambda labels: [rating_entry(labels[0], 4, uncertain="Sehr knapp.", profession_grade=6)]))
    profile = search.kontext.daten / "suchprofil.md"
    profile.write_text(profile.read_text(encoding="utf-8") + "\n## Lehrbeginn\n\nAugust 2027\n", encoding="utf-8")
    ids = many_hits(search, 1)
    _, answer = post(search, "/api/suche/bewerten-paket", {"ids": ids})
    rating = answer["bewertet"][0]["bewertung"]
    assert rating["unsicher"] == "Sehr knapp." and rating["beruf_note"] == 6


def test_settings_default_to_automatic_and_can_be_switched_off(search):
    page = listing(search)
    assert page["einstellungen"]["auto_bewerten"] is True and page["paket"] == 10 and page["grenze"] == 30
    assert post(search, "/api/suche/einstellungen", {"auto_bewerten": False})[0] == 200
    assert listing(search)["einstellungen"]["auto_bewerten"] is False
    assert post(search, "/api/suche/einstellungen", {"auto_bewerten": "nein"})[0] == 400


def test_watching_is_off_until_chosen_and_goes_with_the_plan(search):
    assert listing(search)["einstellungen"]["zuschauen"] is False
    assert json.loads(get(search, "/api/suche/plan")[2])["plan"]["zuschauen"] is False
    assert post(search, "/api/suche/einstellungen", {"zuschauen": True})[0] == 200
    assert json.loads(get(search, "/api/suche/plan")[2])["plan"]["zuschauen"] is True
    assert listing(search)["einstellungen"]["auto_bewerten"] is True, "the other setting stays"
    assert post(search, "/api/suche/einstellungen", {"zuschauen": "ja"})[0] == 400


def test_own_stars_per_profession(search):
    status, saved = post(search, "/api/suche/beruf-sterne", {"beruf": "Fachfrau Gesundheit EFZ", "sterne": 5})
    assert status == 200 and saved["beruf_sterne"] == {"Fachfrau Gesundheit EFZ": 5}
    post(search, "/api/suche/beruf-sterne", {"beruf": "Koch EFZ", "sterne": 2})
    post(search, "/api/suche/beruf-sterne", {"beruf": "Fachfrau Gesundheit EFZ", "sterne": 0})
    assert listing(search)["einstellungen"]["beruf_sterne"] == {"Koch EFZ": 2}


@pytest.mark.parametrize("body", [{"beruf": "Koch", "sterne": 6}, {"beruf": "Koch", "sterne": True}, {"beruf": "", "sterne": 1},
                                  {"beruf": "Koch"}, {"beruf": ["x"], "sterne": 1}])
def test_bad_stars_are_refused(search, body):
    assert post(search, "/api/suche/beruf-sterne", body)[0] == 400


def test_an_uncertain_grade_goes_into_the_note_of_the_application(search, monkeypatch):
    use_client(monkeypatch, PackageClient(lambda labels: [rating_entry(labels[0], uncertain="Sehr knapp.")]))
    hit_id = many_hits(search, 1)[0]
    post(search, "/api/suche/bewerten", {}, id=hit_id)
    taken = post(search, "/api/suche/uebernehmen", {}, id=hit_id)[1]
    entries = yaml.safe_load((search.kontext.daten / "bewerbungen.yaml").read_text(encoding="utf-8"))
    entry = next(b for b in entries if b["id"] == taken["bewerbung_id"])
    assert "Note unsicher: Sehr knapp." in entry["notiz"]


def test_package_with_an_unusable_answer_reports_what_it_cost(search, monkeypatch):
    ids = many_hits(search, 2)
    use_client(monkeypatch, FakeClient(reply="abgeschnitten", stop_reason="max_tokens"))

    status, answer = post(search, "/api/suche/bewerten-paket", {"ids": ids})

    assert status == 200 and sorted(answer["offen"]) == sorted(ids) and answer["kosten_usd"] > 0


TRIAL = {"portal": "yousty", "portal_id": "schnupperlehre-77", "stelle": "Informatiker/in EFZ", "firma": "Muster GmbH", "ort": "Bern",
         "link": "https://www.yousty.ch/de-CH/lehrstellen/profile/77-x#schnupperlehre", "art": "Schnupperlehre",
         "beruf": "Informatiker EFZ", "text": "Schnuppern bei uns."}
APPRENTICESHIP = {**TRIAL, "portal": "LENA", "portal_id": "77", "art": "Lehrstelle", "text": "Lehrstelle bei uns.",
                  "link": "https://www.berufsberatung.ch/de/lehrstellen/77"}


def apprenticeship_profile(s):
    shutil.copy(VORLAGEN / "suchprofil-lehrstelle.md", s.kontext.daten / "suchprofil.md")


def test_trial_and_apprenticeship_at_one_company_stay_two_hits(search):
    apprenticeship_profile(search)
    post(search, "/api/suche/treffer", {"treffer": [APPRENTICESHIP]})

    post(search, "/api/suche/treffer", {"treffer": [TRIAL]})

    assert sorted(t["art"] for t in listing(search)["treffer"]) == ["Lehrstelle", "Schnupperlehre"]


def test_a_trial_page_with_the_address_of_a_stored_apprenticeship_is_still_fetched(search):
    apprenticeship_profile(search)
    plain = {**APPRENTICESHIP, "portal": "yousty", "link": "https://www.yousty.ch/de-CH/lehrstellen/profile/77-x"}
    post(search, "/api/suche/treffer", {"treffer": [plain]})

    answer = post(search, "/api/suche/sichten", {"treffer": [TRIAL]})[1]

    assert answer["holen"] == ["yousty:schnupperlehre-77"]


def test_taking_over_a_trial_names_it_in_the_register(search):
    apprenticeship_profile(search)
    post(search, "/api/suche/treffer", {"treffer": [TRIAL]})
    hit = listing(search)["treffer"][0]

    post(search, f"/api/suche/uebernehmen?id={hit['id']}", {})

    entry = next(b for b in search.kontext.register().alle() if b.get("art") == "Schnupperlehre")
    assert entry["stelle"] == "Schnupperlehre Informatiker/in EFZ"
    folder = search.kontext.daten / "bewerbungen" / entry["id"]
    assert "Art: Schnupperlehre" in (folder / "stelle.md").read_text(encoding="utf-8")


def test_the_page_changes_the_wish_in_the_profile_with_drafts(search):
    apprenticeship_profile(search)
    assert listing(search)["angebote"] == ["lehrstelle", "schnupperlehre"], "as in the template"

    status, answer = post(search, "/api/suche/angebot", {"wahl": "schnupperlehre"})

    assert status == 200 and answer["angebote"] == ["schnupperlehre"]
    assert listing(search)["angebote"] == ["schnupperlehre"]
    assert json.loads(get(search, "/api/suche/plan")[2])["plan"]["angebote"] == ["schnupperlehre"]
    assert any(e.datei.endswith("suchprofil.md") for e in search.kontext.ablage.liste())


def test_a_job_profile_cannot_change_the_wish(search):
    assert post(search, "/api/suche/angebot", {"wahl": "beides"})[0] == 400


def test_a_bad_wish_is_refused(search):
    apprenticeship_profile(search)

    assert post(search, "/api/suche/angebot", {"wahl": "ferienjob"})[0] == 400
    assert post(search, "/api/suche/angebot", "beides")[0] == 400


def _one_hit(s) -> str:
    post(s, "/api/suche/treffer", {"treffer": [{"portal": "jobs.ch", "portal_id": "9", "stelle": "Koch", "firma": "Muster AG", "link": "https://www.jobs.ch/x/9", "text": "Inserat"}]})
    return listing(s)["treffer"][0]["id"]


def test_a_rating_from_claude_is_stored_without_any_ai_call(search, monkeypatch):
    monkeypatch.setattr(routes_ai, "new_client", lambda *a: (_ for _ in ()).throw(AssertionError("no call")))
    wanted = _one_hit(search)
    status, answer = post(search, f"/api/suche/bewertung?id={wanted}", {"note": 2.5, "zusammenfassung": "Passt gut", "passt": ["Erfahrung"], "haken": ["Pendeln"]})
    assert status == 200 and answer["bewertung"]["note"] == 2.5
    stored = listing(search)["treffer"][0]["bewertung"]
    assert stored["zusammenfassung"] == "Passt gut" and stored["haken"] == ["Pendeln"] and stored["modell"] == "Claude (eigenes Abo)"
    assert stored["kosten_usd"] is None and stored["neue_luecken"] == [] and stored["auffaellig"] == []


@pytest.mark.parametrize("body", [{"note": 7, "zusammenfassung": "x"}, {"note": True, "zusammenfassung": "x"}, {"note": "2", "zusammenfassung": "x"},
                                  {"note": 2, "zusammenfassung": "x", "haken": "kein Liste"}, {"note": 2, "zusammenfassung": ""}, []])
def test_a_rating_in_another_form_is_refused(search, body):
    wanted = _one_hit(search)
    assert post(search, f"/api/suche/bewertung?id={wanted}", body)[0] == 400
    assert "bewertung" not in listing(search)["treffer"][0]
