"""What a point under „Was fehlt oder unsicher ist“ would add as an exclusion (#224, G83), without AI.

A word of the point that the hit's title has goes to the title filter, so the search keeps such titles away; the
words the search looks for (Titelfilter Positiv), fillers and words already excluded never do. Any other point goes,
shortened, to the exclusions under Suchrichtungen, which the rating reads with the profile. The profile keeps a list
as one line split at commas, so a proposal ends before the first comma or semicolon.
"""
import dataclasses
import re

import dismissed_words
import title_filter

TITLE = "titel_ausschluss"
AD = "ausschluss"
KINDS = (TITLE, AD)
PLACES = {TITLE: "Im Titel", AD: "Im Inserat"}  # the words of the card Was Sie nicht sehen wollen
SEPARATOR = re.compile(r"[,;]")
TRAILING = ".:!?-– "


@dataclasses.dataclass(frozen=True)
class Proposal:
    kind: str  # TITLE or AD
    value: str


def _title_word(point: str, title: str, blocked: frozenset[str]) -> str | None:
    return next((word for word in dismissed_words.WORD.findall(point)
                 if word.casefold() not in blocked and dismissed_words.has_word(title, word)), None)


def shortened(point: str, chars: int) -> str:
    """The point up to its first comma or semicolon, cut at a space to fit the field."""
    first = " ".join(SEPARATOR.split(point, maxsplit=1)[0].split()).rstrip(TRAILING)
    if len(first) <= chars:
        return first
    cut = first[:chars + 1].rsplit(" ", 1)[0] if " " in first[:chars + 1] else first[:chars]
    return cut.rstrip(TRAILING)


def _has_phrase(point: str, entry: str) -> bool:
    phrase = title_filter.bare(entry)
    return bool(phrase) and re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", point, re.IGNORECASE) is not None


def is_excluded(point: str, entries: list[str]) -> bool:
    """Whether an entry of the title filter or the exclusions stands in the point as a whole word or phrase. A point
    speaks of the ad, not of its title, so a title term counts only whole here, without its «(ganzes Wort)»."""
    return any(_has_phrase(point, entry) for entry in entries)


def propose(point: str, title: str, positive: tuple[str, ...], excluded_titles: tuple[str, ...],
            chars: int) -> Proposal:
    """A title word if the title has one worth excluding, else the shortened point for the exclusions."""
    word = _title_word(point, title, dismissed_words.blocked(positive, excluded_titles))
    return Proposal(TITLE, word) if word else Proposal(AD, shortened(point, chars))
