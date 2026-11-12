"""Which values are personal: collected from cv.yaml, the register entry, the letter and the building blocks,
and found in free text such as a job ad (MIN-334). `ai.pseudonym` replaces them.

Limits, on purpose: a postal code that looks like a year (1900–2099) is not replaced on its own, so years in
the CV stay readable; names in an ad are only found after „Frau“/„Herr“ or in a personal e-mail address.
Other names of contact persons belong into the field „Kontaktperson“ of the application. The same goes for names
of other people in a reference (`secrets_in_own_documents`).
"""
import re

from ai.pseudonym import EMAIL, PHONE, Secret, parse_date, phone_numbers, url_core

MIN_TOKEN_CHARS = 3
MIN_USERNAME_CHARS = 4
TITLES = re.compile(r"^(?:(?:Frau|Herr|Dr|Prof|med|phil|iur|lic|dipl|Dipl)\.?\s+)+")
SEVERAL_PEOPLE = re.compile(r"\s+(?:und|&)\s+|\s*[;/]\s*")
BORN = re.compile(r"geboren(?:\s+am)?\s*[:,]?\s*(.+)", re.IGNORECASE)
DATE_LIKE = re.compile(r"\d{1,2}\.\s?\d{1,2}\.\s?\d{2,4}|\d{4}-\d{1,2}-\d{1,2}|\d{1,2}\.?\s+[A-Za-zäÄ]{3,}\.?\s+\d{4}")
TITLE_NAME = re.compile(r"\b(?:Frau|Herr)\s+(?:(?:Dr|Prof)\.\s+)*([A-ZÄÖÜ][\w'-]+)(?:\s+([A-ZÄÖÜ][\w'-]+))?")
NOT_NAMES = {"ihre", "ihr", "ihnen", "sie", "bewerbung", "bewerbungen", "unterlagen", "dr", "prof", "gerne",
             "freut", "steht", "bitte", "kontakt"}
GENERIC_MAILBOXES = {"info", "jobs", "job", "hr", "career", "careers", "karriere", "bewerbung", "bewerbungen",
                     "kontakt", "contact", "recruiting", "personal", "team", "office", "mail", "admin", "hello"}
YEAR_RANGE = range(1900, 2100)
STREET = re.compile(r"\b[A-ZÄÖÜ][\w.'-]*(?:strasse|str\.|gasse|weg|platz|allee|rain|matte|ring|hof|acker|feld|halde|stutz)\s+\d{1,4}[a-z]?\b"
                    r"|\b[A-ZÄÖÜ][\w.'-]+\s(?:Strasse|Str\.|Gasse|Weg|Platz)\s+\d{1,4}[a-z]?\b"
                    r"|\b(?:Rue|Route|Avenue|Chemin|Via|Piazza)\s[^,\n]{2,40}?\s\d{1,4}[a-z]?\b", re.IGNORECASE)
TOWN_LINE = re.compile(r"(?:^|(?<=,))[ \t]*((?:CH[- ]?)?([1-9]\d{3})\s+[A-ZÄÖÜ][\w'-]+(?:[ \t][\w'-]+){0,2})[ \t]*$", re.MULTILINE)
BIRTH_LABEL = re.compile(r"(?:\b(?:geboren|geburtsdatum|jahrgang)\b|\bgeb\.)(.*(?:\n.*)?)", re.IGNORECASE)  # tables: value on the next line
WEB_LINK = re.compile(r"(?:https?://|www\.|\b(?:linkedin|xing|github)\.com/)[^\s,;<>()]+", re.IGNORECASE)
YEAR = re.compile(r"\b(?:19|20)\d\d\b")
LABELLED = re.compile(r"\b(?:heimatort|bürgerort|zivilstand|nationalität|staatsangehörigkeit)\b\s*:?\s*([^\n,;]{2,60})",
                      re.IGNORECASE)
SOCIAL_NUMBER = re.compile(r"\b756[.\s]?\d{4}[.\s]?\d{4}[.\s]?\d{2}\b")
# The initials as written under basics, quoted or not; for files from before #248, where NO was read as False
MONOGRAM_FIELD = re.compile(r"^[ \t]+x-monogramm[ \t]*:[ \t]*([\"']?)(?P<value>[^\W\d_]{1,3})\1[ \t]*(?:#.*)?$", re.MULTILINE)


def _text(value) -> str:
    return value.strip() if isinstance(value, str) else ""


def strip_titles(name: str) -> str:
    return TITLES.sub("", name.strip()).strip()


def name_secrets(prefix: str, full_name: str) -> list[Secret]:
    """The full name, first and last name alone, middle names, and parts of double names.

    „Anna Maria Muster-Beispiel“ → NAME, NAME_FIRST (Anna), NAME_MIDDLE (Maria), NAME_LAST (Muster-Beispiel),
    NAME_PART (Muster), NAME_PART_2 (Beispiel). LAST always holds one word, so a salutation stays correct.
    """
    name = strip_titles(full_name)
    parts = name.split()
    result = [Secret(prefix, name, "name")]
    if len(parts) >= 2:
        result += [Secret(f"{prefix}_FIRST", parts[0], "name"), Secret(f"{prefix}_LAST", parts[-1], "name")]
        result += [Secret(f"{prefix}_MIDDLE", part, "name") for part in parts[1:-1]]
    for part in parts:
        if "-" in part:
            result += [Secret(f"{prefix}_PART", piece, "name") for piece in part.split("-")]
    return [s for s in result if len(s.value) >= MIN_TOKEN_CHARS]


def people_secrets(prefix: str, text: str) -> list[Secret]:
    """Several people in one field („Petra Meier und Hans Muster“) become CONTACT, CONTACT_2, …"""
    result = []
    for index, person in enumerate(p for p in SEVERAL_PEOPLE.split(text) if p.strip()):
        result += name_secrets(prefix if index == 0 else f"{prefix}_{index + 1}", person)
    return result


def _profile_secrets(index: int, profile: dict) -> list[Secret]:
    url = _text(profile.get("url"))
    username = _text(profile.get("username"))
    if not username and url:
        path = url_core(url).split("/")[1:]
        username = path[-1] if path else ""
    result = [Secret(f"PROFILE_{index}", url, "url")] if url else []
    return result + ([Secret(f"PROFILE_USER_{index}", username)] if len(username) >= MIN_USERNAME_CHARS else [])


def _birth_secrets(details: list) -> list[Secret]:
    result = []
    for detail in details:
        text = _text(detail)
        if m := BORN.search(text):
            result.append(Secret("BIRTH_DATE", m.group(1).strip(), "date"))
        result += [Secret("BIRTH_DATE", d.group(0), "date") for d in DATE_LIKE.finditer(text) if parse_date(d.group(0))]
    return result


def with_written_monogram(cv: dict, text: str) -> dict:
    """cv with the initials as cv.yaml writes them, when YAML 1.1 read them as something else (NO as False, #248)."""
    basics = cv.get("basics") if isinstance(cv.get("basics"), dict) else None
    if basics is None or "x-monogramm" not in basics or isinstance(basics["x-monogramm"], str):
        return cv
    found = MONOGRAM_FIELD.search(text)
    return {**cv, "basics": {**basics, "x-monogramm": found.group("value")}} if found else cv


def secrets_from_cv(cv: dict, minor: bool = False) -> list[Secret]:
    """Personal values from cv.yaml (JSON Resume)."""
    basics = cv.get("basics") if isinstance(cv.get("basics"), dict) else {}
    location = basics.get("location") if isinstance(basics.get("location"), dict) else {}
    postal = _text(location.get("postalCode"))
    result = name_secrets("NAME", _text(basics.get("name")))
    result += [Secret("EMAIL", _text(basics.get("email"))), Secret("PHONE", _text(basics.get("phone")), "phone"),
               Secret("WEBSITE", _text(basics.get("url")), "url"), Secret("ADDRESS", _text(location.get("address"))),
               Secret("PHOTO", _text(basics.get("image"))),
               Secret("LOGO", _text(basics.get("x-logo"))),
               Secret("MONOGRAM", _text(basics.get("x-monogramm")), "initials")]
    if postal and not (postal.isdigit() and int(postal) in YEAR_RANGE):
        result.append(Secret("POSTAL_CODE", postal))
    for index, profile in enumerate(basics.get("profiles") or [], 1):
        if isinstance(profile, dict):
            result += _profile_secrets(index, profile)
    result += _birth_secrets(basics.get("details") or [])
    for index, reference in enumerate(cv.get("references") or [], 1):
        if isinstance(reference, dict):
            result += people_secrets(f"REFERENCE_{index}", _text(reference.get("name")))
    if minor:
        for index, school in enumerate(cv.get("education") or [], 1):
            if isinstance(school, dict):
                result.append(Secret(f"SCHOOL_{index}", _text(school.get("institution"))))
    return [s for s in result if s.value]


def secrets_from_application(entry: dict, letter: dict | None = None) -> list[Secret]:
    """Contact persons of the company (register entry), their e-mail and phone, and named recipients."""
    result = people_secrets("CONTACT", _text(entry.get("kontaktperson")))
    contact_way = _text(entry.get("kontakt"))
    emails = EMAIL.findall(contact_way)
    phones = PHONE.findall(contact_way)
    result += [Secret("CONTACT_EMAIL", e) for e in emails] + [Secret("CONTACT_PHONE", p, "phone") for p in phones]
    if contact_way and not emails and not phones:
        result.append(Secret("CONTACT_WAY", contact_way))
    recipients = (letter or {}).get("empfaenger") or []
    for index, line in enumerate(recipients, 1):
        if isinstance(line, str) and TITLES.match(line.strip()):
            result += people_secrets(f"RECIPIENT_{index}", line)
    return result


def secrets_from_building_blocks(text: str) -> list[Secret]:
    """References named in bausteine.md („- Referenz: Hans Muster, Beispiel AG“): the line and the name."""
    result = []
    for index, line in enumerate(re.findall(r"^- Referenz:\s*(.+)$", text, re.MULTILINE), 1):
        result.append(Secret(f"REFERENCE_NOTE_{index}", line.strip()))
        result += people_secrets(f"REFERENCE_NOTE_{index}_NAME", line.split(",")[0])
    return result


def _mailbox_names(email: str) -> list[Secret]:
    tokens = re.split(r"[._-]", email.split("@")[0])
    if len(tokens) != 2 or not all(t.isalpha() and len(t) >= MIN_TOKEN_CHARS for t in tokens):
        return []
    if any(t.lower() in GENERIC_MAILBOXES for t in tokens):
        return []
    return name_secrets("FOUND_NAME", " ".join(t.capitalize() for t in tokens))


def secrets_found_in(texts: list[str]) -> list[Secret]:
    """E-mail addresses, phone numbers and people („Frau Petra Meier“) in free text, e.g. a job ad."""
    result = []
    for text in texts:
        for email in EMAIL.findall(text):
            result += [Secret("FOUND_EMAIL", email)] + _mailbox_names(email)
        result += [Secret("FOUND_PHONE", phone, "phone") for phone in phone_numbers(text)]
        for match in TITLE_NAME.finditer(text):
            tokens = [t for t in match.groups() if t and t.lower() not in NOT_NAMES]
            if tokens:
                result += name_secrets("FOUND_CONTACT", " ".join(tokens))
    return result


def _birth_secrets_in(text: str) -> list[Secret]:
    result = []
    for match in BIRTH_LABEL.finditer(text):
        rest = match.group(1)
        dates = [d.group(0) for d in DATE_LIKE.finditer(rest) if parse_date(d.group(0))]
        result += [Secret("FOUND_BIRTH_DATE", date, "date") for date in dates]
        if not dates:
            result += [Secret("FOUND_BIRTH_YEAR", year.group(0)) for year in YEAR.finditer(rest.split("\n")[0])]
    return result


def secrets_in_own_documents(texts: list[str]) -> list[Secret]:
    """What a CV or a reference says about the person: street, town line, birth date, origin, AHV number, web links.

    Scanned before anything goes to the AI, also when the form has no address yet. Lines that start with a year
    („2019 Beispiel AG“) are stations of a CV, not towns. Names of other people without „Frau“ or „Herr“ are not
    recognized here.
    """
    result = []
    for text in texts:
        result += [Secret("FOUND_STREET", street) for street in STREET.findall(text)]
        for line, postal in TOWN_LINE.findall(text):
            if int(postal) not in YEAR_RANGE or line.upper().startswith("CH"):
                result.append(Secret("FOUND_TOWN", line.strip()))
        result += _birth_secrets_in(text)
        result += [Secret("FOUND_ORIGIN", value.strip()) for value in LABELLED.findall(text)]
        result += [Secret("FOUND_SOCIAL_NUMBER", number) for number in SOCIAL_NUMBER.findall(text)]
        result += [Secret("FOUND_LINK", link.rstrip(".:!?'\""), "url") for link in WEB_LINK.findall(text)]
    return result
