"""Routes of the page Firmen (G35, #188): the companies of hits and applications and their kununu page.

Neither the browser extension nor Claude reach these routes (allow lists in desktop/native_host.py and
desktop/mcp_tools.py); nothing here goes to the AI.
"""
import datetime

import companies
from server import json_antwort, pflicht


def _applications(k) -> list[dict]:
    return k.register().alle()


def _body(body) -> dict:
    if not isinstance(body, dict):
        raise ValueError("Angaben fehlen")
    return body


def listing(k, parameter, body):
    return json_antwort({"firmen": companies.rows(k.daten, _applications(k)), "heute": datetime.date.today().isoformat()})


def assign(k, parameter, body):
    """„Selbst zuordnen“: a pasted link to the company on kununu.com/ch or kununu.de."""
    key = pflicht(parameter, "firma")
    return json_antwort(companies.assign(k, _applications(k), key, _body(body).get("link")))


def choose(k, parameter, body):
    """„Passende wählen“: one of the companies kununu listed, or none of them."""
    key = pflicht(parameter, "firma")
    values = _body(body)
    link = None if values.get("keine") is True else values.get("link")
    return json_antwort(companies.choose(k, _applications(k), key, link, datetime.date.today()))


GET = {"/api/firmen": listing}
POST = {"/api/firmen/zuordnen": assign, "/api/firmen/waehlen": choose}
