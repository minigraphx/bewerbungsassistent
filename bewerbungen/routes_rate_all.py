"""„Alle prüfen“ on Stellen (G44, #209): what the page names before the person confirms.

The route counts the new hits without a grade, says which of them the extension loads first and which it may not load
(with the reason), and estimates cost and duration with `rate_all`. With the mediation it adds the budget left now and
afterwards, read from the mediation's account. The run itself goes package by package through
`/api/suche/bewerten-paket`; the mediation refuses a package once the budget is used up, and what was rated stays.
Nothing here calls the AI; the extension and Claude cannot reach the route.
"""
import missing_ads
import preferences
import rate_all
import routes_missing_ads
from ai import invitation, prompts, tasks
from ai.connection import find_connection
from ai.errors import AiError
from hits import Hits
from server import json_antwort

NEW = "neu"


def _context_chars(k) -> int:
    """The person's files and the rules go along with every call; only their length counts here."""
    files = [k.daten / name for name in tasks.FILES.values()]
    texts = sum(len(path.read_text(encoding="utf-8")) for path in files if path.is_file())
    return texts + len(prompts.rules(preferences.load(k.daten).address))


def budget_left() -> float | None:
    """What stays of the month's budget with the mediation; None with an own key, without AI or without an answer."""
    try:
        connection = find_connection()
        if not connection.via_mediation:
            return None
        account = invitation.account(connection.base_url, connection.access)
    except AiError:
        return None
    budget, spent = account.get("budget_usd"), account.get("spent_usd")
    if not all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in (budget, spent)):
        return None
    return max(0.0, budget - spent)


def _open_hits(k, store: Hits) -> tuple[list[int | None], list[str], list[dict]]:
    """Lengths of the ads to rate (None: still to load), the hits to load first and the hits that cannot be loaded."""
    lengths, to_load, not_loadable = [], [], []
    for hit in store.all():
        if hit.get("zustand") != NEW or hit.get("bewertung"):
            continue
        text = store.text(hit["id"]).strip()
        if text:
            lengths.append(len(store.ad_text(hit["id"])))
        elif missing_ads.loadable(missing_ads.hit_job(hit)):
            lengths.append(None)
            to_load.append(hit["id"])
        else:
            reason = routes_missing_ads.note_for_hit(k, hit)["grund"]
            not_loadable.append({"id": hit["id"], "stelle": hit["stelle"], "firma": hit.get("firma", ""), "grund": reason})
    return lengths, to_load, not_loadable


def overview(k, parameter, body):
    lengths, to_load, not_loadable = _open_hits(k, Hits(k.daten))
    found = rate_all.estimate(lengths, _context_chars(k))
    left = budget_left() if found.count else None
    after = None if left is None else round(max(0.0, left - found.cost_usd), 2)
    return json_antwort({"anzahl": found.count, "kosten_usd": found.cost_usd, "dauer_minuten": found.minutes,
                         "laden": to_load, "nicht_ladbar": not_loadable,
                         "budget_usd": None if left is None else round(left, 2), "danach_usd": after,
                         "reicht_fuer": rate_all.enough_for(found, left)})


GET = {"/api/suche/alle-pruefen": overview}
POST: dict = {}
