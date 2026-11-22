"""Which term of the positive title filter lets in many poor hits (#210, G45): counted by the app, without AI or cost.

A hit „came in only through X“ when X is the one positive term its title has. The count is made against the terms the
profile has now, not stored per hit: the hint and the evidence are about the current filter, and a term the person
changed has no stale numbers. The AI gets these numbers already counted and only says what should change and why, so
every number the page shows comes from the app.

Per keyword the app also counts over the last runs (G108, #383), from the same counts as „Was die Suche bringt“
(`search_yield`), and marks a keyword «ohne Ertrag» or «überlappend»; the marks only ever lead to a proposal of the AI.
"""
import collections
import dataclasses

import search_yield
import title_examples
import title_filter
from query_log import KEPT_RUNS, UNRELATED

BELOW = 4  # a grade under this does not fit well enough (Swiss grades, 6 is best)
NEEDED_RUNS = KEPT_RUNS  # the marks need as many runs as the log keeps
MAX_SCREENED_TITLES = 30  # example titles the title filter kept out, at most 3 per term (title_examples)
WITHOUT_YIELD, OVERLAPPING = "ohne_ertrag", "ueberlappend"
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
    """Every term found in the title as the search screens titles (title_filter, G104)."""
    return title_filter.all_matches(title or "", terms)


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


# Per keyword over the last runs (G108, #383), from the counts of „Was die Suche bringt“ (search_yield, G103).


@dataclasses.dataclass(frozen=True)
class KeywordCount:
    term: str
    searches: int  # in the last runs, every portal and place
    per_run: int
    raw: int  # what the result lists of the portals held
    screened: int  # of these, titles the title filter kept out
    listed: int  # new hits in the list that a query of this keyword found
    only_here: int  # of these, hits no other keyword found
    good: int  # of the listed, graded GOOD or better
    runs: int  # runs in which the keyword was searched
    empty_runs: int  # of these, runs in which its result lists were all empty
    covered_by: str | None  # the other keyword that found most of its hits
    all_covered: bool  # that one keyword found every one of them
    mark: str | None
    unrelated: int = 0  # of the raw, hits without a required word of the keyword (G110), apart from `screened`

    def as_dict(self) -> dict:
        # «aussortiert» on the page counts both reasons; «ohne_pflichtbezug» names the second when there is any
        unrelated = {UNRELATED: self.unrelated} if self.unrelated else {}
        return {"begriff": self.term, "suchen": self.searches, "suchen_pro_lauf": self.per_run,
                "treffer_portale": self.raw, "aussortiert": self.screened + self.unrelated, **unrelated,
                "treffer": self.listed, "nur_hier": self.only_here, "ab_note_4": self.good, "laeufe": self.runs,
                "laeufe_ohne_treffer": self.empty_runs, "auch_ueber": self.covered_by, "alle_ueber": self.all_covered,
                "marke": self.mark}


@dataclasses.dataclass(frozen=True)
class Counted:
    runs: int
    entries: tuple[KeywordCount, ...]
    niches: tuple[KeywordCount, ...] = ()  # only for the page's table (#393): the AI gets the keywords' numbers alone

    @property
    def enough(self) -> bool:
        return self.runs >= NEEDED_RUNS

    def mark_of(self, term: str) -> str | None:
        return next((entry.mark for entry in self.entries if search_yield.same_term(entry.term, term)), None)

    def marked(self, mark: str) -> tuple[str, ...]:
        return tuple(entry.term for entry in self.entries if entry.mark == mark)

    def as_dict(self) -> dict:
        return {"laeufe": self.runs, "noetig": NEEDED_RUNS, "genug": self.enough,
                "begriffe": [entry.as_dict() for entry in self.entries],
                "nischen": [entry.as_dict() for entry in self.niches]}


def _mark(found: dict, shared: dict, runs: int) -> str | None:
    """«ohne Ertrag» as Suche einstellen marks it (`search_yield`: no hit past the title filter); «überlappend»: every
    hit also came through another keyword. Only for a keyword searched in each of the last NEEDED_RUNS runs."""
    if runs < NEEDED_RUNS or shared["laeufe"] < NEEDED_RUNS:
        return None
    if found["ohne_ertrag"]:
        return WITHOUT_YIELD
    return OVERLAPPING if found["neu"] and not shared["nur_hier"] else None


def _keyword_count(found: dict, shared: dict, runs: int, markable: bool) -> KeywordCount:
    top = shared["auch_ueber"][0] if shared["auch_ueber"] else None
    return KeywordCount(found["begriff"], found["suchen"], round(found["suchen"] / shared["laeufe"]) if shared["laeufe"] else 0,
                        found["treffer"], found["aussortiert"], found["neu"], shared["nur_hier"], found["ab_note_4"],
                        shared["laeufe"], shared["laeufe_ohne_treffer"], top["begriff"] if top else None,
                        bool(top and top["anzahl"] == found["neu"]), _mark(found, shared, runs) if markable else None,
                        found.get(UNRELATED, 0))


def keyword_counts(runs: list[dict], hits: list[dict], terms: tuple[str, ...], niches: tuple[str, ...] = ()) -> Counted:
    """Per keyword of the list, in its order, what the last runs brought and the mark the app gives it; then the niches
    not also in the list, counted alike (#393). A niche is never marked: the review moves only keywords, so its mark
    would lead to no proposal."""
    own = tuple(niche for niche in niches if not any(search_yield.same_term(niche, term) for term in terms))
    names = [*terms, *own]
    found = search_yield.summary(runs, hits, names, with_places=False)["begriffe"]
    shared = search_yield.overlap(runs, hits, names)
    counts = tuple(_keyword_count(one, other, len(runs), index < len(terms))
                   for index, (one, other) in enumerate(zip(found, shared)))
    return Counted(len(runs), counts[:len(terms)], counts[len(terms):])


def screened_titles(runs: list[dict]) -> list[tuple[str | None, int, tuple[str, ...]]]:
    """What the title filter kept out in the last run (G104): per exclusion its count and example titles, then the
    titles without a positive term (None); at most MAX_SCREENED_TITLES examples in all."""
    tally = title_examples.closed(runs[-1].get(title_examples.KEY) if runs else None)
    groups = [*((term, bucket) for term, bucket in tally[title_examples.EXCLUDE].items()),
              (None, tally[title_examples.WITHOUT])]
    result, room = [], MAX_SCREENED_TITLES
    for term, bucket in groups:
        if bucket["anzahl"]:
            examples = tuple(bucket["beispiele"][:room])
            result, room = [*result, (term, bucket["anzahl"], examples)], room - len(examples)
    return result
