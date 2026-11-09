"""The app quits a minute after its last page closed, the way the quit button does (#193, G36).

Each page of the app says it is there every few seconds and says goodbye when it goes, also on a reload. A heartbeat
alone would not do: browsers run the timers of a background tab only about once a minute, so a page counts as
open until it has been silent for PAGE_SILENT_SECONDS; the goodbye makes the minute start when the tab closes.
A request in progress (an AI task runs inside one) and an unfinished search run of the extension hold the app open.
Only the app with pages watches this: the MCP mode and the native host never start a watchdog.
"""
import contextlib
import dataclasses
import logging
import re
import threading
import time
from typing import Callable, Iterator

log = logging.getLogger("bewerbungsbegleiter")

GRACE_SECONDS = 60.0
PAGE_SILENT_SECONDS = 150.0  # longer than two throttled heartbeats of a background tab
SEARCH_SILENT_SECONDS = 15 * 60.0  # a search run whose extension went away stops holding the app
CHECK_EVERY_SECONDS = 5.0
SEARCH_START = frozenset({"/api/suche/plan", "/api/suche/sichten", "/api/suche/treffer", "/api/suche/seite-lesen"})
SEARCH_END = "/api/suche/abschluss"
PAGE_ID = re.compile(r"[A-Za-z0-9-]{1,64}")
BAD_PAGE_ID = "Kennung der Seite fehlt oder ist ungültig"


@dataclasses.dataclass(frozen=True)
class State:
    started: float
    pages: tuple[tuple[str, float], ...] = ()  # page id and when it was last seen
    left_at: float = 0.0
    requests: int = 0
    request_ended_at: float = 0.0
    search_seen: float | None = None  # last request of a search run that has not ended


def _live(state: State, now: float) -> tuple[tuple[str, float], ...]:
    return tuple((page, seen) for page, seen in state.pages if now - seen < PAGE_SILENT_SECONDS)


def seen(state: State, page: str, now: float) -> State:
    others = tuple(item for item in _live(state, now) if item[0] != page)
    return dataclasses.replace(state, pages=(*others, (page, now)))


def left(state: State, page: str, now: float) -> State:
    others = tuple(item for item in _live(state, now) if item[0] != page)
    return dataclasses.replace(state, pages=others, left_at=now)


def request_started(state: State, path: str, now: float) -> State:
    search = now if path in SEARCH_START else state.search_seen
    return dataclasses.replace(state, requests=state.requests + 1, search_seen=search)


def request_ended(state: State, path: str, now: float) -> State:
    search = None if path == SEARCH_END else state.search_seen
    return dataclasses.replace(state, requests=max(0, state.requests - 1), request_ended_at=now, search_seen=search)


def busy(state: State, now: float) -> bool:
    searching = state.search_seen is not None and now - state.search_seen < SEARCH_SILENT_SECONDS
    return state.requests > 0 or searching


def empty_since(state: State, now: float) -> float | None:
    """Since when no page has been open, or None while one is."""
    if _live(state, now):
        return None
    fell_silent = (seen_at + PAGE_SILENT_SECONDS for _, seen_at in state.pages)
    return max(state.started, state.left_at, state.request_ended_at, *fell_silent)


def due(state: State, now: float) -> bool:
    since = empty_since(state, now)
    return since is not None and not busy(state, now) and now - since >= GRACE_SECONDS


class Presence:
    """The state above behind a lock, for the threads of the server."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._lock = threading.Lock()
        self._state = State(started=clock())

    def _apply(self, change: Callable[[State, float], State]) -> None:
        with self._lock:
            self._state = change(self._state, self._clock())

    def page_seen(self, page: str) -> None:
        self._apply(lambda state, now: seen(state, page, now))

    def page_left(self, page: str) -> None:
        self._apply(lambda state, now: left(state, page, now))

    @contextlib.contextmanager
    def request(self, path: str) -> Iterator[None]:
        self._apply(lambda state, now: request_started(state, path, now))
        try:
            yield
        finally:
            self._apply(lambda state, now: request_ended(state, path, now))

    def due(self, now: float | None = None) -> bool:
        with self._lock:
            return due(self._state, self._clock() if now is None else now)


class Watchdog:
    """Looks every few seconds and quits once when no page has been open for a minute."""

    def __init__(self, watched: Presence, quit_app: Callable[[], object], every: float = CHECK_EVERY_SECONDS) -> None:
        self._watched = watched
        self._quit_app = quit_app
        self._every = every
        self._stopped = threading.Event()
        self._quitting = False

    def check(self) -> bool:
        if self._quitting or not self._watched.due():
            return False
        self._quitting = True
        log.info("Kein Fenster der App mehr offen, die App beendet sich")
        self._quit_app()
        return True

    def _run(self) -> None:
        while not self._stopped.wait(self._every):
            try:
                if self.check():
                    return
            except Exception:  # noqa: BLE001 (a failed check must not end the watch; the next one tries again)
                log.exception("Prüfung, ob die App noch offen ist, fehlgeschlagen")
                self._quitting = False

    def start(self) -> None:
        threading.Thread(target=self._run, name="beenden-ohne-fenster", daemon=True).start()

    def stop(self) -> None:
        self._stopped.set()


def _page(body) -> str:
    page = body.get("seite") if isinstance(body, dict) else None
    if not isinstance(page, str) or not PAGE_ID.fullmatch(page):
        raise ValueError(BAD_PAGE_ID)
    return page


def make_routes(watched: Presence) -> tuple[dict, dict]:
    from server import json_antwort

    def here(k, parameter, body):
        watched.page_seen(_page(body))
        return json_antwort({"ok": True})

    def gone(k, parameter, body):
        watched.page_left(_page(body))
        return json_antwort({"ok": True})

    return {}, {"/api/app/da": here, "/api/app/weg": gone}
