"""Routes of the section „Mit dem eigenen Claude-Abo arbeiten“ (MIN-377). Only present in the desktop app; the extension and Claude cannot reach them."""
import dataclasses
import pathlib
from http import HTTPStatus

import claude_setup
import settings

CONFIRM_FIRST = "Bitte zuerst bestätigen, dass Sie die Hinweise gelesen haben."


@dataclasses.dataclass(frozen=True)
class ClaudeRoutes:
    paths: settings.Paths
    config: pathlib.Path
    command: tuple[str, ...]
    skills: pathlib.Path


def make_routes(setup: ClaudeRoutes) -> tuple[dict, dict]:
    from server import Antwort, json_antwort, pflicht

    def state() -> dict:
        command = list(setup.command)
        return {"zugang": settings.claude_access(setup.paths), "desktop_eingetragen": claude_setup.is_entered(setup.config),
                "desktop_veraltet": claude_setup.is_stale(setup.config, command),
                "desktop_datei": str(setup.config), "desktop_text": claude_setup.config_text(command), "code_befehl": claude_setup.code_line(command),
                "skills": list(claude_setup.SKILLS)}

    def status(k, parameter, body):
        return json_antwort(state())

    def access(k, parameter, body):
        if not isinstance(body, dict) or not isinstance(body.get("an"), bool):
            raise ValueError("an erwartet (ja oder nein)")
        if body["an"] and body.get("bestaetigt") is not True:
            raise ValueError(CONFIRM_FIRST)
        settings.set_claude_access(setup.paths, body["an"])
        return json_antwort(state())

    def desktop(k, parameter, body):
        if not isinstance(body, dict) or not isinstance(body.get("eintragen"), bool):
            raise ValueError("eintragen erwartet (ja oder nein)")
        if body["eintragen"] and not settings.claude_access(setup.paths):
            raise ValueError("Bitte zuerst den Zugang einschalten.")
        if body["eintragen"]:
            claude_setup.enter_in_desktop(setup.config, list(setup.command))
        else:
            claude_setup.remove_from_desktop(setup.config)
        return json_antwort(state())

    def skill(k, parameter, body):
        name = pflicht(parameter, "name")
        content = claude_setup.skill_zip(setup.skills, name)
        return Antwort(HTTPStatus.OK, "application/zip", content, (("Content-Disposition", f'attachment; filename="{name}.zip"'),))

    return ({"/api/claude/stand": status, "/api/claude/skill": skill},
            {"/api/claude/zugang": access, "/api/claude/desktop": desktop})
