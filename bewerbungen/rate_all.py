"""What „Alle prüfen“ will cost and take (G44, #209), before anything goes to the AI.

The estimate counts the characters that a run sends and prices them at the current prices of the model that rates
packages (`ai.usage.PRICES_USD`). It errs on the high side: every call pays the full input price, as if nothing were
cached, and half the hits are assumed to reach the grade that gets a second look (`ai.second_look`). Nothing here
reads or sends the texts themselves; only their lengths count.
"""
import dataclasses
import math

from ai import prompts, second_look, tasks
from ai.usage import PER_MILLION, PRICES_USD

MODEL = tasks.MODELS["rate_package"]
CHARS_PER_TOKEN = 3  # German text with names and numbers; rather too many tokens than too few
OUTPUT_TOKENS_PER_AD = 600  # the rating of one ad with its lists, and some room for thinking
SECOND_LOOK_SHARE = 0.5  # rather too high: a hit at grade 4 or better is rated alone three more times
TYPICAL_AD_CHARS = 4_000  # for a hit whose text the extension still has to load
PACKAGE_SECONDS = 45  # one package of ten ads, answer included
SECOND_LOOK_SECONDS = 10  # second_look: the runs of one hit go out together and take about ten seconds
SECONDS_PER_MINUTE = 60
CENT = 0.01


@dataclasses.dataclass(frozen=True)
class Estimate:
    count: int
    cost_usd: float
    minutes: int


def _tokens(chars: int) -> int:
    return chars // CHARS_PER_TOKEN + 1


def _call_usd(input_chars: int, ads: int, model: str) -> float:
    price_in, price_out = PRICES_USD[model]
    return (_tokens(input_chars) * price_in + ads * OUTPUT_TOKENS_PER_AD * price_out) / PER_MILLION


def estimate(ad_lengths: list[int | None], context_chars: int, model: str = MODEL) -> Estimate:
    """`ad_lengths`: characters of each ad to rate, None for one whose text is still missing; `context_chars`: the
    person's files and the rules, which go along with every call."""
    lengths = [min(TYPICAL_AD_CHARS if length is None else length, tasks.MAX_PACKAGE_AD_CHARS) for length in ad_lengths]
    if not lengths:
        return Estimate(0, 0.0, 0)
    fixed = context_chars + len(prompts.RATE_PACKAGE)
    packages = [lengths[i:i + tasks.PACKAGE_SIZE] for i in range(0, len(lengths), tasks.PACKAGE_SIZE)]
    cost = sum(_call_usd(fixed + sum(package), len(package), model) for package in packages)
    looked_at = math.ceil(len(lengths) * SECOND_LOOK_SHARE)
    average = sum(lengths) // len(lengths)
    cost += looked_at * second_look.RUNS * _call_usd(fixed + average, 1, model)
    seconds = len(packages) * PACKAGE_SECONDS + looked_at * SECOND_LOOK_SECONDS
    return Estimate(len(lengths), max(CENT, math.ceil(cost / CENT) * CENT), max(1, math.ceil(seconds / SECONDS_PER_MINUTE)))


def enough_for(estimate_: Estimate, left_usd: float | None) -> int | None:
    """For how many hits the budget left is enough; None when it is enough for all or there is no budget."""
    if left_usd is None or estimate_.count == 0 or left_usd >= estimate_.cost_usd:
        return None
    return max(0, math.floor(left_usd / (estimate_.cost_usd / estimate_.count)))
