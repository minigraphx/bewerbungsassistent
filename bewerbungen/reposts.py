"""Reposts of a known job (G109, #385): when, on which portal and under which link it was advertised again.

A register entry and a discarded hit keep them as a list beside their own link, which never changes; neither does
the entry's stelle.md. Only the search writes the list, never the page.
"""
import datetime

KEY = "wieder_ausgeschrieben"
MAX_REPOSTS = 20  # the newest stay; a job advertised every week still shows when it came last
MAX_LINK = 1000
MAX_PORTAL = 200


def _checked_one(raw) -> dict:
    if not isinstance(raw, dict):
        raise ValueError(f"{KEY}: jeder Eintrag braucht datum, portal und link")
    try:
        day = datetime.date.fromisoformat(str(raw.get("datum"))).isoformat()
    except ValueError:
        raise ValueError(f"{KEY}: kein gültiges Datum ({raw.get('datum')!r})") from None
    portal = " ".join(str(raw.get("portal") or "").split())
    link = str(raw.get("link") or "").strip()
    if not portal or len(portal) > MAX_PORTAL:
        raise ValueError(f"{KEY}: portal fehlt")
    if not link.startswith("https://") or len(link) > MAX_LINK or any(c.isspace() for c in link):
        raise ValueError(f"{KEY}: link muss mit https:// beginnen")
    return {"datum": day, "portal": portal, "link": link}


def checked(raw) -> list[dict]:
    """The list as the register stores it, the newest last."""
    if not isinstance(raw, list):
        raise ValueError(f"{KEY} muss eine Liste sein")
    return [_checked_one(item) for item in raw][-MAX_REPOSTS:]


def record(hit: dict, today: datetime.date) -> dict:
    """The repost of a validated hit: its link passed `hits.checked_link` already."""
    return {"datum": today.isoformat(), "portal": hit["portal"], "link": hit["link"]}


def links(entry: dict) -> list[str]:
    return [repost["link"] for repost in entry.get(KEY) or [] if isinstance(repost, dict) and repost.get("link")]


def appended(entry: dict, new: list[dict]) -> dict:
    """The entry with the reposts it lacks; its own link and every other field stay."""
    known = {entry.get("link"), *links(entry)}
    added = []
    for repost in new:
        if repost["link"] not in known:
            added = [*added, repost]
            known = {*known, repost["link"]}
    return {**entry, KEY: [*(entry.get(KEY) or []), *added][-MAX_REPOSTS:]} if added else entry
