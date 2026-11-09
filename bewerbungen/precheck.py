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
# cv.yaml takes any name: „Schweizerdeutsch“ or „Hochdeutsch“ is German.
LANGUAGE_IN_NAME = re.compile("|".join(sorted(LANGUAGES, key=len, reverse=True)), re.IGNORECASE)
# „Deutsch oder Französisch fliessend“, „Deutsch- und/oder Französischkenntnisse“: one of them is enough.
ALTERNATIVE = re.compile(r"-?\s*(?:(?:und|and)\s*/\s*)?(?:oder|or|bzw\.?|beziehungsweise|/)\s*", re.IGNORECASE)
ABBREVIATED_OR = re.compile(r"\bbzw\.", re.IGNORECASE)  # its dot must not end the clause
ENGLISH_NAMES = r"english|german|french|italian|spanish"
# „Native“ alone is also a tech term („Cloud-native“, „React Native“, „native Apps“): it counts only next to
# „speaker“, „level“ and the like, or right beside a language name.
NATIVE = (r"\bnative[\s-]+(?:speakers?|level|language|proficiency|tongue|" + ENGLISH_NAMES + r")\b"
          r"|\b(?:" + "|".join(LANGUAGES) + r")\w*[\s:-]+native\b")
# One alternation, longer phrases first, so that „sehr gute“ is not read as „gute“.
LEVEL_WORDS = (
    (7, r"muttersprach\w*|erstsprache|" + NATIVE),
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
# „die perfekte Ergänzung“, „ein mittleres Unternehmen“: an inflected level adjective before another noun is about
# that noun. Before a language, „Kenntnisse“ and the like, or lower case („gute mündliche …“), it stays a level.
LEVEL_ADJECTIVE = re.compile(r"(?:perfekt|ausgezeichnet|gut|mittler|verhandlungssicher|stilsicher|flie(?:ss|ß)end)"
                             r"(?:e|en|es|er|em)$", re.IGNORECASE)
NEXT_NOUN = re.compile(r"\s+([A-ZÄÖÜ][\w-]*)")
LANGUAGE_NOUN = re.compile(r"kenntnis|sprach|speaker|ausdruck|beherrsch|kommunikation|verständnis|niveau|"
                           + "|".join(LANGUAGES), re.IGNORECASE)
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
                    r"|\bpflicht\b|\bmuss\b|mindestens\s+\d+\s+jahr", re.IGNORECASE)
# Years count as required experience only with experience named; „seit 25 Jahren“ is the age of the company.
YEARS = re.compile(r"(?<!seit\s)(?<!since\s)\b\d+\+?\s+(?:jahre|years)", re.IGNORECASE)
EXPERIENCE = re.compile(r"erfahrung|experience|praxis", re.IGNORECASE)
# What the company offers is no requirement: „Wir bieten Englischkurse bis C2“, „Weiterbildung bis zum Master“.
OFFERED = re.compile(r"\bwir\s+(?:bieten|unterstützen|finanzieren|fördern|ermöglichen|übernehmen)|unterstützung\s+(?:bei|für)"
                     r"|finanzierung|weiterbildungsmöglichkeit\w*|weiterbildungsangebot\w*|möglichkeit\s+zu[mr]?\b"
                     r"|\bwe\s+(?:offer|support|fund|sponsor)\b", re.IGNORECASE)
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


def _about_another_noun(clause: str, match: re.Match) -> bool:
    noun = NEXT_NOUN.match(clause, match.end())
    return bool(LEVEL_ADJECTIVE.search(match[0]) and noun and not LANGUAGE_NOUN.search(noun[1]))


def _nearest_level(clause: str, mention: re.Match) -> int | None:
    distances = [(max(match.start() - mention.end(), mention.start() - match.end()), int(match.lastgroup[1:]))
                 for match in LEVEL.finditer(clause) if not _about_another_noun(clause, match)]
    near = [pair for pair in distances if pair[0] <= MAX_DISTANCE]
    return min(near)[1] if near else None


def _alternatives(clause: str) -> list[list[re.Match]]:
    """The languages of a clause in groups; languages joined by „oder“, „und/oder“, „or“, „bzw.“ or „/“ share one
    group, also after a hyphen („Deutsch- oder Französischkenntnisse“)."""
    groups: list[list[re.Match]] = []
    for mention in LANGUAGE_MENTION.finditer(clause):
        joined = groups and ALTERNATIVE.fullmatch(clause[groups[-1][-1].end():mention.start()])
        groups = [*groups[:-1], [*groups[-1], mention]] if joined else [*groups, [mention]]
    return groups


def _shortfall(clause: str, mention: re.Match, person: Person) -> str:
    language, wanted = LANGUAGES[mention[1].lower()], _nearest_level(clause, mention)
    have = person.languages.get(language, 0)
    if wanted and wanted > have:
        return f"Verlangt {language.capitalize()} auf Niveau {LEVEL_NAMES[wanted]}, vorhanden ist {LEVEL_NAMES.get(have, 'keine Angabe')}."
    return ""


def _language_reason(text: str, person: Person) -> str:
    if not person.languages:
        return ""
    for clause in CLAUSE.split(ABBREVIATED_OR.sub("bzw", text)):
        if OPTIONAL.search(clause) or OFFERED.search(clause):
            continue
        for group in _alternatives(clause):
            reasons = [_shortfall(clause, mention, person) for mention in group]
            if all(reasons):
                return reasons[0]
    return ""


def _degree_reason(text: str, person: Person) -> str:
    if person.degree is None:
        return ""
    required = [min(levels) for sentence in SENTENCE.split(text) if not (OPTIONAL.search(sentence) or OFFERED.search(sentence))
                for levels in [_degree_levels(sentence)] if levels]
    wanted = max(required, default=0)
    return f"Verlangt {DEGREE_NAMES[wanted]}, vorhanden ist {DEGREE_NAMES[person.degree]}." if wanted > person.degree else ""


def _mentions(text: str, term: str) -> bool:
    """A whole term; one that starts or ends with a sign, like „.NET“ or „C++“, also inside „ASP.NET“."""
    before = "" if not term[:1].isalnum() else r"(?<!\w)"
    after = "" if not term[-1:].isalnum() else r"(?!\w)"
    return re.search(f"{before}{re.escape(term)}{after}", text, re.IGNORECASE) is not None


def _strong(sentence: str) -> bool:
    return bool(STRONG.search(sentence) or (YEARS.search(sentence) and EXPERIENCE.search(sentence)))


def _technology_reason(title: str, text: str, person: Person) -> str:
    for term in person.excluded:
        main = _mentions(title, term) or any(_mentions(sentence, term) and _strong(sentence) and not OPTIONAL.search(sentence)
                                             for sentence in SENTENCE.split(text))
        if main:
            return f"Schwerpunkt {term}, im Suchprofil ausgeschlossen."
    return ""


def check(title: str, text: str, person: Person) -> str:
    """The first reason the ad does not fit by the fixed rules, or "" when it passes."""
    return (_language_reason(text, person) or _degree_reason(text, person)
            or _technology_reason(title, text, person))
