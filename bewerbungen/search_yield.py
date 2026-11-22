"""What the last search runs brought per term and per place (G103, #375), for „Suche einstellen“.

Searches, hits and screen-outs come from the log of the runs (`query_log`); new hits and hits graded 4 or more from the
stored hits that name a query of the term or place and were found since the oldest of these runs. A hit found over
several terms counts for each. Terms match in their forms as the term list compares them (`search_terms.key`), so
„Fachfrau“ and „Fachmann“ are one profession. Every number is counted here, none comes from the AI.
"""
import collections

import search_plan
import search_terms
from hits import DOMAINS, QUERIES
from portal_places import REGION_NAMES
from query_log import KEPT_RUNS

GOOD_GRADE = 4
ICTJOBS = "ictjobs"


def _term_key(word: str) -> str:
    return search_terms.key(word) or word.casefold()


def same_term(one: str, other: str) -> bool:
    """Two names of one keyword, compared as the counts here compare them."""
    return _term_key(one) == _term_key(other)


def _valid_query(query) -> bool:
    """The log is data the person may have edited: only complete queries count."""
    return (isinstance(query, dict) and all(isinstance(query.get(name), str) for name in ("portal", "stichwort", "ort"))
            and type(query.get("treffer")) is int)


def _queries(runs: list[dict]) -> list[tuple[int, dict]]:
    """Each query of the runs with the number of its run."""
    return [(index, query) for index, run in enumerate(runs) for query in run["abfragen"] if _valid_query(query)]


def _tally(entries: list[tuple[int, dict]]) -> dict:
    screened = sum(q["aussortiert"] for _, q in entries if type(q.get("aussortiert")) is int)
    return {"suchen": len(entries), "treffer": sum(q["treffer"] for _, q in entries), "aussortiert": screened,
            "laeufe": len({index for index, _ in entries})}


def _grade(hit: dict):
    note = (hit.get("bewertung") or {}).get("note") if isinstance(hit.get("bewertung"), dict) else None
    return note if type(note) in (int, float) else None


def _hit_queries(hit: dict) -> list[dict]:
    found = hit.get(QUERIES)
    return [q for q in found if isinstance(q, dict)] if isinstance(found, list) else []


def _found(hits: list[dict], start: str | None, matches) -> dict:
    """New hits since `start` that a matching query found, and how many of them have a good grade."""
    if start is None:
        return {"neu": 0, "ab_note_4": 0}
    found = [h for h in hits if str(h.get("gefunden_am", "")) >= start and any(matches(q) for q in _hit_queries(h))]
    return {"neu": len(found), "ab_note_4": sum(1 for h in found if (_grade(h) or 0) >= GOOD_GRADE)}


def _without_yield(tally: dict, runs: int) -> bool:
    """«ohne Ertrag»: no hit in the last runs, and only once there are as many runs as the window holds."""
    return runs >= KEPT_RUNS and tally["laeufe"] >= KEPT_RUNS and tally["treffer"] == 0


def _entry(tally: dict, found: dict, runs: int) -> dict:
    return {"suchen": tally["suchen"], "treffer": tally["treffer"], **found, "aussortiert": tally["aussortiert"],
            "ohne_ertrag": _without_yield(tally, runs)}


def _for_term(name: str, queries, hits, start, runs: int) -> dict:
    key = _term_key(name)
    tally = _tally([(i, q) for i, q in queries if _term_key(q["stichwort"]) == key])
    found = _found(hits, start, lambda q: isinstance(q.get("stichwort"), str) and _term_key(q["stichwort"]) == key)
    return {"begriff": name, **_entry(tally, found, runs)}


def _empty_searches(queries, term_keys: set[str], niche_keys: set[str]) -> list[dict]:
    """Term × portal where every search came back empty, in the order they ran; a niche not in the list is marked."""
    keys = term_keys | niche_keys
    groups = dict.fromkeys((_term_key(q["stichwort"]), q["portal"]) for _, q in queries if _term_key(q["stichwort"]) in keys)
    found = []
    for key, portal in groups:
        mine = [(i, q) for i, q in queries if q["portal"] == portal and _term_key(q["stichwort"]) == key]
        tally = _tally(mine)
        if tally["treffer"] == 0:
            found = [*found, {"begriff": mine[-1][1]["stichwort"], "portal": portal, "suchen": tally["suchen"],
                              "laeufe": tally["laeufe"], "nische": key not in term_keys}]
    return found


def _portal_rank(portal: str) -> int:
    order = search_plan.ALL_PORTALS
    return order.index(portal) if portal in order else len(order)


def _place_name(portal: str, place: str) -> str:
    return REGION_NAMES.get(place, place) if portal == ICTJOBS else place


def _for_places(queries, hits, start, runs: int) -> list[dict]:
    # per portal the places as they ran, a search without place (niches, all of Switzerland) last
    places = sorted(dict.fromkeys((q["portal"], q["ort"]) for _, q in queries), key=lambda pair: (_portal_rank(pair[0]), not pair[1]))
    return [{"portal": portal, "ort": place, "ort_name": _place_name(portal, place),
             **_entry(_tally([(i, q) for i, q in queries if (q["portal"], q["ort"]) == (portal, place)]),
                      _found(hits, start, lambda q, p=portal, o=place: (q.get("portal"), q.get("ort")) == (p, o)), runs)}
            for portal, place in places]


def without_queries(hits: list[dict]) -> int:
    """Hits of the portals from before the app kept their queries; a site the person named never had any."""
    return sum(1 for h in hits if h.get("portal") in DOMAINS and not _hit_queries(h))


def _other_keys(hit: dict, key: str) -> dict[str, str]:
    """The other keywords that found this hit, by key, each with its name as the query had it."""
    words = (q.get("stichwort") for q in _hit_queries(hit))
    return {_term_key(word): word for word in words if isinstance(word, str) and _term_key(word) != key}


def _overlap_of(name: str, queries, hits, start, names: dict[str, str]) -> dict:
    key = _term_key(name)
    mine = [h for h in hits if start is not None and str(h.get("gefunden_am", "")) >= start
            and any(isinstance(q.get("stichwort"), str) and _term_key(q["stichwort"]) == key for q in _hit_queries(h))]
    others = [_other_keys(h, key) for h in mine]
    shared = collections.Counter(other for found in others for other in found)
    named = {other: names.get(other) or word for found in others for other, word in found.items()}
    per_run: dict[int, int] = {}
    for index, q in queries:
        if _term_key(q["stichwort"]) == key:
            per_run = {**per_run, index: per_run.get(index, 0) + q["treffer"]}
    return {"begriff": name, "nur_hier": sum(1 for found in others if not found),
            "auch_ueber": [{"begriff": named[other], "anzahl": count} for other, count in shared.most_common()],
            "laeufe": len(per_run), "laeufe_ohne_treffer": sum(1 for total in per_run.values() if total == 0)}


def overlap(runs: list[dict], hits: list[dict], terms: list[str]) -> list[dict]:
    """Per term, of the new hits it found in these runs (as `summary` counts them), how many only it found and which
    other keywords found the rest, most often first; and in how many runs it was searched, how many brought no hit."""
    queries = _queries(runs)
    start = min((run["datum"] for run in runs), default=None)
    names = {_term_key(word): word for word in terms}
    return [_overlap_of(name, queries, hits, start, names) for name in terms]


def summary(runs: list[dict], hits: list[dict], terms: list[str], with_places: bool, keywords: tuple[str, ...] = ()) -> dict:
    """The yield of the runs given (the last three): per term in the order of the list, the empty searches of these
    terms and of further `keywords` (niches), per place unless the search is for apprenticeships, and the old hits."""
    queries = _queries(runs)
    start = min((run["datum"] for run in runs), default=None)
    term_keys = {_term_key(word) for word in terms}
    niche_keys = {_term_key(word) for word in keywords}
    return {"laeufe": len(runs), "begriffe": [_for_term(name, queries, hits, start, len(runs)) for name in terms],
            "leer": _empty_searches(queries, term_keys, niche_keys), "orte": _for_places(queries, hits, start, len(runs)) if with_places else [],
            "ohne_angabe": without_queries(hits)}
