"""A title word that many dismissed hits share, proposed as a title exclusion on Suche einstellen (#225, G66).

Counted by the app, without AI or cost. A word counts for a hit as the search's title filter would catch it, also as
the start or end of a word (title_filter, G104), so the numbers the page shows are the hits the exclusion would really
keep away; an exclusion marked «(ganzes Wort)» catches only the whole word.
Hits the current exclusion already catches do not count, and a word of the positive filter is never proposed: excluding
it would end the search the person set up. The proposal only names; the profile changes when the person clicks.
"""
import collections
import dataclasses
import re

import title_filter
from hits import TITLE_FILLERS

DISMISSED = "verworfen"
MIN_DISMISSED = 3
MIN_LETTERS = 4  # shorter pieces are mostly „AG“, „m/w“ or „IT“, too vague to exclude
MAX_PROPOSALS = 5
WORD = re.compile(rf"[^\W\d_]{{{MIN_LETTERS},}}")


@dataclasses.dataclass(frozen=True)
class Proposal:
    word: str  # the spelling most dismissed titles use
    ids: tuple[str, ...]  # dismissed hits with the word in the title
    others: int  # hits not dismissed that have it too

    def as_dict(self) -> dict:
        return {"wort": self.word, "ids": list(self.ids), "verworfen": len(self.ids), "andere": self.others}


def has_word(title: str, word: str) -> bool:
    """As the search screens titles: at the start or end of a word, or whole as its marker or length says."""
    return title_filter.matches(title or "", word)


def _caught(title: str, excluded: tuple[str, ...]) -> bool:
    return any(has_word(title, term) for term in excluded)


def blocked(positive: tuple[str, ...], excluded: tuple[str, ...]) -> frozenset[str]:
    """Words never proposed: fillers, every word of a positive term and the words already excluded."""
    words = {word.casefold() for term in (*positive, *excluded) for word in WORD.findall(title_filter.bare(term))}
    return frozenset(words | TITLE_FILLERS)


def _spellings(hits: list[dict], blocked: frozenset[str]) -> dict[str, collections.Counter]:
    """Per casefolded word, how the dismissed titles write it; a title counts each word once."""
    found: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for hit in hits:
        for word in dict.fromkeys(WORD.findall(hit.get("stelle", ""))):
            if word.casefold() not in blocked:
                found[word.casefold()][word] += 1
    return found


def with_word(hits: list[dict], word: str) -> tuple[str, ...]:
    """The dismissed hits behind „Die Stellen ansehen“."""
    return tuple(hit["id"] for hit in hits if hit.get("zustand") == DISMISSED and has_word(hit.get("stelle", ""), word))


def proposals(hits: list[dict], positive: tuple[str, ...], excluded: tuple[str, ...],
              hidden: dict[str, int]) -> list[Proposal]:
    """The words worth a proposal, most dismissed hits first; a word put aside returns once more hits have it."""
    open_hits = [hit for hit in hits if not _caught(hit.get("stelle", ""), excluded)]
    dismissed = [hit for hit in open_hits if hit.get("zustand") == DISMISSED]
    kept = [hit for hit in open_hits if hit.get("zustand") != DISMISSED]
    found = []
    for key, spellings in _spellings(dismissed, blocked(positive, excluded)).items():
        word = spellings.most_common(1)[0][0]
        ids = with_word(dismissed, word)
        if len(ids) >= MIN_DISMISSED and len(ids) > hidden.get(key, 0):
            others = sum(1 for hit in kept if has_word(hit.get("stelle", ""), word))
            found.append(Proposal(word, ids, others))
    return sorted(found, key=lambda p: (-len(p.ids), p.others, p.word.casefold()))[:MAX_PROPOSALS]
