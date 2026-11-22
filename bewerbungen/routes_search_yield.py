"""What the search brings, for „Suche einstellen“ (G103, #375): the yield per term and place of the last three runs.

Only the page reads it; the extension and Claude cannot reach the route (list in desktop/native_host.py).
"""
import excluded_companies
import preferences
import routes_career
import search_plan
import search_yield
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


def yield_of_search(k, parameter, body):
    kind = preferences.load(k.daten).sought
    shown = excluded_companies.shown(Hits(k.daten).all(), excluded_companies.keys(k.daten))
    terms = routes_career.searched_now(k)["gesuchte_berufe"]
    # Apprenticeships are searched by profession around the home (radius): their places tell nothing apart.
    result = search_yield.summary(QueryLog(k.daten).runs(), shown, terms,
                                  with_places=kind != search_plan.KIND_APPRENTICESHIP, keywords=_niches(k))
    return json_antwort({"art": kind, **result})


GET = {"/api/suche/ertrag": yield_of_search}
