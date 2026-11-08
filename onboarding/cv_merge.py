"""Merge the answers of the form into an existing cv.yaml instead of rewriting it (#159, #160, G23).

The form shows only part of the format in lebenslauf/README.md (cv_read.py reads that part). Saving changes only
what the form shows and the answers changed. Keys it never writes (basics.image, basics.x-image, x-* …), fields it
cannot show on an entry (x-display on work, url on projects, …), entries it shows nothing of, and comments and order
stay as they are (ruamel.yaml, like lebenslauf/fotoausschnitt.py). Answers are matched to entries by content, so an
edited or removed entry does not hand its fields to another. Only the job track shows basics.label, basics.url,
basics.summary, basics.profiles, education.area, projects and teaching (G25); the apprenticeship track leaves them alone. Tags are answers since G24, but only
where the answers give them (convert.build_cv with answer_keys): an empty list removes them, no key keeps those of the
file, as for answers from before G24. The same holds for projects, teaching and basics.url (G25, keepUnlessGiven in
form.json): answers from before G25 keep them, an empty list or text removes them. A highlight with tags is written as {text, tags}, one without as plain text, and
new lists of tags in the short form [a, b].
"""
import dataclasses
import io
import re
from collections.abc import Callable

from ruamel.yaml import YAML, YAMLError
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.util import load_yaml_guess_indent

import convert
from cv_read import (BIRTH, INTERESTS, KEPT_BASICS, KEPT_SECTIONS, LOCATION, SECTIONS, TEXT_BASICS, detail_places,
                     detail_values, entry_shown, field_text, highlight_shown, item_text, tag_text)

ABSENT = object()
TAGS = "tags"
HEADINGS = "x-beschriftungen"
JOB_ONLY = {"basics": ("label", "url", "summary", "profiles"), "education": ("area",)}
JOB_ONLY_SECTIONS = frozenset({"projects", "teaching"})
IDENTITY = {"work": ("name", "position", "startDate"), "teaching": ("name", "position", "startDate"),
            "projects": ("name", "description"), "education": ("studyType", "institution", "text"),
            "certificates": ("name", "text"), "languages": ("language",), "skills": ("name",), "interests": ("name",)}
DEFAULT_INDENT = 2
COMMENT_SLOTS, MAP_TAIL, SEQ_TAIL = 4, 2, 0  # layout of ruamel's comment entries (ca.items)
NESTED_MAPPING = re.compile(r"^( *)[^ #\-][^\n]*:[ \t]*\n(?:[ \t]*(?:#[^\n]*)?\n)*( *)[^ #\-\n]", re.M)

Pairing = Callable[[int, list[int], list, object], int | None]
LineMerge = Callable[[object, object], object]


@dataclasses.dataclass(frozen=True)
class Kind:
    """How the form shows the entries of a list, how an answer finds the entry it continues, and (for lines that are
    not plain text) how the answer goes into it."""
    shown: Callable[[object], object]
    fields: tuple[str, ...]
    fallback: Pairing
    merge: LineMerge | None = None


def merged_text(existing_text: str, new_cv: dict, track: str, note: str) -> str | None:
    """The file with the answers merged in; None if it cannot be read, so it stays as it was."""
    try:
        y = _yaml(existing_text)
        doc = y.load(existing_text)
    except (YAMLError, ValueError):
        return None
    if doc is None:
        return convert.cv_file(_settled(_given(new_cv)), note)
    if not isinstance(doc, CommentedMap) or not isinstance(doc.get("basics", {}), (dict, type(None))):
        return None
    # doc is a fresh copy of the file, changed only here
    changed = _merge_cv(doc, new_cv, track == "job")  # new_cv is read only
    if not changed:
        return existing_text
    out = io.StringIO()
    y.dump(doc, out)
    return out.getvalue()


def _yaml(text: str) -> YAML:
    """Round-trip YAML with the indentation of the file, so unchanged parts are written back as they were."""
    _, sequence, offset = load_yaml_guess_indent(text)
    nested = NESTED_MAPPING.search(text)
    mapping = len(nested.group(2)) - len(nested.group(1)) if nested else DEFAULT_INDENT
    y = YAML()
    y.preserve_quotes = True
    y.width = 4096
    y.indent(mapping=mapping if mapping > 0 else DEFAULT_INDENT, sequence=sequence or DEFAULT_INDENT, offset=offset or 0)
    y.representer.add_representer(type(None), lambda r, _: r.represent_scalar("tag:yaml.org,2002:null", "null"))
    return y


def _given(new_cv: dict) -> dict:
    """The answers without the empty values that only say "remove": nothing to write where the file has nothing."""
    basics = {key: value for key, value in new_cv.get("basics", {}).items() if key not in KEPT_BASICS or value}
    rest = {key: value for key, value in new_cv.items() if key != "basics" and (key not in KEPT_SECTIONS or value)}
    return {"basics": basics, **rest} if "basics" in new_cv else rest


def _merge_cv(doc: CommentedMap, new_cv: dict, job: bool) -> bool:
    merged = [key for key in SECTIONS
              if (job or key not in JOB_ONLY_SECTIONS) and (key in new_cv or key not in KEPT_SECTIONS)]
    changes = [_merge_basics(doc, new_cv.get("basics", {}), job),
               *(_merge_list(doc, key, new_cv.get(key, []), _entry_kind(key, SECTIONS[key], job)) for key in merged),
               _merge_list(doc, "interests", new_cv.get("interests", []), _entry_kind("interests", INTERESTS, job)),
               _merge_headings(doc, new_cv)]
    return any(changes)


def _merge_basics(doc: CommentedMap, new: dict, job: bool) -> bool:
    basics = doc.get("basics")
    if basics is None:
        if not new:
            return False
        given = _given({"basics": new})["basics"]
        if "basics" in doc:
            doc["basics"] = given
        else:
            doc.insert(0, "basics", given)
        return True
    texts = [key for key in (*TEXT_BASICS, "summary")
             if (job or key not in JOB_ONLY["basics"]) and (key in new or key not in KEPT_BASICS)]
    changes = [*(_merge_scalar(basics, key, new.get(key) or ABSENT) for key in texts),
               _merge_location(basics, new.get("location", {})),
               _merge_details(basics, new.get("details", []))]
    if job:
        changes.append(_merge_list(basics, "profiles", new.get("profiles", []), PROFILES))
    return any(changes)


def _merge_scalar(entry: dict, key: str, new: object) -> bool:
    """Set or remove one text field; a value the form could not show stays unless the answers give one."""
    old_text = field_text(key, entry.get(key)) if key in entry else ""
    new_text = "" if new is ABSENT or new is None else new
    if (old_text is None and not new_text) or old_text == new_text:
        return False
    if new is ABSENT:
        del entry[key]
    else:
        entry[key] = new
    return True


def _merge_location(basics: CommentedMap, new: dict) -> bool:
    old = basics.get("location")
    if not isinstance(old, dict):
        if not new:
            return False
        basics["location"] = new
        return True
    changed = any([_merge_scalar(old, key, new.get(key, ABSENT)) for key in LOCATION])
    if changed and not old:
        del basics["location"]
    return changed


def _merge_details(basics: CommentedMap, new: list) -> bool:
    """basics.details holds the birth date and the nationality of the form among other lines, which stay."""
    old = basics.get("details")
    if not isinstance(old, list):
        if not new:
            return False
        basics["details"] = new
        return True
    birth, nationality = detail_values(new)
    at_birth, at_nationality = detail_places(old)
    lines = [(line, index) for index, line in enumerate(old)]
    lines = _put_line(lines, at_birth, BIRTH + birth if birth else "", 0)
    # a new nationality goes right after the birth date, as convert._basics writes them
    after_birth = next((i + 1 for i, (_, index) in enumerate(lines) if index == at_birth), 0)
    lines = _put_line(lines, at_nationality, nationality, after_birth)
    return _put_list(basics, "details", lines)


def _put_line(lines: list, at: int | None, text: str, insert_at: int) -> list:
    """Lines with the one at old index `at` set to text (or removed when empty); a new one goes to insert_at."""
    if at is None:
        return [*lines[:insert_at], (text, None), *lines[insert_at:]] if text else lines
    position = next(i for i, (_, index) in enumerate(lines) if index == at)
    line = lines[position][0]
    if not text:
        return [*lines[:position], *lines[position + 1:]]
    if line.strip() == text:
        return lines
    return [*lines[:position], (text, at), *lines[position + 1:]]


def _merge_list(parent: CommentedMap, key: str, new: list, kind: Kind) -> bool:
    """Merge answers into a list of entries or lines: matched ones are updated, unshown ones stay in place."""
    old = parent.get(key)
    if not isinstance(old, list):
        if not new:
            return False
        parent[key] = _new_value(key, new)
        return True
    old_shown = [kind.shown(item) for item in old]
    kept = [_kept_fields(item, kind) for item in new]
    pairs = _match(old_shown, [kind.shown(item) for item in new], kind.fallback, kept)
    edits = [_merge_item(old, j, new[i], kind) for i, j in enumerate(pairs)]
    picks = list(zip(edits, pairs))
    for index, shown in enumerate(old_shown):
        if shown is None:
            picks.insert(min(index, len(picks)), (old[index], index))
    updated = any(j is not None and kind.shown(old[j]) != old_shown[j] for j in pairs)
    return _put_list(parent, key, picks) or updated


def _merge_item(old: list, j: int | None, new: object, kind: Kind) -> object:
    """The entry or line that continues old[j] with the answer new; a new answer as it is."""
    if j is None:
        return new
    item = old[j]
    if kind.merge:
        return kind.merge(item, new)
    if isinstance(new, dict):
        for key in kind.fields:
            if key in KEPT_UNLESS_GIVEN and key not in new:
                continue
            if key in LIST_KINDS:
                _merge_list(item, key, new.get(key, []), LIST_KINDS[key])
            else:
                _merge_scalar(item, key, new.get(key, ABSENT))
        return item
    if item_text(item) == new:
        return item
    if isinstance(item, dict):
        item["text"] = new
        return item
    return new


def _kept_fields(answer: object, kind: Kind) -> tuple[str, ...]:
    """Fields an answer leaves to the file: tags it does not give (a highlight as plain text gives none)."""
    if kind is HIGHLIGHTS:
        return (TAGS,) if not isinstance(answer, dict) or TAGS not in answer else ()
    return tuple(key for key in kind.fields if key in KEPT_UNLESS_GIVEN and isinstance(answer, dict) and key not in answer)


def _without(shown: object, keys: tuple[str, ...]) -> object:
    """What an answer that leaves keys to the file is compared on; a line without its tags is its text."""
    if not keys or not isinstance(shown, dict):
        return shown
    rest = {key: value for key, value in shown.items() if key not in keys}
    return rest["text"] if list(rest) == ["text"] else rest


def _match(old_shown: list, new_shown: list, fallback: Pairing, kept: list[tuple[str, ...]]) -> list[int | None]:
    """For each answer the index of the old entry it continues, or None for a new one; equal ones first."""
    pairs: list[int | None] = [None] * len(new_shown)
    free = [i for i, shown in enumerate(old_shown) if shown is not None]
    for i, shown in enumerate(new_shown):
        same = [k for k in free if _without(old_shown[k], kept[i]) == _without(shown, kept[i])]
        j = i if i in same else next(iter(same), None)
        if j is not None:
            pairs[i] = j
            free.remove(j)
    for i, shown in enumerate(new_shown):
        j = None if pairs[i] is not None else fallback(i, free, old_shown, shown)
        if j is not None:
            pairs[i] = j
            free.remove(j)
    return pairs


def _same_place(i: int, free: list[int], old_shown: list, shown: object) -> int | None:
    return i if i in free else None


def _line_text(shown: object) -> object:
    return shown["text"] if isinstance(shown, dict) else shown


def _same_text_or_place(i: int, free: list[int], old_shown: list, shown: object) -> int | None:
    """A line whose tags changed continues the line with its text; an edited one the line in its place."""
    text = _line_text(shown)
    same = next((k for k in free if _line_text(old_shown[k]) == text), None)
    return same if same is not None else _same_place(i, free, old_shown, shown)


def _merge_highlight(item: object, new: object) -> object:
    """The highlight that continues item with the answer: its text, its tags if it gives them, other fields kept.

    One that loses its last tag becomes plain text again, unless it holds more than its text.
    """
    text = new["text"] if isinstance(new, dict) else new
    tags = new.get(TAGS) if isinstance(new, dict) else None  # None: the answer leaves the tags to the file
    if not isinstance(item, dict):
        return item if item_text(item) == text and not tags else _commented({"text": text, TAGS: tags} if tags else text)
    if item_text(item) != text:
        item["text"] = text
    if tags is None:
        return item
    had_tags = TAGS in item
    _merge_list(item, TAGS, tags, TAG_LINES)
    if had_tags and TAGS not in item and list(item) == ["text"]:
        return item["text"]
    return item


def _no_pairing(i: int, free: list[int], old_shown: list, shown: object) -> int | None:
    return None


def _same_identity(identity: tuple[str, ...]) -> Pairing:
    """An edited entry still continues the old one when one of its identifying fields is the same."""

    def pairing(i: int, free: list[int], old_shown: list, shown: object) -> int | None:
        if not shown:
            return None
        fits = [k for k in free if any(shown.get(key) and old_shown[k].get(key) == shown.get(key) for key in identity)]
        return i if i in fits else next(iter(fits), None)

    return pairing


def _put_list(parent: CommentedMap, key: str, picks: list[tuple[object, int | None]]) -> bool:
    """Write the list picked from the old one (value, old index or None); False when it is the same list.

    The old list is refilled in place: ruamel keeps the blank lines after a list on the list itself.
    """
    old = parent[key]
    if [j for _, j in picks] == list(range(len(old))) and all(value is old[j] for value, j in picks):
        return False
    if not picks:
        del parent[key]
        return True
    comments = dict(old.ca.items)
    blank = _take_blank_lines(_tail(old, len(old) - 1)) if old and picks[-1][1] != len(old) - 1 else None
    del old[:]
    old.ca.items.clear()
    old.extend(_commented(value) for value, _ in picks)
    for index, (_, j) in enumerate(picks):
        if j is not None and j in comments:
            old.ca.items[index] = comments[j]
    if blank is not None:
        _put_blank_lines(_tail(old, len(old) - 1), blank)
    return True


def _settled(value: object) -> object:
    """New answers as the file writes them: no empty list of tags, a highlight without tags as plain text."""
    if isinstance(value, (CommentedMap, CommentedSeq)):
        return value
    if isinstance(value, list):
        return [_settled(item) for item in value]
    if not isinstance(value, dict):
        return value
    if value.get(TAGS) == []:
        rest = {key: item for key, item in value.items() if key != TAGS}
        return rest["text"] if list(rest) == ["text"] else _settled(rest)
    return {key: _settled(item) for key, item in value.items()}


def _commented(value: object) -> object:
    """New answers as round-trip nodes, so blank lines and comments can attach to them."""
    value = _settled(value)
    if isinstance(value, dict) and not isinstance(value, CommentedMap):
        return CommentedMap((key, _new_value(key, item)) for key, item in value.items())
    if isinstance(value, list) and not isinstance(value, CommentedSeq):
        return CommentedSeq(_commented(item) for item in value)
    return value


def _new_value(key: object, value: object) -> object:
    """A new value under key; tags in the short form [a, b], as lebenslauf/README.md writes them."""
    node = _commented(value)
    if key == TAGS and isinstance(node, CommentedSeq):
        node.fa.set_flow_style()
    return node


def _tail(node: CommentedMap | CommentedSeq, key: object) -> tuple:
    """Where ruamel keeps what follows the last value under node[key]: (container, key, place in its comment entry)."""
    value = node[key]
    if isinstance(value, (CommentedMap, CommentedSeq)) and value and not value.fa.flow_style():
        return _tail(value, list(value)[-1] if isinstance(value, CommentedMap) else len(value) - 1)
    return node, key, MAP_TAIL if isinstance(node, CommentedMap) else SEQ_TAIL


def _take_blank_lines(tail: tuple) -> object | None:
    """Blank lines after a list belong after its new last entry; a comment stays with its line."""
    container, key, place = tail
    entry = container.ca.items.get(key)
    if not entry or entry[place] is None or entry[place].value.strip():
        return None
    token, entry[place] = entry[place], None
    return token


def _put_blank_lines(tail: tuple, token: object) -> None:
    container, key, place = tail
    slot = container.ca.items.setdefault(key, [None] * COMMENT_SLOTS)
    if slot[place] is None:
        slot[place] = token


def _merge_headings(doc: CommentedMap, new_cv: dict) -> bool:
    """The headings the apprenticeship track sets follow the track; any others are the person's own."""
    made = new_cv.get(HEADINGS)
    if made and HEADINGS not in doc:
        doc[HEADINGS] = made
        return True
    if not made and HEADINGS in doc and doc[HEADINGS] == convert.APPRENTICESHIP_HEADINGS:
        del doc[HEADINGS]
        return True
    return False


def _entry_kind(key: str, fields: tuple[str, ...], job: bool) -> Kind:
    owned = tuple(field for field in fields if job or field not in JOB_ONLY.get(key, ()))
    return Kind(lambda entry: entry_shown(entry, owned), owned, _same_identity(IDENTITY[key]))


def _profile_shown(profile: object) -> dict | None:
    shown = entry_shown(profile, ("url",))
    return {"url": convert.full_url(shown["url"])} if shown else None


LINES = Kind(item_text, (), _same_place)
TAG_LINES = Kind(tag_text, (), _same_place)
HIGHLIGHTS = Kind(highlight_shown, (), _same_text_or_place, _merge_highlight)
LIST_KINDS = {"highlights": HIGHLIGHTS, "keywords": LINES, TAGS: TAG_LINES}
KEPT_UNLESS_GIVEN = frozenset({TAGS})
PROFILES = Kind(_profile_shown, (), _no_pairing)
