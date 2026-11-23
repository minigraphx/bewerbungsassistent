"""Routes of the languages (G10, G12, #94), for the card «Sprache» under Einstellungen, KI, Budget und Sprache.

Neither the browser extension nor Claude reach these routes (allow lists in desktop/native_host.py and
desktop/mcp_tools.py).
"""
import language_settings
from server import json_antwort

PATH = "/api/sprachen"


def show(k, parameter, body):
    return json_antwort(language_settings.load(k.daten).as_dict())


def store(k, parameter, body):
    return json_antwort(language_settings.save(k, body).as_dict())


GET = {PATH: show}
POST = {PATH: store}
