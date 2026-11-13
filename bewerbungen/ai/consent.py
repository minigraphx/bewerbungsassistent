"""Consent before the first AI call (MIN-401).

The app is for adults: with the search for an apprenticeship a parent or legal guardian sets it up and confirms that.
The kind of search decides the wording, there is no question about age. What was agreed to stays in the data folder of
the person with version, kind and time; a new wording or another kind of search asks again. A confirmation does not
prove anything about the person, it holds because the pilot runs on personal invitations to adults.
"""
import datetime
import json
import os
import pathlib

import search_plan
from ai.errors import SetupNeeded
from dateien import schreibe_atomar

FILE = "einwilligung.json"
VERSION = "2026-11"
PAGE_VARIABLE = "BEWERBUNGSBEGLEITER_DATENSCHUTZ_URL"
MISSING = "Vor der ersten KI-Nutzung braucht es die Einwilligung: unter „KI einrichten“."
STALE_PAGE = "Der Text hat sich geändert. Bitte die Seite neu laden und nochmals lesen."
_SENDING = ("Ich habe die Datenschutzerklärung gelesen und bin einverstanden, dass Texte aus {whose} Unterlagen für die "
            "KI-Funktionen an Anthropic gehen, auch in die USA. Sie können indirekt auf {hints} hindeuten.")
WORDING = {
    search_plan.KIND_JOB: "Ich bin mindestens 18 Jahre alt. " + _SENDING.format(
        whose="meinen", hints="eine Arbeitslosigkeit oder auf Angaben aus Zeugnissen"),
    search_plan.KIND_APPRENTICESHIP: (
        "Ich bin Elternteil oder gesetzliche Vertretung und mindestens 18 Jahre alt. Ich richte die App für die "
        "jugendliche Person ein und habe mit ihr besprochen, was an die KI geht. ") + _SENDING.format(
        whose="ihren", hints="Angaben aus Zeugnissen"),
}


def _saved(data_dir: pathlib.Path) -> dict:
    try:
        saved = json.loads((data_dir / FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return saved if isinstance(saved, dict) else {}


def is_given(data_dir: pathlib.Path, kind: str) -> bool:
    saved = _saved(data_dir)
    return saved.get("fassung") == VERSION and saved.get("art") == kind


def require(data_dir: pathlib.Path, kind: str) -> None:
    if not is_given(data_dir, kind):
        raise SetupNeeded(MISSING)


def give(data_dir: pathlib.Path, kind: str, version: str, now: datetime.datetime) -> None:
    """`version` is what the page showed: agreeing to a text it no longer has does not count."""
    if version != VERSION:
        raise ValueError(STALE_PAGE)
    entry = {"fassung": VERSION, "art": kind, "zeit": now.isoformat(timespec="seconds")}
    schreibe_atomar(data_dir / FILE, json.dumps(entry, ensure_ascii=False).encode("utf-8"))


def withdraw(data_dir: pathlib.Path) -> None:
    (data_dir / FILE).unlink(missing_ok=True)


def receipt(data_dir: pathlib.Path) -> str:
    """Version and kind for the mediation, so that the operator can show the consent; no names."""
    saved = _saved(data_dir)
    return f"{saved['fassung']} {saved['art']}" if saved.get("fassung") and saved.get("art") else ""


def _page_link() -> str:
    link = os.environ.get(PAGE_VARIABLE, "")
    return link if link.startswith("https://") else ""


def state(data_dir: pathlib.Path, kind: str) -> dict:
    return {"erteilt": is_given(data_dir, kind), "fassung": VERSION, "text": WORDING[kind], "link": _page_link()}
