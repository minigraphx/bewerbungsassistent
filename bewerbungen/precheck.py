"""Rule-based pre-check of an ad before rating (G33): languages, degree and excluded technologies.

Fixed rules, no AI, unambiguous signals only (Andy, 10.11.2026). A hit is marked only when a sentence states a
requirement with an explicit marker („zwingend“, „erforderlich“, „muss“, „required“, „obligatoire“ …) and names a CEFR
level or „Muttersprache“ for a language, a degree without an alternative, or an excluded technology on its own. A hedge
in the sentence, a level given only as an adjective („gute Kenntnisse“, „fliessend“) or a technology listed among others
leaves the hit to the AI rating. When in doubt, the hit passes. A marked hit keeps its place, below the others.
Missing data lets the hit pass: a person without languages or degree in cv.yaml and profile.
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
             "rätoromanisch": "rätoromanisch", "français": "französisch", "francais": "französisch",
             "anglais": "englisch", "allemand": "deutsch"}
# „Deutschland“ is a country, not the language.
LANGUAGE_MENTION = re.compile(r"\b(" + "|".join(sorted(LANGUAGES, key=len, reverse=True)) + r")(?!land)\w*", re.IGNORECASE)
# cv.yaml takes any name: „Schweizerdeutsch“ or „Hochdeutsch“ is German.
LANGUAGE_IN_NAME = re.compile("|".join(sorted(LANGUAGES, key=len, reverse=True)), re.IGNORECASE)
# „Deutsch oder Französisch C1“, „Deutsch- und/oder Französischkenntnisse“: one of them is enough.
ALTERNATIVE = re.compile(r"-?\s*(?:(?:und|and)\s*/\s*)?(?:oder|or|bzw\.?|beziehungsweise|/)\s*", re.IGNORECASE)
# The ad's level: only a CEFR level or mother tongue. Adjectives like „gut“ or „fliessend“ are left to the AI.
AD_LEVEL = re.compile(r"\b(?P<cefr>[abc][12])\b|(?P<native>muttersprach\w*|erstsprache)", re.IGNORECASE)
CEFR = {"a1": 1, "a2": 2, "b1": 3, "b2": 4, "c1": 5, "c2": 6}
NATIVE_LEVEL = 7
MAX_DISTANCE = 25  # characters between a language and its level within one clause
# The person's own level may be a word, as cv.yaml and the profile write it („Englisch (gut)“).
PERSON_LEVEL_WORDS = (
    (7, r"muttersprach\w*|erstsprache|native"),
    (6, r"\bc2\b|verhandlungssicher\w*|stilsicher\w*|perfekt\w*"),
    (5, r"\bc1\b|sehr\s+gut\w*|flie(?:ss|ß)end\w*|ausgezeichnet\w*|fluent"),
    (4, r"\bb2\b|\bgut\w*|\bgood\b"),
    (3, r"\bb1\b|\bmittel\b|mittlere\w*"),
    (2, r"\ba2\b|grundkenntnis\w*|basic"),
    (1, r"\ba1\b"),
)
PERSON_LEVEL = re.compile("|".join(f"(?P<l{level}>{words})" for level, words in PERSON_LEVEL_WORDS), re.IGNORECASE)
LEVEL_NAMES = {1: "A1", 2: "A2", 3: "B1", 4: "B2", 5: "C1", 6: "C2", 7: "Muttersprache"}
MANDATORY = re.compile(r"zwingend\w*|vorausgesetzt|voraussetzung\w*|erforderlich\w*|\bmuss\b|\bmüssen\b|\bpflicht\b"
                       r"|unabdingbar\w*|unerlässlich\w*|\brequired\b|\bmandatory\b|\bmust\b|\bexigée?s?\b|\brequise?s?\b"
                       r"|obligatoire\w*", re.IGNORECASE)
HEDGE = re.compile(r"von vorteil|wünschenswert|idealerweise|nice to have|ein plus|\bplus\b|vorteilhaft|erwünscht|optional"
                   r"|bevorzugt|preferred|souhaitée?s?|un atout|de préférence"
                   # a marker that is negated says the opposite: „nicht zwingend“, „keine Voraussetzung“
                   r"|nicht\s+(?:zwingend|erforderlich|vorausgesetzt|unbedingt|notwendig|nötig|pflicht)"
                   r"|keine\s+(?:voraussetzung|pflicht|bedingung)|kein\s+muss|not\s+(?:required|mandatory|a\s+must)"
                   r"|pas\s+(?:obligatoire|exigé|requis)", re.IGNORECASE)
DEGREE_ALTERNATIVE = re.compile(r"gleichwertig|vergleichbar|oder entsprechende|oder mehrjährige|oder ähnlich|or equivalent"
                                r"|or similar|ou équivalent", re.IGNORECASE)
DEGREE_WORDS = (
    # „Promotion“ alone is mostly marketing („Sales Promotion“); a doctorate says so.
    (5, "Doktorat", r"\bph\.?\s?d\b|doktorat\w*|abgeschlossene[nrs]?\s+promotion\b|promoviert\w*|doktortitel"),
    (4, "Master", r"(?<!scrum[ -])\bmaster(?:abschluss|studium|degree)?\b(?![\s-]*data)|\bm\.?\s?sc\b|lizentiat\w*"),
    (3, "Bachelor", r"\bbachelor\w*|\bb\.?\s?sc\b|hochschulabschluss|hochschulstudium|universitätsabschluss"
                    r"|abgeschlossene[sn]?\s+(?:\w+\s+)?studium|fh-abschluss|uni-abschluss"),
    (2, "höhere Berufsbildung", r"fachausweis|höhere\w*\s+fachschule|\bhf\b|eidg\.?\s+diplom"),
    (1, "Berufslehre", r"\befz\b|berufslehre|lehrabschluss|berufsabschluss|abgeschlossene\s+lehre"),
)
DEGREE_NAMES = {level: name for level, name, _ in DEGREE_WORDS}
# A technology named next to others („Java, Python und Go“) is listed, not the focus.
LISTED_BEFORE = re.compile(r"(?:[,/]|\b(?:und|oder|sowie|and|or))\s*$", re.IGNORECASE)
LISTED_AFTER = re.compile(r"^(?:-\w+)?\s*(?:[,/]|(?:und|oder|sowie|and|or)\b)", re.IGNORECASE)
ABBREVIATIONS = re.compile(r"\b(bzw|z\.\s?b|eidg|inkl|ca|d\.\s?h|mind|evtl)\.", re.IGNORECASE)
SENTENCE = re.compile(r"[\n.;!?•·]+(?:\s|$)|\n")
CLAUSE = re.compile(r",")
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
    levels = [int(match.lastgroup[1:]) for match in PERSON_LEVEL.finditer(text)]
    return max(levels) if levels else None


def _degree_levels(text: str) -> list[int]:
    return [level for level, _, words in DEGREE_WORDS if re.search(words, text, re.IGNORECASE)]


def _languages(cv: dict, profile: str) -> dict[str, int]:
    found = [(entry.get("language"), entry.get("fluency")) for entry in cv.get("languages") or [] if isinstance(entry, dict)]
    found += [match.groups() for line in search_plan.section_lines(profile, LANGUAGES_SECTION) for match in NAMED_LEVEL.finditer(line)]
    known: dict[str, int] = {}
    for name, fluency in found:
        named = LANGUAGE_IN_NAME.search(str(name or ""))
        language, level = LANGUAGES[named[0].lower()] if named else None, _level_of(str(fluency or ""))
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


def _required_sentences(text: str) -> list[str]:
    """Sentences that state a requirement with an explicit marker and no hedge."""
    sentences = SENTENCE.split(ABBREVIATIONS.sub(lambda match: match[1].replace(".", ""), text))
    return [sentence for sentence in sentences if MANDATORY.search(sentence) and not HEDGE.search(sentence)]


def _ad_level(match: re.Match) -> int:
    return CEFR[match["cefr"].lower()] if match["cefr"] else NATIVE_LEVEL


def _wanted_level(sentence: str, mention: re.Match) -> int | None:
    """The lowest CEFR level or mother tongue next to the language in its clause; none means no level was stated."""
    bounds = [0, *(match.end() for match in CLAUSE.finditer(sentence)), len(sentence) + 1]
    start = max(bound for bound in bounds if bound <= mention.start())
    end = min(bound for bound in bounds if bound > mention.start())
    clause = sentence[start:end]
    near = [_ad_level(match) for match in AD_LEVEL.finditer(clause)
            if max(match.start() + start - mention.end(), mention.start() - match.end() - start) <= MAX_DISTANCE]
    return min(near) if near else None


def _alternatives(sentence: str) -> list[list[re.Match]]:
    """The languages of a sentence in groups; languages joined by „oder“, „und/oder“, „or“, „bzw“ or „/“ share one."""
    groups: list[list[re.Match]] = []
    for mention in LANGUAGE_MENTION.finditer(sentence):
        joined = groups and ALTERNATIVE.fullmatch(sentence[groups[-1][-1].end():mention.start()])
        groups = [*groups[:-1], [*groups[-1], mention]] if joined else [*groups, [mention]]
    return groups


def _shortfall(sentence: str, mention: re.Match, person: Person) -> str:
    language, wanted = LANGUAGES[mention[1].lower()], _wanted_level(sentence, mention)
    have = person.languages.get(language, 0)
    if wanted and wanted > have:
        return f"Verlangt {language.capitalize()} auf Niveau {LEVEL_NAMES[wanted]}, vorhanden ist {LEVEL_NAMES.get(have, 'keine Angabe')}."
    return ""


def _language_reason(text: str, person: Person) -> str:
    if not person.languages:
        return ""
    for sentence in _required_sentences(text):
        for group in _alternatives(sentence):
            reasons = [_shortfall(sentence, mention, person) for mention in group]
            if all(reasons):
                return reasons[0]
    return ""


def _degree_reason(text: str, person: Person) -> str:
    if person.degree is None:
        return ""
    required = [min(levels) for sentence in _required_sentences(text) if not DEGREE_ALTERNATIVE.search(sentence)
                for levels in [_degree_levels(sentence)] if levels]
    wanted = max(required, default=0)
    return f"Verlangt {DEGREE_NAMES[wanted]}, vorhanden ist {DEGREE_NAMES[person.degree]}." if wanted > person.degree else ""


def _term(term: str) -> re.Pattern:
    """A whole term; one that starts or ends with a sign, like „.NET“ or „C++“, also inside „ASP.NET“."""
    before = "" if not term[:1].isalnum() else r"(?<!\w)"
    after = "" if not term[-1:].isalnum() else r"(?!\w)"
    return re.compile(f"{before}{re.escape(term)}{after}", re.IGNORECASE)


def _named_alone(sentence: str, term: str) -> bool:
    return any(not (LISTED_BEFORE.search(sentence[:match.start()]) or LISTED_AFTER.match(sentence[match.end():]))
               for match in _term(term).finditer(sentence))


def _technology_reason(title: str, text: str, person: Person) -> str:
    for term in person.excluded:
        if _term(term).search(title) or any(_named_alone(sentence, term) for sentence in _required_sentences(text)):
            return f"Schwerpunkt {term}, im Suchprofil ausgeschlossen."
    return ""


def check(title: str, text: str, person: Person) -> str:
    """The first reason the ad does not fit by the fixed rules, or "" when it passes."""
    return (_language_reason(text, person) or _degree_reason(text, person)
            or _technology_reason(title, text, person))
