"""What „Vorbefüllen“ will cost and take (G85, #271), before anything goes to the AI.

The same method as „Alle prüfen“ (G44, `bewerbungen/rate_all.py`): only lengths count, every character that would be
sent is priced at the full input price of the prefill model, as if nothing were cached, the answer at a fixed size
that errs high, rounded up to the cent and the minute. The texts are those `read_documents.collect_texts` reads on
this computer, within its limits, in the frame of the request `prefill.suggest` sends. Nothing here masks, sends or
remembers a text, and nothing creates an AI client.
"""
import paths  # noqa: F401  (makes the module bewerbungen importable)
import prefill
import rate_all
import read_documents
from ai import prompts, tasks

MODEL = tasks.MODELS["prefill"]
# rather too large: a long CV as pairs of field and value with its lists, and some room for thinking
OUTPUT_TOKENS = 8_000
BASE_SECONDS = 45  # the request with the rules and an answer of a short CV
SECONDS_PER_CHAR = 0.001  # more text read, longer answer: about a second per thousand characters


def estimate(form: dict, track: str, reading: read_documents.Reading, model: str = MODEL) -> rate_all.Estimate:
    """Count, cost in USD and minutes for the texts that would go to the AI; nothing when none would."""
    if not reading.texts:
        return rate_all.Estimate(0, 0.0, 0)
    instructions = tasks.prefill_instructions(prefill.field_guide(form, track))
    sent = len(prompts.PREFILL_RULES) + len(instructions) + len(prefill.documents_prompt(form, track, reading.texts))
    cost = rate_all.call_usd(sent, OUTPUT_TOKENS, model)
    seconds = BASE_SECONDS + sum(len(t.text) for t in reading.texts) * SECONDS_PER_CHAR
    return rate_all.Estimate(len(reading.texts), rate_all.cents_up(cost), rate_all.whole_minutes(seconds))
