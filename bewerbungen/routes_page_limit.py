"""Routes of the page limit of the CV (G51), for the switch under Einstellungen > Erweitert.

Neither the browser extension nor Claude reach these routes (allow lists in desktop/native_host.py and
desktop/mcp_tools.py).
"""
import page_limit
from server import json_antwort

PATH = "/api/unterlagen/seitengrenze"


def show(k, parameter, body):
    return json_antwort(page_limit.as_dict(page_limit.load(k.daten)))


def store(k, parameter, body):
    return json_antwort(page_limit.as_dict(page_limit.save(k, body)))


GET = {PATH: show}
POST = {PATH: store}
