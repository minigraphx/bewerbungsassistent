"""A last successful run dated in the future does not shrink the search window (#196)."""
import datetime

import search_plan

TODAY = datetime.date(2026, 10, 26)
WINDOW = 21


def days_after(last_run: datetime.date) -> int:
    return search_plan.portal_days(WINDOW, ("jobs.ch",), {"jobs.ch": last_run.isoformat()}, TODAY)["jobs.ch"]


def test_a_last_run_a_week_ahead_searches_the_full_window():
    assert days_after(TODAY + datetime.timedelta(days=7)) == WINDOW


def test_a_last_run_tomorrow_searches_the_full_window():
    assert days_after(TODAY + datetime.timedelta(days=1)) == WINDOW


def test_a_last_run_three_days_ago_still_searches_four_days():
    assert days_after(TODAY - datetime.timedelta(days=3)) == 4


def test_a_last_run_today_searches_one_day():
    assert days_after(TODAY) == 1
