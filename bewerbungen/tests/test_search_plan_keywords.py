"""Every keyword line of the profile is searched (#174), every term of it (G43)."""
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


def test_terms_beyond_what_the_app_lets_one_add_are_all_searched():
    plan = search_plan.parse(profile(CORE))
    assert len(CORE) > search_plan.MAX_KEYWORDS
    assert plan.keywords == (*CORE, *SECOND), "G43: no fixed maximum, so no term is dropped"
    assert plan.hints == ()


def test_a_term_of_the_second_group_can_be_removed_as_the_page_shows_it():
    changed = search_terms.removed(profile(CORE[:3]), "Scrum Master")
    assert search_plan.parse(changed).keywords == (*CORE[:3], "Projektleitung IT")


def test_the_plan_for_the_extension_carries_every_term(server):  # noqa: F811
    (server.kontext.daten / "suchprofil.md").write_text(profile(CORE), encoding="utf-8")
    plan = json.loads(get(server, "/api/suche/plan")[2])["plan"]
    assert plan["stichworte"] == [*CORE, *SECOND]
    assert not any("Nicht gesucht" in h for h in plan["hinweise"])
