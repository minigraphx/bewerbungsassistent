"""Prices and costs per call. USD per million tokens (Claude API, as of 11.2026).

Cache writes cost 1.25 times the input price, cache reads 0.1 times. The same table is in the app
(`bewerbungen/ai/usage.py`); a test keeps both equal.
"""
import dataclasses

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
    def from_dict(cls, data: object) -> "Usage":
        if not isinstance(data, dict):
            return cls()

        def number(name: str) -> int:
            value = data.get(name)
            return value if isinstance(value, int) and value >= 0 else 0
        return cls(number("input_tokens"), number("output_tokens"),
                   number("cache_creation_input_tokens"), number("cache_read_input_tokens"))

    def merge(self, other: "Usage") -> "Usage":
        """Streaming reports input in message_start and output in message_delta; keep the larger value of each."""
        return Usage(*(max(a, b) for a, b in zip(dataclasses.astuple(self), dataclasses.astuple(other))))


def cost_usd(model: str, usage: Usage) -> float:
    price_in, price_out = PRICES_USD[model]
    total = (usage.input_tokens * price_in + usage.cache_creation_input_tokens * price_in * CACHE_WRITE_FACTOR
             + usage.cache_read_input_tokens * price_in * CACHE_READ_FACTOR + usage.output_tokens * price_out)
    return round(total / PER_MILLION, 6)
