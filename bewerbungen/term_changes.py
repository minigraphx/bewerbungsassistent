"""Changes to what a job search looks for (#210, G45): search terms and the two title filters, never anything else.

A proposal is a list of changes, each one decision: an area, the terms that go and the terms that come. The app checks
every change against the profile before the person sees it. Each term is then a switch of its own (G102, #371): the
page names the terms that are on, the app takes only current and proposed ones, works out the result and the limits
of the search (G43) itself, and writes exactly that. Places, portals, the window and the exclusions stay.
With the counts of the last runs (G108, #383) a change may also merge a keyword into another, move it to the niches
or limit it to portals (`term_moves`); a keyword the app marks «überlappend» is never simply removed.
"""
import dataclasses
import hashlib
import json

import search_plan
import search_terms
import term_moves
import title_filter
from ai import career

KEYWORDS, POSITIVE, EXCLUDE = "keywords", "positive", "exclude"
MOVED = "verschoben"  # in the switches of the page: the keywords whose move is on (G108)
AREAS = (KEYWORDS, POSITIVE, EXCLUDE)
AREA_NAMES = {KEYWORDS: "Suchbegriffe", POSITIVE: "Titel enthält eines davon", EXCLUDE: "Titel enthält keines davon"}
AREA_KEYS = {KEYWORDS: "suchbegriffe", POSITIVE: "positiv", EXCLUDE: "ausschluss"}
TITLE_LABELS = {POSITIVE: "positiv", EXCLUDE: "ausschluss"}
MAX_CHANGES = 10
MAX_TERMS_PER_CHANGE = 6
MAX_REASON = 400
MIN_AVOIDED_WORD = career.MIN_AVOIDED_WORD
NOTHING_CHANGED = "Mit dieser Auswahl bleibt alles wie bisher."
NOT_OFFERED = "Diese Auswahl passt nicht zum Vorschlag. Bitte die Seite neu laden."
SWITCH_OFF_WHERE = "Bitte noch {left} ausschalten, unter «Bisherige Begriffe» oder bei den Vorschlägen."
OVER_KEYWORDS = "Mit dieser Auswahl wären es {count} Suchbegriffe, höchstens {limit} gehen. " + SWITCH_OFF_WHERE
OVER_KEYWORDS_BEFORE = ("Mit dieser Auswahl wären es {count} Suchbegriffe. Höchstens {limit} gehen; da es schon "
                        "{earlier} sind, dürfen es nicht mehr werden. " + SWITCH_OFF_WHERE)
OVER_TITLES = ("Mit dieser Auswahl hätte «{area}» {count} Begriffe, höchstens {limit} gehen. "
               "Bitte dort noch {left} ausschalten.")
NO_TERMS_LEFT = "Danach stünde kein Suchbegriff mehr in der Suche. Bitte mindestens einen einschalten."
# G43: every search runs, in stages; the line says how many there would be, no longer up to a limit.
# #340: two parts, which the page joins with «·» (seiten/dot-line.js).
LIMITS_PARTS = ("Danach: {keywords} von {max_keywords} Suchbegriffen", "bis {queries} {searches} pro Portal")
# A profile from before the limit may keep its terms, but not grow (#371).
LIMITS_OVER_BEFORE = "Danach: {keywords} Suchbegriffe, erlaubt sind {earlier}"
AREA_LIMITS = {KEYWORDS: search_plan.MAX_KEYWORDS, POSITIVE: search_plan.MAX_TITLE_TERMS,
               EXCLUDE: search_plan.MAX_TITLE_TERMS}


@dataclasses.dataclass(frozen=True)
class Terms:
    """What the three areas hold; the profile has more, but the proposal touches only these."""
    keywords: tuple[str, ...]
    positive: tuple[str, ...]
    exclude: tuple[str, ...]

    def of(self, area: str) -> tuple[str, ...]:
        return {KEYWORDS: self.keywords, POSITIVE: self.positive, EXCLUDE: self.exclude}[area]

    def as_dict(self) -> dict:
        return {AREA_KEYS[area]: list(self.of(area)) for area in AREAS}

    @property
    def digest(self) -> str:
        """Changes when the person changes a term, not when anything else in the profile does."""
        return hashlib.sha256(json.dumps(self.as_dict(), ensure_ascii=False).encode("utf-8")).hexdigest()


@dataclasses.dataclass(frozen=True)
class Change:
    area: str
    remove: tuple[str, ...]
    add: tuple[str, ...]
    reason: str
    kind: str = term_moves.CHANGE
    into: str = ""  # a merge: the keyword that stays and finds the same hits
    moved: str = ""  # a move to the niches or onto portals: the keyword, which neither goes nor comes (G108)
    portals: tuple[str, ...] = ()

    @property
    def is_move(self) -> bool:
        return self.kind in term_moves.MOVES


def terms_of(text: str) -> Terms:
    return Terms(search_plan.listed_job_terms(text), search_plan.title_terms(text, TITLE_LABELS[POSITIVE]),
                 search_plan.title_terms(text, TITLE_LABELS[EXCLUDE]))


def _same(area: str, one: str, other: str) -> bool:
    """Search terms compare like the search does (forms of a name); title terms as words, ignoring case and whether
    they carry «(ganzes Wort)», so one term never stands twice in a list."""
    if area == KEYWORDS:
        return search_plan.profession_words(one) == search_plan.profession_words(other)
    return title_filter.bare(one).casefold() == title_filter.bare(other).casefold()


def _contains(area: str, terms: tuple[str, ...], term: str) -> bool:
    return any(_same(area, known, term) for known in terms)


def _identical(area: str, one: str, other: str) -> bool:
    """Like `_same`, but a title term with «(ganzes Wort)» differs from the term without: the switches name both."""
    return _same(area, one, other) and (area == KEYWORDS or title_filter.marked(one) == title_filter.marked(other))


def _holds(area: str, terms: tuple[str, ...], term: str) -> bool:
    return any(_identical(area, known, term) for known in terms)


def _restyled(area: str, terms: tuple[str, ...], term: str) -> str | None:
    """The term of the list that `term` only marks or unmarks as a whole word (G104): a change of that same term."""
    return next((known for known in terms if _same(area, known, term) and not _identical(area, known, term)), None)


def avoided_words(text: str) -> tuple[str, ...]:
    """What the person rules out: the section „Ausschlüsse“ and the excluded titles. Nothing with these words comes in."""
    lines = search_plan.section_lines(text, "## Ausschlüsse")
    values = [found[2] for found in map(search_plan.PAIR.match, (line.strip() for line in lines)) if found]
    words = [word for value in [*values, *search_plan.title_terms(text, TITLE_LABELS[EXCLUDE])]
             for word in search_plan.split_terms(value)]
    return tuple(dict.fromkeys(word.strip().casefold() for word in words if len(word.strip()) >= MIN_AVOIDED_WORD))


def _avoids(term: str, avoided: tuple[str, ...]) -> bool:
    return any(word in term.casefold() for word in avoided)


def _name(area: str, name: object) -> str | None:
    """A term as the AI wrote it; in a title filter it may end in «(ganzes Wort)» (G104), checked without it."""
    if area != KEYWORDS and isinstance(name, str) and title_filter.marked(name):
        plain = title_filter.bare(name)
        return title_filter.with_marker(plain) if career.is_job_term(plain) else None
    return " ".join(name.split()) if career.is_job_term(name) else None


def _names(area: str, value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    names = (_name(area, name) for name in value[:MAX_TERMS_PER_CHANGE])
    return tuple(dict.fromkeys(name for name in names if name))


def _reason(raw: dict) -> str:
    return raw.get("reason").strip()[:MAX_REASON] if isinstance(raw.get("reason"), str) else ""


def _cleaned_move(raw: dict, kind: str, current: Terms, placement: term_moves.Placement) -> Change | None:
    """A merge, a move to the niches or a limit to portals: about exactly one keyword of the list, adding none."""
    names = _names(KEYWORDS, raw.get("remove"))
    if raw.get("area") != KEYWORDS or len(names) != 1 or raw.get("add") or not _contains(KEYWORDS, current.keywords, names[0]):
        return None
    term, reason = _as_written(KEYWORDS, current, names[0]), _reason(raw)
    if not reason:
        return None
    if kind == term_moves.MERGE:
        into = _name(KEYWORDS, raw.get("into"))
        if not into or not _contains(KEYWORDS, current.keywords, into) or _same(KEYWORDS, term, into):
            return None
        return Change(KEYWORDS, (term,), (), reason, kind, into=_as_written(KEYWORDS, current, into))
    if not placement.grouped:  # without named lines under Keywords a term has no line to leave
        return None
    if kind == term_moves.NICHE:
        return Change(KEYWORDS, (), (), reason, kind, moved=term)
    portals = term_moves.checked_portals(raw.get("portals"), term, placement)
    return Change(KEYWORDS, (), (), reason, kind, moved=term, portals=portals) if portals else None


def _cleaned(raw: object, current: Terms, avoided: tuple[str, ...], taken: dict[str, tuple[str, ...]],
             placement: term_moves.Placement, overlapping: tuple[str, ...]) -> Change | None:
    """A change of the AI as the app accepts it; None if any part of it does not hold, so a replacement stays whole."""
    if not isinstance(raw, dict) or raw.get("area") not in AREAS:
        return None
    kind = raw.get("kind") or term_moves.CHANGE
    if kind != term_moves.CHANGE:
        return _cleaned_move(raw, kind, current, placement) if kind in term_moves.KINDS else None
    change = _cleaned_change(raw, current, avoided, taken)
    if change and change.area == KEYWORDS and not change.add and any(_contains(KEYWORDS, overlapping, t) for t in change.remove):
        return None  # «überlappend»: its hits came through other keywords too, so at most a merge names where they go
    return change


def _cleaned_change(raw: dict, current: Terms, avoided: tuple[str, ...], taken: dict[str, tuple[str, ...]]) -> Change | None:
    area = raw["area"]
    asked_remove, asked_add = _names(area, raw.get("remove")), _names(area, raw.get("add"))
    remove = tuple(_as_written(area, current, term) for term in asked_remove if _contains(area, current.of(area), term))
    add = tuple(term for term in asked_add
                if (not _contains(area, current.of(area), term) or _restyled(area, current.of(area), term))
                and not _contains(area, taken.get(area, ()), term)
                and (area == EXCLUDE or not _avoids(term, avoided)))
    reason = _reason(raw)
    if (asked_remove and not remove) or (asked_add and not add) or not (remove or add) or not reason:
        return None
    if len(remove) != len(asked_remove) or len(add) != len(asked_add):
        return None
    # Marking «Sales» as «Sales (ganzes Wort)» replaces the term, so the list never holds it twice.
    restyled = (_restyled(area, current.of(area), term) for term in add)
    return Change(area, tuple(dict.fromkeys((*remove, *(term for term in restyled if term)))), add, reason)


def _as_written(area: str, current: Terms, term: str) -> str:
    return next((known for known in current.of(area) if _same(area, known, term)), term)


def _touched(change: Change) -> tuple[str, ...]:
    return (*change.remove, *((change.moved,) if change.moved else ()))


def _clashes(change: Change, taken: dict[str, tuple[str, ...]]) -> bool:
    """A term an earlier change removes, moves or merges into is not touched again, nor merged into once gone."""
    gone, kept = taken.get(f"-{change.area}", ()), taken.get(f"={change.area}", ())
    return (any(_contains(change.area, (*gone, *kept), term) for term in _touched(change))
            or bool(change.into and _contains(change.area, gone, change.into)))


def cleaned_changes(raw: object, current: Terms, avoided: tuple[str, ...],
                    placement: term_moves.Placement = term_moves.Placement(),
                    overlapping: tuple[str, ...] = ()) -> tuple[Change, ...]:
    """Every change that holds, each term once across the proposal; at most MAX_CHANGES. `overlapping`: the keywords
    the app marks «überlappend» (G108), which no change simply removes."""
    changes, taken = [], {}
    for entry in raw if isinstance(raw, list) else []:
        change = _cleaned(entry, current, avoided, taken, placement, overlapping)
        if change is not None and not _clashes(change, taken):
            changes = [*changes, change]
            taken = {**taken, change.area: (*taken.get(change.area, ()), *change.add),
                     f"-{change.area}": (*taken.get(f"-{change.area}", ()), *_touched(change)),
                     f"={change.area}": (*taken.get(f"={change.area}", ()), *((change.into,) if change.into else ()))}
    return tuple(changes[:MAX_CHANGES])


def outcome(current: Terms, changes: tuple[Change, ...]) -> Terms:
    """The three areas after these changes: what goes leaves, what comes is added at the end; a keyword moved to the
    niches leaves the list of keywords too, a keyword limited to portals stays in it."""
    def after(area: str) -> tuple[str, ...]:
        mine = [change for change in changes if change.area == area]
        gone = [*(term for change in mine for term in change.remove),
                *(change.moved for change in mine if change.kind == term_moves.NICHE)]
        kept = tuple(term for term in current.of(area) if not _contains(area, tuple(gone), term))
        return (*kept, *(term for change in mine for term in change.add))
    return Terms(after(KEYWORDS), after(POSITIVE), after(EXCLUDE))


def places_factor(text: str) -> int:
    """How many places one term is searched in on the busiest portal; one without places."""
    try:
        plan = search_plan.parse(text)
    except ValueError:
        return 1
    return max(1, len(plan.places), len(plan.postal_codes), len(plan.regions))


def allowed(before: Terms) -> dict[str, int]:
    """How many terms each area may hold: its limit, or as many as it has, since a profile from before may keep them."""
    return {AREA_KEYS[area]: max(AREA_LIMITS[area], len(before.of(area))) for area in AREAS}


def _over_message(area: str, count: int, earlier: int, left: int) -> str:
    limit = AREA_LIMITS[area]
    if area != KEYWORDS:
        return OVER_TITLES.format(area=AREA_NAMES[area], count=count, limit=limit, left=left)
    if earlier > limit:
        return OVER_KEYWORDS_BEFORE.format(count=count, limit=limit, earlier=earlier, left=left)
    return OVER_KEYWORDS.format(count=count, limit=limit, left=left)


def _limits_line(before: Terms, after: Terms, places: int) -> list[str]:
    numbers = {"keywords": len(after.keywords), "max_keywords": search_plan.MAX_KEYWORDS,
               "earlier": len(before.keywords), "queries": len(after.keywords) * places,
               "searches": "Suche" if len(after.keywords) * places == 1 else "Suchen"}
    first = LIMITS_OVER_BEFORE if len(before.keywords) > search_plan.MAX_KEYWORDS else LIMITS_PARTS[0]
    return [part.format(**numbers) for part in (first, *LIMITS_PARTS[1:])]


def limits(before: Terms, after: Terms, places: int, moves: int = 0) -> dict:
    """The parts of the line about the limits, how many terms are too many per area, and why the choice cannot be
    taken over: only what goes over a limit and grows, a search without terms, or a choice that changes nothing,
    where a move to the niches or onto portals (`moves`) is a change too."""
    room = allowed(before)
    too_many = {AREA_KEYS[area]: max(0, len(after.of(area)) - room[AREA_KEYS[area]]) for area in AREAS}
    blocked = next((_over_message(area, len(after.of(area)), len(before.of(area)), too_many[AREA_KEYS[area]])
                    for area in AREAS if too_many[AREA_KEYS[area]]), None)
    if not after.keywords:
        blocked = NO_TERMS_LEFT
    if blocked is None and after == before and not moves:
        blocked = NOTHING_CHANGED
    return {"teile": _limits_line(before, after, places), "gesperrt": blocked, "zu_viel": too_many, "erlaubt": room}


def _proposed(area: str, changes: tuple[Change, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(term for change in changes if change.area == area for term in change.add))


def _moved_terms(area: str, changes: tuple[Change, ...]) -> tuple[str, ...]:
    return tuple(change.moved for change in changes if change.area == area and change.is_move)


def _selected_in(area: str, current: Terms, changes: tuple[Change, ...], on: object) -> Change:
    """The terms a move concerns have no switch of their own here: the move's one switch decides (`_moves_on`)."""
    offered = (*current.of(area), *_proposed(area, changes))
    if not isinstance(on, list) or len(on) > len(offered):
        raise ValueError(NOT_OFFERED)
    if not all(isinstance(term, str) and _holds(area, offered, term) for term in on):
        raise ValueError(NOT_OFFERED)
    wanted, fixed = tuple(on), _moved_terms(area, changes)
    remove = tuple(term for term in current.of(area) if not _holds(area, wanted, term) and not _contains(area, fixed, term))
    kept = tuple(term for term in current.of(area) if term not in remove)
    return Change(area, remove, tuple(term for term in _proposed(area, changes)
                                      if _holds(area, wanted, term) and not _contains(area, kept, term)), "")


def selected(current: Terms, changes: tuple[Change, ...], on: object) -> tuple[Change, ...]:
    """The switches of the page as one change per area: a current term that is off goes, a proposed term that is on
    comes. The page names every area; a term that is neither current nor proposed for its area is refused, so nothing
    the page sends can bring in anything else, and the order is the app's, not the page's."""
    if not isinstance(on, dict):
        raise ValueError(NOT_OFFERED)
    found = (_selected_in(area, current, changes, on.get(AREA_KEYS[area])) for area in AREAS)
    return (*(change for change in found if change.remove or change.add), *_moves_on(changes, on.get(MOVED, [])))


def _moves_on(changes: tuple[Change, ...], on: object) -> tuple[Change, ...]:
    """The moves whose one switch is on (G102, G108), named by their keyword; any other name is refused."""
    moves = tuple(change for change in changes if change.is_move)
    if not isinstance(on, list) or not all(isinstance(term, str) and any(_same(KEYWORDS, c.moved, term) for c in moves)
                                           for term in on):
        raise ValueError(NOT_OFFERED)
    return tuple(change for change in moves if any(_same(KEYWORDS, change.moved, term) for term in on))


def untouched(current: Terms, changes: tuple[Change, ...]) -> Terms:
    """The current terms no change removes or moves, matched like the search does, so a term in a card is never also
    below."""
    def kept(area: str) -> tuple[str, ...]:
        gone = tuple(term for change in changes if change.area == area for term in _touched(change))
        return tuple(term for term in current.of(area) if not _contains(area, gone, term))
    return Terms(kept(KEYWORDS), kept(POSITIVE), kept(EXCLUDE))


def applied(text: str, changes: tuple[Change, ...]) -> str:
    """The profile with these changes; all removals first, so that a replacement never runs into the limit.

    The limits are checked before (`limits`), so adding here may go past what adding by hand allows: a profile from
    before the limit can take a term over once it switched enough others off.
    """
    for change in changes:
        for term in change.remove:
            text = (search_terms.removed(text, term) if change.area == KEYWORDS
                    else search_terms.without_title_term(text, TITLE_LABELS[change.area], term))
    for change in changes:
        for term in change.add:
            text = (search_terms.added(text, term, limit=None) if change.area == KEYWORDS
                    else search_terms.with_title_term(text, TITLE_LABELS[change.area], term))
    for change in changes:
        if change.is_move:
            text = term_moves.moved(text, change.kind, change.moved, change.portals)
    return text


def moves_of(changes: tuple[Change, ...]) -> tuple[tuple[str, str, tuple[str, ...]], ...]:
    """The moves among these changes as `term_moves.after` takes them."""
    return tuple((change.kind, change.moved, change.portals) for change in changes if change.is_move)


def _quoted(terms: tuple[str, ...], marks: str = "«»") -> str:
    named = [f"{marks[0]}{term}{marks[1]}" for term in terms]
    return named[0] if len(named) == 1 else f"{', '.join(named[:-1])} und {named[-1]}"


def _listing(terms: tuple[str, ...]) -> str:
    return terms[0] if len(terms) == 1 else f"{', '.join(terms[:-1])} und {terms[-1]}"


def sentence(change: Change) -> str:
    """The change in one sentence, the label of its checkbox."""
    if change.kind != term_moves.CHANGE:
        return term_moves.sentence(change.kind, change.moved or change.remove[0], change.into, change.portals)
    if change.area == KEYWORDS and change.remove and not change.add:
        return f"{_quoted(change.remove, '„“')} entfernen"  # G108: as the counts on the page name a keyword
    if change.area != KEYWORDS and len(change.remove) == len(change.add) == 1 and _same(change.area, *change.remove,
                                                                                        *change.add):
        return f"„{change.remove[0]}“ ersetzen durch „{change.add[0]}“"
    if change.remove and change.add:
        return f"{_quoted(change.remove)} ersetzen durch {_listing(change.add)}"
    if change.add:
        if change.area == EXCLUDE:
            return f"{_quoted(change.add)} ausschliessen"
        prefix = ("Suchbegriff " if len(change.add) == 1 else "Suchbegriffe ") if change.area == KEYWORDS else ""
        return f"{prefix}{_quoted(change.add)} aufnehmen"
    if change.area == EXCLUDE:
        return f"{_quoted(change.remove)} nicht mehr ausschliessen"
    return f"{_quoted(change.remove)} entfernen"
