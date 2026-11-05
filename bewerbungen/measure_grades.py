"""How much does the AI's grade for the same ad vary (MIN-389)? Rates ads one by one and in packages, stores nothing in
hits or register. Costs real money, so it only runs with --ja. The output names no company: the ids stay in the file under
`.ki/` of the data folder, which is not in Git.

  ../.venv/bin/python measure_grades.py <datenordner> [--anzahl 8] [--runden 4] [--id <bewerbung>] [--hoechstens 3] --ja
"""
import argparse
import dataclasses
import datetime
import json
import pathlib
import random
import string
import sys
from statistics import mean

from ai import tasks
from ai.connection import find_connection, make_client
from ai.errors import AiError, AnswerError
from dateien import schreibe_atomar
from hits import Hits

LIMIT_REACHED = "Kostengrenze erreicht."
NOTHING_TO_MEASURE = "Keine bewerteten Treffer mit Inseratstext gefunden."
ROUGH_USD_PER_RATING = 0.03  # only for the plan; the run counts what it really costs
SHUFFLE_SEED = 389


@dataclasses.dataclass(frozen=True)
class Measurement:
    single: dict[str, list[float]]
    package: dict[str, list[float]]
    cost_usd: float
    stopped: str


def _resolve(hits: list[dict], wanted: str) -> str:
    for hit in hits:
        if wanted in (hit["id"], hit.get("bewerbung_id")):
            return hit["id"]
    raise ValueError(f"Kein Treffer zu {wanted}.")


def choose(store: Hits, count: int, wanted: tuple[str, ...] | list[str] = ()) -> list[str]:
    """Named ads first, then rated ads spread evenly over their grades: variation may differ between good and bad fits."""
    hits = store.all()
    named = [_resolve(hits, item) for item in wanted]
    rated = sorted((h for h in hits if (h.get("bewertung") or {}).get("note") and h["id"] not in named
                    and store.text(h["id"]).strip()), key=lambda h: (h["bewertung"]["note"], h["id"]))
    room = max(count - len(named), 0)
    if room >= len(rated):
        return [*named, *(h["id"] for h in rated)]
    if room == 1:
        return [*named, rated[len(rated) // 2]["id"]]
    steps = [round(n * (len(rated) - 1) / (room - 1)) for n in range(room)] if room else []
    return [*named, *(rated[step]["id"] for step in steps)]


def _with_rating(found: dict[str, list[float]], ad_id: str, grade: float) -> dict[str, list[float]]:
    return {**found, ad_id: [*found.get(ad_id, []), grade]}


def _one_call(gateway, material, ads: dict[str, str], step: tuple[str, str | list[str]]) -> tuple[dict[str, float], float]:
    kind, target = step
    if kind == "single":
        result = tasks.rate_match(gateway, material, ads[target])
        return {target: result["grade"]}, result["cost_usd"] or 0
    result = tasks.rate_package(gateway, material, [(ad_id, ads[ad_id]) for ad_id in target])
    return {ad_id: rating["grade"] for ad_id, rating in result["ratings"].items()}, result["cost_usd"] or 0


def _steps(ids: list[str], rounds: int) -> list[tuple[str, str | list[str]]]:
    """Every round all ads alone, then all together in another order: neighbours in a package may matter."""
    shuffler = random.Random(SHUFFLE_SEED)
    steps = []
    for _ in range(rounds):
        steps += [("single", ad_id) for ad_id in ids]
        steps.append(("package", shuffler.sample(ids, len(ids))))
    return steps


def measure(gateway, material, store: Hits, ids: list[str], rounds: int, cost_limit: float, progress=lambda text: None) -> Measurement:
    ads = {ad_id: store.ad_text(ad_id) for ad_id in ids}
    single, package, cost, stopped = {}, {}, 0.0, ""
    steps = _steps(ids, rounds)
    for number, step in enumerate(steps, 1):
        try:
            grades, spent = _one_call(gateway, material, ads, step)
        except AnswerError as error:  # one unusable answer says nothing about the others
            cost += error.cost_usd or 0
            progress(f"{number}/{len(steps)}: Antwort nicht verwendbar")
            continue
        except AiError as error:
            stopped = str(error)
            break
        cost += spent
        for ad_id, grade in grades.items():
            if step[0] == "single":
                single = _with_rating(single, ad_id, grade)
            else:
                package = _with_rating(package, ad_id, grade)
        progress(f"{number}/{len(steps)}: bisher {cost:.2f} USD")
        if cost >= cost_limit and number < len(steps):
            stopped = LIMIT_REACHED
            break
    return Measurement(single, package, cost, stopped)


def _span(grades: list[float]) -> float:
    return max(grades) - min(grades) if grades else 0


def _grades(grades: list[float]) -> str:
    return " ".join(f"{grade:g}" for grade in grades) or "–"


def _shift(found: Measurement) -> float | None:
    both = [ad for ad in found.single if found.package.get(ad)]
    return mean(mean(found.package[ad]) - mean(found.single[ad]) for ad in both) if both else None


def report(found: Measurement, stored: dict[str, float | None]) -> str:
    """Letters instead of companies, so the output can go into a chat."""
    ids = list(dict.fromkeys([*found.single, *found.package]))
    rows = [f"{string.ascii_uppercase[n % 26]}  bisher {stored.get(ad) or '–'}  einzeln: {_grades(found.single.get(ad, []))}"
            f"  Paket: {_grades(found.package.get(ad, []))}" for n, ad in enumerate(ids)]
    singles, packages = [v for v in found.single.values() if v], [v for v in found.package.values() if v]
    shift = _shift(found)
    summary = [
        f"Grösste Spanne einzeln: {max(map(_span, singles), default=0):.1f}, im Schnitt {mean(map(_span, singles)) if singles else 0:.2f}",
        f"Grösste Spanne Paket: {max(map(_span, packages), default=0):.1f}, im Schnitt {mean(map(_span, packages)) if packages else 0:.2f}",
        f"Einzeln ab 1 Note Spanne: {sum(_span(v) >= 1 for v in singles)} von {len(singles)}",
        f"Paket ab 1 Note Spanne: {sum(_span(v) >= 1 for v in packages)} von {len(packages)}",
        f"Paket minus einzeln im Schnitt: {shift:+.2f}" if shift is not None else "Paket minus einzeln: nicht messbar",
        f"Kosten: {found.cost_usd:.2f} USD",
    ]
    return "\n".join([*rows, "", *summary, *([f"Abgebrochen: {found.stopped}"] if found.stopped else [])])


def _save(data_dir: pathlib.Path, found: Measurement, stored: dict, now: datetime.datetime) -> pathlib.Path:
    path = data_dir / ".ki" / f"notenmessung-{now:%Y%m%d-%H%M%S}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    content = {"einzeln": found.single, "paket": found.package, "bisher": stored, "kosten_usd": found.cost_usd, "abgebrochen": found.stopped}
    schreibe_atomar(path, json.dumps(content, ensure_ascii=False, indent=1).encode("utf-8"))
    return path


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Misst, wie stark die Note der KI für dasselbe Inserat schwankt.")
    parser.add_argument("datenordner", type=pathlib.Path)
    parser.add_argument("--anzahl", type=int, default=8, help="Anzahl Inserate, höchstens eine Paketgrösse")
    parser.add_argument("--runden", type=int, default=4)
    parser.add_argument("--id", action="append", default=[], help="Bewerbung oder Treffer, der sicher dabei sein soll")
    parser.add_argument("--hoechstens", type=float, default=3.0, help="Kostengrenze in USD")
    parser.add_argument("--ja", action="store_true", help="wirklich laufen lassen, kostet Geld")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if not 2 <= args.anzahl <= tasks.PACKAGE_SIZE or args.runden < 1:
        print(f"--anzahl muss zwischen 2 und {tasks.PACKAGE_SIZE} liegen, --runden mindestens 1.", file=sys.stderr)
        return 2
    store = Hits(args.datenordner)
    try:
        ids = choose(store, args.anzahl, args.id)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 2
    if len(ids) < 2:
        print(NOTHING_TO_MEASURE, file=sys.stderr)
        return 2
    rough = args.runden * (len(ids) + len(ids) / 2) * ROUGH_USD_PER_RATING
    print(f"{len(ids)} Inserate, {args.runden} Runden: {args.runden * (len(ids) + 1)} KI-Aufrufe, grob {rough:.2f} USD, "
          f"höchstens {args.hoechstens:.2f} USD. Treffer und Register bleiben unverändert.")
    if not args.ja:
        print("Zum Starten denselben Befehl mit --ja.")
        return 0
    try:
        material = tasks.load_material(args.datenordner)
        gateway = tasks.make_gateway(args.datenordner, material, make_client(find_connection()))
    except AiError as error:
        print(error, file=sys.stderr)
        return 2
    found = measure(gateway, material, store, ids, args.runden, args.hoechstens, progress=lambda text: print(text, flush=True))
    stored = {ad_id: (store.get(ad_id).get("bewertung") or {}).get("note") for ad_id in ids}
    print(report(found, stored))
    print(f"Mit den Kennungen gespeichert: {_save(args.datenordner, found, stored, datetime.datetime.now())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
