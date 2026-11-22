"""Terms the search runs twice, or that a broader term already covers, for «Doppelt gesucht» (G106, #377).

A duplicate is one term (`search_terms.key`: the same words) in two lines under Keywords that the plan reads: the
core list, the other named lines with the «Nur» lines (G105) and the niches. An overlap is a term whose words all
stand in another term of the same list, while the broader one runs on at least the same portals; a niche and a
keyword never overlap, since the niches run without a place. What each costs is what the next run would save without
it, counted as the estimate of the page counts (`search_stages.size` of the chosen portals). The app only proposes:
nothing here writes, and a removal is offered only if the plan can still search afterwards.
Only job profiles: an apprenticeship profile names professions, one per line.
"""
import dataclasses
import itertools

import required_words
import search_plan
import search_stages
import search_terms
import term_pair_texts as words
from hits import QUERIES
from term_pair_texts import CORE, GROUP, LIMIT, NICHE

DUPLICATE = "doppelt"
OVERLAP = "enthalten"
PREFIXES = (f"{DUPLICATE}:", f"{OVERLAP}:")
MAX_ID = 600
GONE = "Das hat sich inzwischen geändert. Die Liste ist neu geladen."
NO_UNDO = "Rückgängig geht hier nicht mehr. Bitte den Begriff neu aufnehmen."


@dataclasses.dataclass(frozen=True)
class Line:
    """A line under Keywords that the plan searches, `id` its label with the number of lines before it so labelled."""
    id: str
    label: str
    kind: str
    index: int
    terms: tuple[str, ...]
    portals: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True)
class Option:
    side: str
    term: str
    line: Line | None  # None: the term leaves every line of the list, as Entfernen in the list does
    after: str
    offered: bool  # False when the plan could not search afterwards, e.g. without any keyword


@dataclasses.dataclass(frozen=True)
class Candidate:
    id: str
    kind: str
    term: str
    lines: tuple[Line, ...]  # a duplicate: the two lines; an overlap: none
    broader: str
    options: tuple[Option, ...]


@dataclasses.dataclass(frozen=True)
class Removal:
    text: str
    term: str
    line: str | None
    done: str
    back: str


def searches(text: str, postal_code: str | None, switched_off: list[str] | None) -> int | None:
    """The searches of one run as the page estimates them; None if the plan cannot search with this profile."""
    try:
        plan = search_plan.parse(text, postal_code)
    except ValueError:
        return None
    return search_stages.size(search_plan.chosen(plan, switched_off).as_dict())["suchen"]


def _terms(value: str) -> tuple[str, ...]:
    """The terms of a line as the plan reads them, each once."""
    names = (" ".join(term.replace("`", "").split())[:search_plan.MAX_VALUE] for term in search_plan.split_terms(value))
    found: dict[str, str] = {}
    for name in filter(None, names):
        key = search_terms.key(name) or name.casefold()
        found = found if key in found else {**found, key: name}
    return tuple(found.values())


def _kind(key: str, label: str, core: bool, niche: bool) -> str | None:
    if key.startswith(search_plan.CORE_LABEL):
        return None if core else CORE
    if key.startswith(search_plan.NICHE_LABEL):
        return None if niche else NICHE
    return LIMIT if search_plan.limit_portals(label) else GROUP


def lines_of(text: str) -> tuple[Line, ...]:
    """The searched lines under Keywords, as `search_plan` picks them: the first core list and the first niche line,
    of the other labels the first line, but every «Nur» line."""
    rows = text.split("\n")
    start, end = search_plan.section_bounds(rows, search_terms.KEYWORDS_KEY)
    found: tuple[Line, ...] = ()
    for index in range(start + 1, end) if start is not None else ():
        match = search_plan.PAIR.match(rows[index].strip())
        if not match:
            continue
        label = match[1].strip()
        key = label.lower()
        kind = _kind(key, label, any(line.kind == CORE for line in found), any(line.kind == NICHE for line in found))
        before = sum(line.label.lower() == key for line in found)
        if kind is None or (kind == GROUP and before and not search_plan.LIMIT_LABEL.match(key)):
            continue
        found = (*found, Line(f"{key}#{before}", label, kind, index, _terms(match[2]), search_plan.limit_portals(label) or ()))
    return found


def line_index(text: str, line_id: str) -> int | None:
    return next((line.index for line in lines_of(text) if line.id == line_id), None)


def _searchable(text: str, after: str) -> bool:
    try:
        search_plan.parse(after)
    except ValueError:
        return False
    return after != text


def _ordered(lines: tuple[Line, ...]) -> tuple[Line, ...]:
    rank = {CORE: 0, GROUP: 1, LIMIT: 1, NICHE: 2}
    return tuple(sorted(lines, key=lambda line: rank[line.kind]))


def _duplicates(text: str, lines: tuple[Line, ...]) -> list[Candidate]:
    places = [(search_terms.key(term), line, term) for line in _ordered(lines) for term in line.terms]
    keys = dict.fromkeys(key for key, _, _ in places if key)
    found = []
    for key in keys:
        mine = [(line, term) for k, line, term in places if k == key]
        for (a, term_a), (b, term_b) in itertools.combinations(mine, 2):
            afters = ((side, line, term, search_terms.removed_from_line(text, term, line.index))
                      for side, line, term in (("a", a, term_a), ("b", b, term_b)))
            options = tuple(Option(side, term, line, after, _searchable(text, after)) for side, line, term, after in afters)
            found = [*found, Candidate(f"{DUPLICATE}:{key}:{a.id}|{b.id}", DUPLICATE, term_a, (a, b), "", options)]
    return found


def _portals(plan: search_plan.SearchPlan, term: str) -> frozenset[str]:
    return frozenset(dict(plan.portal_limits).get(term, search_plan.PORTALS))


def _overlaps(text: str, lines: tuple[Line, ...]) -> list[Candidate]:
    try:
        plan = search_plan.parse(text)
    except ValueError:
        return []
    niche = next((line for line in lines if line.kind == NICHE), None)
    found = []
    for terms, line in ((plan.keywords, None), (plan.niche_keywords, niche)):
        for broad, narrow in itertools.permutations(terms, 2):
            wide, close = search_plan.profession_words(broad), search_plan.profession_words(narrow)
            if not wide or not wide < close or (line is None and not _portals(plan, narrow) <= _portals(plan, broad)):
                continue
            after = search_terms.removed(text, narrow) if line is None else search_terms.removed_from_line(text, narrow, line.index)
            option = Option("a", narrow, line, after, _searchable(text, after))
            marker = "" if line is None else f":{NICHE}"
            found = [*found, Candidate(f"{OVERLAP}:{search_terms.key(narrow)}|{search_terms.key(broad)}{marker}", OVERLAP,
                                       narrow, (), broad, (option,))]
    return found


def candidates(text: str) -> list[Candidate]:
    if search_plan.APPRENTICESHIP_MARK in text:
        return []
    lines = lines_of(text)
    return [*_duplicates(text, lines), *_overlaps(text, lines)]


def _saved(after: str, total: int, postal_code: str | None, switched_off: list[str] | None) -> int | None:
    later = searches(after, postal_code, switched_off)
    return None if later is None else total - later


def lost_portals(text: str, after: str, postal_code: str | None, switched_off: list[str] | None) -> tuple[str, ...]:
    """The portals the run leaves out without the entry: until the person chooses, ictjobs runs only for a term that
    fits it (`search_plan.chosen`). A portal the person chose stays as it is, so then none."""
    if switched_off is not None:
        return ()
    try:
        before, later = (search_plan.chosen(search_plan.parse(profile, postal_code), None).portals for profile in (text, after))
    except ValueError:
        return ()
    return tuple(portal for portal in before if portal not in later)


def _query_keys(hit: dict) -> set[str]:
    found = hit.get(QUERIES)
    queries = found if isinstance(found, list) else []
    return {search_terms.key(q["stichwort"]) for q in queries if isinstance(q, dict) and isinstance(q.get("stichwort"), str)}


def _shared(shown: list[dict], narrow: str, broad: str) -> tuple[int, int] | None:
    """#375: the hits a query of the narrower term found, and how many of them a query of the broader one found too;
    None without any, as before the app kept the queries."""
    mine = [keys for keys in map(_query_keys, shown) if search_terms.key(narrow) in keys]
    return (len(mine), sum(search_terms.key(broad) in keys for keys in mine)) if mine else None


def _option(option: Option, saved: int, overlap: bool) -> dict:
    kind, label = (None, "") if overlap or option.line is None else (option.line.kind, option.line.label)
    return {"seite": option.side, "knopf": words.button(option.term, kind, label),
            "name": words.button_name(option.term, kind, label), "spart": saved}


def _line_facts(line: Line) -> tuple[str, str, tuple[str, ...]]:
    return line.kind, line.label, line.portals


def _duplicate(candidate: Candidate, text: str, total: int, postal_code: str | None,
               switched_off: list[str] | None) -> dict:
    first, second = (_saved(option.after, total, postal_code, switched_off) for option in candidate.options)
    # a removal the plan cannot search without costs what the run has besides the other entry
    cost_a = first if first is not None else max(total - (second or 0), 0)
    cost_b = second if second is not None else max(total - cost_a, 0)
    lost_a, lost_b = (lost_portals(text, option.after, postal_code, switched_off) for option in candidate.options)
    a, b = candidate.lines
    return {"text": words.duplicate(candidate.term, _line_facts(a), _line_facts(b), cost_a, cost_b, (lost_a, lost_b)),
            "optionen": [_option(option, cost, False) for option, cost in zip(candidate.options, (cost_a, cost_b))
                         if option.offered]}


def _overlap(candidate: Candidate, text: str, total: int, postal_code: str | None, switched_off: list[str] | None,
             shown: list[dict]) -> dict:
    [option] = candidate.options
    cost = max(_saved(option.after, total, postal_code, switched_off) or 0, 0)
    shared = _shared(shown, candidate.term, candidate.broader)
    lost = lost_portals(text, option.after, postal_code, switched_off)
    return {"text": words.overlap(candidate.term, candidate.broader, cost, shared, lost),
            "optionen": [_option(option, cost, True)] if option.offered else []}


def pairs(text: str, postal_code: str | None, switched_off: list[str] | None, kept, shown: list[dict]) -> list[dict]:
    """What «Doppelt gesucht» shows, one entry per pair the person has not kept; nothing changes the profile here."""
    total = searches(text, postal_code, switched_off)
    if total is None:
        return []
    found = []
    for candidate in candidates(text):
        if candidate.id in kept:
            continue
        body = (_duplicate(candidate, text, total, postal_code, switched_off) if candidate.kind == DUPLICATE
                else _overlap(candidate, text, total, postal_code, switched_off, shown))
        found = [*found, {"id": candidate.id, "art": candidate.kind, "begriff": candidate.term, **body,
                          "behalten": words.KEEP, "behalten_name": words.keep_name(candidate.term, candidate.broader)}]
    return found


def removal(text: str, pair_id: str, side: str, postal_code: str | None, switched_off: list[str] | None) -> Removal:
    """The profile without the entry the person chose, with what to say; GONE if the pair or the choice is no more."""
    candidate = next((found for found in candidates(text) if found.id == pair_id), None)
    option = next((o for o in candidate.options if o.side == side and o.offered), None) if candidate else None
    if option is None:
        raise ValueError(GONE)
    before, after = searches(text, postal_code, switched_off), searches(option.after, postal_code, switched_off)
    saved = before - after if before is not None and after is not None else 0
    line = option.line
    kind, label = (None, "") if candidate.kind == OVERLAP or line is None else (line.kind, line.label)
    lost = lost_portals(text, option.after, postal_code, switched_off)
    return Removal(option.after, option.term, line.id if line else None,
                   words.removed(option.term, kind, label, saved, lost), words.back(option.term, line.kind if line else None, line.label if line else ""))


def restored(former: str | None, text: str, name: str, line_id: str) -> str:
    """Rückgängig after removing from one line: the former profile if it differs in exactly that, else the term back
    at the end of that line; NO_UNDO once the line is gone."""
    index = line_index(former, line_id) if former is not None else None
    if index is not None and former != text and search_terms.removed_from_line(former, name, index) == text:
        return former
    words = _former_words(former, name, line_id)
    index = line_index(text, line_id)
    if index is None:
        raise ValueError(NO_UNDO)
    return search_terms.added_to_line(text, required_words.with_words(name, words), index)


def _former_words(former: str | None, name: str, line_id: str) -> tuple[str, ...]:
    """The required words the term had in that line (G110), so that it comes back with them."""
    index = line_index(former, line_id) if former is not None else None
    match = search_plan.PAIR.match(former.split("\n")[index].strip()) if index is not None else None
    return required_words.entry_words(match[2], name) if match else ()
