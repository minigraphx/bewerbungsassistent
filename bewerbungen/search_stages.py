"""How big a search run is (G43): every search runs, per portal in stages, and a long run is announced first.

The extension builds the searches (erweiterung/lib/queries.js buildQueries) and runs them in stages of STAGE_SIZE with
STAGE_PAUSE_SECONDS between them; the app sends both with the plan. Here the app counts the same searches from the plan
it sends, so that the page Stellen and the popup can say before the start how many there are and how long it takes.
erweiterung/tests/fixtures/run-size.json keeps the two counts equal.
"""
import math

from amount_text import minutes_text

STAGE_SIZE = 30  # searches per portal in a row, then the longer pause
STAGE_PAUSE_SECONDS = 60
STAGE_PAUSE_WORDS = "einer Minute"  # STAGE_PAUSE_SECONDS in the announcement
# A search reads up to three result pages with 0.6 s between requests, plus loading: rough, rather too much.
SECONDS_PER_SEARCH = 5
# #391: a jobscout24 region search reads up to max_seiten_regionen pages instead of max_seiten, so the time counts each
# search by its pages, relative to the plan's own max_seiten. A measured region search with a common term read all 10
# pages, its list never ran short, at about 0.4 s per page plus the pause: still under what SECONDS_PER_SEARCH allows.
DEFAULT_PAGES = 3  # as search_plan.MAX_PAGES, for a plan that names no pages
APPRENTICESHIP_PORTALS = frozenset({"LENA", "yousty"})
PLACE_FIELDS = {"jobs.ch": "orte", "jobscout24": "plz", "ictjobs": "regionen"}  # as PLACE in queries.js
ANNOUNCEMENT = ("Diese Suche dauert etwa {minutes}: {searches} Suchen in {stages} Etappen, mit je {pause} Pause "
                "dazwischen. Viele neue Inserate machen sie länger.")


def _count(values: object) -> int:
    return len(values) if isinstance(values, list) else 0


def _runs_on(term: object, portal: str, limits: object) -> bool:
    """As runsOn in queries.js: a term the profile limits to some portals (G105) runs only there."""
    only = limits.get(term) if isinstance(limits, dict) and isinstance(term, str) else None
    return not isinstance(only, list) or portal in only


def _keywords_on(portal: str, plan: dict) -> int:
    terms = plan.get("stichworte")
    return sum(_runs_on(term, portal, plan.get("nur_portale")) for term in terms) if isinstance(terms, list) else 0


def _searches(portal: str, plan: dict) -> int:
    """As buildQueries: keyword × place, niches without place on jobs.ch, the whole country when there is no place;
    jobscout24 with regions once per keyword."""
    keywords, niches = _keywords_on(portal, plan), _count(plan.get("nischen"))
    if portal in APPRENTICESHIP_PORTALS:
        area = _count(plan.get("orte")) or _count(plan.get("kantone"))
        return (_count(plan.get("angebote")) or 1) * keywords * area
    if portal == "job-room":
        return keywords + niches
    if portal not in PLACE_FIELDS:
        return 0
    # G107: with regions jobscout24 searches each term once in all of them, its postcodes rest
    places = 1 if _by_region(portal, plan) else _count(plan.get(PLACE_FIELDS[portal]))
    free = niches if portal == "jobs.ch" else 0
    everywhere = keywords if plan.get("schweizweit") or not places else 0
    return places * keywords + free + everywhere


def _by_region(portal: str, plan: dict) -> bool:
    return portal == "jobscout24" and _count(plan.get("regionen_jobscout24")) > 0


def _pages(plan: dict) -> tuple[int, int]:
    """As pagesOf in queries.js: the pages a search reads at most, and those of a jobscout24 region search."""
    pages, by_region = plan.get("max_seiten"), plan.get("max_seiten_regionen")
    pages = pages if isinstance(pages, int) and pages > 0 else DEFAULT_PAGES
    return pages, by_region if isinstance(by_region, int) and by_region > 0 else pages


def searches_per_portal(plan: dict) -> dict[str, int]:
    """The searches of each portal of the plan, as /api/suche/plan sends it to the extension."""
    return {portal: _searches(portal, plan) for portal in plan.get("portale") or []}


def pages_per_portal(plan: dict) -> dict[str, int]:
    """The result pages the searches of each portal read at most (#391): a region search its own limit, once per term."""
    pages, by_region = _pages(plan)
    return {portal: count * pages + (_keywords_on(portal, plan) * (by_region - pages) if _by_region(portal, plan) else 0)
            for portal, count in searches_per_portal(plan).items()}


def size(plan: dict) -> dict:
    """Searches, stages and rough minutes of a run, and the announcement when a portal needs more than one stage.

    The stages count searches, as the extension runs them; the time counts pages, a search of the plan's pages being
    SECONDS_PER_SEARCH, so a jobscout24 region search of up to 10 pages weighs 10/3 of one (#391)."""
    per_portal = searches_per_portal(plan)
    stages = {portal: math.ceil(count / STAGE_SIZE) for portal, count in per_portal.items()}
    searches, pauses = sum(per_portal.values()), sum(max(0, count - 1) for count in stages.values())
    pages = _pages(plan)[0]
    # whole numbers only: seconds times pages per search, then rounded up to minutes
    weighted = sum(pages_per_portal(plan).values()) * SECONDS_PER_SEARCH + pauses * STAGE_PAUSE_SECONDS * pages
    minutes = -(-weighted // (60 * pages))
    long = pauses > 0
    text = ANNOUNCEMENT.format(minutes=minutes_text(minutes), searches=searches, stages=sum(stages.values()),
                               pause=STAGE_PAUSE_WORDS) if long else ""
    return {"suchen": searches, "etappen": sum(stages.values()), "minuten": minutes, "lang": long, "text": text,
            "pro_portal": per_portal}


def for_extension(plan: dict) -> dict:
    """What the plan adds for the extension: how it runs the stages, and the announcement for its popup."""
    return {"etappe_abfragen": STAGE_SIZE, "etappe_pause_sekunden": STAGE_PAUSE_SECONDS, "umfang": size(plan)}
