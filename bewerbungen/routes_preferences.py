"""Routes of the choice from the setup (MIN-369): what is sought, the form of address, RAV.

Read by every page for its text set, written by the setup and later by „Meine Angaben“. Neither the browser
extension nor Claude reach these routes (allow lists in desktop/native_host.py and desktop/mcp_tools.py).
"""
import preferences
from server import json_antwort


def show(k, parameter, body):
    return json_antwort(preferences.load(k.daten).as_dict())


def store(k, parameter, body):
    return json_antwort(preferences.save(k, body).as_dict())


GET = {"/api/einrichtung/wahl": show}
POST = {"/api/einrichtung/wahl": store}
