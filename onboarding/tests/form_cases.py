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


def known_of(case: dict) -> frozenset[str]:
    """The tags a case takes as already in the data folder (G24)."""
    return frozenset(expand(tag) for tag in case.get("known", []))


def expand_all(value):
    """expand() inside lists and objects too, for the answers a case takes as read from cv.yaml."""
    if isinstance(value, dict) and "$repeat" not in value:
        return {key: expand_all(item) for key, item in value.items()}
    if isinstance(value, list):
        return [expand_all(item) for item in value]
    return expand(value)


def loaded_of(case: dict) -> dict | None:
    """The answers a case takes as read from cv.yaml (G23); None when it gives none."""
    return expand_all(case["loaded"]) if "loaded" in case else None


def base_bundle(track: str) -> dict:
    return copy.deepcopy(CASES["bases"][track])
