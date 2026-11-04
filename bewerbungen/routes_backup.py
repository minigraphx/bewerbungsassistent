"""Routes of the backup (MIN-359): the ZIP for the browser, the reminder, and the note that it was saved."""
from http import HTTPStatus

import backup
from server import Antwort, json_antwort


def _state(k) -> dict:
    return backup.reminder(k.daten, k.register().alle(), k.heute())


def stand(k, parameter, body):
    return json_antwort(_state(k))


def datei(k, parameter, body):
    name = backup.file_name(k.heute())
    return Antwort(HTTPStatus.OK, "application/zip", backup.create(k.daten), (("Content-Disposition", f'attachment; filename="{name}"'),))


def erledigt(k, parameter, body):
    backup.mark_done(k.daten, k.heute())
    return json_antwort(_state(k))


GET = {"/api/sicherung/stand": stand, "/api/sicherung/datei": datei}
POST = {"/api/sicherung/erledigt": erledigt}
