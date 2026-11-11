"""Which term of the positive title filter lets in many poor hits (#210, G45): counted by the app, without AI or cost.

A hit „came in only through X“ when X is the one positive term its title has. The count is made against the terms the
profile has now, not stored per hit: the hint and the evidence are about the current filter, and a term the person
changed has no stale numbers. The AI gets these numbers already counted and only says what should change and why, so
every number the page shows comes from the app.
"""
import collections
import dataclasses
import re

BELOW = 4  # a grade under this does not fit well enough (Swiss grades, 6 is best)
MIN_RATED = 30
MIN_ONLY = 10
MIN_SHARE = 0.2
MIN_BELOW_SHARE = 0.7
EXAMPLES = 3


@dataclasses.dataclass(frozen=True)
class Evidence:
    term: str
    ids: tuple[str, ...]  # rated hits whose only positive term is `term`
    below: int  # of these, how many are graded below BELOW
    rated: int  # all rated hits
    examples: tuple[str, ...]  # the most frequent titles among those below

    @property
    def too_general(self) -> bool:
        return len(self.ids) >= MIN_ONLY and self.below >= MIN_BELOW_SHARE * len(self.ids)

    def as_dict(self) -> dict:
        return {"begriff": self.term, "anzahl": len(self.ids), "unter": self.below, "alle": self.rated,
                "beispiele": list(self.examples), "zu_allgemein": self.too_general}


def grade(hit: dict) -> float | None:
    value = (hit.get("bewertung") or {}).get("note") if isinstance(hit.get("bewertung"), dict) else None
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def rated(hits: list[dict]) -> list[dict]:
    return [hit for hit in hits if grade(hit) is not None]


def matching(title: str, terms: tuple[str, ...]) -> tuple[str, ...]:
    """Every term found in the title as a whole word, as the search screens titles (hits._title_match)."""
    return tuple(term for term in terms if re.search(rf"(?<!\w){re.escape(term)}(?!\w)", title or "", re.IGNORECASE))


def evidence(hits: list[dict], terms: tuple[str, ...]) -> dict[str, Evidence]:
    """Per positive term with at least one hit that came in only through it; the key is the term casefolded."""
    graded = rated(hits)
    only: dict[str, list[dict]] = collections.defaultdict(list)
    for hit in graded:
        found = matching(hit.get("stelle", ""), terms)
        if len(found) == 1:
            only[found[0]].append(hit)
    result = {}
    for term, came_in in only.items():
        below = [hit for hit in came_in if grade(hit) < BELOW]
        common = collections.Counter(hit.get("stelle", "") for hit in below).most_common(EXAMPLES)
        result[term.casefold()] = Evidence(term, tuple(hit["id"] for hit in came_in), len(below), len(graded),
                                           tuple(title for title, _ in common))
    return result


def strongest(hits: list[dict], terms: tuple[str, ...]) -> Evidence | None:
    """The one case worth a hint after a search, or None: enough rated hits, a term that alone brings many, mostly poor."""
    found = evidence(hits, terms)
    total = len(rated(hits))
    if total < MIN_RATED:
        return None
    strong = [ev for ev in found.values()
              if len(ev.ids) >= MIN_ONLY and len(ev.ids) >= MIN_SHARE * total and ev.below >= MIN_BELOW_SHARE * len(ev.ids)]
    return max(strong, key=lambda ev: (ev.below, len(ev.ids)), default=None)


def since(hits: list[dict]) -> str:
    """The day of the oldest rated hit, as the page says which hits the AI saw."""
    days = sorted(str(hit.get("gefunden_am")) for hit in rated(hits) if hit.get("gefunden_am"))
    return days[0] if days else ""
