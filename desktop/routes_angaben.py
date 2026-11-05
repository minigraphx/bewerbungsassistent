"""Routes of the page „Meine Angaben“ (MIN-366): the onboarding template inside the app.

The port of the app changes with every start, so the browser's own storage would be lost: the state of the
form and the documents go straight to the data folder (`dokumente/`, not in Git). Taking over uses the same
checks as importing a file (`onboarding/import_bundle.py`), with drafts of what it replaces.
Suggestions from documents (`onboarding/prefill.py`) run outside the lock, because the AI takes a while.
"""
import base64
import binascii
import json
import logging
import pathlib
import threading

import preferences
from routes_setup import Setup, ready_data_dir, rejected_answer

log = logging.getLogger(__name__)

STATE_FILE = "dokumente/angaben-stand.json"
UPLOAD_ROUTE = "/api/angaben/unterlage"
PREFILL_ROUTE = "/api/angaben/vorbefuellen"
BASE64_OVERHEAD = 4 / 3
JSON_OVERHEAD_BYTES = 10_000
DEFAULT_TRACK = "job"  # only for the wording of messages
TRACKS = {preferences.JOB: "job", preferences.APPRENTICESHIP: "apprenticeship"}  # setup → form (form.json tracks)
PREFILL_RUNNING = "Die Unterlagen werden schon gelesen. Bitte einen Moment warten."


def _body(body) -> dict:
    if not isinstance(body, dict):
        raise ValueError("Die Anfrage hat eine unbekannte Form.")
    return body


def _state_path(folder: pathlib.Path) -> pathlib.Path:
    from dateien import im_ordner
    return im_ordner(folder, STATE_FILE)


def _existing_basics(folder: pathlib.Path) -> list[str]:
    import convert
    return [rel for rel in convert.BASICS if (folder / rel).is_file()]


def _read_state(folder: pathlib.Path) -> dict | None:
    """The kept state of the form; a broken file must not keep the person from the page."""
    path = _state_path(folder)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        log.warning("Zwischenstand nicht lesbar: %s", error)
        return None


def _track(form: dict, value: object) -> str:
    return value if isinstance(value, str) and value in form["tracks"] else DEFAULT_TRACK


def _one_at_a_time(routes: dict, lock: threading.Lock) -> dict:
    """The server runs requests in threads; the list of pending documents is read, changed and written back."""

    def guarded(route):
        def run(k, parameter, body):
            with lock:
                return route(k, parameter, body)
        return run

    return {path: guarded(route) for path, route in routes.items()}


def _decode(body: dict) -> bytes:
    data = body.get("data")
    if not isinstance(data, str):
        raise ValueError("Die Datei fehlt.")
    try:
        return base64.b64decode(data, validate=True)
    except binascii.Error as error:
        raise ValueError("Die Datei liess sich nicht lesen.") from error


def _choice(folder: pathlib.Path) -> dict:
    """What the setup chose (MIN-369), or what follows from the search profile before a choice: the page shows it on
    the start instead of asking again, and starts in its track."""
    choice = preferences.load(folder)
    return {"track": TRACKS[choice.sought], "anrede": choice.address, "rav": choice.rav, "gewaehlt": choice.chosen}


def make_routes(state: Setup) -> tuple[dict, dict, dict]:
    """GET routes, POST routes and the request size allowed for uploads."""
    from dateien import schreibe_atomar
    from server import json_antwort
    import archive
    import documents
    import import_bundle
    import import_documents
    import prefill
    import routes_ai
    import validation

    form = validation.load_form()
    documents_lock = threading.Lock()
    prefill_running = threading.Lock()
    upload_limit = int(form["documents"]["maxFileBytes"] * BASE64_OVERHEAD) + JSON_OVERHEAD_BYTES

    def overview(k, parameter, body):
        folder = ready_data_dir(state, k)
        return json_antwort({"stand": _read_state(folder), "unterlagen": import_documents.pending_documents(folder),
                             "vorhanden": _existing_basics(folder), "wahl": _choice(folder)})

    def not_taken_over(k, parameter, body):
        stored = _read_state(ready_data_dir(state, k))
        return json_antwort({"offen": isinstance(stored, dict) and stored.get("offen") is True})

    def keep_state(k, parameter, body):
        folder = ready_data_dir(state, k)
        stored = _body(body).get("stand")
        if not isinstance(stored, dict):
            raise ValueError("Der Zwischenstand hat eine unbekannte Form.")
        schreibe_atomar(_state_path(folder), json.dumps(stored, ensure_ascii=False).encode("utf-8"))
        return json_antwort({"ok": True})

    def discard_state(k, parameter, body):
        _state_path(ready_data_dir(state, k)).unlink(missing_ok=True)
        return json_antwort({"ok": True})

    def add_document(k, parameter, body):
        folder = ready_data_dir(state, k)
        request = _body(body)
        data = _decode(request)
        known = import_documents.pending_documents(folder)
        entry = {"category": request.get("category"), "name": request.get("name"), "size": len(data)}
        entries = [*({"category": d["category"], "name": d["name"], "size": d["size"]} for d in known), entry]
        errors = documents.validate_documents(form, entries)
        if errors:
            track = _track(form, request.get("track"))
            raise ValueError(" ".join(documents.describe(form, track, entries, e) for e in errors))
        document = archive.Document(entry["category"], entry["name"], data)
        import_documents.store_documents(folder, (document,), state.today())
        return json_antwort({"unterlagen": import_documents.pending_documents(folder)})

    def remove_document(k, parameter, body):
        folder = ready_data_dir(state, k)
        rel = _body(body).get("datei")
        if not isinstance(rel, str):
            raise ValueError("Die Unterlage fehlt.")
        import_documents.remove_pending(folder, rel)
        return json_antwort({"unterlagen": import_documents.pending_documents(folder)})

    def take_over(k, parameter, body):
        folder = ready_data_dir(state, k)
        request = _body(body)
        replace = bool(request.get("ersetzen"))
        try:
            result = import_bundle.import_answers(folder, request.get("bundle"), state.today(), force=replace)
        except import_bundle.ImportRejected as rejected:
            return rejected_answer(rejected, replace, json_antwort)
        if not result.incomplete:
            import_documents.settle_read(folder)
        return json_antwort({"geschrieben": result.written, "unvollstaendig": result.incomplete,
                             "behalten": list(result.kept_terms)})

    def prefill_documents(k, parameter, body):
        """Suggestions only: nothing is written to the person's files, the page shows them for checking."""
        folder = ready_data_dir(state, k)
        request = _body(body)
        data = request.get("data")
        if not isinstance(data, dict):
            raise ValueError("Die Angaben haben eine unbekannte Form.")
        if not prefill_running.acquire(blocking=False):
            raise ValueError(PREFILL_RUNNING)
        try:
            result = routes_ai.run_ai(
                lambda: prefill.suggest(form, folder, request.get("track"), data, routes_ai.new_client))
        finally:
            prefill_running.release()
        with documents_lock:
            import_documents.mark_read(folder, result["datei"])
        return json_antwort(result)

    return ({"/api/angaben/stand": overview, "/api/angaben/offen": not_taken_over},
            _one_at_a_time({"/api/angaben/stand": keep_state, "/api/angaben/stand-loeschen": discard_state,
                            UPLOAD_ROUTE: add_document, "/api/angaben/unterlage-entfernen": remove_document,
                            "/api/angaben/uebernehmen": take_over}, documents_lock)
            | {PREFILL_ROUTE: prefill_documents},
            {UPLOAD_ROUTE: upload_limit})
