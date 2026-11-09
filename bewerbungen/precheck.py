"""Rule-based pre-check of an ad before rating (G33): languages, degree and excluded technologies.

Fixed rules, no AI. A hit that fails keeps its place in the list, below the others, with the reason. Whatever is
missing lets the hit pass: an ad without a level, a person without languages or degree in cv.yaml and profile.
Excluded technologies come from the profile, section „Ausschlüsse“, line „Technologien als Schwerpunkt“.
"""
import dataclasses
import pathlib
import re

import yaml

import search_plan

LANGUAGES = {"deutsch": "deutsch", "german": "deutsch", "französisch": "französisch", "franzoesisch": "französisch",
             "french": "französisch", "englisch": "englisch", "english": "englisch", "italienisch": "italienisch",
             "italian": "italienisch", "spanisch": "spanisch", "spanish": "spanisch", "portugiesisch": "portugiesisch",
             "rätoromanisch": "rätoromanisch"}
LANGUAGE_MENTION = re.compile(r"\b(" + "|".join(sorted(LANGUAGES, key=len, reverse=True)) + r")\w*", re.IGNORECASE)
# One alternation, longer phrases first, so that „sehr gute“ is not read as „gute“.
LEVEL_WORDS = (
    (7, r"muttersprach\w*|erstsprache|native"),
    (6, r"\bc2\b|verhandlungssicher\w*|stilsicher\w*|perfekt\w*"),
    (5, r"\bc1\b|sehr\s+gut\w*|flie(?:ss|ß)end\w*|ausgezeichnet\w*|fluent"),
    (4, r"\bb2\b|\bgut\w*|\bgood\b"),
    (3, r"\bb1\b|\bmittel\b|mittlere\w*"),
    (2, r"\ba2\b|grundkenntnis\w*|basic"),
    (1, r"\ba1\b"),
)
LEVEL = re.compile("|".join(f"(?P<l{level}>{words})" for level, words in LEVEL_WORDS), re.IGNORECASE)
LEVEL_NAMES = {1: "A1", 2: "A2", 3: "B1", 4: "B2", 5: "C1", 6: "C2", 7: "Muttersprache"}
MAX_DISTANCE = 40  # characters between a language and its level
DEGREE_WORDS = (
    (5, "Doktorat", r"\bph\.?\s?d\b|doktorat\w*|\bpromotion\b|promoviert\w*"),
    (4, "Master", r"(?<!scrum[ -])\bmaster(?:abschluss|studium|degree)?\b(?![\s-]*data)|\bm\.?\s?sc\b|lizentiat\w*"),
    (3, "Bachelor", r"\bbachelor\w*|\bb\.?\s?sc\b|hochschulabschluss|hochschulstudium|universitätsabschluss"
                    r"|abgeschlossene[sn]?\s+(?:\w+\s+)?studium|fh-abschluss|uni-abschluss"),
    (2, "höhere Berufsbildung", r"fachausweis|höhere\w*\s+fachschule|\bhf\b|eidg\.?\s+diplom"),
    (1, "Berufslehre", r"\befz\b|berufslehre|lehrabschluss|berufsabschluss|abgeschlossene\s+lehre"),
)
DEGREE_NAMES = {level: name for level, name, _ in DEGREE_WORDS}
OPTIONAL = re.compile(r"von vorteil|wünschenswert|ein plus|nice to have|idealerweise|vorteilhaft|erwünscht|optional"
                      r"|gleichwertig|vergleichbar|oder entsprechende|oder mehrjährige|or equivalent|or similar", re.IGNORECASE)
STRONG = re.compile(r"mehrjährig|langjährig|fundiert|ausgewiesen|vertieft|profund|schwerpunkt|expert|voraussetzung"
                    r"|\bpflicht\b|\bmuss\b|mindestens\s+\d+\s+jahr|\d+\+?\s+jahre", re.IGNORECASE)
SENTENCE = re.compile(r"[\n.;•·]+(?:\s|$)|\n")
CLAUSE = re.compile(r"[\n.;,•·]+(?:\s|$)|\n")
EXCLUSIONS_SECTION = "## Ausschlüsse"
TECHNOLOGY_LABEL = "technologien"
LANGUAGES_SECTION = "## Sprachen"
DEGREE_SECTION = "## Abschluss und Erfahrung"
NAMED_LEVEL = re.compile(r"([A-Za-zÄÖÜäöüé]+)\s*\(([^()]*)\)")


@dataclasses.dataclass(frozen=True)
class Person:
    languages: dict[str, int]  # canonical language → level 1 (A1) to 7 (Muttersprache)
    degree: int | None  # highest degree level, None when nothing says
    excluded: tuple[str, ...]


def _level_of(text: str) -> int | None:
    levels = [int(match.lastgroup[1:]) for match in LEVEL.finditer(text)]
    return max(levels) if levels else None


def _degree_levels(text: str) -> list[int]:
    return [level for level, _, words in DEGREE_WORDS if re.search(words, text, re.IGNORECASE)]


def _languages(cv: dict, profile: str) -> dict[str, int]:
    found = [(entry.get("language"), entry.get("fluency")) for entry in cv.get("languages") or [] if isinstance(entry, dict)]
    found += [match.groups() for line in search_plan.section_lines(profile, LANGUAGES_SECTION) for match in NAMED_LEVEL.finditer(line)]
    known: dict[str, int] = {}
    for name, fluency in found:
        language, level = LANGUAGES.get(str(name or "").strip().lower()), _level_of(str(fluency or ""))
        if language and level:
            known = {**known, language: max(level, known.get(language, 0))}
    return known


def _degree(cv: dict, profile: str) -> int | None:
    texts = [" ".join(str(entry.get(field) or "") for field in ("studyType", "area"))
             for entry in cv.get("education") or [] if isinstance(entry, dict)]
    levels = [level for text in [*texts, *search_plan.section_lines(profile, DEGREE_SECTION)] for level in _degree_levels(text)]
    return max(levels) if levels else None


def _excluded(profile: str) -> tuple[str, ...]:
    pairs = (search_plan.PAIR.match(line) for line in search_plan.section_lines(profile, EXCLUSIONS_SECTION))
    values = [match[2] for match in pairs if match and match[1].strip().lower().startswith(TECHNOLOGY_LABEL)]
    return tuple(dict.fromkeys(term.strip() for value in values for term in search_plan.split_terms(value) if term.strip()))


def person_of(cv: dict, profile: str) -> Person:
    cv = cv if isinstance(cv, dict) else {}
    return Person(languages=_languages(cv, profile), degree=_degree(cv, profile), excluded=_excluded(profile))


def for_folder(data_dir: pathlib.Path) -> Person:
    """The person as cv.yaml and the profile describe them; an unreadable file counts as missing data."""
    try:
        cv = yaml.safe_load((data_dir / "cv.yaml").read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        cv = {}
    try:
        profile = (data_dir / search_plan.PROFILE).read_text(encoding="utf-8")
    except OSError:
        profile = ""
    return person_of(cv, profile)


def _nearest_level(clause: str, mention: re.Match) -> int | None:
    distances = [(max(match.start() - mention.end(), mention.start() - match.end()), int(match.lastgroup[1:]))
                 for match in LEVEL.finditer(clause)]
    near = [pair for pair in distances if pair[0] <= MAX_DISTANCE]
    return min(near)[1] if near else None


def _language_reason(text: str, person: Person) -> str:
    if not person.languages:
        return ""
    for clause in CLAUSE.split(text):
        if OPTIONAL.search(clause):
            continue
        for mention in LANGUAGE_MENTION.finditer(clause):
            language, wanted = LANGUAGES[mention[1].lower()], _nearest_level(clause, mention)
            have = person.languages.get(language, 0)
            if wanted and wanted > have:
                return (f"Verlangt {language.capitalize()} auf Niveau {LEVEL_NAMES[wanted]}, "
                        f"vorhanden ist {LEVEL_NAMES.get(have, 'keine Angabe')}.")
    return ""


def _degree_reason(text: str, person: Person) -> str:
    if person.degree is None:
        return ""
    required = [min(levels) for sentence in SENTENCE.split(text) if not OPTIONAL.search(sentence)
                for levels in [_degree_levels(sentence)] if levels]
    wanted = max(required, default=0)
    return f"Verlangt {DEGREE_NAMES[wanted]}, vorhanden ist {DEGREE_NAMES[person.degree]}." if wanted > person.degree else ""


def _mentions(text: str, term: str) -> bool:
    """A whole term; one that starts or ends with a sign, like „.NET“ or „C++“, also inside „ASP.NET“."""
    before = "" if not term[:1].isalnum() else r"(?<!\w)"
    after = "" if not term[-1:].isalnum() else r"(?!\w)"
    return re.search(f"{before}{re.escape(term)}{after}", text, re.IGNORECASE) is not None


def _technology_reason(title: str, text: str, person: Person) -> str:
    for term in person.excluded:
        main = _mentions(title, term) or any(_mentions(sentence, term) and STRONG.search(sentence) and not OPTIONAL.search(sentence)
                                             for sentence in SENTENCE.split(text))
        if main:
            return f"Schwerpunkt {term}, im Suchprofil ausgeschlossen."
    return ""


def check(title: str, text: str, person: Person) -> str:
    """The first reason the ad does not fit by the fixed rules, or "" when it passes."""
    return (_language_reason(text, person) or _degree_reason(text, person)
            or _technology_reason(title, text, person))
