"""Amounts and durations as the person reads them in texts of the server (#339, G45).

They read like the cost lines of the pages (`seiten/treffer-logik.js`, #334, #336): the currency before the amount, and
a no-break space so that number and unit never part at the end of a line. Screen readers read it as a space.
"""
NBSP = " "


def money_text(amount: float, currency: str) -> str:
    """„CHF 0.05“: what the pages write with `money`."""
    return f"{currency}{NBSP}{amount:.2f}"


def _counted(count: int, one: str, many: str) -> str:
    return f"{count}{NBSP}{one if count == 1 else many}"


def minutes_text(count: int) -> str:
    """„23 Minuten“, „1 Minute“: what the pages write with `minutes`."""
    return _counted(count, "Minute", "Minuten")


def seconds_text(count: int) -> str:
    """„30 Sekunden“, „1 Sekunde“."""
    return _counted(count, "Sekunde", "Sekunden")
