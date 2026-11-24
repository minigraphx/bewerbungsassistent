"""What the search brings, for „Suche einstellen“ (G103, #375): the yield per term and place of the last three runs,
and per title filter term example titles of the last run (G104, #382).

Only the page reads it; the extension and Claude cannot reach the route (list in desktop/native_host.py).
"""
import excluded_companies
import preferences
import routes_career
import search_plan
import search_yield
import title_examples
from hits import Hits
from query_log import QueryLog
from server import json_antwort


def _niches(k) -> tuple[str, ...]:
    """Niche keywords are searched but not in the term list; their empty searches still count. None while the profile
    cannot be searched yet."""
    try:
        return search_plan.for_folder(k.daten).niche_keywords
    except ValueError:
        return ()


def _niche_remote(k) -> bool:
    """G125: whether a remote mention keeps a niche hit outside the region, so the page words «ausserhalb» to match."""
    try:
        return search_plan.for_folder(k.daten).niche_remote_kept
    except ValueError:
        return True


def _title_examples(k, runs: list[dict], kind: str) -> dict | None:
    """Per title filter term the titles of the last run it let through or kept out (G104); only a job search has a
    title filter, and a profile the search cannot read yet has none."""
    if kind == search_plan.KIND_APPRENTICESHIP:
        return None
    try:
        plan = search_plan.for_folder(k.daten)
    except ValueError:
        return None
    return title_examples.summary(runs[-1] if runs else None, plan.title_positive, plan.title_exclude)


def yield_of_search(k, parameter, body):
    kind = preferences.load(k.daten).sought
    shown = excluded_companies.shown(Hits(k.daten).all(), excluded_companies.keys(k.daten))
    terms = routes_career.searched_now(k)["gesuchte_berufe"]
    runs = QueryLog(k.daten).runs()
    # Apprenticeships are searched by profession around the home (radius): their places tell nothing apart.
    result = search_yield.summary(runs, shown, terms, with_places=kind != search_plan.KIND_APPRENTICESHIP, keywords=_niches(k))
    # G110: required words are a job search's only
    unrelated = search_yield.unrelated(runs, terms) if kind != search_plan.KIND_APPRENTICESHIP else []
    return json_antwort({"art": kind, **result, "titelfilter": _title_examples(k, runs, kind), "ohne_pflichtbezug": unrelated,
                         "nischen_remote": _niche_remote(k)})


GET = {"/api/suche/ertrag": yield_of_search}
