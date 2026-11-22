"""The words of «Doppelt gesucht» on Suche einstellen (G106, #377), as the UI/UX review gave them for the core list and
the niches; any other line is named as the profile labels it. No form of address, so one text fits Sie and du."""
CORE, NICHE, GROUP, LIMIT = "kernliste", "nischen", "gruppe", "nur"
KEEP = "Beide behalten"
KEPT = "Beide bleiben. Die App fragt bei diesem Paar nicht wieder."


def searches_word(count: int) -> str:
    return "1 Suche" if count == 1 else f"{count} Suchen"


def _place(kind: str, label: str) -> str:
    return {CORE: "in der Kernliste", NICHE: "bei den Nischen"}.get(kind, f"in der Zeile „{label}“")


def _subject(kind: str, label: str) -> str:
    return "die Kernliste" if kind == CORE else f"die Zeile „{label}“"


def _named(portals: tuple[str, ...]) -> str:
    return portals[0] if len(portals) == 1 else f"{', '.join(portals[:-1])} und {portals[-1]}"


def _capitalised(text: str) -> str:
    return f"{text[0].upper()}{text[1:]}"


def _searched_once(a: tuple[str, str, tuple[str, ...]], b: tuple[str, str, tuple[str, ...]]) -> bool:
    """Whether the reason already says the plan runs the term only once: no niche, and not one limited line alone."""
    return b[0] != NICHE and sum(line[0] == LIMIT for line in (a, b)) != 1


def _why(a: tuple[str, str, tuple[str, ...]], b: tuple[str, str, tuple[str, ...]]) -> str:
    """Why the second entry adds little: the niches run without a place; else the plan searches the term once."""
    if b[0] == NICHE:
        return f"Bei den Nischen sucht die App ohne Ort, also auch alles, was {_subject(a[0], a[1])} findet."
    limited = [line for line in (a, b) if line[0] == LIMIT]
    if not limited:
        return "Die App sucht ihn trotzdem nur einmal."
    if len(limited) == 2:
        return "Die App sucht ihn nur einmal, auf den Portalen beider Zeilen."
    free, only = (a, b) if b[0] == LIMIT else (b, a)
    return (f"Weil er auch {_place(free[0], free[1])} steht, sucht die App ihn auf allen Portalen, nicht nur auf "
            f"{_named(only[2])}.")


def _costs(a: tuple[str, str, tuple[str, ...]], b: tuple[str, str, tuple[str, ...]], cost_a: int, cost_b: int) -> str:
    if cost_a and cost_b:
        return (f"{_capitalised(_place(a[0], a[1]))} kostet er {searches_word(cost_a)} pro Suchlauf, "
                f"{_place(b[0], b[1])} {cost_b}.")
    if not cost_a and not cost_b:
        # «nur einmal» in the reason says it already (UI/UX build review)
        return "" if _searched_once(a, b) else "Doppelt kostet er keine zusätzliche Suche."
    (paid, cost), free = ((a, cost_a), b) if cost_a else ((b, cost_b), a)
    return (f"{_capitalised(_place(paid[0], paid[1]))} kostet er {searches_word(cost)} pro Suchlauf, "
            f"{_place(free[0], free[1])} keine zusätzliche.")


def _goes_off(without: str, lost: tuple[str, ...]) -> str:
    """A portal the run leaves out without the entry; the count already has it."""
    return f"{without} sucht die App nicht mehr auf {_named(lost)}; das ist in der Zahl schon eingerechnet." if lost else ""


def _sentences(*parts: str) -> str:
    return " ".join(part for part in parts if part)


def duplicate(term: str, a: tuple[str, str, tuple[str, ...]], b: tuple[str, str, tuple[str, ...]],
              cost_a: int, cost_b: int, lost: tuple[tuple[str, ...], tuple[str, ...]] = ((), ())) -> str:
    """`a` and `b` as (kind, label, portals), the core list first and the niches last; `lost` the portals the run
    leaves out without each entry."""
    lost_a, lost_b = lost
    return _sentences(f"„{term}“ steht zweimal: {_place(a[0], a[1])} und {_place(b[0], b[1])}.", _why(a, b),
                      _costs(a, b, cost_a, cost_b), _goes_off(f"Ohne den Eintrag {_place(a[0], a[1])}", lost_a),
                      _goes_off(f"Ohne den Eintrag {_place(b[0], b[1])}", lost_b))


def _shared(broad: str, shared: tuple[int, int]) -> str:
    """#375: of the postings a query of the narrower term found, how many a query of the broader one found too; each
    posting counts once, so they are «Stellen», not «Treffer» (#383)."""
    total, both = shared
    if total == 1:
        return f"Seine einzige Stelle kam {'auch' if both else 'nicht'} über „{broad}“."
    if both == total:
        return f"Alle seine {total} Stellen kamen auch über „{broad}“."
    verb = {0: "kam keine", 1: "kam eine auch"}.get(both, f"kamen {both} auch")
    return f"Von seinen {total} Stellen {verb} über „{broad}“."


def _finds(shared: tuple[int, int] | None) -> str:
    """«meist schon» only while the hits do not say otherwise: with less than half through the broader term, «sollte»."""
    return "sollte diese Stellen auch finden" if shared and shared[1] * 2 < shared[0] else "findet diese Stellen meist schon"


def overlap(narrow: str, broad: str, cost: int, shared: tuple[int, int] | None, lost: tuple[str, ...] = ()) -> str:
    return _sentences(f"„{narrow}“ steckt ganz in „{broad}“: Die Suche nach „{broad}“ {_finds(shared)}.",
                      f"„{narrow}“ kostet {searches_word(cost)} pro Suchlauf.", _goes_off("Ohne ihn", lost),
                      _shared(broad, shared) if shared else "")


def button(term: str, kind: str | None, label: str) -> str:
    """The button of a removal; without `kind` the term leaves the whole list."""
    if kind is None:
        return f"„{term}“ entfernen"
    return {CORE: "Aus der Kernliste entfernen", NICHE: "Bei den Nischen entfernen"}.get(kind, f"Aus der Zeile „{label}“ entfernen")


def button_name(term: str, kind: str | None, label: str) -> str:
    """What a screen reader hears: the visible words first, then the term, since every block has such buttons."""
    shown = button(term, kind, label)
    return shown if kind is None else f"{shown}: „{term}“"


def keep_name(term: str, broader: str) -> str:
    return f"{KEEP}: „{term}“ und „{broader}“" if broader else f"{KEEP}: „{term}“"


def _from(kind: str, label: str) -> str:
    return {CORE: "aus der Kernliste", NICHE: "bei den Nischen"}.get(kind, f"aus der Zeile „{label}“")


def removed(term: str, kind: str | None, label: str, saved: int, lost: tuple[str, ...] = ()) -> str:
    done = f"„{term}“ entfernt." if kind is None else f"„{term}“ {_from(kind, label)} entfernt."
    # «Suchlauf» is the run and «Suche» one query (UI/UX review 0.3.3), so the run is what saves searches
    off = f"sucht nicht mehr auf {_named(lost)}" if lost else ""
    if saved > 0:
        rest = f"Der nächste Suchlauf spart {searches_word(saved)}{f' und {off}' if off else ''}."
    else:
        rest = f"Der nächste Suchlauf {off}." if off else "Der nächste Suchlauf bleibt gleich gross."
    return f"{done} {rest}"


def back(term: str, kind: str | None, label: str) -> str:
    return f"„{term}“ ist wieder in der Suche." if kind is None else f"„{term}“ steht wieder {_place(kind, label)}."
