"""Several places share the query limit of a portal, and the plan says how far each gets (#175)."""
import search_plan

KEYWORDS = ("Python", "TypeScript", "Go", "Rust", "Kotlin", "Swift", "SQL", "Linux", "Docker", "Kubernetes",
            "Terraform", "Ansible", "React", "Vue", "Angular")
NICHES = ("EdTech", "GovTech", "MedTech", "CleanTech", "FinTech", "LegalTech")
PROFILE = f"""# Suchprofil

## Region
- Kantone (job-room): BE, SO
- Orte (jobs.ch): Bern, Thun, Biel, Solothurn
- PLZ (jobscout24): 3000, 3600, 2500, 4500
- Regionen (ictjobs): grossraum-bern

## Keywords
- Kernliste: {", ".join(KEYWORDS)}
- Nischen (ohne Ort suchen): {", ".join(NICHES)}
"""


def test_the_plan_keeps_every_place_in_profile_order():
    plan = search_plan.parse(PROFILE).as_dict()
    assert plan["orte"] == ["Bern", "Thun", "Biel", "Solothurn"]
    assert plan["plz"] == ["3000", "3600", "2500", "4500"]
    assert (plan["stichworte"], plan["nischen"]) == (list(KEYWORDS), list(NICHES))
    assert plan["max_abfragen"] == search_plan.MAX_QUERIES == 30


def test_the_plan_says_how_many_keywords_each_place_searches():
    hints = search_plan.parse(PROFILE).hints
    assert ("jobs.ch: 30 Suchen reichen nicht für alle 15 Begriffe in 4 Orten; pro Ort laufen die ersten 6. "
            "Wichtige Begriffe nach vorne stellen.") in hints
    assert ("jobscout24: 30 Suchen reichen nicht für alle 15 Begriffe in 4 Orten; in 3000 und 3600 laufen die ersten 8, "
            "in 2500 und 4500 die ersten 7. Wichtige Begriffe nach vorne stellen.") in hints  # #195: the real shares
    assert not any(hint.startswith("ictjobs:") for hint in hints), "one region searches every keyword"


def test_the_hint_goes_with_its_portal():
    hints = search_plan.chosen(search_plan.parse(PROFILE), ["jobs.ch"]).hints
    assert [hint.split(":")[0] for hint in hints] == ["jobscout24"]


def test_few_keywords_need_no_hint():
    text = PROFILE.replace(", ".join(KEYWORDS), "Python, SQL")
    assert search_plan.parse(text).hints == ()
