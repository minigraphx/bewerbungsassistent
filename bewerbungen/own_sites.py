"""Further sites for the search, named by the person (MIN-348): they only count with an own API key.

An address is what the person sees in the browser (MIN-387): the extension uses the search form of that page if it
has one and reads the page either way. Addresses with the placeholders {begriff} and {ort} keep working, but nobody
should have to know them. Sites with their own adapter stay with it. Hits stay on the site's host: the name of the site is
its host, and `hits.checked_link` holds links to it.
"""
import hashlib
import ipaddress
import re
import urllib.parse

from ai.connection import own_key
from hits import DOMAINS, Hits, OWN_SITES

MAX_SITES = 5
MAX_ADDRESS = 500
ID_LENGTH = 16
PLACEHOLDER = re.compile(r"\{[^{}]*\}")
ALLOWED_PLACEHOLDERS = {"{begriff}", "{ort}"}
FORBIDDEN_CHARACTERS = "\\@ "
INNER_ENDINGS = (".local", ".localhost", ".internal", ".intranet", ".lan", ".home")
TOP_LEVEL = re.compile(r"(xn--[a-z0-9-]+|[a-z]{2,})")  # browsers read 127.1 or 0x7f.0.0.1 as addresses, not as names
TRACKING = re.compile(r"^(utm_.*|ref|refid|trk.*|tracking.*|position|pagenum|gclid|fbclid|msclkid|source|src)$", re.I)
BAD_ADDRESS = "„{address}“ geht nicht: {why}"


def _refuse(address, why: str) -> ValueError:
    return ValueError(BAD_ADDRESS.format(address=str(address)[:80], why=why))


def _is_inner(host: str) -> bool:
    """This computer or the local network: the search only reads public sites."""
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return "." not in host or host.endswith(INNER_ENDINGS) or not TOP_LEVEL.fullmatch(host.rsplit(".", 1)[-1])


def _portal(address: str) -> str:
    filled = PLACEHOLDER.sub("x", address)
    parts = urllib.parse.urlsplit(filled)
    host = (parts.hostname or "").lower()
    if parts.scheme != "https" or parts.netloc.lower() != host or not host:
        raise _refuse(address, "Die Adresse muss mit https:// beginnen und darf weder Anmeldedaten noch einen Port enthalten.")
    if "{" in urllib.parse.urlsplit(address).netloc or _is_inner(host):
        raise _refuse(address, "Das ist keine öffentliche Seite.")
    try:
        portal = host.encode("idna").decode("ascii").removeprefix("www.")  # as the browser writes the host
    except UnicodeError as error:
        raise _refuse(address, "Das ist keine öffentliche Seite.") from error
    if "." not in portal:
        raise _refuse(address, "Das ist keine öffentliche Seite.")
    return portal


def clean(address) -> dict:
    """{"portal": host, "adresse": address}; ValueError with a message for the person if it cannot be used."""
    if not isinstance(address, str) or not address.strip():
        raise _refuse(address, "Das ist keine Adresse.")
    if len(address) > MAX_ADDRESS or any(c in address for c in FORBIDDEN_CHARACTERS) or any(ord(c) < 0x20 for c in address):
        raise _refuse(address, "Die Adresse ist zu lang oder enthält Zeichen, die nicht in eine Adresse gehören.")
    if "://" not in address:
        address = f"https://{address}"
    if not set(PLACEHOLDER.findall(address)) <= ALLOWED_PLACEHOLDERS or PLACEHOLDER.sub("", address).count("{") + PLACEHOLDER.sub("", address).count("}"):
        raise _refuse(address, "Erlaubt sind nur die Platzhalter {begriff} und {ort}.")
    portal = _portal(address)
    if any(portal == domain or portal.endswith("." + domain) for domain in DOMAINS.values()):
        raise _refuse(address, "Diese Seite durchsucht die App schon.")
    return {"portal": portal, "adresse": address}


def configured(store: Hits) -> list[dict]:
    """What is stored, without what does not hold (the file can be edited by hand)."""
    sites = []
    for address in store.settings()[OWN_SITES]:
        try:
            sites.append(clean(address))
        except ValueError:
            continue
    return sites


def active(store: Hits) -> list[dict]:
    return configured(store) if own_key() else []


def active_portals(store: Hits) -> frozenset[str]:
    return frozenset(site["portal"] for site in active(store))


def save(store: Hits, addresses) -> list[dict]:
    if not isinstance(addresses, list):
        raise ValueError("Liste der Adressen erwartet")
    if len(addresses) > MAX_SITES:
        raise ValueError(f"Es gehen höchstens {MAX_SITES} weitere Seiten.")
    sites = [clean(address) for address in addresses]
    portals = [site["portal"] for site in sites]
    if len(set(portals)) < len(portals):
        raise ValueError("Eine Seite steht zweimal in der Liste. Pro Seite geht eine Adresse.")
    store.set_own_sites([site["adresse"] for site in sites])
    return sites


def link_id(link: str) -> str:
    """The same ad under another tracking parameter stays the same hit."""
    parts = urllib.parse.urlsplit(link)
    kept = sorted((name, value) for name, value in urllib.parse.parse_qsl(parts.query) if not TRACKING.match(name))
    plain = urllib.parse.urlunsplit((parts.scheme, parts.netloc.lower(), parts.path.rstrip("/"), urllib.parse.urlencode(kept), ""))
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()[:ID_LENGTH]
