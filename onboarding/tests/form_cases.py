"""The shared cases of cases.json for the tests; imported by name, not from conftest (#93).

A plain `from conftest import` finds another module's conftest when several modules run in one pytest call.
"""
import copy
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
CASES = json.loads((ROOT / "tests" / "cases.json").read_text(encoding="utf-8"))


def expand(value):
    """Resolve {"$repeat": s, "times": n} placeholders used in cases.json."""
    if isinstance(value, dict) and "$repeat" in value:
        return value["$repeat"] * value["times"]
    return value


def _walk(container, keys):
    for key in keys:
        container = container[int(key)] if isinstance(container, list) else container[key]
    return container


def apply_case(case: dict) -> dict:
    """Build the bundle of a case: base plus 'set' and 'remove' operations (a new object)."""
    bundle = copy.deepcopy(CASES["bases"][case["base"]])
    for path, value in case.get("set", []):
        *parents, last = path.split(".")
        target = _walk(bundle, parents)
        if isinstance(target, list):
            target[int(last)] = expand(value)
        else:
            target[last] = expand(value)
    for path in case.get("remove", []):
        *parents, last = path.split(".")
        del _walk(bundle, parents)[last]
    return bundle


def base_bundle(track: str) -> dict:
    return copy.deepcopy(CASES["bases"][track])
