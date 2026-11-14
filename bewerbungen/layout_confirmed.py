"""The person confirms a breach of the layout rules before the application goes out (G52, #237).

Each breach the check names has a key: the fingerprint of the PDF, the rule and the page. Confirming stores the key in
`bewerbungen/<id>/pruefung-bestaetigt.yaml`, no text, so without drafts. A new build changes the fingerprint, so a
confirmation holds for exactly the PDF the person looked at. Until every breach is confirmed, no form opens
(routes_apply). After sending, nothing changes any more.
"""
import hashlib
import pathlib
from collections.abc import Iterable

import yaml

import unterlagen
from dateien import lies_yaml, schreibe_atomar

FILE = "pruefung-bestaetigt.yaml"
FINGERPRINT_LENGTH = 16
UNKNOWN = "Diese Meldung gibt es nicht mehr. Bitte erneut prüfen."
ALREADY_SENT = "Diese Bewerbung ist schon versendet."


def key(pdf: pathlib.Path, rule: str, page: int, number: int = 0) -> str:
    """The key of a breach; `number` tells apart several breaches of one rule on the same page."""
    fingerprint = hashlib.sha256(pdf.read_bytes()).hexdigest()[:FINGERPRINT_LENGTH]
    return f"{fingerprint}:{rule}:{page}" + (f":{number}" if number else "")


def _path(daten: pathlib.Path, entry_id: str) -> pathlib.Path:
    return unterlagen.bewerbungsordner(daten, entry_id) / FILE


def confirmed(daten: pathlib.Path, entry_id: str) -> frozenset[str]:
    stored = lies_yaml(_path(daten, entry_id), None)
    keys = stored.get("bestaetigt") if isinstance(stored, dict) else None
    return frozenset(k for k in keys if isinstance(k, str)) if isinstance(keys, list) else frozenset()


def confirm(daten: pathlib.Path, entry: dict, wanted: str, current: Iterable[str]) -> frozenset[str]:
    """Confirms one of the current breaches; keys of PDFs that are gone are dropped on the way."""
    if entry.get("versand"):
        raise ValueError(ALREADY_SENT)
    current = set(current)
    if wanted not in current:
        raise ValueError(UNKNOWN)
    kept = sorted((confirmed(daten, entry["id"]) & current) | {wanted})
    text = yaml.safe_dump({"bestaetigt": kept}, sort_keys=False)
    schreibe_atomar(_path(daten, entry["id"]), text.encode("utf-8"))
    return frozenset(kept)
