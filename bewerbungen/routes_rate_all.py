"""„Alle prüfen“ on Stellen (G44, #209): what the page names before the person confirms.

The route counts the new hits without a grade, says which of them the extension loads first and which it may not load
(with the reason), and estimates cost and duration with `rate_all`. With the mediation the amounts are in CHF (G46) and
it adds the credit of the code left now and afterwards, read from the mediation's account; with an own key they are in
USD. The run itself goes package by package through `/api/suche/bewerten-paket`; the mediation refuses a package once
the credit is used up (G80), and what was rated stays.
Nothing here calls the AI; the extension and Claude cannot reach the route.
"""
import dataclasses

import excluded_companies
import missing_ads
import preferences
import rate_all
import routes_missing_ads
from ai import invitation, prompts, tasks, usage
from ai.connection import currency_now, find_connection
from ai.errors import AiError
from hits import Hits
from server import json_antwort

NEW = "neu"


def _context_chars(k) -> int:
    """The person's files and the rules go along with every call; only their length counts here."""
    files = [k.daten / name for name in tasks.FILES.values()]
    texts = sum(len(path.read_text(encoding="utf-8")) for path in files if path.is_file())
    return texts + len(prompts.rules(preferences.load(k.daten).address))


def credit_left() -> float | None:
    """What stays of the credit of the code in CHF; None with an own key, without AI or without an answer."""
    try:
        connection = find_connection()
        if not connection.via_mediation:
            return None
        account = invitation.account(connection.base_url, connection.access)
    except AiError:
        return None
    credit, spent = account.get("credit_chf"), account.get("spent_chf")
    if not all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in (credit, spent)):
        return None
    return max(0.0, credit - spent)


def _open_hits(k, store: Hits) -> tuple[list[int | None], list[str], list[dict]]:
    """Lengths of the ads to rate (None: still to load), the hits to load first and the hits that cannot be loaded."""
    lengths, to_load, not_loadable = [], [], []
    for hit in excluded_companies.shown(store.all(), excluded_companies.keys(k.daten)):
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


@dataclasses.dataclass(frozen=True)
class Priced:
    """An estimate in the currency the person sees (G46), with the credit of the code when there is one."""
    currency: str
    rate: float  # per USD
    cost: float
    left: float | None

    def fields(self) -> dict:
        """kosten, waehrung, guthaben and danach, as „Alle prüfen“ and „Vorbefüllen“ (G85) name them."""
        after = None if self.left is None else round(max(0.0, self.left - self.cost), 2)
        return {"kosten": self.cost, "waehrung": self.currency,
                "guthaben": None if self.left is None else round(self.left, 2), "danach": after}


def priced(cost_usd: float, with_credit: bool) -> Priced:
    """`with_credit`: ask the mediation for the credit left; not when nothing would go to the AI."""
    left = credit_left() if with_credit else None
    currency = currency_now()
    rate = usage.CHF_PER_USD if currency == usage.MEDIATION_CURRENCY else 1.0
    return Priced(currency, rate, round(cost_usd * rate, 2), left)


def overview(k, parameter, body):
    lengths, to_load, not_loadable = _open_hits(k, Hits(k.daten))
    found = rate_all.estimate(lengths, _context_chars(k))
    money = priced(found.cost_usd, bool(found.count))
    return json_antwort({"anzahl": found.count, **money.fields(), "dauer_minuten": found.minutes,
                         "laden": to_load, "nicht_ladbar": not_loadable,
                         "reicht_fuer": rate_all.enough_for(found, None if money.left is None else money.left / money.rate)})


GET = {"/api/suche/alle-pruefen": overview}
POST: dict = {}
