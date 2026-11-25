"""Routes of the languages (G10, G12, #94), for the card «Sprache» under Einstellungen, KI, Budget und Sprache, and
the language switch in the sidebar and on Einrichtung (#435).

`uebersetzung` tells the pages whether the translation is on: until #434 a choice is only stored, afterwards the
switch reloads the page in the new language. Neither the browser extension nor Claude reach these routes (allow
lists in desktop/native_host.py and desktop/mcp_tools.py).
"""
import language_settings
import ui_texts
from server import json_antwort

PATH = "/api/sprachen"


def _answer(settings: language_settings.Settings):
    return json_antwort({**settings.as_dict(), "uebersetzung": ui_texts.is_on()})


def show(k, parameter, body):
    return _answer(language_settings.load(k.daten))


def store(k, parameter, body):
    return _answer(language_settings.save(k, body))


GET = {PATH: show}
POST = {PATH: store}
