"""Several places of a portal keep their order in the plan (#175); each searches every keyword (G43)."""
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


def test_every_place_searches_every_keyword_so_no_place_shares_a_limit():
    """G43 replaced the shared limit and its hint (#175, #195) with stages: nothing is left to share."""
    assert search_plan.parse(PROFILE).hints == ()


def test_few_keywords_need_no_hint():
    text = PROFILE.replace(", ".join(KEYWORDS), "Python, SQL")
    assert search_plan.parse(text).hints == ()
