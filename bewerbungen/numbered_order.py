"""Moving the terms of a numbered list in place (G87, #285): the professions of an apprenticeship, the search directions.

There the number is the priority, and the rating reads the list as it stands, so the list itself carries the order
the person sets and the profile holds no second one. A line keeps its remark and the lines indented below it; a
priority follows the line only if it was the same as the number, as when a term is removed.
"""
import re
from collections.abc import Callable
from dataclasses import dataclass

from search_plan import DIRECTION, section_bounds

Part = tuple[str, frozenset[str]]  # a term as written on its line, and the words that make it the same term
Splitter = Callable[[str], tuple[list[Part], str]]  # a line's text into its terms and the remark after them


@dataclass(frozen=True)
class Entry:
    lines: tuple[str, ...]  # the numbered line and the lines indented below it
    number: int
    body: str


@dataclass(frozen=True)
class Piece:
    entry: int
    parts: tuple[int, ...]  # which terms of the entry, in their new order
    first: bool  # the first piece of its entry, which keeps the lines below it


def _entries(lines: list[str]) -> tuple[list[Entry], list[str], int, int]:
    """The numbered entries, the other lines among them, and where the first one starts and the last one ends."""
    entries: list[Entry] = []
    owned: frozenset[int] = frozenset()
    for index, line in enumerate(lines):
        found = DIRECTION.match(line.strip())
        if found:
            entries = [*entries, Entry((line,), int(line.strip().split(".", 1)[0]), found[1])]
            owned = owned | {index}
        elif entries and index - 1 in owned and line[:1] in (" ", "\t") and line.strip():
            entries = [*entries[:-1], Entry((*entries[-1].lines, line), entries[-1].number, entries[-1].body)]
            owned = owned | {index}
    if not entries:
        return [], [], 0, 0
    first, after = min(owned), max(owned) + 1
    return entries, [lines[i] for i in range(first, after) if i not in owned], first, after


def _with_priority(body: str, old: int, new: int) -> str:
    return re.sub(rf"\(Priorität {old}(?!\d)", f"(Priorität {new}", body, count=1)


def _written(entry: Entry, piece: Piece, position: int, split: Splitter) -> list[str]:
    parts, remark = split(entry.body)
    whole = piece.parts == tuple(range(len(parts)))
    if whole and position == entry.number:
        return list(entry.lines)
    body = entry.body if whole else f"{', '.join(parts[i][0] for i in piece.parts)}{remark}"
    head = entry.lines[0]
    indent = head[:len(head) - len(head.lstrip())]
    return [f"{indent}{position}. {_with_priority(body, entry.number, position)}", *(entry.lines[1:] if piece.first else ())]


def _rewritten(text: str, title: str, split: Splitter, arrange: Callable[[list[Entry]], list[Piece]]) -> str:
    lines = text.split("\n")
    start, end = section_bounds(lines, title[3:].lower())
    if start is None:
        return text
    section = lines[start + 1:end]
    entries, loose, first, after = _entries(section)
    pieces = arrange(entries) if entries else []
    unchanged = [Piece(e, tuple(range(len(split(entry.body)[0]))), True) for e, entry in enumerate(entries)]
    if pieces == unchanged:
        return text
    written = [line for position, piece in enumerate(pieces, 1)
               for line in _written(entries[piece.entry], piece, position, split)]
    return "\n".join([*lines[:start + 1], *section[:first], *written, *loose, *section[after:], *lines[end:]])


def _first_places(entries: list[Entry], split: Splitter) -> dict[frozenset[str], tuple[int, int]]:
    """Where the search reads each term: the first entry and term that names it."""
    places: dict[frozenset[str], tuple[int, int]] = {}
    for e, entry in enumerate(entries):
        for p, (_, words) in enumerate(split(entry.body)[0]):
            places.setdefault(words, (e, p))
    return places


def placed(text: str, title: str, order: tuple[frozenset[str], ...], split: Splitter) -> str:
    """The list with its terms in this order: terms of one line that stay together keep sharing it, a term moved away
    from the others of its line gets a line of its own with the same remark. Lines without a term of the order
    (a repeated term, a line the search does not read) come last."""
    def arrange(entries: list[Entry]) -> list[Piece]:
        places = _first_places(entries, split)
        pieces: list[Piece] = []
        for words in (words for words in order if words in places):
            e, p = places[words]
            if pieces and pieces[-1].entry == e:
                pieces = [*pieces[:-1], Piece(e, (*pieces[-1].parts, p), pieces[-1].first)]
            else:
                pieces = [*pieces, Piece(e, (p,), all(piece.entry != e for piece in pieces))]
        return _with_the_rest(entries, pieces, split)
    return _rewritten(text, title, split, arrange)


def _with_the_rest(entries: list[Entry], pieces: list[Piece], split: Splitter) -> list[Piece]:
    """Terms the order does not name stay on the first line of their entry; entries without any come last."""
    used = {(piece.entry, p) for piece in pieces for p in piece.parts}
    rest = {e: tuple(p for p in range(len(split(entry.body)[0])) if (e, p) not in used) for e, entry in enumerate(entries)}
    kept = [Piece(piece.entry, (*piece.parts, *rest[piece.entry]), True) if piece.first else piece for piece in pieces]
    named = {piece.entry for piece in pieces}
    return [*kept, *(Piece(e, tuple(range(len(split(entry.body)[0]))), True) for e, entry in enumerate(entries)
                     if e not in named)]


def aligned(text: str, title: str, order: tuple[frozenset[str], ...], split: Splitter) -> str:
    """The list with the entries that name a term of the order sorted by it, in the places such entries hold; the
    others stay where they are. For a list the search does not read its terms from, so nothing there disagrees."""
    rank = {words: place for place, words in reversed(list(enumerate(order)))}

    def arrange(entries: list[Entry]) -> list[Piece]:
        ranks = [min((rank[w] for _, w in split(entry.body)[0] if w in rank), default=None) for entry in entries]
        slots = [e for e, r in enumerate(ranks) if r is not None]
        moved = iter(sorted(slots, key=lambda e: ranks[e]))
        chosen = [next(moved) if r is not None else e for e, r in enumerate(ranks)]
        return [Piece(e, tuple(range(len(split(entries[e].body)[0]))), True) for e in chosen]
    return _rewritten(text, title, split, arrange)
