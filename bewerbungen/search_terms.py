"""What a person searches for, and changing it from the page (MIN-375).

An apprenticeship profile names professions. A job profile searches its line „Kernliste“ if it has one, else its numbered
search directions, where one line can hold several terms and bullets of its own. Everything else in the profile stays as written.
"""
import re
from collections.abc import Callable

import search_plan
from search_plan import APPRENTICESHIP_MARK, DIRECTION, MAX_KEYWORDS, MAX_VALUE, profession_words

DIRECTIONS_SECTION = "## Suchrichtungen"
KEYWORDS_KEY = "keywords"
AFTER_DIRECTIONS = "## Region"
CORE_LIST = re.compile(r"^(-\s+kernliste[^:]*:\s*)(.*)$", re.IGNORECASE)
TERMS_AND_REMARK = re.compile(r"^([^(]*?)(\s*\(.*)?$")
FULL = "Ihre Suche hat schon {limit} Begriffe, mehr sucht sie nicht. Entfernen Sie zuerst einen."


def current(text: str) -> tuple[str, ...]:
    return search_plan.professions_in(text) if APPRENTICESHIP_MARK in text else search_plan.job_terms(text)


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


def _words_as_shown(part: str) -> frozenset[str]:
    """The words of an entry as the plan cuts it, because the page can only name it like that."""
    return profession_words(" ".join(part.replace("`", "").split())[:MAX_VALUE])


def added(text: str, name: str) -> str:
    """The profile text with this term at the end of what is searched; a term that is there changes nothing."""
    if APPRENTICESHIP_MARK in text:
        return search_plan.with_profession(text, name)
    known = current(text)
    if profession_words(name) in map(profession_words, known):
        return text
    if len(known) >= MAX_KEYWORDS:
        raise ValueError(FULL.format(limit=MAX_KEYWORDS))
    clean = " ".join(name.split())
    lines = text.split("\n")
    core = _core_list_line(lines)
    if core is not None:
        return "\n".join([*lines[:core], f"{lines[core].rstrip(' ,')}, {clean}", *lines[core + 1:]])
    start, end = search_plan.section_bounds(lines, DIRECTIONS_SECTION[3:].lower())
    used = 0 if start is None else sum(bool(DIRECTION.match(row.strip())) for row in lines[start:end])
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
        return None if _words_as_shown(search_plan.REMARK.sub("", body)) == wanted else body
    return change


def _without_direction(wanted: frozenset[str]) -> Callable[[str], str | None]:
    def change(body: str) -> str | None:
        terms, remark = TERMS_AND_REMARK.match(body).groups()
        parts = [part.strip() for part in terms.split(",") if part.strip()]
        kept = [part for part in parts if _words_as_shown(part) != wanted]
        if len(kept) == len(parts):
            return body
        return f"{', '.join(kept)}{remark or ''}" if kept else None
    return change


def removed(text: str, name: str) -> str:
    """The profile text without this term; a term that is not there changes nothing."""
    wanted = profession_words(name)
    if APPRENTICESHIP_MARK in text:
        return _renumbered(text, search_plan.PROFESSIONS_SECTION, _without_profession(wanted))
    lines = text.split("\n")
    core = _core_list_line(lines)
    if core is None:
        return _renumbered(text, DIRECTIONS_SECTION, _without_direction(wanted))
    prefix, value = CORE_LIST.match(lines[core].strip()).groups()
    parts = [part.strip() for part in value.split(",") if part.strip()]
    kept = [part for part in parts if _words_as_shown(part) != wanted]
    if len(kept) == len(parts):
        return text
    indent = lines[core][:len(lines[core]) - len(lines[core].lstrip())]
    return "\n".join([*lines[:core], f"{indent}{prefix}{', '.join(kept)}".rstrip(), *lines[core + 1:]])


def _kept_offers(old: str, new: str) -> str:
    """The wish from the page stays if the form says nothing about it."""
    if search_plan.OFFERS_SECTION in new or search_plan.OFFERS_SECTION not in old:
        return new
    lines = search_plan.section_lines(old, search_plan.OFFERS_SECTION)
    return search_plan.with_section_line(new, search_plan.OFFERS_SECTION, "\n".join(lines), APPRENTICESHIP_MARK) if lines else new


def kept_on_replace(old: str, new: str) -> tuple[str, tuple[str, ...]]:
    """A profile from the form replaces the old one: what the old one searched stays, after what the form names.

    Terms are added and removed on the page without the form knowing, so the form cannot mean to drop them. Whoever
    does not want one any more removes it on the page. A different kind of search shares nothing.
    """
    if (APPRENTICESHIP_MARK in old) != (APPRENTICESHIP_MARK in new):
        return new, ()
    text, kept = new, []
    for term in current(old):
        try:
            changed = added(text, term)
        except ValueError:  # the list is full: the rest stays only in the draft of the old profile
            break
        if changed != text:
            kept = [*kept, term]
        text = changed
    return (_kept_offers(old, text) if APPRENTICESHIP_MARK in new else text), tuple(kept)

