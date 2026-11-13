"""Suche einstellen (#263, A4, G57): one page in four cards plus Erweitert, with the time window and further sites."""
import json
import pathlib
import shutil

import search_plan
from test_ai_tasks import VORLAGEN
from test_app import get, server  # noqa: F401  (server is a fixture)

SEITEN = pathlib.Path(__file__).resolve().parents[1] / "seiten"


def read(name: str) -> str:
    return (SEITEN / name).read_text(encoding="utf-8")


def test_the_frame_reads_workload_exclusions_and_title_filters_from_the_profile():
    frame = search_plan.frame((VORLAGEN / "suchprofil.md").read_text(encoding="utf-8"))
    assert frame["pensum"] == "80–100%"
    assert frame["ausschluss"] == ["Bildung ohne IT-Bezug", "Recruiting"]
    assert frame["titel_ausschluss"][:2] == ["Praktikum", "Lehrstelle"]
    assert "Python" in frame["titel_positiv"]


def test_a_profile_without_these_parts_has_an_empty_frame():
    assert search_plan.frame("# Suchprofil\n\n## Keywords\n- Kernliste: Python\n") == {
        "pensum": "", "ausschluss": [], "titel_ausschluss": [], "titel_positiv": []}


def test_the_route_gives_the_frame_and_an_empty_one_without_profile(server):  # noqa: F811
    status, _, content = get(server, "/api/suche/rahmen")
    assert status == 200 and json.loads(content)["pensum"] == ""
    shutil.copy(VORLAGEN / "suchprofil.md", server.kontext.daten / "suchprofil.md")
    assert json.loads(get(server, "/api/suche/rahmen")[2])["ausschluss"] == ["Bildung ohne IT-Bezug", "Recruiting"]


def test_the_page_is_served_and_leads_back_to_stellen(server):  # noqa: F811
    status, _, content = get(server, "/suche-einstellen")
    assert status == 200
    page = content.decode()
    assert '<a href="/treffer"' in page and "<title>Suche einstellen</title>" in page


def test_four_cards_and_erweitert_hold_the_settings():
    html = read("suche-einstellen.html")
    for card in ("karte-begriffe", "karte-region", "karte-nicht", "karte-wo"):
        assert f'id="{card}"' in html, card
    erweitert = html[html.index('<details id="erweitert"'):html.index('class="settings-page__foot"')]
    assert 'id="zeitfenster-tage"' in erweitert and 'id="auto-bewerten"' in erweitert and 'id="zuschauen"' in erweitert
    wo = html[html.index('id="karte-wo"'):html.index("</section>", html.index('id="weitere-seiten"'))]
    assert 'id="portale-liste"' in wo and 'id="seiten"' in wo


def test_time_window_and_further_sites_left_the_settings_g57():
    settings = read("einstellungen.html") + read("einstellungen.js")
    for gone in ('id="zeitfenster"', "zeitfenster.js", "Weitere Seiten durchsuchen", 'id="seiten"', "/api/suche/weitere-seiten"):
        assert gone not in settings, gone


def test_stellen_links_to_the_page_instead_of_opening_a_section():
    html = read("treffer.html")
    assert 'id="einstellen"' not in html and 'id="portale-liste"' not in html and 'id="suchliste"' not in html
    assert 'href="/suche-einstellen"' in html
    assert 'href="/suche-einstellen#zeitfenster"' in html
