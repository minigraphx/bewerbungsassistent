"""How big a search run is (G43): every search runs, per portal in stages, and a long run is announced first.

The extension builds the searches (erweiterung/lib/queries.js buildQueries) and runs them in stages of STAGE_SIZE with
STAGE_PAUSE_SECONDS between them; the app sends both with the plan. Here the app counts the same searches from the plan
it sends, so that the page Stellen and the popup can say before the start how many there are and how long it takes.
erweiterung/tests/fixtures/run-size.json keeps the two counts equal.
"""
import math

STAGE_SIZE = 30  # searches per portal in a row, then the longer pause
STAGE_PAUSE_SECONDS = 60
STAGE_PAUSE_WORDS = "einer Minute"  # STAGE_PAUSE_SECONDS in the announcement
# A search reads up to three result pages with 0.6 s between requests, plus loading: rough, rather too much.
SECONDS_PER_SEARCH = 5
APPRENTICESHIP_PORTALS = frozenset({"LENA", "yousty"})
PLACE_FIELDS = {"jobs.ch": "orte", "jobscout24": "plz", "ictjobs": "regionen"}  # as PLACE in queries.js
ANNOUNCEMENT = ("Diese Suche dauert etwa {minutes} Minuten: {searches} Suchen in {stages} Etappen, mit je {pause} Pause "
                "dazwischen. Viele neue Inserate machen sie länger.")


def _count(values: object) -> int:
    return len(values) if isinstance(values, list) else 0


def _searches(portal: str, plan: dict) -> int:
    """As buildQueries: keyword × place, niches without place on jobs.ch, the whole country when there is no place."""
    keywords, niches = _count(plan.get("stichworte")), _count(plan.get("nischen"))
    if portal in APPRENTICESHIP_PORTALS:
        area = _count(plan.get("orte")) or _count(plan.get("kantone"))
        return (_count(plan.get("angebote")) or 1) * keywords * area
    if portal == "job-room":
        return keywords + niches
    if portal not in PLACE_FIELDS:
        return 0
    places = _count(plan.get(PLACE_FIELDS[portal]))
    free = niches if portal == "jobs.ch" else 0
    everywhere = keywords if plan.get("schweizweit") or not places else 0
    return places * keywords + free + everywhere


def searches_per_portal(plan: dict) -> dict[str, int]:
    """The searches of each portal of the plan, as /api/suche/plan sends it to the extension."""
    return {portal: _searches(portal, plan) for portal in plan.get("portale") or []}


def size(plan: dict) -> dict:
    """Searches, stages and rough minutes of a run, and the announcement when a portal needs more than one stage."""
    per_portal = searches_per_portal(plan)
    stages = {portal: math.ceil(count / STAGE_SIZE) for portal, count in per_portal.items()}
    searches, pauses = sum(per_portal.values()), sum(max(0, count - 1) for count in stages.values())
    minutes = math.ceil((searches * SECONDS_PER_SEARCH + pauses * STAGE_PAUSE_SECONDS) / 60)
    long = pauses > 0
    text = ANNOUNCEMENT.format(minutes=minutes, searches=searches, stages=sum(stages.values()),
                               pause=STAGE_PAUSE_WORDS) if long else ""
    return {"suchen": searches, "etappen": sum(stages.values()), "minuten": minutes, "lang": long, "text": text,
            "pro_portal": per_portal}


def for_extension(plan: dict) -> dict:
    """What the plan adds for the extension: how it runs the stages, and the announcement for its popup."""
    return {"etappe_abfragen": STAGE_SIZE, "etappe_pause_sekunden": STAGE_PAUSE_SECONDS, "umfang": size(plan)}
