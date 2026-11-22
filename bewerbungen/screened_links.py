"""Links of hits the app did not store, each with the fingerprint of the setting that kept it out (G110, G111).

A hit screened out once at add time, when its ad text was there, is not loaded again on the next run: the screening
counts it with its reason straight away. As soon as the setting behind it changes (the required words of a term, the
cantons and places of the region), the fingerprint no longer matches and the ad is asked for again. The file is data
the person may have edited, so only a link with a list of words stays.
"""
import pathlib

from dateien import lies_yaml, schreibe_yaml

MAX_LINKS = 3000  # links remembered per file; the oldest go first

Fingerprint = list[str]


def remembered(folder: pathlib.Path, name: str) -> dict[str, Fingerprint]:
    raw = lies_yaml(folder / name, {})
    if not isinstance(raw, dict):
        return {}
    return {link: words for link, words in raw.items()
            if isinstance(link, str) and isinstance(words, list) and all(isinstance(word, str) for word in words)}


def was_screened(known: dict[str, Fingerprint], link: str, fingerprint: Fingerprint) -> bool:
    return known.get(link) == fingerprint


def remember(folder: pathlib.Path, name: str, found: list[tuple[str, Fingerprint]]) -> None:
    """Note screened-out links with their fingerprints; the caller holds the lock of the hits."""
    if not found:
        return
    added = dict(found)
    kept = {link: words for link, words in remembered(folder, name).items() if link not in added}
    merged = list({**kept, **added}.items())[-MAX_LINKS:]
    schreibe_yaml(folder / name, dict(merged))
