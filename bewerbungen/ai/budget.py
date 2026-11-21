"""The monthly AI budget of the mediation (G98) in the words of the server.

The mediation names the month of the budget and the day it renews (`monat`, `erneuert_am` of `/v1/account`). The app
passes them on and words them; it never takes them from its own clock, which may be wrong. A mediation that names no
renewal still counts a one-time credit (G80), and its words stay.
"""
import datetime
import re

from ai import errors, invitation
from ai.connection import find_connection

MONTHS = ("Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November",
          "Dezember")
MONTH = re.compile(r"\d{4}-(0[1-9]|1[0-2])")
# Day and month never part at the end of a line; screen readers read it as a space.
NBSP = "\u00a0"


def _renewal_day(value: object) -> datetime.date | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.date.fromisoformat(value) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) else None
    except ValueError:
        return None


def renewal_fields(account: dict | None) -> dict:
    """`monat` and `erneuert_am` as the mediation sent them, both or neither; nothing a page could not read."""
    if not isinstance(account, dict):
        return {}
    month, renews = account.get("monat"), account.get("erneuert_am")
    if not isinstance(month, str) or MONTH.fullmatch(month) is None or _renewal_day(renews) is None:
        return {}
    return {"monat": month, "erneuert_am": renews}


def month_of(account: dict | None) -> tuple[str, str] | None:
    """("November", "1. Dezember") for the words of the pages; None from a mediation that names no renewal."""
    fields = renewal_fields(account)
    if not fields:
        return None
    day = _renewal_day(fields["erneuert_am"])
    return MONTHS[int(fields["monat"][5:]) - 1], f"{day.day}.{NBSP}{MONTHS[day.month - 1]}"


def used_up_message(account: dict | None) -> str:
    """What a refusal of the mediation says once the budget is used up, as Einstellungen say it."""
    named = month_of(account)
    if named is None:
        return errors.CREDIT_USED_ONCE
    return errors.CREDIT_USED.format(month=named[0], renews=named[1])


def used_up_error() -> errors.AiError:
    """The refusal (402) names no date; the account of the access does. Without an answer the words of G80 stay."""
    try:
        connection = find_connection()
        account = invitation.account(connection.base_url, connection.access) if connection.via_mediation else None
    except errors.AiError:
        account = None
    return errors.CreditUsedUp(used_up_message(account))
