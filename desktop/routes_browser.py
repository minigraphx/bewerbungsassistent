"""Route of the card «Browser der App» under Einstellungen, Browser und Erweiterung (G99, #369). Only in the packaged app.

The page learns the choice and which browsers this computer has; it saves on change. A browser that is not found
cannot be saved, but a saved one that is gone stays the choice, so the page can say it was not found.
"""
import dataclasses
from typing import Callable

import app_browser
import settings


@dataclasses.dataclass(frozen=True)
class BrowserRoutes:
    paths: settings.Paths
    system: Callable[[], app_browser.System] = app_browser.current_system


def _state(routes: BrowserRoutes) -> dict:
    system = routes.system()
    found = app_browser.installed(system)
    return {"gewaehlt": settings.app_browser(routes.paths), "plattform": app_browser.page_platform(system.platform),
            "browser": [{"wert": choice, "gefunden": found[choice]} for choice in settings.BROWSER_CHOICES]}


def make_routes(routes: BrowserRoutes) -> tuple[dict, dict]:
    from server import json_antwort

    def show(k, parameter, body):
        return json_antwort(_state(routes))

    def choose(k, parameter, body):
        choice = body.get("wahl") if isinstance(body, dict) else None
        if choice not in settings.BROWSER_CHOICES:
            raise ValueError("Diesen Browser kennt die App nicht.")
        if not app_browser.installed(routes.system())[choice]:
            raise ValueError("Dieser Browser wurde auf diesem Computer nicht gefunden.")
        settings.set_app_browser(routes.paths, choice)
        return json_antwort(_state(routes))

    return {"/api/app/browser": show}, {"/api/app/browser": choose}
