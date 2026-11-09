"""The positive title filter of the search profile screens titles before the full text is loaded (G31)."""
import json

import hits
import search_plan
from test_app import post, server  # noqa: F401  (server is a fixture)

PROFILE = """# Suchprofil

## Region
- Kantone (job-room): BE
- Orte (jobs.ch): Bern
- PLZ (jobscout24): 3000

## Keywords
- Kernliste: Python, Daten

## Titelfilter
- Positiv: Python, Entwickler/Developer, Data
- Ausschluss: Praktikum
"""
REASON = "kein Positivbegriff im Titel"


def ad(number: int, title: str) -> dict:
    return {"portal": "jobs.ch", "portal_id": f"t-{number}", "stelle": title, "firma": "Beispiel AG", "ort": "Bern",
            "link": f"https://www.jobs.ch/de/stellenangebote/detail/t-{number}/", "alter_tage": 3}


LISTING = [ad(1, "Python Developer"), ad(2, "Sachbearbeiter Einkauf"), ad(3, "Senior DATA Engineer"),
           ad(4, "Praktikum Python"), ad(5, "Pythonista gesucht")]


def test_the_plan_reads_the_positive_terms_split_on_comma_and_slash():
    assert search_plan.parse(PROFILE).title_positive == ("Python", "Entwickler", "Developer", "Data")


def test_titles_without_a_positive_term_are_screened_before_the_text(tmp_path):
    result = hits.Hits(tmp_path).screen(LISTING, ("Praktikum",), 45, [], title_positive=("Python", "Developer", "Data"))
    assert result["holen"] == ["jobs.ch:t-1", "jobs.ch:t-3"]
    assert {"stelle": "Sachbearbeiter Einkauf", "grund": REASON} in result["gefiltert"]
    assert {"stelle": "Pythonista gesucht", "grund": REASON} in result["gefiltert"], "whole words only"
    assert {"stelle": "Praktikum Python", "grund": "Titel: Praktikum"} in result["gefiltert"]


def test_without_a_positive_line_nothing_changes(tmp_path):
    assert search_plan.parse(PROFILE.replace("- Positiv: Python, Entwickler/Developer, Data\n", "")).title_positive == ()
    result = hits.Hits(tmp_path).screen(LISTING, ("Praktikum",), 45, [])
    assert result["holen"] == ["jobs.ch:t-1", "jobs.ch:t-2", "jobs.ch:t-3", "jobs.ch:t-5"]


def test_the_route_screens_with_the_positive_line_of_the_profile(server):  # noqa: F811
    (server.kontext.daten / "suchprofil.md").write_text(PROFILE, encoding="utf-8")
    status, screened = post(server, "/api/suche/sichten", {"treffer": LISTING})
    assert status == 200, json.dumps(screened)
    assert screened["holen"] == ["jobs.ch:t-1", "jobs.ch:t-3"]
    assert [entry["grund"] for entry in screened["gefiltert"]].count(REASON) == 2
