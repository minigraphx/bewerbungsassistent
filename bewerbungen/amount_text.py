"""Amounts and durations as the person reads them in texts of the server (#339, G45).

They read like the cost lines of the pages (`seiten/treffer-logik.js`, #334, #336): the currency before the amount, and
a no-break space so that number and unit never part at the end of a line. Screen readers read it as a space.
Durations are T (#422), so the unit is said in the app language like `minutes` and `seconds` of the pages.
"""
from ui_message import T

NBSP = "\u00a0"


def money_text(amount: float, currency: str) -> str:
    """„CHF 0.05“: what the pages write with `money`."""
    return f"{currency}{NBSP}{amount:.2f}"


def minutes_text(count: int) -> str:
    """„23 Minuten“, „1 Minute“: what the pages write with `minutes`."""
    if count == 1:
        return T("{anzahl}{nbsp}Minute", anzahl=count, nbsp=NBSP)
    return T("{anzahl}{nbsp}Minuten", anzahl=count, nbsp=NBSP)


def seconds_text(count: int) -> str:
    """„30 Sekunden“, „1 Sekunde“."""
    if count == 1:
        return T("{anzahl}{nbsp}Sekunde", anzahl=count, nbsp=NBSP)
    return T("{anzahl}{nbsp}Sekunden", anzahl=count, nbsp=NBSP)
