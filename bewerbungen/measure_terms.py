"""Which model with which effort proposes search terms best (#274)? Runs the review of „Suchbegriffe prüfen“ with the
person's own data for each combination, the same text each time, and changes nothing in the search profile. Costs real
money, so it only runs with --ja. The output gives numbers only; the proposals themselves, with the person's terms, stay
in a file under `.ki/` of the data folder, which is not in Git, to be read side by side.

Thinking counts toward max_tokens, so every run gets the same generous room: a cut-off answer is then the model's doing.

  ../.venv/bin/python measure_terms.py <datenordner> [--modell claude-sonnet-5-5:medium ...] [--runden 2] [--hoechstens 1] --ja
"""
import argparse
import dataclasses
import datetime
import json
import pathlib
import sys
import time
from statistics import mean

import preferences
import search_plan
import term_changes
from ai import consent, tasks, term_review
from ai.connection import find_connection, make_client
from ai.errors import AiError, AnswerError
from ai.usage import PRICES_USD
from dateien import schreibe_atomar
from hits import Hits

EFFORTS = ("low", "medium", "high", "xhigh", "max")
COMBINATIONS = (("claude-haiku-5-5", "medium"), ("claude-haiku-5-5", "high"),
                ("claude-sonnet-5-5", "low"), ("claude-sonnet-5-5", "medium"))
ROOM = 16_000  # the most the mediation passes on
ROUGH_USD_PER_RUN = 0.03  # only for the plan; the run counts what it really costs
LIMIT_REACHED = "Kostengrenze erreicht."
NO_PROFILE = "Im Datenordner fehlt das Suchprofil."
WRONG_COMBINATION = "Modell und Effort als modell:effort angeben, etwa claude-sonnet-5-5:medium."


@dataclasses.dataclass(frozen=True)
class Run:
    model: str
    effort: str
    seconds: float
    cost_usd: float
    output_tokens: int | None = None
    cut_off: bool = False
    proposal: dict | None = None
    kept: int = 0
    replaced: int = 0  # changes that take something out and put something more precise in


@dataclasses.dataclass(frozen=True)
class Measurement:
    runs: tuple[Run, ...]
    stopped: str


def combination(text: str) -> tuple[str, str]:
    model, _, effort = text.partition(":")
    if model not in PRICES_USD or effort not in EFFORTS:
        raise ValueError(WRONG_COMBINATION)
    return model, effort


def _proposal(result: dict) -> dict:
    return {"summary": result["summary"], "changes": [dataclasses.asdict(change) for change in result["changes"]]}


def _one_run(review, model: str, effort: str) -> Run:
    started = time.monotonic()
    try:
        result = review(model, effort)
    except AnswerError as error:  # a cut-off answer is a result of this combination, not the end of the run
        return Run(model, effort, time.monotonic() - started, error.cost_usd or 0, cut_off=True)
    changes = result["changes"]
    return Run(model, effort, time.monotonic() - started, result["cost_usd"] or 0, result["output_tokens"],
               proposal=_proposal(result), kept=len(changes),
               replaced=sum(bool(change.remove) and bool(change.add) for change in changes))


def _reviewer(data_dir: pathlib.Path, client):
    text = (data_dir / search_plan.PROFILE).read_text(encoding="utf-8")
    current, hits = term_changes.terms_of(text), Hits(data_dir).all()
    material = tasks.load_material(data_dir, partial=True)
    gateway = tasks.make_gateway(data_dir, material, client)
    request_text = term_review.prompt(current, hits)
    avoided = term_changes.avoided_words(text)
    return lambda model, effort: term_review.review(gateway, material, current, avoided, request_text, model, effort, ROOM)


def measure(data_dir: pathlib.Path, combinations, rounds: int, cost_limit: float, client=None,
            progress=lambda text: None) -> Measurement:
    review = _reviewer(data_dir, client or make_client(find_connection()))
    runs, cost = [], 0.0
    planned = [(model, effort) for model, effort in combinations for _ in range(rounds)]
    for number, (model, effort) in enumerate(planned, 1):
        try:
            run = _one_run(review, model, effort)
        except AiError as error:
            return Measurement(tuple(runs), str(error))
        runs.append(run)
        cost += run.cost_usd
        progress(f"{number}/{len(planned)}: {model} {effort}, bisher {cost:.2f} USD")
        if cost >= cost_limit and number < len(planned):
            return Measurement(tuple(runs), LIMIT_REACHED)
    return Measurement(tuple(runs), "")


def _average(values: list, form: str) -> str:
    return format(mean(values), form) if values else "–"


def report(found: Measurement) -> str:
    """Numbers per combination; which proposal is better, a person judges from the saved file."""
    combos = list(dict.fromkeys((run.model, run.effort) for run in found.runs))
    rows = []
    for model, effort in combos:
        runs = [run for run in found.runs if (run.model, run.effort) == (model, effort)]
        answered = [run for run in runs if not run.cut_off]
        rows.append(f"{model} {effort}: abgebrochen {len(runs) - len(answered)} von {len(runs)}"
                    f" · Tokens {_average([r.output_tokens for r in answered if r.output_tokens is not None], '.0f')}"
                    f" · Änderungen {_average([r.kept for r in answered], '.1f')}"
                    f" · davon ersetzt {_average([r.replaced for r in answered], '.1f')}"
                    f" · {_average([r.seconds for r in runs], '.0f')} s"
                    f" · {_average([r.cost_usd for r in runs], '.4f')} USD")
    total = sum(run.cost_usd for run in found.runs)
    return "\n".join([*rows, "", f"Kosten: {total:.2f} USD", *([f"Abgebrochen: {found.stopped}"] if found.stopped else [])])


def _save(data_dir: pathlib.Path, found: Measurement, now: datetime.datetime) -> pathlib.Path:
    path = data_dir / ".ki" / f"begriffsmessung-{now:%Y%m%d-%H%M%S}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    runs = [{"modell": run.model, "effort": run.effort, "sekunden": round(run.seconds, 1), "kosten_usd": run.cost_usd,
             "ausgabe_tokens": run.output_tokens, "abgeschnitten": run.cut_off, "vorschlag": run.proposal}
            for run in found.runs]
    schreibe_atomar(path, json.dumps({"laeufe": runs, "abgebrochen": found.stopped}, ensure_ascii=False, indent=1).encode("utf-8"))
    return path


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Vergleicht Modelle und Effort beim Prüfen der Suchbegriffe.")
    parser.add_argument("datenordner", type=pathlib.Path)
    parser.add_argument("--modell", action="append", default=[], help="modell:effort, mehrfach; ohne Angabe die üblichen vier")
    parser.add_argument("--runden", type=int, default=2, help="Läufe pro Kombination")
    parser.add_argument("--hoechstens", type=float, default=1.0, help="Kostengrenze in USD")
    parser.add_argument("--ja", action="store_true", help="wirklich laufen lassen, kostet Geld")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        combinations = [combination(text) for text in args.modell] or list(COMBINATIONS)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 2
    if args.runden < 1 or not (args.datenordner / search_plan.PROFILE).is_file():
        print(NO_PROFILE if args.runden >= 1 else "--runden mindestens 1.", file=sys.stderr)
        return 2
    calls = args.runden * len(combinations)
    print(f"{len(combinations)} Kombinationen, {args.runden} Runden: {calls} KI-Aufrufe, grob {calls * ROUGH_USD_PER_RUN:.2f} USD, "
          f"höchstens {args.hoechstens:.2f} USD. Das Suchprofil bleibt unverändert.")
    if not args.ja:
        print("Zum Starten denselben Befehl mit --ja.")
        return 0
    try:
        consent.require(args.datenordner, preferences.strictest_kind(args.datenordner))
        client = make_client(find_connection())
        found = measure(args.datenordner, combinations, args.runden, args.hoechstens, client,
                        progress=lambda text: print(text, flush=True))
    except (AiError, ValueError) as error:
        print(error, file=sys.stderr)
        return 2
    print(report(found))
    print(f"Vorschläge zum Vergleichen gespeichert: {_save(args.datenordner, found, datetime.datetime.now())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
