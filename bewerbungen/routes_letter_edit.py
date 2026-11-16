"""Route for the letter editor on the application page (G94, #332): saves subject, salutation, paragraphs and closing.

It saves like „Inhalte als Text“: a test build first (`inhalte.pruefe_inhalt`), then the file with drafts before and
after (`Kontext.mit_entwurf`). A write changes the fingerprint, so the approval is void on its own (letter_approval).
"""
from http import HTTPStatus

import inhalte
import letter_approval
import letter_edit
import unterlagen
from dateien import schreibe_atomar
from server import Antwort, json_antwort, pflicht

DRAFT_NOTE = "Anschreiben geändert"


def _refuse_fixed(k, entry: dict) -> None:
    """Sent or replaced by an own PDF, the letter stays as it is; the same words as for the approval."""
    if entry.get("versand"):
        raise ValueError(letter_approval.ALREADY_SENT)
    if unterlagen.own_letter(k.daten, entry) is not None:
        raise ValueError(letter_approval.OWN_LETTER)


def _write(k, path, edit: letter_edit.LetterEdit) -> bool:
    """Checks and writes the letter; False when nothing would change. LetterChanged when the file moved on."""
    if letter_approval.fingerprint(path) != edit.fingerprint:
        raise letter_edit.LetterChanged()
    current = path.read_text(encoding="utf-8")
    if letter_edit.unchanged(current, edit):
        return False
    text = letter_edit.merged(current, edit)
    with k.sperre:
        inhalte.pruefe_inhalt(k.daten, path.relative_to(k.daten).as_posix(), text, k.build)

    def write() -> None:
        # under the lock of mit_entwurf: nothing may have written the file since it was read
        if letter_approval.fingerprint(path) != edit.fingerprint:
            raise letter_edit.LetterChanged()
        schreibe_atomar(path, text.encode("utf-8"))

    k.mit_entwurf(path, DRAFT_NOTE, write)
    return True


def save(k, parameter, body) -> Antwort:
    edit = letter_edit.request_of(body)
    entry = k.register().hole(pflicht(parameter, "id"))
    _refuse_fixed(k, entry)
    try:
        changed = _write(k, unterlagen.letter_source(k.daten, entry["id"]), edit)
    except letter_edit.LetterChanged:
        return json_antwort({"fehler": letter_edit.CHANGED}, HTTPStatus.CONFLICT)
    return json_antwort({"geaendert": changed})


GET = {}
POST = {"/api/bewerbung/anschreiben": save}
