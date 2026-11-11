"""Changes to what a job search looks for (#210, G45): search terms and the two title filters, never anything else.

A proposal is a list of changes, each one decision: an area, the terms that go and the terms that come. The app checks
every change against the profile before the person sees it, works out the result of the chosen ones and the limits of
the search (G43), and writes only the chosen changes. Niches, places, portals, the window and the exclusions stay.
"""
import dataclasses
import hashlib
import json

import search_plan
import search_terms
from ai import career

KEYWORDS, POSITIVE, EXCLUDE = "keywords", "positive", "exclude"
AREAS = (KEYWORDS, POSITIVE, EXCLUDE)
AREA_NAMES = {KEYWORDS: "Suchbegriffe", POSITIVE: "Titel enthält eines davon", EXCLUDE: "Titel enthält keines davon"}
TITLE_LABELS = {POSITIVE: "positiv", EXCLUDE: "ausschluss"}
MAX_CHANGES = 10
MAX_TERMS_PER_CHANGE = 6
MAX_REASON = 400
MIN_AVOIDED_WORD = career.MIN_AVOIDED_WORD
NOTHING_CHOSEN = "Mindestens eine Änderung anhaken."
OVER_KEYWORDS = "Mit dieser Auswahl wären es {count} Suchbegriffe, gesucht werden höchstens {limit}. Bitte weniger Änderungen anhaken."
OVER_TITLES = "Mit dieser Auswahl hätte «{area}» {count} Begriffe, höchstens {limit} gehen. Bitte weniger Änderungen anhaken."
OVER_QUERIES = ("Mit dieser Auswahl wären es bis {count} Suchen pro Portal, höchstens {limit} laufen. "
                "Bitte weniger Änderungen anhaken.")
NO_TERMS_LEFT = "Danach stünde kein Suchbegriff mehr in der Suche. Bitte weniger Änderungen anhaken."
LIMITS_LINE = "Danach: {keywords} von {max_keywords} Suchbegriffen · bis {queries} von {max_queries} Suchen pro Portal"


@dataclasses.dataclass(frozen=True)
class Terms:
    """What the three areas hold; the profile has more, but the proposal touches only these."""
    keywords: tuple[str, ...]
    positive: tuple[str, ...]
    exclude: tuple[str, ...]

    def of(self, area: str) -> tuple[str, ...]:
        return {KEYWORDS: self.keywords, POSITIVE: self.positive, EXCLUDE: self.exclude}[area]

    def as_dict(self) -> dict:
        return {"suchbegriffe": list(self.keywords), "positiv": list(self.positive), "ausschluss": list(self.exclude)}

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


def terms_of(text: str) -> Terms:
    return Terms(search_plan.listed_job_terms(text), search_plan.title_terms(text, TITLE_LABELS[POSITIVE]),
                 search_plan.title_terms(text, TITLE_LABELS[EXCLUDE]))


def _same(area: str, one: str, other: str) -> bool:
    """Search terms compare like the search does (forms of a name); title terms as words, ignoring case."""
    if area == KEYWORDS:
        return search_plan.profession_words(one) == search_plan.profession_words(other)
    return one.casefold() == other.casefold()


def _contains(area: str, terms: tuple[str, ...], term: str) -> bool:
    return any(_same(area, known, term) for known in terms)


def avoided_words(text: str) -> tuple[str, ...]:
    """What the person rules out: the section „Ausschlüsse“ and the excluded titles. Nothing with these words comes in."""
    lines = search_plan.section_lines(text, "## Ausschlüsse")
    values = [found[2] for found in map(search_plan.PAIR.match, (line.strip() for line in lines)) if found]
    words = [word for value in [*values, *search_plan.title_terms(text, TITLE_LABELS[EXCLUDE])]
             for word in search_plan.split_terms(value)]
    return tuple(dict.fromkeys(word.strip().casefold() for word in words if len(word.strip()) >= MIN_AVOIDED_WORD))


def _avoids(term: str, avoided: tuple[str, ...]) -> bool:
    return any(word in term.casefold() for word in avoided)


def _names(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    names = (" ".join(name.split()) for name in value[:MAX_TERMS_PER_CHANGE] if career.is_job_term(name))
    return tuple(dict.fromkeys(names))


def _cleaned(raw: object, current: Terms, avoided: tuple[str, ...], taken: dict[str, tuple[str, ...]]) -> Change | None:
    """A change of the AI as the app accepts it; None if any part of it does not hold, so a replacement stays whole."""
    if not isinstance(raw, dict) or raw.get("area") not in AREAS:
        return None
    area = raw["area"]
    asked_remove, asked_add = _names(raw.get("remove")), _names(raw.get("add"))
    remove = tuple(term for term in asked_remove if _contains(area, current.of(area), term))
    add = tuple(term for term in asked_add
                if not _contains(area, current.of(area), term) and not _contains(area, taken.get(area, ()), term)
                and (area == EXCLUDE or not _avoids(term, avoided)))
    reason = raw.get("reason").strip()[:MAX_REASON] if isinstance(raw.get("reason"), str) else ""
    if (asked_remove and not remove) or (asked_add and not add) or not (remove or add) or not reason:
        return None
    if len(remove) != len(asked_remove) or len(add) != len(asked_add):
        return None
    return Change(area, tuple(_as_written(area, current, term) for term in remove), add, reason)


def _as_written(area: str, current: Terms, term: str) -> str:
    return next((known for known in current.of(area) if _same(area, known, term)), term)


def cleaned_changes(raw: object, current: Terms, avoided: tuple[str, ...]) -> tuple[Change, ...]:
    """Every change that holds, each term once across the proposal; at most MAX_CHANGES."""
    changes, taken = [], {}
    for entry in raw if isinstance(raw, list) else []:
        change = _cleaned(entry, current, avoided, taken)
        if change is not None and not any(_contains(change.area, taken.get(f"-{change.area}", ()), t) for t in change.remove):
            changes = [*changes, change]
            taken = {**taken, change.area: (*taken.get(change.area, ()), *change.add),
                     f"-{change.area}": (*taken.get(f"-{change.area}", ()), *change.remove)}
    return tuple(changes[:MAX_CHANGES])


def outcome(current: Terms, changes: tuple[Change, ...]) -> Terms:
    """The three areas after these changes: what goes leaves, what comes is added at the end."""
    def after(area: str) -> tuple[str, ...]:
        mine = [change for change in changes if change.area == area]
        gone = [term for change in mine for term in change.remove]
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


def limits(before: Terms, after: Terms, places: int) -> dict:
    """The line about the limits, and why the choice cannot be taken over: only what goes over a limit and grows."""
    queries_before, queries_after = len(before.keywords) * places, len(after.keywords) * places
    checks = (
        (len(after.keywords), len(before.keywords), search_plan.MAX_KEYWORDS,
         OVER_KEYWORDS.format(count=len(after.keywords), limit=search_plan.MAX_KEYWORDS)),
        *((len(after.of(area)), len(before.of(area)), search_plan.MAX_TITLE_TERMS,
           OVER_TITLES.format(area=AREA_NAMES[area], count=len(after.of(area)), limit=search_plan.MAX_TITLE_TERMS))
          for area in (POSITIVE, EXCLUDE)),
        (queries_after, queries_before, search_plan.MAX_QUERIES,
         OVER_QUERIES.format(count=queries_after, limit=search_plan.MAX_QUERIES)),
    )
    blocked = next((message for count, earlier, limit, message in checks if count > limit and count > earlier), None)
    if not after.keywords:
        blocked = NO_TERMS_LEFT
    line = LIMITS_LINE.format(keywords=len(after.keywords), max_keywords=search_plan.MAX_KEYWORDS,
                              queries=min(queries_after, search_plan.MAX_QUERIES), max_queries=search_plan.MAX_QUERIES)
    return {"zeile": line, "gesperrt": blocked}


def chosen(changes: tuple[Change, ...], picked: object) -> tuple[Change, ...]:
    """The changes the person ticked, by their place in the proposal; anything else is refused."""
    if not isinstance(picked, list) or any(type(i) is not int or not 0 <= i < len(changes) for i in picked):
        raise ValueError(NOTHING_CHOSEN)
    wanted = sorted(set(picked))
    if not wanted:
        raise ValueError(NOTHING_CHOSEN)
    return tuple(changes[i] for i in wanted)


def applied(text: str, changes: tuple[Change, ...]) -> str:
    """The profile with these changes; all removals first, so that a replacement never runs into the limit."""
    for change in changes:
        for term in change.remove:
            text = (search_terms.removed(text, term) if change.area == KEYWORDS
                    else search_terms.without_title_term(text, TITLE_LABELS[change.area], term))
    for change in changes:
        for term in change.add:
            text = (search_terms.added(text, term) if change.area == KEYWORDS
                    else search_terms.with_title_term(text, TITLE_LABELS[change.area], term))
    return text


def _quoted(terms: tuple[str, ...]) -> str:
    named = [f"«{term}»" for term in terms]
    return named[0] if len(named) == 1 else f"{', '.join(named[:-1])} und {named[-1]}"


def _listing(terms: tuple[str, ...]) -> str:
    return terms[0] if len(terms) == 1 else f"{', '.join(terms[:-1])} und {terms[-1]}"


def sentence(change: Change) -> str:
    """The change in one sentence, the label of its checkbox."""
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
