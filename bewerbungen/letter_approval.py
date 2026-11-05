"""Approving the letter of an application (MIN-369): the person has read it before it goes out.

The approval holds for exactly that text: a new draft or an edit of `anschreiben.yaml` makes it void. It is stored as a
fingerprint in `bewerbungen/<id>/freigabe.yaml`, no text, so without drafts. A letter the person uploaded as PDF is
their own and needs no approval; without a letter there is nothing to approve.

Beside it the last content review of the AI (/api/ki/pruefen) is kept for the same text (`pruefung-ki.json`), so the
page can show which statements lack evidence until the letter changes. It holds text of the letter and stays in the
data folder like the letter itself.
"""
import datetime
import hashlib
import json
import pathlib

import yaml

import unterlagen
from dateien import lies_yaml, schreibe_atomar

APPROVAL_FILE = "freigabe.yaml"
REVIEW_FILE = "pruefung-ki.json"
NOTHING_TO_APPROVE = "Es gibt noch kein Anschreiben zum Freigeben."
OWN_LETTER = "Ein eigenes Anschreiben braucht keine Freigabe."
ALREADY_SENT = "Diese Bewerbung ist schon versendet."


def fingerprint(path: pathlib.Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def _folder(daten: pathlib.Path, entry_id: str) -> pathlib.Path:
    return unterlagen.bewerbungsordner(daten, entry_id)


def state(daten: pathlib.Path, entry: dict) -> dict:
    """{needed, approved, on}: needed only for a draft that counts and has not gone out yet."""
    current = fingerprint(unterlagen.letter_source(daten, entry["id"]))
    needed = current is not None and not entry.get("versand") and unterlagen.own_letter(daten, entry) is None
    stored = lies_yaml(_folder(daten, entry["id"]) / APPROVAL_FILE, None)
    approved = isinstance(stored, dict) and stored.get("fingerabdruck") == current and current is not None
    return {"noetig": needed, "freigegeben": approved, "am": stored.get("am") if approved else None}


def missing(daten: pathlib.Path, entry: dict) -> bool:
    found = state(daten, entry)
    return found["noetig"] and not found["freigegeben"]


def approve(daten: pathlib.Path, entry: dict, today: datetime.date) -> dict:
    if entry.get("versand"):
        raise ValueError(ALREADY_SENT)
    if unterlagen.own_letter(daten, entry) is not None:
        raise ValueError(OWN_LETTER)
    current = fingerprint(unterlagen.letter_source(daten, entry["id"]))
    if current is None:
        raise ValueError(NOTHING_TO_APPROVE)
    text = yaml.safe_dump({"fingerabdruck": current, "am": today.isoformat()}, sort_keys=False)
    schreibe_atomar(_folder(daten, entry["id"]) / APPROVAL_FILE, text.encode("utf-8"))
    return state(daten, entry)


def keep_review(daten: pathlib.Path, entry_id: str, result: dict, today: datetime.date) -> None:
    current = fingerprint(unterlagen.letter_source(daten, entry_id))
    if current is None:
        return
    kept = {"fingerabdruck": current, "am": today.isoformat(),
            **{key: result.get(key) for key in ("requirements", "unsupported", "new_gaps", "model", "cost_usd")}}
    schreibe_atomar(_folder(daten, entry_id) / REVIEW_FILE, json.dumps(kept, ensure_ascii=False, indent=1).encode("utf-8"))


def review(daten: pathlib.Path, entry_id: str) -> dict | None:
    """The kept review, as long as the letter is still the one that was reviewed."""
    path = _folder(daten, entry_id) / REVIEW_FILE
    try:
        kept = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None
    except (OSError, json.JSONDecodeError):
        return None
    current = fingerprint(unterlagen.letter_source(daten, entry_id))
    if not isinstance(kept, dict) or current is None or kept.get("fingerabdruck") != current:
        return None
    return {key: value for key, value in kept.items() if key != "fingerabdruck"}
