"""Every keyword line of the profile is searched, and what the limit drops is named (#174)."""
import json

import search_plan
import search_terms
from test_app import get, server  # noqa: F401  (server is a fixture)

CORE = ("Python", "TypeScript", "Go", "Rust", "Kotlin", "Swift", "SQL", "Linux", "Docker", "Kubernetes", "Terraform",
        "Ansible", "React", "Vue", "Angular", "Django", "Flask", "Spark", "Kafka", "Airflow", "Grafana", "Prometheus",
        "PostgreSQL", "Redis")
SECOND = ("Projektleitung IT", "Scrum Master")


def profile(core: tuple[str, ...]) -> str:
    return f"""# Suchprofil

## Region
- Kantone (job-room): BE
- Orte (jobs.ch): Bern
- PLZ (jobscout24): 3000

## Keywords
- Kernliste: {", ".join(core)}
- Zweite Richtung: {", ".join(SECOND)}
- Nischen (ohne Ort suchen): EdTech
- nur Festanstellung, keine Temporärstellen
"""


def test_a_second_named_group_is_searched_after_the_core_list():
    plan = search_plan.parse(profile(CORE[:3]))
    assert plan.keywords == (*CORE[:3], *SECOND)
    assert plan.niche_keywords == ("EdTech",)
    assert plan.hints == ()


def test_terms_over_the_limit_are_named_in_a_hint():
    plan = search_plan.parse(profile(CORE))
    assert plan.keywords == CORE[:search_plan.MAX_KEYWORDS]
    dropped = (*CORE[search_plan.MAX_KEYWORDS:], *SECOND)
    assert plan.hints == (f"Gesucht werden höchstens 15 Begriffe. Nicht gesucht: {', '.join(dropped)}. "
                          "Weniger wichtige Begriffe entfernen.",)


def test_the_hint_stays_with_any_choice_of_portals():
    plan = search_plan.chosen(search_plan.parse(profile(CORE)), ["jobs.ch", "jobscout24"])
    assert any("Nicht gesucht" in h for h in plan.hints)


def test_a_term_of_the_second_group_can_be_removed_as_the_page_shows_it():
    changed = search_terms.removed(profile(CORE[:3]), "Scrum Master")
    assert search_plan.parse(changed).keywords == (*CORE[:3], "Projektleitung IT")


def test_the_page_suche_shows_the_dropped_terms(server):  # noqa: F811
    (server.kontext.daten / "suchprofil.md").write_text(profile(CORE), encoding="utf-8")
    hints = json.loads(get(server, "/api/suche/liste")[2])["hinweise"]
    assert any("Nicht gesucht" in h and "Scrum Master" in h for h in hints)
