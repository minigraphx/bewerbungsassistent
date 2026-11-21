"""Calendar months in Swiss time (G98): the monthly budget renews at midnight in Zurich, not in UTC.

A month is "YYYY-MM". The time zone comes from the system's tz database; without it the import fails, so the
service never starts counting months in the wrong zone.
"""
import datetime
import re
import zoneinfo

ZONE = zoneinfo.ZoneInfo("Europe/Zurich")
MONTH = re.compile(r"(\d{4})-(0[1-9]|1[0-2])")


def month_of(moment: datetime.datetime) -> str:
    return moment.astimezone(ZONE).strftime("%Y-%m")


def _first_day(year: int, month: int) -> datetime.datetime:
    return datetime.datetime(year, month, 1, tzinfo=ZONE)


def bounds(month: str) -> tuple[datetime.datetime, datetime.datetime]:
    """Midnight in Zurich at the start of the month and of the next one; ValueError unless "YYYY-MM"."""
    match = MONTH.fullmatch(month)
    if match is None:
        raise ValueError(f"month expected as YYYY-MM, got {month!r}")
    year, number = int(match[1]), int(match[2])
    return _first_day(year, number), _first_day(year + number // 12, number % 12 + 1)


def renews_on(moment: datetime.datetime) -> datetime.date:
    """The day the budget of the month of `moment` renews: the first of the next month."""
    return bounds(month_of(moment))[1].date()
