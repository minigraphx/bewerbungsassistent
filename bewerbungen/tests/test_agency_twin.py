"""An agency ad that may be a job already in the register gets a hint (G34); invented agencies and register."""
import datetime
import json

import hits
import search_plan
from test_app import get, post, server  # noqa: F401  (server is a fixture)

TODAY = datetime.date(2026, 11, 9)
AGENCY = "Beispiel Personal AG"
REGISTER = [
    {"id": "muster-ag-python", "firma": "Muster AG", "stelle": "Python-Entwickler/in", "pensum": "80–100 %", "status": "Beworben"},
    {"id": "probe-gmbh-koch", "firma": "Probe GmbH", "stelle": "Koch", "pensum": "100 %", "status": "Absage"},
    {"id": "test-ag-daten", "firma": "Test AG", "stelle": "Data Engineer", "pensum": "60 %", "status": "Gespräch"},
]


def ad(number: int, title: str, company: str = AGENCY, pensum: str = "") -> dict:
    found = {"portal": "jobs.ch", "portal_id": f"a-{number}", "stelle": title, "firma": company, "ort": "Bern",
             "link": f"https://www.jobs.ch/de/stellenangebote/detail/a-{number}/", "text": "Inserat."}
    return {**found, "pensum": pensum} if pensum else found


def stored_hint(tmp_path, *ads, agencies=(AGENCY,)) -> list:
    store = hits.Hits(tmp_path)
    store.add(list(ads), REGISTER, TODAY, agencies=agencies)
    return [hit.get("hinweis", "") for hit in store.all()]


def test_an_agency_ad_with_the_title_and_pensum_of_an_open_entry_gets_a_hint(tmp_path):
    [hint] = stored_hint(tmp_path, ad(1, "Python Entwickler (m/w/d) 80-100%"))
    assert hint == "Könnte dieselbe Stelle sein wie „Python-Entwickler/in“ bei Muster AG (Beworben) in Ihren Bewerbungen."


def test_another_pensum_or_title_gets_no_hint(tmp_path):
    assert stored_hint(tmp_path, ad(1, "Data Engineer", pensum="100 %"), ad(2, "Projektleiter Bau")) == ["", ""]


def test_closed_entries_are_not_compared(tmp_path):
    assert stored_hint(tmp_path, ad(1, "Koch 100%")) == [""]
    for status in ("Absage", "Zusage", "Verworfen", "Zurückgezogen"):
        register = [{**REGISTER[0], "status": status}]
        store = hits.Hits(tmp_path / status)
        store.add([ad(1, "Python Entwickler")], register, TODAY, agencies=(AGENCY,))
        assert "hinweis" not in store.all()[0]


def test_a_direct_ad_keeps_the_company_check_only(tmp_path):
    assert stored_hint(tmp_path, ad(1, "Python Entwickler", company="Andere AG")) == [""]
    [hint] = stored_hint(tmp_path / "direkt", ad(2, "Tester", company="Muster AG"))
    assert hint == "Bei Muster AG gibt es schon: Python-Entwickler/in (Beworben)"


def test_without_the_agency_in_the_list_nothing_is_compared(tmp_path):
    assert stored_hint(tmp_path, ad(1, "Python Entwickler"), agencies=()) == [""]


def test_the_code_lists_agencies_and_the_profile_adds_more():
    assert len(hits.AGENCIES) >= 5
    text = "# Suchprofil\n\n## Vermittler\n- Weitere Vermittler: Beispiel Personal AG, Probe Staffing\n"
    assert search_plan.agencies_in(text) == ("Beispiel Personal AG", "Probe Staffing")


def test_the_route_uses_the_agencies_of_the_profile(server):  # noqa: F811
    daten = server.kontext.daten
    profile = (daten / "suchprofil.md").read_text(encoding="utf-8") if (daten / "suchprofil.md").is_file() else "# Suchprofil\n"
    (daten / "suchprofil.md").write_text(profile + f"\n## Vermittler\n- Weitere Vermittler: {AGENCY}\n", encoding="utf-8")
    server.kontext.register().speichere(REGISTER[0])
    assert post(server, "/api/suche/treffer", {"treffer": [ad(1, "Python Entwickler 80%")]})[0] == 200
    [hit] = json.loads(get(server, "/api/suche/liste")[2])["treffer"]
    assert "Python-Entwickler/in" in hit["hinweis"]
