"""What a person searches for, and changing it from the page (MIN-375).

An apprenticeship profile names professions. A job profile searches its line „Kernliste“ and the other named lines under
„Keywords“ but the niches if it has any, else its numbered search directions, where one line can hold several terms and
bullets of its own. Everything else in the profile stays as written.
The order set on Suche einstellen (G87) moves professions and search directions within their numbered list, since
the number is their priority (`numbered_order`). Terms from Keywords get a section of their own, „Reihenfolge der
Suche“, which the plan reads before the lines they come from; a term it does not name comes after, so a new one goes
to the end, as a new line of a numbered list does.
A line «- Nur <Portal>: …» limits its terms to those portals (G105): a term can be removed from it and moved like any
other, but a new term never goes there, and a profile from the form keeps the line.
"""
import re
from collections.abc import Callable

import numbered_order
import required_words
import search_frame
import search_plan
import title_filter
from search_plan import (APPRENTICESHIP_MARK, DIRECTION, MAX_DIRECTION, MAX_DIRECTIONS, MAX_KEYWORDS, MAX_PROFESSION_NAME,
                         MAX_VALUE, profession_words)
from ui_message import T

DIRECTIONS_SECTION = "## Suchrichtungen"
KEYWORDS_KEY = "keywords"
KEYWORDS_SECTION = "## Keywords"
AFTER_DIRECTIONS = "## Region"
REGION_SECTION = AFTER_DIRECTIONS
CORE_LIST = re.compile(r"^(-\s+kernliste[^:]*:\s*)(.*)$", re.IGNORECASE)
# Every named line under Keywords but the niches is searched (#174), so a term can be removed from any of them;
# of the core lists only the first counts.
GROUP_LINE = re.compile(r"^(-\s+[^:]+:\s*)(.*)$")
OTHER_GROUP = re.compile(r"^-\s+(?!kernliste|nischen)[^:]+:\s*\S", re.IGNORECASE)
TERMS_AND_REMARK = re.compile(r"^([^(]*?)(\s*\(.*)?$")
TITLE_SECTION = "## Titelfilter"
TITLE_LABELS = {"positiv": "Positiv", "ausschluss": "Ausschluss"}
AFTER_TITLES = "## Sprachen"
NICHE_LINE = "- Nischen (ohne Ort suchen): {terms}"
LIMIT_LINE = "- Nur {portals}: {terms}"
FULL = "Die Suche hat schon {limit} Begriffe, mehr gehen hier nicht. Bitte zuerst einen entfernen."
FULL_DIRECTIONS = "Die Suche hat schon {limit} Suchrichtungen. Bitte zuerst eine entfernen."
ORDER_NOTE = ("Die Suche sucht die Begriffe in dieser Reihenfolge, die wichtigsten zuerst; neue kommen ans Ende. "
              "Ändern auf „Suche einstellen“.")
ORDER_CHANGED = "Die Liste hat sich inzwischen geändert und ist neu geladen. Bitte nochmals verschieben."
# G110: a numbered search direction ends at its first bracket, so required words would silently do nothing there.
NO_REMARK_IN_DIRECTIONS = ("Pflichtwörter gelten nur für Begriffe unter „Keywords“. Bitte den Begriff ohne "
                           "„(nur mit …)“ aufnehmen.")


def current(text: str) -> tuple[str, ...]:
    return search_plan.professions_in(text) if APPRENTICESHIP_MARK in text else search_plan.job_terms(text)


def is_searched(text: str, name: str) -> bool:
    """Whether the profile searches this term already, in any form the plan reads as the same."""
    return profession_words(name) in map(profession_words, current(text))


def key(name: str) -> str:
    """The same for two forms of a name, so that a page can compare what it shows with what is searched."""
    return " ".join(sorted(profession_words(name)))


def _core_list_line(lines: list[str]) -> int | None:
    """The line the plan reads: the first core list decides, and an empty one counts as none."""
    start, end = search_plan.section_bounds(lines, KEYWORDS_KEY)
    if start is None:
        return None
    first = next((i for i in range(start + 1, end) if CORE_LIST.match(lines[i].strip())), None)
    return first if first is not None and CORE_LIST.match(lines[first].strip())[2].strip(" `,") else None


def _group_lines(lines: list[str]) -> list[int]:
    """The filled lines under Keywords that the plan searches: the core list, then the other named groups."""
    start, end = search_plan.section_bounds(lines, KEYWORDS_KEY)
    if start is None:
        return []
    core = _core_list_line(lines)
    others = [i for i in range(start + 1, end) if OTHER_GROUP.match(lines[i].strip())]
    return [*([core] if core is not None else []), *others]


def _is_limit(line: str) -> bool:
    """Whether the line is «- Nur <Portal>: …» (G105), whose terms run only on those portals."""
    found = search_plan.PAIR.match(line.strip())
    return bool(found and search_plan.LIMIT_LABEL.match(found[1].strip()))


def _new_term_line(lines: list[str]) -> int | None:
    """Where a new term goes: the core list, else the first other group, else an empty core list; never a «Nur»
    line, which would limit it to portals the person did not choose for it (G105)."""
    core = _core_list_line(lines)
    if core is not None:
        return core
    groups = _group_lines(lines)
    group = next((i for i in groups if not _is_limit(lines[i])), None)
    if group is not None or not groups:  # without any group the search reads the directions, so the term goes there
        return group
    start, end = search_plan.section_bounds(lines, KEYWORDS_KEY)
    return next((i for i in range(start + 1, end) if CORE_LIST.match(lines[i].strip())), None)


def _appended(line: str, term: str) -> str:
    kept = line.rstrip(" ,")
    return f"{kept} {term}" if kept.endswith(":") else f"{kept}, {term}"


def _words_as_shown(part: str, chars: int = MAX_VALUE) -> frozenset[str]:
    """The words of an entry as the plan cuts it, because the page can only name it like that."""
    return profession_words(" ".join(part.replace("`", "").split())[:chars])


def _as_apprenticeship(text: str) -> str:
    """The profile with the mark the apprenticeship plan reads, before its professions or its region.

    The start stays empty: only the person knows it, and the plan searches without one.
    """
    lines = text.split("\n")
    anchors = [next((i for i, row in enumerate(lines) if row.strip().lower() == title.lower()), None)
               for title in (search_plan.PROFESSIONS_SECTION, AFTER_DIRECTIONS)]
    place = next((i for i in anchors if i is not None), None)
    if place is None:
        return f"{text.rstrip()}\n\n{APPRENTICESHIP_MARK}\n"
    return "\n".join([*lines[:place], APPRENTICESHIP_MARK, "", *lines[place:]])


def added(text: str, name: str, kind: str | None = None, limit: int | None = MAX_KEYWORDS) -> str:
    """The profile text with this term at the end of what is searched; a term that is there changes nothing.

    With `kind` an apprenticeship, a profile that searches nothing yet becomes an apprenticeship profile (#147): the
    setup chose it, but a profile without a start lacks „## Lehrbeginn“. A profile with terms keeps its kind.
    A new term goes to the end of the saved order too (G87), also when an old line of the order still names it.
    `limit` None is for a caller that checked the limits of the whole choice itself (term_changes, #371).
    """
    changed = _added(text, name, kind, limit)
    return changed if changed == text else _without_in_order(changed, profession_words(name))


def _added(text: str, name: str, kind: str | None, limit: int | None) -> str:
    if APPRENTICESHIP_MARK not in text and kind == search_plan.KIND_APPRENTICESHIP and not current(text):
        text = _as_apprenticeship(text)
    if APPRENTICESHIP_MARK in text:
        return search_plan.with_profession(text, name)
    known = current(text)
    if profession_words(name) in map(profession_words, known):
        return text
    if limit is not None and len(known) >= limit:
        raise ValueError(T(FULL, limit=limit))
    clean = " ".join(name.split())
    lines = text.split("\n")
    target = _new_term_line(lines)
    if target is not None:
        return "\n".join([*lines[:target], _appended(lines[target], clean), *lines[target + 1:]])
    if _group_lines(lines):  # only «Nur» lines: the term gets a core list of its own, first under Keywords
        start, _ = search_plan.section_bounds(lines, KEYWORDS_KEY)
        return "\n".join([*lines[:start + 1], f"- Kernliste: {clean}", *lines[start + 1:]])
    if required_words.words_in(clean):
        raise ValueError(NO_REMARK_IN_DIRECTIONS)
    start, end = search_plan.section_bounds(lines, DIRECTIONS_SECTION[3:].lower())
    used = 0 if start is None else sum(bool(DIRECTION.match(row.strip())) for row in lines[start:end])
    if used >= MAX_DIRECTIONS:  # lines, not terms: one line can repeat a term or hold several (#316)
        raise ValueError(T(FULL_DIRECTIONS, limit=MAX_DIRECTIONS))
    return search_plan.with_section_line(text, DIRECTIONS_SECTION, f"{used + 1}. {clean}", AFTER_DIRECTIONS)


def _moved_up(line: str, body: str, dropped: int) -> str:
    """The line with a number that closes the gap; a priority follows only if it was the same as the number."""
    indent = line[:len(line) - len(line.lstrip())]
    old = int(line.strip().split(".", 1)[0])
    if not dropped:
        return line if body == DIRECTION.match(line.strip())[1] else f"{indent}{old}. {body}"
    new = max(old - dropped, 1)
    return f"{indent}{new}. {body.replace(f'(Priorität {old}', f'(Priorität {new}')}"


def _renumbered(text: str, title: str, change: Callable[[str], str | None]) -> str:
    """Every numbered line of the section through `change`; None drops it with the bullets indented below it."""
    lines = text.split("\n")
    start, end = search_plan.section_bounds(lines, title[3:].lower())
    if start is None:
        return text
    result, dropped, dropping = [], 0, False
    for line in lines[start + 1:end]:
        found = DIRECTION.match(line.strip())
        if found:
            body = change(found[1])
            dropping = body is None
            if dropping:
                dropped += 1
            else:
                result.append(_moved_up(line, body, dropped))
        elif not (dropping and line[:1] in (" ", "\t") and line.strip()):
            dropping = False
            result.append(line)
    return "\n".join([*lines[:start + 1], *result, *lines[end:]])


def _without_profession(wanted: frozenset[str]) -> Callable[[str], str | None]:
    def change(body: str) -> str | None:
        return None if _words_as_shown(search_plan.REMARK.sub("", body), MAX_PROFESSION_NAME) == wanted else body
    return change


def _without_direction(wanted: frozenset[str]) -> Callable[[str], str | None]:
    def change(body: str) -> str | None:
        terms, remark = TERMS_AND_REMARK.match(body).groups()
        parts = [part.strip() for part in terms.split(",") if part.strip()]
        kept = [part for part in parts if _words_as_shown(part, MAX_DIRECTION) != wanted]
        if len(kept) == len(parts):
            return body
        return f"{', '.join(kept)}{remark or ''}" if kept else None
    return change


def _without_term(part: str, wanted: frozenset[str]) -> str:
    """An entry of the core list without the term; „Verkauf/Sales“ is two terms to the plan (#176), so one can go.
    A remark in brackets, such as the required words (G110), stays with the rest of the entry."""
    terms = search_plan.split_terms(part)
    kept = [term.strip() for term in terms if _words_as_shown(term) != wanted]
    if len(kept) == len(terms):
        return part
    return f"{'/'.join(kept)}{''.join(search_plan.BRACKETS.findall(part))}" if kept else ""


def removed(text: str, name: str) -> str:
    """The profile text without this term, in the saved order too; a term that is not there changes nothing."""
    wanted = profession_words(name)
    return _without_in_order(_removed(text, wanted), wanted)


def _removed(text: str, wanted: frozenset[str]) -> str:
    if APPRENTICESHIP_MARK in text:
        return _renumbered(text, search_plan.PROFESSIONS_SECTION, _without_profession(wanted))
    lines = text.split("\n")
    groups = _group_lines(lines)
    if not groups:
        return _renumbered(text, DIRECTIONS_SECTION, _without_direction(wanted))
    changed = [*lines]
    for index in groups:
        changed[index] = _without_in_line(lines[index], wanted)
    return text if changed == lines else "\n".join(changed)


def removed_from_line(text: str, name: str, index: int) -> str:
    """The profile without this term in the one line at `index` only, such as the niches (#377); once the list no
    longer searches it, it leaves the saved order too."""
    lines = text.split("\n")
    wanted = profession_words(name)
    changed = _without_in_line(lines[index], wanted)
    if changed == lines[index]:
        return text
    after = "\n".join([*lines[:index], changed, *lines[index + 1:]])
    return after if is_searched(after, name) else _without_in_order(after, wanted)


def added_to_line(text: str, name: str, index: int) -> str:
    """The profile with this term at the end of the line at `index`; a term the line has changes nothing."""
    lines = text.split("\n")
    found = GROUP_LINE.match(lines[index].strip())
    if found is None:
        raise ValueError(T("Zeile {zeile} ist keine Liste von Begriffen", zeile=index + 1))
    if profession_words(name) in {_words_as_shown(term) for term in search_plan.split_terms(found[2])}:
        return text
    return "\n".join([*lines[:index], _appended(lines[index], " ".join(name.split())), *lines[index + 1:]])


def _without_in_order(text: str, wanted: frozenset[str]) -> str:
    """The saved order without this term, the rest numbered anew; without the section nothing changes."""
    def change(body: str) -> str | None:
        return None if profession_words(body) == wanted else body
    return _renumbered(text, search_plan.ORDER_SECTION, change)


def _order_block(names: tuple[str, ...]) -> list[str]:
    return [search_plan.ORDER_SECTION, ORDER_NOTE, *(f"{place}. {name}" for place, name in enumerate(names, 1)), ""]


def _with_order(text: str, names: tuple[str, ...]) -> str:
    """The profile with this order as its section, in place of the old one, or else before „## Region“ or at the end."""
    lines = text.split("\n")
    start, end = search_plan.section_bounds(lines, search_plan.ORDER_KEY)
    block = _order_block(names)
    if start is not None:
        return "\n".join([*lines[:start], *block, *lines[end:]])
    place = next((i for i, row in enumerate(lines) if row.strip() == AFTER_DIRECTIONS), None)
    if place is None:
        return "\n".join([text.rstrip(), "", *block])
    return "\n".join([*lines[:place], *block, *lines[place:]])


def _without_order(text: str) -> str:
    lines = text.split("\n")
    start, end = search_plan.section_bounds(lines, search_plan.ORDER_KEY)
    return text if start is None else "\n".join([*lines[:start], *lines[end:]])


def _profession_parts(body: str) -> tuple[list[numbered_order.Part], str]:
    name = search_plan.REMARK.sub("", body)
    return [(name, _words_as_shown(name, MAX_PROFESSION_NAME))], body[len(name):]


def _direction_parts(body: str) -> tuple[list[numbered_order.Part], str]:
    terms, remark = TERMS_AND_REMARK.match(body).groups()
    return [(part.strip(), _words_as_shown(part, MAX_DIRECTION)) for part in terms.split(",") if part.strip()], remark or ""


def _searches_groups(text: str) -> bool:
    return APPRENTICESHIP_MARK not in text and bool(_group_lines(text.split("\n")))


def searches_keyword_lines(text: str) -> bool:
    """Whether a job profile searches named lines under Keywords, so a term can move between them (G108)."""
    return _searches_groups(text)


def reordered(text: str, names: list[str]) -> str:
    """The profile with the searched terms in this order (G87); `names` must be exactly the terms searched now.

    The order names each term as the search reads it, so whatever the page sends, only known terms are written.
    Professions and search directions move within their numbered list, whose number is the priority the rating
    reads; terms from Keywords get the section, and search directions naming them follow it."""
    known = current(text)
    if sorted(map(key, names)) != sorted(map(key, known)):
        raise ValueError(ORDER_CHANGED)
    rest, ordered = known, ()
    for name in names:
        index = next(i for i, term in enumerate(rest) if profession_words(term) == profession_words(name))
        rest, ordered = (*rest[:index], *rest[index + 1:]), (*ordered, rest[index])
    words = tuple(map(profession_words, ordered))
    if APPRENTICESHIP_MARK in text:
        return _without_order(numbered_order.placed(text, search_plan.PROFESSIONS_SECTION, words, _profession_parts))
    if not _searches_groups(text):
        return _without_order(numbered_order.placed(text, DIRECTIONS_SECTION, words, _direction_parts))
    return numbered_order.aligned(_with_order(text, ordered), DIRECTIONS_SECTION, words, _direction_parts)


def _kept_order(old: str, new: str) -> str:
    """The order of the old profile, if the new one has none: the form does not show it. A numbered list from the
    form carries its own order."""
    lines = search_plan.section_lines(old, search_plan.ORDER_SECTION)
    if not lines or search_plan.section_lines(new, search_plan.ORDER_SECTION) or not _searches_groups(new):
        return new
    names = tuple(found[1] for found in map(DIRECTION.match, (line.strip() for line in lines)) if found)
    return _with_order(new, names) if names else new


def _without_in_line(line: str, wanted: frozenset[str],
                     without: Callable[[str, frozenset[str]], str] = _without_term) -> str:
    """A line such as „- Kernliste: a, b“ without the term, written as before; a comma in brackets splits nothing."""
    prefix, value = GROUP_LINE.match(line.strip()).groups()
    parts = [part.strip() for part in search_plan.ENTRY_COMMA.split(value) if part.strip()]
    kept = [rest for rest in (without(part, wanted) for part in parts) if rest]
    if kept == parts:
        return line
    indent = line[:len(line) - len(line.lstrip())]
    return f"{indent}{prefix}{', '.join(kept)}".rstrip()


def _title_line(lines: list[str], label: str) -> int | None:
    """The line of the title filter the search reads for this label: the first one that starts with it."""
    start, end = search_plan.section_bounds(lines, TITLE_SECTION[3:].lower())
    if start is None:
        return None
    return next((i for i in range(start + 1, end)
                 if (found := search_plan.PAIR.match(lines[i].strip())) and found[1].strip().lower().startswith(label)), None)


def with_title_term(text: str, label: str, term: str) -> str:
    """The profile with this term at the end of a title filter line (#210); a term that is there changes nothing."""
    clean = " ".join(term.split())
    known = {title_filter.bare(found).casefold() for found in search_plan.title_terms(text, label)}
    if title_filter.bare(clean).casefold() in known:
        return text
    lines = text.split("\n")
    index = _title_line(lines, label)
    if index is None:
        return search_plan.with_section_line(text, TITLE_SECTION, f"- {TITLE_LABELS[label]}: {clean}", AFTER_TITLES)
    line = lines[index].rstrip(" ,")
    joined = f"{line} {clean}" if line.endswith(":") else f"{line}, {clean}"
    return "\n".join([*lines[:index], joined, *lines[index + 1:]])


def without_title_term(text: str, label: str, term: str) -> str:
    """The profile without this term in a title filter line; „Developer/Engineer“ is two terms, so one can go. A term
    is the same with or without «(ganzes Wort)», and the rest of its group keeps the marker (G104)."""
    lines = text.split("\n")
    index = _title_line(lines, label)
    if index is None:
        return text
    changed = _without_in_line(lines[index], profession_words(title_filter.bare(term)), _without_title_term)
    return text if changed == lines[index] else "\n".join([*lines[:index], changed, *lines[index + 1:]])


def _without_title_term(part: str, wanted: frozenset[str]) -> str:
    terms = search_plan.split_terms(part)
    kept = [term for term in terms if _words_as_shown(term) != wanted]
    if len(kept) == len(terms):
        return part
    return title_filter.with_marker("/".join(kept)) if kept and title_filter.marked(part) else "/".join(kept)


def _keyword_line(lines: list[str], wanted: Callable[[str], bool]) -> int | None:
    """The first line under Keywords whose label `wanted` accepts."""
    start, end = search_plan.section_bounds(lines, KEYWORDS_KEY)
    found = ((i, search_plan.PAIR.match(lines[i].strip())) for i in range(start + 1, end)) if start is not None else ()
    return next((i for i, match in found if match and wanted(match[1].strip())), None)


def _with_keyword_line(text: str, line: str) -> str:
    """The profile with a new line after the last named line under Keywords, where the plan reads it."""
    lines = text.split("\n")
    start, end = search_plan.section_bounds(lines, KEYWORDS_KEY)
    if start is None:
        return search_plan.with_section_line(text, KEYWORDS_SECTION, line, TITLE_SECTION)
    last = max((i for i in range(start + 1, end) if search_plan.PAIR.match(lines[i].strip())), default=start)
    return "\n".join([*lines[:last + 1], line, *lines[last + 1:]])


def moved_to_niches(text: str, name: str) -> str:
    """The term leaves every searched line and joins the niches, which run without a place (G108, #383); its required
    words go with it (G110)."""
    entry = _as_written(text, name)
    without = removed(text, name)
    niche = _keyword_line(without.split("\n"), lambda label: label.lower().startswith(search_plan.NICHE_LABEL))
    if niche is not None:
        return added_to_line(without, entry, niche)
    return _with_keyword_line(without, NICHE_LINE.format(terms=entry))


def _as_written(text: str, name: str) -> str:
    """The term with the required words the profile gives it (G110), for a change that writes it elsewhere."""
    return required_words.with_words(" ".join(name.split()), required_words.written_words(text, name))


def limited_to(text: str, name: str, portals: tuple[str, ...]) -> str:
    """The term runs only on these portals (G105, G108): out of every searched line, into the «Nur» line that names
    exactly them, or a new one. Its place in the saved order stays, since the search still runs it."""
    entry = _as_written(text, name)
    without = _removed(text, profession_words(name))
    wanted = {portal.casefold() for portal in portals}
    line = _keyword_line(without.split("\n"), lambda label: {p.casefold() for p in search_plan.limit_portals(label) or ()} == wanted)
    if line is not None:
        return added_to_line(without, entry, line)
    return _with_keyword_line(without, LIMIT_LINE.format(portals=", ".join(portals), terms=entry))


def _kept_offers(old: str, new: str) -> str:
    """The wish from the page stays if the form says nothing about it."""
    if search_plan.OFFERS_SECTION in new or search_plan.OFFERS_SECTION not in old:
        return new
    lines = search_plan.section_lines(old, search_plan.OFFERS_SECTION)
    return search_plan.with_section_line(new, search_plan.OFFERS_SECTION, "\n".join(lines), APPRENTICESHIP_MARK) if lines else new


def _kept_limits(old: str, new: str) -> str:
    """The «Nur» lines of the old profile (G105), as written, after the new one's lines under Keywords: the form has
    no field for them, so it cannot mean to drop them, and their terms must not land in the core list."""
    written = {line.strip() for line in search_plan.section_lines(new, KEYWORDS_SECTION)}
    text = new
    for line in search_plan.section_lines(old, KEYWORDS_SECTION):
        if _is_limit(line) and line.strip() not in written:
            text = search_plan.with_section_line(text, KEYWORDS_SECTION, line, TITLE_SECTION)
    return text


def _kept_jobscout24_regions(old: str, new: str) -> str:
    """«Regionen (jobscout24)» (G107) is chosen on Suche einstellen; the form has no field for it, so it stays."""
    def regions_line(text: str) -> str | None:
        found = (search_plan.PAIR.match(line.strip()) for line in search_plan.section_lines(text, REGION_SECTION))
        return next((match[0] for match in found if match and search_plan.is_jobscout24_regions(match[1])), None)
    line = regions_line(old)
    if line is None or regions_line(new) is not None:
        return new
    return search_plan.with_section_line(new, REGION_SECTION, line, KEYWORDS_SECTION)


def _kept_niche_remote(old: str, new: str) -> str:
    """The remote switch for niches (G125) is set on Suche einstellen; the form has no field for it, so it stays, under
    «- Remote: …» of the new profile."""
    value = search_frame.raw_value(old, search_frame.NICHE_REMOTE)
    if not value or search_frame.raw_value(new, search_frame.NICHE_REMOTE):
        return new
    return search_frame.with_raw_value(new, search_frame.NICHE_REMOTE, value)


def kept_on_replace(old: str, new: str) -> tuple[str, tuple[str, ...]]:
    """A profile from the form replaces the old one: what the old one searched stays, after what the form names.

    Terms are added and removed on the page without the form knowing, so the form cannot mean to drop them. Whoever
    does not want one any more removes it on the page. The order set there stays too (G87). A different kind of
    search shares nothing.
    """
    if (APPRENTICESHIP_MARK in old) != (APPRENTICESHIP_MARK in new):
        return new, ()
    text, kept = _kept_niche_remote(old, _kept_jobscout24_regions(old, _kept_limits(old, new))), []
    for term in current(old):
        try:
            # its required words only where they count, under Keywords (G110)
            changed = added(text, _as_written(old, term) if _searches_groups(text) else term)
        except ValueError:  # the list is full: the rest stays only in the draft of the old profile
            break
        if changed != text:
            kept = [*kept, term]
        text = changed
    text = _kept_order(old, text)
    return (_kept_offers(old, text) if APPRENTICESHIP_MARK in new else text), tuple(kept)

