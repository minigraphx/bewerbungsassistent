"""Required words of a broad keyword (G110, #386): «Berufsbildner (nur mit Informatik, ICT, Plattform)».

The remark follows an entry on any line under Keywords that the search reads (core list, named groups, «Nur» lines,
niches); in a slash group it holds for every alternative. The portals get only the term: `search_plan.split_terms`
leaves every bracket out, so older apps read plain «Berufsbildner». A term the profile lists once more without a remark
has none, as a term on a line without «Nur» runs everywhere (G105). Numbered search directions and apprenticeship
profiles carry none.

A hit that only such terms found stays only if its title, or the ad text that is loaded anyway, names one of the
words, matched like the title filter (G104). The others are not stored; their links wait in `ohne-pflichtbezug.yaml`
with the words they lacked, so that the next run does not load them again, until the remark changes. No AI, no fetch
of its own.
"""
import dataclasses
import pathlib
import re
from collections.abc import Iterable

import search_plan
import title_filter
from dateien import lies_yaml, schreibe_yaml

REASON = "ohne Pflichtbezug"
LINKS_FILE = "ohne-pflichtbezug.yaml"
MAX_LINKS = 3000  # links remembered; the oldest go first
MAX_WORDS = 20
# A word as the add field takes it: like a job term (ai/career.JOB_TERM), without the comma that separates the words.
WORD = re.compile(r"[^\x00-\x1f\x85  #<>,()`:|/]+")

Key = frozenset[str]


def _merged(groups: Iterable[tuple[str, ...]]) -> tuple[str, ...]:
    """The words of several remarks, each once whatever its case, in the order they came."""
    seen: dict[str, str] = {}
    for word in (word for group in groups for word in group):
        seen = seen if word.casefold() in seen else {**seen, word.casefold(): word}
    return tuple(seen.values())[:MAX_WORDS]


def words_in(entry: str) -> tuple[str, ...]:
    """The required words of one entry, as written; none without a remark «(nur mit …)»."""
    found = search_plan.REQUIRED_REMARK.search(entry or "")
    if found is None:
        return ()
    return _merged([tuple(" ".join(word.split()) for word in found[1].split(",") if word.strip())])


def is_remark_valid(entry: str) -> bool:
    """Whether an entry with a remark names at least one word, and every word is one the add field takes."""
    found = search_plan.REQUIRED_REMARK.search(entry or "")
    words = [word.strip() for word in found[1].split(",")] if found else []
    return bool(words) and all(word and WORD.fullmatch(word) for word in words)


def bare(entry: str) -> str:
    """The entry without its remark, as the search and the page name the term."""
    return " ".join(search_plan.REQUIRED_REMARK.sub("", entry or "").split())


def with_words(term: str, words: tuple[str, ...]) -> str:
    """The entry as the profile writes it: the term, and its remark if it has words."""
    return f"{bare(term)} (nur mit {', '.join(words)})" if words else bare(term)


def _key(term: str) -> Key:
    return search_plan.profession_words(term)


def _entries(value: str) -> list[tuple[list[str], tuple[str, ...]]]:
    """Each entry of a line: its terms (a slash group has several) and the words of its remark."""
    return [(search_plan.split_terms(entry), words_in(entry)) for entry in search_plan.ENTRY_COMMA.split(value)]


def entry_words(value: str, name: str) -> tuple[str, ...]:
    """The words of the entry of this line value that holds the term; none if it has no remark."""
    wanted = _key(name)
    return next((words for terms, words in _entries(value) if any(_key(term) == wanted for term in terms)), ())


def written_words(text: str, name: str) -> tuple[str, ...]:
    """The words the profile gives this term on the first line that has a remark for it, so that a change written
    elsewhere takes them along."""
    if search_plan.APPRENTICESHIP_MARK in text:
        return ()
    return next((words for words in (entry_words(value, name) for value in search_plan.keyword_values(text)) if words), ())


@dataclasses.dataclass(frozen=True)
class Required:
    """Per term (by its words) the words its hits need; a term without any is not listed."""
    terms: tuple[tuple[Key, tuple[str, ...]], ...] = ()

    def of_term(self, name: str) -> tuple[str, ...]:
        return dict(self.terms).get(_key(name), ())

    def of_queries(self, queries) -> tuple[str, ...]:
        """The words a hit needs: those of its terms when every query that found it had one; none as soon as another
        keyword found it too, or for a hit without queries (an older extension)."""
        found = dict(self.terms)
        keys = [_key(query["stichwort"]) for query in queries or []
                if isinstance(query, dict) and isinstance(query.get("stichwort"), str)]
        if not keys or any(key not in found for key in keys):
            return ()
        return _merged(found[key] for key in keys)


NONE = Required()


def of_profile(text: str) -> Required:
    """The required words of a job profile's terms."""
    if search_plan.APPRENTICESHIP_MARK in text:
        return NONE
    remarked: dict[Key, tuple[str, ...]] = {}
    plain: frozenset[Key] = frozenset()
    for value in search_plan.keyword_values(text):
        for terms, words in _entries(value):
            for key in filter(None, map(_key, terms)):
                if words:
                    remarked = {**remarked, key: _merged((remarked.get(key, ()), words))}
                else:
                    plain = plain | {key}
    return Required(tuple((key, words) for key, words in remarked.items() if key not in plain))


def of_folder(data_dir: pathlib.Path) -> Required:
    path = data_dir / search_plan.PROFILE
    return of_profile(path.read_text(encoding="utf-8")) if path.is_file() else NONE


def fits(words: tuple[str, ...], *texts: str) -> bool:
    """Whether a title or an ad text names one of the words, as the title filter matches a term."""
    return any(title_filter.matches(text, word) for text in texts if text for word in words)


def _fingerprint(words: tuple[str, ...]) -> list[str]:
    return sorted({word.casefold() for word in words})


def remembered(folder: pathlib.Path) -> dict[str, list[str]]:
    """Links screened out for want of a required word, each with the words it lacked; the file is data."""
    raw = lies_yaml(folder / LINKS_FILE, {})
    if not isinstance(raw, dict):
        return {}
    return {link: words for link, words in raw.items()
            if isinstance(link, str) and isinstance(words, list) and all(isinstance(word, str) for word in words)}


def was_unrelated(known: dict[str, list[str]], link: str, words: tuple[str, ...]) -> bool:
    """Screened out before for the same words: a changed remark asks for the ad again."""
    return known.get(link) == _fingerprint(words)


def remember(folder: pathlib.Path, found: list[tuple[str, tuple[str, ...]]]) -> None:
    """Note screened-out links with their words; the caller holds the lock of the hits."""
    if not found:
        return
    known = remembered(folder)
    added = {link: _fingerprint(words) for link, words in found}
    kept = {link: words for link, words in known.items() if link not in added}
    merged = list({**kept, **added}.items())[-MAX_LINKS:]
    schreibe_yaml(folder / LINKS_FILE, dict(merged))
