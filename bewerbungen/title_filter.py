"""How a term of the title filter matches a job title (G31, G104), for the search and everything that counts like it.

German joins words: „Softwareentwickler:in“, „Erwachsenenbildung“. So a term also matches as the start or the end of a
word, in any case, but never in its middle. A term of three letters or digits at most („KI“, „QA“, „SAP“) would hide
in too many words and matches only as a whole word, as does a term the person marks with «(ganzes Wort)», such as
„Intern (ganzes Wort)“, which leaves „International“ alone. The marker stays on the term as the profile writes it, so
every list that carries the term carries the rule too.
"""
import dataclasses
import re

WHOLE_WORD = "(ganzes Wort)"
MAX_SHORT = 3  # letters and digits of a term that only matches as a whole word
_MARKER = re.compile(r"\s*\(\s*ganzes\s+wort\s*\)", re.IGNORECASE)
_WORD_CHARACTER = re.compile(r"\w")


def marked(value: str) -> bool:
    """Whether the person wrote «(ganzes Wort)» in this entry; for a slash group it holds for each alternative."""
    return _MARKER.search(value or "") is not None


def bare(term: str) -> str:
    """The term without the marker, as the title shows it."""
    return " ".join(_MARKER.sub(" ", term or "").split())


def with_marker(term: str) -> str:
    return f"{bare(term)} {WHOLE_WORD}"


def whole_word(term: str) -> bool:
    return marked(term) or len(_WORD_CHARACTER.findall(bare(term))) <= MAX_SHORT


def _pattern(term: str) -> re.Pattern:
    word = re.escape(bare(term))
    rule = rf"(?<!\w){word}(?!\w)" if whole_word(term) else rf"(?<!\w){word}|{word}(?!\w)"
    return re.compile(rule, re.IGNORECASE)


def matches(title: str, term: str) -> bool:
    return bool(bare(term)) and _pattern(term).search(title or "") is not None


def all_matches(title: str, terms: tuple[str, ...]) -> tuple[str, ...]:
    """Every term that matches, in the order of the list."""
    return tuple(term for term in terms if matches(title, term))


def first_match(title: str, terms: tuple[str, ...]) -> str | None:
    return next((term for term in terms if matches(title, term)), None)


@dataclasses.dataclass(frozen=True)
class Verdict:
    """What the title filter made of one title: the exclusions it has, else the positive terms that let it through.
    `without_term`: there are positive terms and the title has none of them."""
    excluded_by: tuple[str, ...]
    passed_by: tuple[str, ...]
    without_term: bool

    @property
    def kept_out(self) -> bool:
        return bool(self.excluded_by) or self.without_term


def verdict(title: str, exclude: tuple[str, ...], positive: tuple[str, ...]) -> Verdict:
    excluded_by = all_matches(title, exclude)
    passed_by = () if excluded_by else all_matches(title, positive)
    return Verdict(excluded_by, passed_by, not excluded_by and bool(positive) and not passed_by)
