"""Entering sent applications as work efforts in Job-Room (MIN-347): what can be chosen and what goes into the form.

The data is derived from the register and only goes to the extension, which fills the form for the person. It is
particularly sensitive (Art. 5 DSG), so nothing here may reach the AI.
"""
import datetime
import pathlib
import re

import search_plan
from register import jobroom_angaben, jobroom_ergebnis, schweizer_datum

MAX_PER_RUN = 20
NOT_APPLIED = "Noch nicht beworben."
ALREADY_ENTERED = "Schon im RAV eingetragen."
REMIND_FROM_DAY = 25
DEADLINE_DAY = 5
MONTHS = ("Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember")
CHANNELS = {"elektronisch": "electronic", "schriftlich": "letter", "persönlich": "personal", "telefonisch": "phone"}
CHANNELS_WITH_ADDRESS = ("letter", "personal")
WORKLOADS = {"Vollzeit": "full", "Teilzeit": "part"}
RESULTS = {"Anstellung": "employed", "Absage": "rejected"}
EMAIL = re.compile(r"[^\s,;<>:()\[\]\"']+@[^\s,;<>()\[\]\"']+\.[A-Za-z]{2,}")
WEB_ADDRESS = re.compile(r"https?://[^\s,;<>]+")
PHONE = re.compile(r"\+?\d[\d\s/().-]{6,}\d")
POSTAL_CITY = re.compile(r"^(.*?)\s*\b(?:CH-?)?(\d{4})\s+(\D.*)$", re.IGNORECASE)
COUNTRY = re.compile(r"^(?:schweiz|suisse|svizzera|switzerland|ch)$", re.IGNORECASE)
CARE_OF = re.compile(r"^c/o\b", re.IGNORECASE)
PARTS = re.compile(r"[\n,]|\s/\s")
PO_BOX = re.compile(r"^(?:postfach|case postale|casella postale)\b\s*(\d*)$", re.IGNORECASE)
STREET_NUMBER = re.compile(r"^(.*\S)\s+(\d+\s?[A-Za-z]?)$")


def applies(data_dir: pathlib.Path) -> bool:
    """People looking for an apprenticeship are not registered with an RAV as a rule."""
    return search_plan.kind_of_folder(data_dir) != search_plan.KIND_APPRENTICESHIP


def blocker(entry: dict) -> str | None:
    if entry.get("rav_eingetragen_am"):
        return ALREADY_ENTERED
    return None if entry.get("beworben_am") else NOT_APPLIED


def _street_parts(candidates: list[str]) -> dict:
    """A company name may come first: the street stands nearest to the city, a line with a number is the surest."""
    numbered = [match for match in map(STREET_NUMBER.match, candidates) if match]
    if numbered:
        return {"street": numbered[-1][1], "house_number": numbered[-1][2]}
    return {"street": candidates[-1]} if candidates else {}


def _address_parts(address: str | None, company: str | None) -> dict:
    """Free text in the register → the fields of the form; a part that is not recognised stays out."""
    parts = [part.strip() for part in PARTS.split(address or "") if part.strip()]
    found, others = {}, []
    for part in parts:
        postal, box = POSTAL_CITY.match(part), PO_BOX.match(part)
        if postal:
            found["postal_city"] = f"{postal[2]} {postal[3]}"
            others += [postal[1]] if postal[1] else []
        elif box:
            found["po_box"] = box[1]
        elif not (COUNTRY.match(part) or CARE_OF.match(part) or part == company):
            others.append(part)
    return {**found, **_street_parts(others)}


def _first(pattern: re.Pattern, text: str) -> str | None:
    match = pattern.search(text)
    return match[0].strip() if match else None


def _contact_parts(contact: str | None) -> dict:
    text = contact or ""
    email, web = _first(EMAIL, text), _first(WEB_ADDRESS, text)
    rest = text.replace(email or "\0", " ").replace(web or "\0", " ")
    phone = _first(PHONE, rest)
    return {"email": email, "url": web, "phone": phone.split(" / ")[0] if phone else None}


def form_values(entry: dict) -> dict:
    """What goes into one entry of the form; what is unknown is left out and stays open for the person."""
    details = jobroom_angaben(entry)
    channel = CHANNELS.get(details["art"], CHANNELS["elektronisch"])
    contact = _contact_parts(entry.get("kontakt"))
    values = {
        "date": schweizer_datum(entry.get("beworben_am")),
        "channel": channel,
        "company": details.get("arbeitgeber"),
        "contact_person": details.get("kontaktperson"),
        "occupation": details.get("stelle"),
        **contact,
        "url": entry.get("formular_link") or entry.get("link") or contact["url"],
        "workload": WORKLOADS.get(details.get("pensum")),
        "through_rav": details["rav_zuweisung"],
        "result": RESULTS.get(jobroom_ergebnis(entry), "open"),
        "interview": bool(entry.get("gespraech_am")) or entry.get("status") == "Gespräch",
        **(_address_parts(entry.get("adresse"), entry.get("firma")) if channel in CHANNELS_WITH_ADDRESS else {}),
    }
    return {key: value for key, value in values.items() if value not in (None, "")}


def _due_month(today: datetime.date) -> datetime.date | None:
    """First day of the month whose entries are due; Job-Room passes them on to the RAV by the 5th of the next month."""
    if today.day >= REMIND_FROM_DAY:
        return today.replace(day=1)
    if today.day <= DEADLINE_DAY:
        return (today.replace(day=1) - datetime.timedelta(days=1)).replace(day=1)
    return None


def reminder(entries: list[dict], today: datetime.date) -> dict | None:
    """What is still missing around the end of the month, only for people who have used this before."""
    month = _due_month(today)
    if month is None or not any(entry.get("rav_eingetragen_am") for entry in entries):
        return None
    prefix = month.strftime("%Y-%m-")
    missing = [entry["id"] for entry in entries
               if str(entry.get("beworben_am") or "").startswith(prefix) and not entry.get("rav_eingetragen_am")]
    if not missing:
        return None
    next_month = (month + datetime.timedelta(days=32)).replace(day=DEADLINE_DAY)
    return {"ids": missing, "monat": f"{MONTHS[month.month - 1]} {month.year}", "frist": next_month.strftime("%d.%m.%Y")}
