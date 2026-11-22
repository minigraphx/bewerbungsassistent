"""The cases of #382 through the screening the extension calls (G104), with an invented profile."""
import hits
import search_plan

PROFILE = """# Suchprofil

## Keywords
- Kernliste: Kursleiter

## Titelfilter
- Positiv: Software, Kurs, Applikation
- Ausschluss: Pflege, Intern (ganzes Wort), Sales
"""


def ad(number: int, title: str) -> dict:
    return {"portal": "jobs.ch", "portal_id": f"c-{number}", "stelle": title, "firma": "Beispiel AG", "ort": "Bern",
            "link": f"https://www.jobs.ch/de/stellenangebote/detail/c-{number}/", "alter_tage": 2}


def screened(tmp_path, titles: list[str], profile: str = PROFILE) -> dict:
    plan = search_plan.parse(profile)
    listing = [ad(number, title) for number, title in enumerate(titles, 1)]
    return hits.Hits(tmp_path).screen(listing, plan.title_exclude, 45, [], title_positive=plan.title_positive)


def test_compound_titles_pass_the_positive_filter(tmp_path):
    result = screened(tmp_path, ["Softwareentwickler:in", "Kursleiter-in für Erwachsene", "Applikationsentwickler/in"])
    assert result["holen"] == ["jobs.ch:c-1", "jobs.ch:c-2", "jobs.ch:c-3"]
    assert result["gefiltert"] == []


def test_a_compound_title_is_excluded(tmp_path):
    result = screened(tmp_path, ["Pflegefachperson HF mit Berufsbildnerfunktion", "Salesforce-Entwickler Software"])
    assert {"stelle": "Pflegefachperson HF mit Berufsbildnerfunktion", "grund": "Titel: Pflege"} in result["gefiltert"]
    assert {"stelle": "Salesforce-Entwickler Software", "grund": "Titel: Sales"} in result["gefiltert"]
    assert result["holen"] == []


def test_international_sales_is_not_excluded_by_intern_as_a_whole_word(tmp_path):
    only_exclusions = PROFILE.replace("- Positiv: Software, Kurs, Applikation\n", "").replace(", Sales", "")
    result = screened(tmp_path, ["International Sales", "Intern Marketing"], only_exclusions)
    assert result["holen"] == ["jobs.ch:c-1"]
    assert result["gefiltert"] == [{"stelle": "Intern Marketing", "grund": "Titel: Intern"}]
