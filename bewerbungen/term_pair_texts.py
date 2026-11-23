"""The words of «Doppelt gesucht» on Suche einstellen (G106, #377), as the UI/UX review gave them for the core list and
the niches; any other line is named as the profile labels it. No form of address, so one text fits Sie and du.

Every text is a T (#425), so the page says it in the app language; terms and line labels are profile data and stay.
Each wording is its own template, since a place («bei den Nischen») and a source of removal differ in French."""
import functools

from ui_message import T, listing

CORE, NICHE, GROUP, LIMIT = "kernliste", "nischen", "gruppe", "nur"
KEEP = T("Beide behalten")
KEPT = T("Beide bleiben. Die App fragt bei diesem Paar nicht wieder.")

Line = tuple[str, str, tuple[str, ...]]


def searches_word(count: int) -> str:
    return T("1 Suche") if count == 1 else T("{anzahl} Suchen", anzahl=count)


def _place(kind: str, label: str) -> str:
    if kind == CORE:
        return T("in der Kernliste")
    if kind == NICHE:
        return T("bei den Nischen")
    return T("in der Zeile „{label}“", label=label)


def _place_first(kind: str, label: str) -> str:
    """The place at the start of a sentence."""
    if kind == CORE:
        return T("In der Kernliste")
    if kind == NICHE:
        return T("Bei den Nischen")
    return T("In der Zeile „{label}“", label=label)


def _subject(kind: str, label: str) -> str:
    return T("die Kernliste") if kind == CORE else T("die Zeile „{label}“", label=label)


def _named(portals: tuple[str, ...]) -> str:
    return listing(list(portals))


def _searched_once(a: Line, b: Line) -> bool:
    """Whether the reason already says the plan runs the term only once: no niche, and not one limited line alone."""
    return b[0] != NICHE and sum(line[0] == LIMIT for line in (a, b)) != 1


def _why(a: Line, b: Line) -> str:
    """Why the second entry adds little: the niches run without a place; else the plan searches the term once."""
    if b[0] == NICHE:
        return T("Bei den Nischen sucht die App ohne Ort, also auch alles, was {subjekt} findet.",
                 subjekt=_subject(a[0], a[1]))
    limited = [line for line in (a, b) if line[0] == LIMIT]
    if not limited:
        return T("Die App sucht ihn trotzdem nur einmal.")
    if len(limited) == 2:
        return T("Die App sucht ihn nur einmal, auf den Portalen beider Zeilen.")
    free, only = (a, b) if b[0] == LIMIT else (b, a)
    return T("Weil er auch {ort} steht, sucht die App ihn auf allen Portalen, nicht nur auf {portale}.",
             ort=_place(free[0], free[1]), portale=_named(only[2]))


def _costs(a: Line, b: Line, cost_a: int, cost_b: int) -> str:
    if cost_a and cost_b:
        return T("{ort} kostet er {suchen} pro Suchlauf, {ort2} {anzahl}.", ort=_place_first(a[0], a[1]),
                 suchen=searches_word(cost_a), ort2=_place(b[0], b[1]), anzahl=cost_b)
    if not cost_a and not cost_b:
        # «nur einmal» in the reason says it already (UI/UX build review)
        return "" if _searched_once(a, b) else T("Doppelt kostet er keine zusätzliche Suche.")
    (paid, cost), free = ((a, cost_a), b) if cost_a else ((b, cost_b), a)
    return T("{ort} kostet er {suchen} pro Suchlauf, {ort2} keine zusätzliche.", ort=_place_first(paid[0], paid[1]),
             suchen=searches_word(cost), ort2=_place(free[0], free[1]))


def _goes_off(without: str, lost: tuple[str, ...]) -> str:
    """A portal the run leaves out without the entry; the count already has it."""
    if not lost:
        return ""
    return T("{ohne} sucht die App nicht mehr auf {portale}; das ist in der Zahl schon eingerechnet.", ohne=without,
             portale=_named(lost))


def _without_entry(line: Line) -> str:
    return T("Ohne den Eintrag {ort}", ort=_place(line[0], line[1]))


def _sentences(*parts: str) -> str:
    """The sentences joined by a space; a T of placeholders only, so each sentence keeps its own language."""
    said = [part for part in parts if part]
    return functools.reduce(lambda joined, part: T("{a} {b}", a=joined, b=part), said[1:], said[0]) if said else ""


def duplicate(term: str, a: Line, b: Line, cost_a: int, cost_b: int,
              lost: tuple[tuple[str, ...], tuple[str, ...]] = ((), ())) -> str:
    """`a` and `b` as (kind, label, portals), the core list first and the niches last; `lost` the portals the run
    leaves out without each entry."""
    lost_a, lost_b = lost
    return _sentences(T("„{begriff}“ steht zweimal: {ort} und {ort2}.", begriff=term, ort=_place(a[0], a[1]),
                        ort2=_place(b[0], b[1])),
                      _why(a, b), _costs(a, b, cost_a, cost_b), _goes_off(_without_entry(a), lost_a),
                      _goes_off(_without_entry(b), lost_b))


def _shared(broad: str, shared: tuple[int, int]) -> str:
    """#375: of the postings a query of the narrower term found, how many a query of the broader one found too; each
    posting counts once, so they are «Stellen», not «Treffer» (#383)."""
    total, both = shared
    if total == 1 and both:
        return T("Seine einzige Stelle kam auch über „{breit}“.", breit=broad)
    if total == 1:
        return T("Seine einzige Stelle kam nicht über „{breit}“.", breit=broad)
    if both == total:
        return T("Alle seine {anzahl} Stellen kamen auch über „{breit}“.", anzahl=total, breit=broad)
    if both == 0:
        return T("Von seinen {anzahl} Stellen kam keine über „{breit}“.", anzahl=total, breit=broad)
    if both == 1:
        return T("Von seinen {anzahl} Stellen kam eine auch über „{breit}“.", anzahl=total, breit=broad)
    return T("Von seinen {anzahl} Stellen kamen {beide} auch über „{breit}“.", anzahl=total, beide=both, breit=broad)


def _contained(narrow: str, broad: str, shared: tuple[int, int] | None) -> str:
    """«meist schon» only while the hits do not say otherwise: with less than half through the broader term, «sollte»."""
    if shared and shared[1] * 2 < shared[0]:
        return T("„{eng}“ steckt ganz in „{breit}“: Die Suche nach „{breit}“ sollte diese Stellen auch finden.",
                 eng=narrow, breit=broad)
    return T("„{eng}“ steckt ganz in „{breit}“: Die Suche nach „{breit}“ findet diese Stellen meist schon.",
             eng=narrow, breit=broad)


def overlap(narrow: str, broad: str, cost: int, shared: tuple[int, int] | None, lost: tuple[str, ...] = ()) -> str:
    return _sentences(_contained(narrow, broad, shared),
                      T("„{eng}“ kostet {suchen} pro Suchlauf.", eng=narrow, suchen=searches_word(cost)),
                      _goes_off(T("Ohne ihn"), lost), _shared(broad, shared) if shared else "")


def button(term: str, kind: str | None, label: str) -> str:
    """The button of a removal; without `kind` the term leaves the whole list."""
    if kind is None:
        return T("„{begriff}“ entfernen", begriff=term)
    if kind == CORE:
        return T("Aus der Kernliste entfernen")
    if kind == NICHE:
        return T("Bei den Nischen entfernen")
    return T("Aus der Zeile „{label}“ entfernen", label=label)


def button_name(term: str, kind: str | None, label: str) -> str:
    """What a screen reader hears: the visible words first, then the term, since every block has such buttons."""
    shown = button(term, kind, label)
    return shown if kind is None else T("{knopf}: „{begriff}“", knopf=shown, begriff=term)


def keep_name(term: str, broader: str) -> str:
    if broader:
        return T("Beide behalten: „{begriff}“ und „{breit}“", begriff=term, breit=broader)
    return T("Beide behalten: „{begriff}“", begriff=term)


def _done(term: str, kind: str | None, label: str) -> str:
    if kind is None:
        return T("„{begriff}“ entfernt.", begriff=term)
    if kind == CORE:
        return T("„{begriff}“ aus der Kernliste entfernt.", begriff=term)
    if kind == NICHE:
        return T("„{begriff}“ bei den Nischen entfernt.", begriff=term)
    return T("„{begriff}“ aus der Zeile „{label}“ entfernt.", begriff=term, label=label)


def _next_run(saved: int, lost: tuple[str, ...]) -> str:
    # «Suchlauf» is the run and «Suche» one query (UI/UX review 0.3.3), so the run is what saves searches
    if saved > 0 and lost:
        return T("Der nächste Suchlauf spart {suchen} und sucht nicht mehr auf {portale}.",
                 suchen=searches_word(saved), portale=_named(lost))
    if saved > 0:
        return T("Der nächste Suchlauf spart {suchen}.", suchen=searches_word(saved))
    if lost:
        return T("Der nächste Suchlauf sucht nicht mehr auf {portale}.", portale=_named(lost))
    return T("Der nächste Suchlauf bleibt gleich gross.")


def removed(term: str, kind: str | None, label: str, saved: int, lost: tuple[str, ...] = ()) -> str:
    return _sentences(_done(term, kind, label), _next_run(saved, lost))


def back(term: str, kind: str | None, label: str) -> str:
    if kind is None:
        return T("„{begriff}“ ist wieder in der Suche.", begriff=term)
    return T("„{begriff}“ steht wieder {ort}.", begriff=term, ort=_place(kind, label))
