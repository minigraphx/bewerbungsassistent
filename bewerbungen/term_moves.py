"""Where a keyword runs, for the term review (G108, #383): moving it to the niches or limiting it to portals.

Neither adds nor removes a term, so under G102 such a change has one switch, which switches the whole change. The
niches run without a place; a «Nur» line limits its terms to the portals it names (G105). The app only checks and
words what the AI proposes and writes it when the person takes it over; nothing here moves a term by itself.
"""
import dataclasses

import search_plan
import search_terms

CHANGE, MERGE, NICHE, PORTALS = "change", "merge", "niche", "portals"
KINDS = (CHANGE, MERGE, NICHE, PORTALS)
MOVES = (NICHE, PORTALS)
NICHE_WORD = "zu den Nischen"
LIMIT_WORD = "nur {portals}"
NICHE_SENTENCE = "„{term}“ zu den Nischen verschieben (ohne Ort suchen)"
LIMIT_SENTENCE = "„{term}“ nur auf {portals} suchen"
MERGE_SENTENCE = "„{term}“ in „{into}“ zusammenlegen"


@dataclasses.dataclass(frozen=True)
class Placement:
    """The niches and «Nur» lines of a profile, and whether it names its keywords in lines a term can leave."""
    niches: tuple[str, ...] = ()
    limits: tuple[tuple[str, tuple[str, ...]], ...] = ()
    grouped: bool = False


def placement_of(text: str) -> Placement:
    try:
        plan = search_plan.parse(text)
    except ValueError:
        return Placement()
    return Placement(plan.niche_keywords, plan.portal_limits, search_terms.searches_keyword_lines(text))


def same(one: str, other: str) -> bool:
    return search_plan.profession_words(one) == search_plan.profession_words(other)


def _holds(terms, term: str) -> bool:
    return any(same(known, term) for known in terms)


def checked_portals(value: object, term: str, placement: Placement) -> tuple[str, ...] | None:
    """The portals as the app names them (`search_plan.PORTALS`), in the order given; None when one is unknown, when
    they are all of them (no limit) or when the term runs on exactly these already."""
    if not isinstance(value, list) or not value or not all(isinstance(name, str) for name in value):
        return None
    known = {portal.casefold(): portal for portal in search_plan.PORTALS}
    names = [known.get(name.strip().casefold()) for name in value[:len(search_plan.PORTALS)]]
    portals = tuple(dict.fromkeys(names))
    if not all(portals) or len(portals) == len(search_plan.PORTALS):
        return None
    now = next((limit for name, limit in placement.limits if same(name, term)), ())
    return None if set(now) == set(portals) else portals


def sentence(kind: str, term: str, into: str = "", portals: tuple[str, ...] = ()) -> str:
    if kind == MERGE:
        return MERGE_SENTENCE.format(term=term, into=into)
    if kind == NICHE:
        return NICHE_SENTENCE.format(term=term)
    return LIMIT_SENTENCE.format(term=term, portals=", ".join(portals))


def word(kind: str, portals: tuple[str, ...]) -> str:
    """The word on the one switch of a move, when it is on."""
    return NICHE_WORD if kind == NICHE else LIMIT_WORD.format(portals=", ".join(portals))


def moved(text: str, kind: str, term: str, portals: tuple[str, ...]) -> str:
    return search_terms.moved_to_niches(text, term) if kind == NICHE else search_terms.limited_to(text, term, portals)


def after(placement: Placement, moves: tuple[tuple[str, str, tuple[str, ...]], ...], gone: tuple[str, ...]) -> Placement:
    """The niches and limits once these moves (kind, term, portals) are made and the terms `gone` removed."""
    niches = (*placement.niches, *(term for kind, term, _ in moves if kind == NICHE and not _holds(placement.niches, term)))
    limited = {term for kind, term, _ in moves}
    kept = tuple((name, limit) for name, limit in placement.limits if not _holds(gone, name) and not _holds(limited, name))
    return Placement(niches, (*kept, *((term, portals) for kind, term, portals in moves if kind == PORTALS)),
                     placement.grouped)


def niche_view(before: Placement, now: Placement) -> list[dict]:
    return [{"begriff": term, "neu": not _holds(before.niches, term)} for term in now.niches]


def limit_view(before: Placement, now: Placement) -> list[dict]:
    """The «Nur» lines after the change, one per set of portals, each term with „neu“ if it was not limited so."""
    lines: dict[tuple[str, ...], list[dict]] = {}
    for term, portals in now.limits:
        new = (term, portals) not in before.limits
        lines = {**lines, portals: [*lines.get(portals, []), {"begriff": term, "neu": new}]}
    return [{"portale": list(portals), "begriffe": terms} for portals, terms in lines.items()]
