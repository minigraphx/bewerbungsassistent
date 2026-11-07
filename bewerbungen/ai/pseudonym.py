"""Replace personal data with placeholders before any text goes to the AI, and put it back afterwards (MIN-334).

Known values (from `ai.personal`: name, address, contacts, birth date, profiles, references, contact persons)
are matched in their usual variants: phone numbers in any Swiss notation, links with or without scheme,
dates in several formats, names also in the genitive and without umlauts or accents (#110).
E-mail addresses, phone numbers and contact persons found in the texts themselves
(`ai.personal.secrets_found_in`, e.g. in a job ad) are added per request with `extended`.

Placeholders look like `{{NAME}}`. `unmask` puts the values back; an unknown placeholder is an error.
`check_clean` is the last check before sending and does not rely on the same patterns only: any e-mail
address or phone number left over, or a known value written without spaces or accents, stops the request.
"""
import dataclasses
import re
import unicodedata

PLACEHOLDER = re.compile(r"\{\{\s*([A-Za-z][A-Za-z0-9_]*)\s*\}\}")
NEUTRALIZE_BRACES = re.compile(r"\{(?=\{)")  # {{{X}}} → { { {X}}}: no placeholder can come from the input
EMAIL = re.compile(r"(?<![\w.+-])[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE = re.compile(r"(?<![\w+])(?:\+|00|0)\d(?:[\s./()-]{0,3}\d){8,}(?!\d)")
_DATE_PART = r"(?:\d{1,2}[./]){1,2}\d{2,4}"
DATE_RANGE = re.compile(rf"{_DATE_PART}(?:[\s./()-]{{0,3}}{_DATE_PART})*")  # „09.2015 - 06.2019“ in a CV, no phone number
SEPARATORS = r"[\s./()-]*"
SWISS_PREFIX = r"(?:(?:\+|00)41" + SEPARATORS + r"(?:\(0\)" + SEPARATORS + r")?|\(?0)"
MONTHS = ["januar", "februar", "märz", "april", "mai", "juni", "juli", "august", "september", "oktober",
          "november", "dezember"]
NUMERIC_DATE = re.compile(r"(\d{1,2})\.\s?(\d{1,2})\.\s?(\d{4}|\d{2})")
ISO_DATE = re.compile(r"(\d{4})-(\d{1,2})-(\d{1,2})")
WORD_DATE = re.compile(r"(\d{1,2})\.?\s+([A-Za-zäÄ]+)\.?\s+(\d{4})")
TWO_DIGIT_PIVOT = 30  # „1.5.11“ is 2011, „1.5.85“ is 1985
MIN_FOLDED_CHARS = 10  # shorter values are too likely to appear by chance once spaces are removed
FOLD_UMLAUTS = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})
# How a name may be written without its umlauts or accents (MIN-334, #110): „Müller“ as „Mueller“ or „Muller“
UMLAUT_SPELLINGS = {"ä": "(?:ä|ae|a)", "ö": "(?:ö|oe|o)", "ü": "(?:ü|ue|u)", "ß": "(?:ß|ss)"}
UMLAUT_PAIRS = {"ae": "ä", "oe": "ö", "ue": "ü"}  # and „Mueller“ stored, „Müller“ written


# What the person reads when a request is stopped (#111): the first part of the field that matches decides,
# so REFERENCE_NOTE_1_NAME is a reference and CONTACT_EMAIL an e-mail address.
FIELD_LABELS = (("EMAIL", "E-Mail"), ("PHONE", "Telefon"), ("BIRTH", "Geburtsdatum"), ("SOCIAL_NUMBER", "AHV-Nummer"),
                ("ORIGIN", "Heimatort, Zivilstand oder Nationalität"), ("STREET", "Adresse"), ("ADDRESS", "Adresse"),
                ("POSTAL_CODE", "Postleitzahl"), ("TOWN", "Wohnort"), ("PROFILE_USER", "Benutzername"),
                ("PROFILE", "Link"), ("WEBSITE", "Link"), ("LINK", "Link"), ("PHOTO", "Foto"), ("SCHOOL", "Schule"),
                ("REFERENCE", "Referenz"), ("CONTACT_WAY", "Kontaktweg"), ("CONTACT", "Kontaktperson"),
                ("RECIPIENT", "Kontaktperson"), ("NAME", "Name"))
UNKNOWN_LABEL = "persönliche Angabe"


def label(field: str) -> str:
    """The German word for a field like NAME_LAST or FOUND_PHONE_2."""
    for key, text in FIELD_LABELS:
        if re.search(rf"(?:^|_){key}(?:_|$)", field):
            return text
    return UNKNOWN_LABEL


def phone_numbers(text: str) -> list[str]:
    """Everything in the text that looks like a phone number."""
    return [m for m in PHONE.findall(text) if not DATE_RANGE.fullmatch(m)]


class PseudonymError(Exception):
    """Personal data would reach the AI, or an answer cannot be restored. Message in German."""


@dataclasses.dataclass(frozen=True)
class Secret:
    field: str
    value: str
    kind: str = "text"  # text, name, phone, url, date

    @property
    def placeholder(self) -> str:
        return f"{{{{{self.field}}}}}"


def _norm(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def _fold(text: str, umlauts: bool = False) -> str:
    """Lower case, without accents, spaces and punctuation: „Müller-Meier“ → „mullermeier“ (or „muellermeier“)."""
    text = text.casefold()
    if umlauts:
        text = text.translate(FOLD_UMLAUTS)
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if c.isalnum() and not unicodedata.combining(c))


def _letter(char: str) -> str:
    """One letter of a name as a pattern: an umlaut also as ae/a, an accented letter also without its accent."""
    if char.lower() in UMLAUT_SPELLINGS:
        return UMLAUT_SPELLINGS[char.lower()]
    plain = "".join(c for c in unicodedata.normalize("NFD", char) if not unicodedata.combining(c))
    return f"(?:{re.escape(char)}|{re.escape(plain)})" if plain and plain != char else re.escape(char)


def _spellings(word: str) -> str:
    parts, i = [], 0
    while i < len(word):
        pair = word[i:i + 2]
        if pair.lower() in UMLAUT_PAIRS:
            parts.append(f"(?:{re.escape(pair)}|{UMLAUT_PAIRS[pair.lower()]})")
            i += 2
        else:
            parts.append(_letter(word[i]))
            i += 1
    return "".join(parts)


def _words(value: str, spellings: bool = False) -> str:
    return r"\s+".join(_spellings(part) if spellings else re.escape(part) for part in value.split())


def _text_pattern(value: str, name: bool = False) -> re.Pattern:
    """A name also in the genitive and without umlauts or accents; other text exactly, but in any case."""
    end = r"(?=s?(?![\w@]))" if name else r"(?![\w@])"
    return re.compile(r"(?<![\w@.])" + _words(value, spellings=name) + end, re.IGNORECASE)


def _digits_pattern(digits: str) -> str:
    return SEPARATORS.join(re.escape(d) for d in digits)


def _phone_pattern(value: str) -> re.Pattern | None:
    digits = re.sub(r"\D", "", value.replace("(0)", ""))
    for prefix in ("0041", "41"):
        if digits.startswith(prefix) and (prefix == "0041" or value.strip().startswith("+")):
            digits = "0" + digits[len(prefix):]
    if len(digits) < 6:
        return None
    body = SWISS_PREFIX + _digits_pattern(digits[1:]) if digits.startswith("0") else _digits_pattern(digits)
    return re.compile(r"(?<!\d)" + body + r"(?!\d)")


def url_core(value: str) -> str:
    """„https://www.example.ch/profil/“ → „example.ch/profil“."""
    core = re.sub(r"^[a-z]+://", "", value.strip(), flags=re.IGNORECASE)
    return re.sub(r"^www\.", "", core, flags=re.IGNORECASE).rstrip("/")


def _url_pattern(value: str) -> re.Pattern:
    return re.compile(r"(?<![\w-])" + re.escape(url_core(value)) + r"(?![\w-]|\.\w)", re.IGNORECASE)


def parse_date(value: str) -> tuple[int, int, int] | None:
    """(day, month, year) from „1.5.2011“, „01.05.11“, „2011-05-01“ or „1. Mai 2011“."""
    text = value.strip()
    if m := ISO_DATE.search(text):
        return int(m.group(3)), int(m.group(2)), int(m.group(1))
    if m := NUMERIC_DATE.search(text):
        year = int(m.group(3))
        if year < 100:
            year += 2000 if year <= TWO_DIGIT_PIVOT else 1900
        return int(m.group(1)), int(m.group(2)), year
    if (m := WORD_DATE.search(text)) and m.group(2).lower()[:3] in [name[:3] for name in MONTHS]:
        return int(m.group(1)), [name[:3] for name in MONTHS].index(m.group(2).lower()[:3]) + 1, int(m.group(3))
    return None


def _date_pattern(value: str) -> re.Pattern:
    parsed = parse_date(value)
    if parsed is None:
        return _text_pattern(value)
    day, month, year = parsed
    name = MONTHS[month - 1]
    forms = [rf"0?{day}\.\s?0?{month}\.\s?(?:{year}|{year % 100:02d})", rf"{year}-0?{month}-0?{day}",
             rf"0?{day}\.?\s+(?:{name}|{name[:3]}\.?)\s+{year}"]
    return re.compile(r"(?<!\d)(?:" + "|".join(forms) + r")(?!\d)", re.IGNORECASE)


def _pattern(secret: Secret) -> re.Pattern:
    value = _norm(secret.value)
    if secret.kind == "phone":
        return _phone_pattern(value) or _text_pattern(value)
    if secret.kind == "url":
        return _url_pattern(value)
    if secret.kind == "date":
        return _date_pattern(value)
    return _text_pattern(value, name=secret.kind == "name")


@dataclasses.dataclass(frozen=True)
class _Rule:
    secret: Secret
    pattern: re.Pattern


class Pseudonymizer:
    """Masks and restores one set of personal values. Longer values are replaced first."""

    def __init__(self, secrets: list[Secret]) -> None:
        self._secrets = tuple(sorted(_unique(secrets), key=lambda s: len(s.value), reverse=True))
        self._rules = tuple(_Rule(s, _pattern(s)) for s in self._secrets)
        self._by_field = {s.field: (url_core(s.value) if s.kind == "url" else s.value) for s in self._secrets}

    @property
    def fields(self) -> list[str]:
        """Names of the replaced fields, for the log (never the values)."""
        return sorted(self._by_field)

    def covers(self, value: str) -> bool:
        return any(rule.pattern.fullmatch(_norm(value).strip()) for rule in self._rules)

    def extended(self, secrets: list[Secret]) -> "Pseudonymizer":
        """A new Pseudonymizer that also replaces these values, unless they are covered already."""
        new = [s for s in secrets if not self.covers(s.value)]
        return Pseudonymizer(list(self._secrets) + new) if new else self

    def finds(self, text: str) -> bool:
        """Does this text contain one of the values, in any of the forms `mask` knows?"""
        normalized = _norm(text)
        return any(rule.pattern.search(normalized) for rule in self._rules)

    def mask(self, text: str) -> str:
        result = NEUTRALIZE_BRACES.sub("{ ", _norm(text))
        for rule in self._rules:
            result = rule.pattern.sub(rule.secret.placeholder, result)
        return result

    def check_clean(self, texts: list[str] | str) -> None:
        """Raise if anything personal is still in texts that are about to be sent."""
        leaked: set[str] = set()
        for text in [texts] if isinstance(texts, str) else texts:
            normalized = _norm(text)
            leaked |= {label(rule.secret.field) for rule in self._rules if rule.pattern.search(normalized)}
            leaked |= {"E-Mail"} if EMAIL.search(normalized) else set()
            leaked |= {"Telefon"} if phone_numbers(normalized) else set()
            leaked |= {label(field) for field in self._folded_leaks(normalized)}
        if leaked:
            raise PseudonymError(f"Persönliche Angaben wären an die KI gegangen ({', '.join(sorted(leaked))}); "
                                 "nichts gesendet.")

    def _folded_leaks(self, text: str) -> set[str]:
        folded = _fold(PLACEHOLDER.sub(" ", text))
        result = set()
        for secret in self._secrets:
            if secret.kind not in ("text", "name"):
                continue
            variants = {_fold(secret.value), _fold(secret.value, umlauts=True)}
            if any(len(v) >= MIN_FOLDED_CHARS and v in folded for v in variants):
                result.add(secret.field)
        return result

    def unmask(self, text: str) -> str:
        unknown = sorted({m.group(1) for m in PLACEHOLDER.finditer(text) if m.group(1).upper() not in self._by_field})
        if unknown:
            raise PseudonymError(f"Die Antwort der KI enthält unbekannte Platzhalter ({', '.join(unknown)}).")
        return PLACEHOLDER.sub(lambda m: self._by_field[m.group(1).upper()], text)

    def unmask_data(self, value):
        """unmask for every string inside JSON-like data (dicts, lists)."""
        if isinstance(value, str):
            return self.unmask(value)
        if isinstance(value, list):
            return [self.unmask_data(v) for v in value]
        if isinstance(value, dict):
            return {k: self.unmask_data(v) for k, v in value.items()}
        return value


def _unique(secrets: list[Secret]) -> list[Secret]:
    """One placeholder per value and one value per placeholder (NAME_MIDDLE, NAME_MIDDLE_2, …)."""
    by_value: dict[str, Secret] = {}
    used: set[str] = set()
    for secret in secrets:
        value = _norm(secret.value).strip()
        if not value or value.casefold() in by_value:
            continue
        field, number = secret.field, 2
        while field in used:
            field, number = f"{secret.field}_{number}", number + 1
        used.add(field)
        by_value[value.casefold()] = Secret(field, value, secret.kind)
    return list(by_value.values())
