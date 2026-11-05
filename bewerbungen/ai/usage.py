"""Cost log of AI calls in the data folder (`.ki/nutzung.jsonl`): model, tokens, cost, never any content.

One JSON line per call. Prices are USD per million tokens (Claude API, as of 11.2026); cache writes cost
1.25 times the input price, cache reads 0.1 times. The mediation (MIN-344) keeps its own log per person;
this one lets the person and the pilot see what a single application costs.
"""
import dataclasses
import datetime
import json
import pathlib
import threading

from dateien import im_ordner

LOG_PATH = ".ki/nutzung.jsonl"
_WRITE_LOCK = threading.Lock()  # calls can run side by side (ai/second_look.py)
PER_MILLION = 1_000_000
CACHE_WRITE_FACTOR = 1.25
CACHE_READ_FACTOR = 0.1
PRICES_USD = {  # model: (input, output) per million tokens
    "claude-opus-5-5": (4.0, 20.0),
    "claude-sonnet-5-5": (2.0, 10.0),
    "claude-haiku-5-5": (0.1, 0.5),
}


@dataclasses.dataclass(frozen=True)
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0

    @classmethod
    def from_response(cls, usage) -> "Usage":
        def number(name: str) -> int:
            value = getattr(usage, name, 0)
            return value if isinstance(value, int) else 0
        return cls(number("input_tokens"), number("output_tokens"),
                   number("cache_creation_input_tokens"), number("cache_read_input_tokens"))


def cost_usd(model: str, usage: Usage) -> float | None:
    """Cost of one call, or None for a model without a known price."""
    if model not in PRICES_USD:
        return None
    price_in, price_out = PRICES_USD[model]
    total = (usage.input_tokens * price_in + usage.cache_creation_input_tokens * price_in * CACHE_WRITE_FACTOR
             + usage.cache_read_input_tokens * price_in * CACHE_READ_FACTOR + usage.output_tokens * price_out)
    return round(total / PER_MILLION, 6)


class UsageLog:
    """Appends one line per call; reading sums up per task and month."""

    def __init__(self, data_dir: pathlib.Path) -> None:
        self.path = im_ordner(data_dir, LOG_PATH)

    def record(self, *, task: str, model: str, usage: Usage, fields: list[str], request_id: str | None,
               now: datetime.datetime) -> dict:
        entry = {
            "time": now.isoformat(timespec="seconds"), "task": task, "model": model,
            **dataclasses.asdict(usage), "cost_usd": cost_usd(model, usage),
            "replaced_fields": sorted(fields), "request_id": request_id,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with _WRITE_LOCK, self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry

    def entries(self) -> list[dict]:
        if not self.path.is_file():
            return []
        result = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue  # a line cut off by a crash; the others still count
            if isinstance(entry, dict):
                result.append(entry)
        return result

    def month_total_usd(self, month: str) -> float:
        """Sum of known costs in a month ("2026-11")."""
        return round(sum(e.get("cost_usd") or 0 for e in self.entries() if str(e.get("time", "")).startswith(month)), 6)
