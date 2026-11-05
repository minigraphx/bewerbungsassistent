"""A good grade is looked at again before it counts (MIN-389).

Measured on one set of ads, a grade from a package varied by up to two grades for the same ad, and a single ad rated
alone by up to one. A hit at grade 4 or better is what a person acts on, so it is rated alone three times and the
middle grade counts. The three runs of a hit go out together, the hits one after the other: a run takes about ten
seconds, which stays within the calls per minute that the mediation allows. A hit that could not be looked at again
keeps its package rating; the caller says so.
"""
import concurrent.futures
import dataclasses

from ai import tasks
from ai.errors import AiError, AnswerError
from ai.gateway import Gateway

CHECK_FROM_GRADE = 4
RUNS = 3


@dataclasses.dataclass(frozen=True)
class Look:
    rating: dict  # the rating that counts now
    grades: tuple  # the runs alone, in order; empty when none could be used
    first_grade: float | None  # the grade from the package; None when the ad was alone there and counts as a run
    cost_usd: float | None


@dataclasses.dataclass(frozen=True)
class _Runs:
    ratings: tuple
    cost_usd: float | None
    stopped: bool  # connection, access or budget: asking again would fail too


def deserved(rating: dict) -> bool:
    return rating["grade"] >= CHECK_FROM_GRADE


def middle_grade(grades: list) -> float:
    """The middle one; of two the lower, because an honest grade rather disappoints early than late."""
    return sorted(grades)[(len(grades) - 1) // 2]


def _add(cost: float | None, more: float | None) -> float | None:
    return cost if more is None else (cost or 0) + more


def _one_run(gateway: Gateway, material: tasks.Material, ad: tuple[str, str]) -> _Runs:
    try:
        result = tasks.rate_package(gateway, material, [ad])
    except AnswerError as error:
        return _Runs((), error.cost_usd, False)
    except AiError:
        return _Runs((), None, True)
    rating = result["ratings"].get(ad[0])
    return _Runs((rating,) if rating else (), result["cost_usd"], False)


def _run(gateway: Gateway, material: tasks.Material, ad: tuple[str, str], count: int) -> _Runs:
    """The runs of one ad at the same time; the rules are cached by then, so they cost and take little."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=count) as pool:
        runs = list(pool.map(lambda _: _one_run(gateway, material, ad), range(count)))
    cost = None
    for run in runs:
        cost = _add(cost, run.cost_usd)
    return _Runs(tuple(rating for run in runs for rating in run.ratings), cost, any(run.stopped for run in runs))


def _all_suspicious_lines(ratings: tuple) -> list[str]:
    """A line that one run noticed stays noticed, whichever run counts in the end."""
    return list(dict.fromkeys(line for rating in ratings for line in rating["suspicious_lines"]))


def _look(first: dict, was_alone: bool, runs: _Runs) -> Look:
    first_grade = None if was_alone else first["grade"]
    counted = (first, *runs.ratings) if was_alone else runs.ratings
    if not runs.ratings:
        return Look(first, (), first_grade, runs.cost_usd)
    grades = tuple(rating["grade"] for rating in counted)
    middle = middle_grade(list(grades))
    chosen = next(rating for rating in counted if rating["grade"] == middle)
    lines = _all_suspicious_lines((first, *runs.ratings))
    return Look({**chosen, "suspicious_lines": lines}, grades, first_grade, runs.cost_usd)


def look_again(gateway: Gateway, material: tasks.Material, ads: list[tuple[str, str]], good: dict[str, dict]) -> dict[str, Look]:
    """`good` are the ratings to check by ad id. An ad that was alone in its package has had its first run already."""
    was_alone = len(ads) == 1
    count = RUNS - 1 if was_alone else RUNS
    looks, stopped = {}, False
    for ad in ads:
        if ad[0] not in good:
            continue
        runs = _Runs((), None, True) if stopped else _run(gateway, material, ad, count)
        stopped = runs.stopped
        looks = {**looks, ad[0]: _look(good[ad[0]], was_alone, runs)}
    return looks
