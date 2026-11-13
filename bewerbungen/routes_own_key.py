"""Routes of the page „Einstellungen“ (MIN-348, #265): the person's own API key and what the AI costs.

The key only comes in, it never goes out again: no route answers with it, not even in part. The extension cannot
reach these routes (list in `desktop/native_host.py`).
"""
from ai import connection, own_key
from ai.usage import UsageLog
from routes_ai import run_ai
from server import json_antwort

CONFIRM_FIRST = "Bitte zuerst die Hinweise lesen und bestätigen."
OTHER_TASK = "weitere"  # a line without a readable task still counts, the page names it „Weitere“


def _by_task(entries: list[dict], month: str) -> dict:
    """Calls and known costs of the month per task, for the budget on the page (G46)."""
    result: dict[str, dict] = {}
    for entry in entries:
        if not str(entry.get("time", "")).startswith(month):
            continue
        task = entry.get("task") if isinstance(entry.get("task"), str) and entry.get("task") else OTHER_TASK
        cost = entry.get("cost_usd") if isinstance(entry.get("cost_usd"), (int, float)) else 0
        before = result.get(task, {"aufrufe": 0, "usd": 0})
        result = {**result, task: {"aufrufe": before["aufrufe"] + 1, "usd": round(before["usd"] + cost, 6)}}
    return result


def _costs(k) -> dict:
    """What this data folder has noted; the bill from Anthropic is what counts."""
    entries = UsageLog(k.daten).entries()
    month = k.heute().strftime("%Y-%m")
    total = sum(entry.get("cost_usd") or 0 for entry in entries)
    return {"monat_usd": UsageLog(k.daten).month_total_usd(month), "gesamt_usd": round(total, 6), "aufrufe": len(entries),
            "aufgaben": _by_task(entries, month)}


def _state(k) -> dict:
    return {"gesetzt": connection.own_key() is not None, "kosten": _costs(k)}


def status(k, parameter, body):
    return json_antwort(_state(k))


def save(k, parameter, body):
    if not isinstance(body, dict) or body.get("bestaetigt") is not True:
        raise ValueError(CONFIRM_FIRST)
    run_ai(lambda: own_key.save(body.get("schluessel")))
    return json_antwort(_state(k))


def remove(k, parameter, body):
    run_ai(own_key.remove)
    return json_antwort(_state(k))


GET = {"/api/schluessel": status}
POST = {"/api/schluessel/speichern": save, "/api/schluessel/entfernen": remove}
