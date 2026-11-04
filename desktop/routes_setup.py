"""Routes of the setup page (MIN-342): choose the data folder, import the einstieg file.

The app starts on a placeholder folder until a data folder is chosen; then `switch` gives the running
server the new folder, without a restart. The AI invitation uses the existing routes under /api/ki/.
"""
import dataclasses
import datetime
import pathlib
import sys
from http import HTTPStatus
from typing import Callable

import dialogs
import extension
import settings
import setup

DIALOG_KINDS = ("ordner", "datei")


@dataclasses.dataclass
class Setup:
    paths: settings.Paths
    switch: Callable[[pathlib.Path], None]
    suggestion: pathlib.Path
    forbidden: tuple[pathlib.Path, ...] = ()
    choose: Callable[[str, pathlib.Path], pathlib.Path | None] = (
        lambda kind, start: dialogs.choose(kind, start, sys.platform))
    downloads: pathlib.Path = dataclasses.field(default_factory=lambda: pathlib.Path.home() / "Downloads")
    today: Callable[[], datetime.date] = datetime.date.today
    extension_dir: pathlib.Path | None = None  # developer add-on to load in the browser (MIN-339)
    reveal: Callable[[pathlib.Path], None] = lambda folder: dialogs.reveal(folder, sys.platform)
    open_page: Callable[[str], None] = lambda browser: dialogs.open_extensions_page(browser, sys.platform)

    def data_dir(self) -> pathlib.Path | None:
        return settings.chosen_data_dir(self.paths)


def _sync(state: Setup, k) -> bool:
    """Use the chosen folder when the server still runs on another one (e.g. a USB stick plugged in later)."""
    chosen = state.data_dir()
    if chosen is None or not chosen.is_dir() or k.daten == chosen.resolve():
        return False
    state.switch(chosen)
    return True


def _path(body) -> str:
    value = body.get("pfad") if isinstance(body, dict) else None
    if not isinstance(value, str):
        raise ValueError("Pfad fehlt")
    return value


def make_routes(state: Setup) -> tuple[dict, dict]:
    from server import json_antwort

    def overview(k, parameter, body, switched: bool | None = None):
        switched = _sync(state, k) if switched is None else switched
        chosen = state.data_dir()
        has_cv = chosen is not None and (chosen / "cv.yaml").is_file()
        return json_antwort({"eingerichtet": chosen is not None, "datenordner": str(chosen) if chosen else None,
                             "fehlt": chosen is not None and not chosen.is_dir(), "gewechselt": switched,
                             "vorschlag": str(state.suggestion), "lebenslauf": has_cv,
                             "erweiterung": _extension(state)})

    def check(k, parameter, body):
        found = setup.check_folder(_path(body), state.forbidden)
        return json_antwort({"pfad": str(found.path), "zustand": found.state, "text": found.text})

    def choose_data_dir(k, parameter, body):
        found = setup.check_folder(_path(body), state.forbidden)
        folder = setup.prepare(found)
        state.switch(folder)
        settings.remember_data_dir(state.paths, folder)
        return overview(k, parameter, body, switched=False)

    def dialog(k, parameter, body):
        kind = body.get("art") if isinstance(body, dict) else None
        if kind not in DIALOG_KINDS:
            raise ValueError("Unbekannte Auswahl")
        start = state.downloads if kind == "datei" else (state.data_dir() or state.suggestion).parent
        chosen = state.choose(kind, start if start.is_dir() else pathlib.Path.home())
        return json_antwort({"pfad": str(chosen) if chosen else None})

    def import_einstieg(k, parameter, body):
        return _import(state, k, body, json_antwort)

    def show_folder(k, parameter, body):
        kind = body.get("art") if isinstance(body, dict) else None
        folders = {"erweiterung": state.extension_dir, "datenordner": state.data_dir()}
        if kind not in folders or folders[kind] is None:
            raise ValueError("Unbekannter Ordner")
        state.reveal(folders[kind])
        return json_antwort({"ok": True})

    def extensions_page(k, parameter, body):
        if state.extension_dir is None:
            raise ValueError("Die Erweiterung gibt es nur in der installierten App.")
        state.open_page(body.get("browser") if isinstance(body, dict) else None)
        state.reveal(state.extension_dir)
        return json_antwort({"ok": True})

    return ({"/api/app/einrichtung": overview},
            {"/api/app/ordner-pruefen": check, "/api/app/datenordner": choose_data_dir,
             "/api/app/waehlen": dialog, "/api/app/einstieg": import_einstieg,
             "/api/app/ordner-zeigen": show_folder, "/api/app/erweiterungsseite": extensions_page})


def _extension(state: Setup) -> dict | None:
    if state.extension_dir is None:
        return None
    return {"ordner": str(state.extension_dir), "version": extension.version(state.extension_dir)}


def ready_data_dir(state: Setup, k) -> pathlib.Path:
    """The chosen data folder, in use by the server; ValueError with a German message if there is none."""
    target = state.data_dir()
    if target is None:
        raise ValueError("Bitte zuerst den Datenordner wählen.")
    if not target.is_dir():
        raise ValueError(f"Der Datenordner {target} wurde nicht gefunden.")
    _sync(state, k)
    return target


def rejected_answer(rejected, replace: bool, json_antwort):
    """Existing files become a question (409, the page offers to replace them), anything else an error."""
    problems = rejected.messages
    existing = any("gibt es schon" in p for p in problems)
    text = " ".join(p.replace("Zum Ersetzen mit --force aufrufen", "Zum Ersetzen „Vorhandene Dateien ersetzen“ wählen")
                    for p in problems)
    if existing and not replace:
        return json_antwort({"fehler": text, "vorhanden": True}, HTTPStatus.CONFLICT)
    raise ValueError(text) from rejected


def _import(state: Setup, k, body, json_antwort):
    import import_bundle  # onboarding/; imported late, it pulls in the form definition
    target = ready_data_dir(state, k)
    source = pathlib.Path(_path(body).strip()).expanduser()
    if not source.is_file():
        raise ValueError("Die Datei wurde nicht gefunden.")
    replace = bool(body.get("ersetzen"))
    try:
        result = import_bundle.import_file(target, source, state.today(), force=replace)
    except import_bundle.ImportRejected as rejected:
        return rejected_answer(rejected, replace, json_antwort)
    return json_antwort({"geschrieben": result.written, "dokumente": result.documents,
                         "unvollstaendig": result.incomplete})
