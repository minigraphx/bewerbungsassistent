"""An ad from a page the person has open (MIN-345): check without storing, save once, see what is there already."""
import pytest

import routes_ai
from test_ai_tasks import PackageClient, rating_entry
from test_app import post, server  # noqa: F401  (server is a fixture)
from test_routes_search import listing, search  # noqa: F401  (search is a fixture)

AD = {"stelle": "Daten-Ingenieur", "firma": "Vorbild Daten AG", "ort": "Bern", "link": "https://www.linkedin.com/jobs/view/123/?refId=abc&trk=x",
      "text": "Wir suchen eine Person für unsere Datenplattform. " * 8}


def rating_client():
    return PackageClient(lambda labels: [rating_entry(label, 5, summary="Passt gut.") for label in labels])


@pytest.fixture
def rated(search, monkeypatch):  # noqa: F811
    client = rating_client()
    monkeypatch.setattr(routes_ai, "new_client", lambda: client)
    return search, client


def applications(s):
    return s.kontext.register().alle()


def test_check_rates_the_ad_and_stores_nothing(rated):
    s, client = rated
    before = applications(s)

    status, answer = post(s, "/api/seite/pruefen", AD)

    assert status == 200 and answer["bewertung"]["note"] == 5 and answer["bewertung"]["zusammenfassung"] == "Passt gut."
    assert answer["vorhanden"] is None and answer["hinweis"] == ""
    assert applications(s) == before
    assert listing(s)["treffer"] == []
    assert "Datenplattform" in client.messages.calls[0]["messages"][0]["content"]


def test_save_makes_an_application_with_the_ad_and_the_rating(rated):
    s, _ = rated

    status, answer = post(s, "/api/seite/speichern", {**AD, "bewertung": {"note": 5, "zusammenfassung": "Passt gut.", "haken": ["Weit weg"]}})

    assert status == 200 and answer["neu"] is True
    entry = next(b for b in applications(s) if b["id"] == answer["bewerbung"]["id"])
    assert entry["firma"] == "Vorbild Daten AG" and entry["stelle"] == "Daten-Ingenieur" and entry["status"] == "Gemerkt"
    assert entry["passung"] == 5 and entry["portal"] == "linkedin.com" and "Passt gut." in entry["notiz"] and "Weit weg" in entry["notiz"]
    assert "Datenplattform" in (s.kontext.daten / "bewerbungen" / entry["id"] / "stelle.md").read_text(encoding="utf-8")


def test_save_without_a_rating_works(rated):
    s, _ = rated

    status, answer = post(s, "/api/seite/speichern", AD)

    assert status == 200 and answer["neu"] is True
    assert not next(b for b in applications(s) if b["id"] == answer["bewerbung"]["id"]).get("passung")


def test_saving_twice_shows_the_existing_application(rated):
    s, _ = rated
    first = post(s, "/api/seite/speichern", AD)[1]
    count = len(applications(s))

    second = post(s, "/api/seite/speichern", {**AD, "link": "https://www.linkedin.com/jobs/view/123/?refId=other"})[1]

    assert second["neu"] is False and second["bewerbung"]["id"] == first["bewerbung"]["id"]
    assert len(applications(s)) == count


def test_same_company_and_title_under_another_link_is_a_duplicate(rated):
    s, _ = rated
    first = post(s, "/api/seite/speichern", AD)[1]

    second = post(s, "/api/seite/speichern", {**AD, "firma": "Vorbild Daten", "link": "https://karriere.beispiel.ch/data-engineer"})[1]

    assert second["neu"] is False and second["bewerbung"]["id"] == first["bewerbung"]["id"]


def test_query_values_that_name_the_job_keep_ads_apart(rated):
    s, _ = rated
    post(s, "/api/seite/speichern", {**AD, "link": "https://jobs.example.ch/stelle?id=1"})

    second = post(s, "/api/seite/speichern", {**AD, "stelle": "BI Spezialist", "link": "https://jobs.example.ch/stelle?id=2"})[1]

    assert second["neu"] is True


def test_check_names_an_existing_application_and_others_at_the_company(rated):
    s, _ = rated
    post(s, "/api/seite/speichern", AD)

    same = post(s, "/api/seite/pruefen", AD)[1]
    other = post(s, "/api/seite/pruefen", {**AD, "stelle": "BI Spezialist", "link": "https://www.linkedin.com/jobs/view/999/"})[1]

    assert same["vorhanden"]["stelle"] == "Daten-Ingenieur" and same["vorhanden"]["status"] == "Gemerkt"
    assert other["vorhanden"] is None and "Vorbild Daten AG" in other["hinweis"]


@pytest.mark.parametrize("change", [
    {"stelle": ""}, {"text": ""}, {"text": 5}, {"link": ""}, {"link": "javascript:alert(1)"}, {"link": "file:///etc/passwd"},
    {"link": "https://user@example.ch/x"}, {"link": "chrome://settings"}, {"link": "https://exa mple.ch/"},
])
def test_bad_ads_are_refused(rated, change):
    s, _ = rated

    assert post(s, "/api/seite/pruefen", {**AD, **change})[0] == 400
    assert post(s, "/api/seite/speichern", {**AD, **change})[0] == 400


def test_saving_needs_a_company(rated):
    s, _ = rated

    status, answer = post(s, "/api/seite/speichern", {**AD, "firma": ""})

    assert status == 400 and "Firma" in answer["fehler"]


@pytest.mark.parametrize("rating", [{"note": 9}, {"note": "gut"}, {"note": True}, {"zusammenfassung": "ohne Note"}, "kaputt", {"note": 4, "haken": "kein Array"}])
def test_a_bad_rating_does_not_reach_the_register(rated, rating):
    s, _ = rated

    status, answer = post(s, "/api/seite/speichern", {**AD, "bewertung": rating})

    assert status == 400 and "Bewertung" in answer["fehler"]
    assert not any(b["stelle"] == "Daten-Ingenieur" for b in applications(s))


def test_a_long_text_is_cut_not_refused(rated):
    s, _ = rated

    assert post(s, "/api/seite/pruefen", {**AD, "text": "x " * 40_000})[0] == 200


def test_an_unusable_answer_is_a_clear_message(search, monkeypatch):  # noqa: F811
    monkeypatch.setattr(routes_ai, "new_client", lambda: PackageClient(lambda labels: []))

    status, answer = post(search, "/api/seite/pruefen", AD)

    assert status == 400 and "nicht bewertet" in answer["fehler"]


def test_the_ai_does_not_get_the_address_of_the_page(rated):
    s, client = rated

    post(s, "/api/seite/pruefen", {**AD, "link": "https://www.linkedin.com/jobs/view/123/?midToken=geheim1"})

    prompt = client.messages.calls[0]["messages"][0]["content"]
    assert "geheim1" not in prompt and "linkedin" not in prompt.lower()


def test_tracking_and_session_values_stay_out_of_the_register(rated):
    s, _ = rated
    link = "https://jobs.example.ch/stelle?id=7&utm_source=x&midToken=geheim1&midSig=geheim2&trackingId=geheim3&refId=geheim4&sessionid=geheim5"

    answer = post(s, "/api/seite/speichern", {**AD, "link": link})[1]

    entry = next(b for b in applications(s) if b["id"] == answer["bewerbung"]["id"])
    assert entry["link"] == "https://jobs.example.ch/stelle?id=7"
    assert "geheim" not in (s.kontext.daten / "bewerbungen" / entry["id"] / "stelle.md").read_text(encoding="utf-8")


def test_a_retry_after_a_failed_write_brings_the_ad(rated, monkeypatch):
    import routes_page
    s, _ = rated
    real = routes_page.schreibe_atomar

    def full(path, data):
        raise OSError("Datenträger voll")

    monkeypatch.setattr(routes_page, "schreibe_atomar", full)
    status, _answer = post(s, "/api/seite/speichern", AD)
    assert status != 200
    monkeypatch.setattr(routes_page, "schreibe_atomar", real)

    answer = post(s, "/api/seite/speichern", AD)[1]

    assert answer["neu"] is False
    assert "Datenplattform" in (s.kontext.daten / "bewerbungen" / answer["bewerbung"]["id"] / "stelle.md").read_text(encoding="utf-8")


def test_an_existing_ad_text_is_not_overwritten(rated):
    s, _ = rated
    first = post(s, "/api/seite/speichern", AD)[1]
    path = s.kontext.daten / "bewerbungen" / first["bewerbung"]["id"] / "stelle.md"
    path.write_text("Eigene Fassung", encoding="utf-8")

    post(s, "/api/seite/speichern", {**AD, "text": "Anderer Text " * 20})

    assert path.read_text(encoding="utf-8") == "Eigene Fassung"


def test_two_ads_under_one_address_are_two_ads(rated):
    s, _ = rated
    link = "https://firma.example.ch/karriere"
    post(s, "/api/seite/speichern", {**AD, "link": link})

    second = post(s, "/api/seite/speichern", {**AD, "stelle": "BI Spezialist", "link": link})[1]

    assert second["neu"] is True


def test_route_fragments_keep_ads_apart_and_others_are_dropped(rated):
    s, _ = rated
    answer = post(s, "/api/seite/speichern", {**AD, "link": "https://firma.example.ch/k#/job/1"})[1]
    assert next(b for b in applications(s) if b["id"] == answer["bewerbung"]["id"])["link"] == "https://firma.example.ch/k#/job/1"

    other = post(s, "/api/seite/speichern", {**AD, "stelle": "BI Spezialist", "link": "https://firma.example.ch/x#bewerben"})[1]
    assert next(b for b in applications(s) if b["id"] == other["bewerbung"]["id"])["link"] == "https://firma.example.ch/x"


def test_a_closed_application_does_not_block_a_new_one(rated):
    s, _ = rated
    first = post(s, "/api/seite/speichern", AD)[1]
    register = s.kontext.register()
    register.speichere({**register.hole(first["bewerbung"]["id"]), "status": "Absage"})

    check = post(s, "/api/seite/pruefen", AD)[1]
    second = post(s, "/api/seite/speichern", AD)[1]
    third = post(s, "/api/seite/speichern", AD)[1]

    assert check["vorhanden"]["status"] == "Absage", "the check still names it"
    assert second["neu"] is True and second["bewerbung"]["id"] != first["bewerbung"]["id"]
    assert third["neu"] is False and third["bewerbung"]["id"] == second["bewerbung"]["id"]
