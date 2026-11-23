"""What the page Stellen suchen says about the search window (#208, option A of docs/design/suchzeitraum.md, G32).

Normally the next search starts on the day of the last one, so the page names only the last search. A second line
comes when that is not so: on the first search, when portals catch up and when the pause was longer than the window.
A portal with a problem says it in its problem line. Runs store only a date, so the texts name days, never a time.
Apprenticeship portals and further sites search without a date: they never show one.
"""
import datetime

import search_plan
from ui_message import T

# The sentences are T (#422): German as before, said in the app language by the server.
FIRST = "Die erste Suche nimmt Inserate der letzten {days} Tage."
GAP = "Die nächste Suche nimmt nur die letzten {days} Tage, ab {start}."
NEW_ONE = "{names} sucht zum ersten Mal, die letzten {days} Tage."
NEW_MANY = "{names} suchen zum ersten Mal, die letzten {days} Tage."
AFTER_PROBLEM = "Sobald die Suche dort wieder geht, holt sie die Inserate ab {start} nach."
AFTER_PROBLEM_WINDOW = "Sobald die Suche dort wieder geht, holt sie die Inserate der letzten {days} Tage nach."
TODAY = "heute"
YESTERDAY = "gestern"
ON_DAY = "am {datum}"
TWO_NAMES = "{namen} und {letzter}"
MANY_CATCH_UP = "{anzahl} Portale holen nach, ab {datum}."
ONE_CATCHES_UP = "{namen} holt ab {datum} nach."
SOME_CATCH_UP = "{namen} holen ab {datum} nach."
TWO_CATCH_UP = "{erstes} holt ab {datum} nach, {zweites} ab {datum2}."
BOTH = "{nachholen} {neu}"  # two sentences in a row: no words of its own, each part keeps its language
MANY = 3  # from three portals on, one number instead of names


def _date(value: object) -> datetime.date | None:
    try:
        return datetime.date.fromisoformat(str(value))
    except ValueError:
        return None


def swiss(day: datetime.date) -> str:
    return day.strftime("%d.%m.%Y")


def when(value: object, today: datetime.date) -> str:
    """„heute“, „gestern“ or „am 24.10.2026“; "" for a date that cannot be read."""
    day = _date(value)
    if day is None:
        return ""
    past = (today - day).days
    if past == 0:
        return T(TODAY)
    if past == 1:
        return T(YESTERDAY)
    return T(ON_DAY, datum=swiss(day))


def _names(names: list[str]) -> str:
    return T(TWO_NAMES, namen=", ".join(names[:-1]), letzter=names[-1]) if len(names) > 1 else names[0]


def catching_up(late: dict[str, datetime.date]) -> str:
    """The sentence for portals that start before the last search, in the order of the portals."""
    if not late:
        return ""
    if len(late) >= MANY:
        return T(MANY_CATCH_UP, anzahl=len(late), datum=swiss(min(late.values())))
    names, days = list(late), list(late.values())
    if len(late) == 1:
        return T(ONE_CATCHES_UP, namen=_names(names), datum=swiss(days[0]))
    if days[0] == days[1]:
        return T(SOME_CATCH_UP, namen=_names(names), datum=swiss(days[0]))
    return T(TWO_CATCH_UP, erstes=names[0], datum=swiss(days[0]), zweites=names[1], datum2=swiss(days[1]))


def _problems(last_run: dict) -> set[str]:
    portals = last_run.get("portale") if isinstance(last_run.get("portale"), dict) else {}
    return {name for name, portal in portals.items() if isinstance(portal, dict) and portal.get("problem")}


def _starts(window: int, portals: tuple[str, ...], success: dict, today: datetime.date) -> dict[str, datetime.date]:
    days = search_plan.portal_days(window, portals, success, today)
    return {portal: today - datetime.timedelta(days=days[portal] - 1) for portal in portals}


def _second_line(window: int, last_day: datetime.date, starts: dict, success: dict, problems: set,
                 today: datetime.date) -> tuple[str, bool]:
    window_start = today - datetime.timedelta(days=window - 1)
    if window_start > last_day:
        closes = (today - last_day).days + 1 <= search_plan.MAX_WINDOW_DAYS
        return T(GAP, days=window, start=swiss(window_start)), window < search_plan.MAX_WINDOW_DAYS and closes
    fresh = [portal for portal in starts if portal not in success and portal not in problems]
    late = {portal: start for portal, start in starts.items()
            if start < last_day and portal in success and portal not in problems}
    new = _first_time(fresh, window) if fresh else ""
    behind = catching_up(late)
    return (T(BOTH, nachholen=behind, neu=new) if behind and new else behind or new), False


def _first_time(fresh: list[str], window: int) -> str:
    if len(fresh) == 1:
        return T(NEW_ONE, names=_names(fresh), days=window)
    return T(NEW_MANY, names=_names(fresh), days=window)


def _after_problem(portal: str, starts: dict, success: dict, window: int) -> str:
    """Its last success, or the whole window when that lies further back or there was none."""
    last = _date(success.get(portal))
    if last is None or last < starts[portal]:
        return T(AFTER_PROBLEM_WINDOW, days=window)
    return T(AFTER_PROBLEM, start=swiss(starts[portal]))


def _portal_rows(starts: dict, success: dict, problems: set, today: datetime.date) -> list[dict]:
    return [{"portal": portal, "zuletzt": when(success.get(portal), today), "ab": swiss(start), "problem": portal in problems}
            for portal, start in starts.items()]


def _success(last_run: dict | None) -> dict[str, str]:
    found = (last_run or {}).get("erfolgreich_am")
    return {str(k): str(v) for k, v in found.items() if _date(v)} if isinstance(found, dict) else {}


def display(kind: str, window: int, portals: tuple[str, ...], last_run: dict | None, today: datetime.date) -> dict:
    """{zeitfenster, letzte, zeile, zeitfenster_aendern, nachholen: {portal: sentence}, portale: [rows for the settings]}."""
    shown = {"zeitfenster": window, "letzte": "", "zeile": "", "zeitfenster_aendern": False, "nachholen": {}, "portale": []}
    dated = tuple(portal for portal in portals if portal in search_plan.PORTALS)
    if kind == search_plan.KIND_APPRENTICESHIP or not dated:
        return shown
    last_run = last_run if isinstance(last_run, dict) else None
    success = _success(last_run)
    starts = _starts(window, dated, success, today)
    problems = _problems(last_run or {}) & set(dated)
    shown = {**shown, "portale": _portal_rows(starts, success, problems, today)}
    last_day = _date((last_run or {}).get("datum"))
    if last_run is None or last_day is None or last_day > today:
        return {**shown, "zeile": T(FIRST, days=window) if last_run is None else ""}
    line, change = _second_line(window, last_day, starts, success, problems, today)
    behind = {portal: _after_problem(portal, starts, success, window) for portal in dated if portal in problems}
    return {**shown, "letzte": when(last_day.isoformat(), today), "zeile": line, "zeitfenster_aendern": change,
            "nachholen": behind}
