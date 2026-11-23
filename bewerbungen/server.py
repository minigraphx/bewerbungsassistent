"""Lokaler HTTP-Server des Bewerbungsbegleiters: nur 127.0.0.1, Token pro Start, Host-Prüfung gegen
DNS-Rebinding, Content-Security-Policy ohne Inline-Skripte.

Routen sind Funktionen `(kontext, parameter, body) -> Antwort`. Alle `/api/`-Routen brauchen das Token:
GET als Parameter `t`, POST als Header `X-Token` mit JSON-Body. Eine Seite (HTML) enthält es und geht nur mit Sitzung
hinaus: Der Link mit dem Token (`entry_url`) setzt das Cookie, denn den Port erreichen auch andere Konten des Rechners.
"""
import contextlib
import dataclasses
import http.cookies
import json
import logging
import mimetypes
import pathlib
import re
import secrets
import urllib.parse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable, ContextManager

import page_translation
import translation_catalog
import ui_texts

SEITEN = pathlib.Path(__file__).resolve().parent / "seiten"
MAX_BODY = 2 * 1024 * 1024
MAX_DISCARD = 64 * 1024 * 1024  # a larger request is cut off, its answer may get lost
DISCARD_CHUNK = 64 * 1024
FRAMING = "frame-ancestors 'self'"
CSP = ("default-src 'self'; img-src 'self' blob: data:; frame-src 'self' blob:; object-src 'self'; "
       f"style-src 'self'; script-src 'self'; base-uri 'none'; form-action 'none'; {FRAMING}")
# A page may bring its own policy as meta tag (the template with hashes); it then replaces the default one.
EIGENE_CSP = re.compile(r'<meta http-equiv="Content-Security-Policy" content="([^"]+)">')
log = logging.getLogger("bewerbungsbegleiter")


SESSION_COOKIE = "bewerbungsbegleiter-{port}"  # cookies do not tell ports apart
SESSION_DAYS = 30  # the session ends with the app anyway; this keeps it across a restart of the browser
PAGE_LOCKED = ("<!doctype html><html lang=\"de-CH\"><head><meta charset=\"utf-8\"><title>Bewerbungsbegleiter</title>"
               "<link rel=\"stylesheet\" href=\"/stil.css\"></head><body><main class=\"einrichtung\"><h1>Bewerbungsbegleiter</h1>"
               "<p>Diese Seite öffnet sich nur über die App. Bitte den Bewerbungsbegleiter über sein Programmsymbol "
               "öffnen, auch wenn er schon läuft.</p></main></body></html>")


UNSAFE_IN_HEADER = re.compile(r"[^A-Za-z0-9._ -]")


class NichtGefunden(KeyError):
    pass


class ActionError(ValueError):
    """A 400 whose answer also names what the page can do about it, such as opening the window „KI einrichten“."""

    def __init__(self, message: str, action: str) -> None:
        super().__init__(message)
        self.action = action


class StatusError(Exception):
    """A message for the person with a status of its own: a failure that is not about the values sent, so the page
    does not tie it to a field (G97, #350)."""

    def __init__(self, message: str, status: int) -> None:
        super().__init__(message)
        self.status = status


@dataclasses.dataclass(frozen=True)
class Antwort:
    status: int
    typ: str
    inhalt: bytes
    kopf: tuple[tuple[str, str], ...] = ()
    # The value of a JSON answer: the handler says its T messages in the app language before it goes out (#415).
    wert: Any = dataclasses.field(default=None, compare=False, repr=False)


def _json(wert: Any) -> bytes:
    return json.dumps(wert, ensure_ascii=False).encode("utf-8")


def json_antwort(wert: Any, status: int = HTTPStatus.OK) -> Antwort:
    return Antwort(status, "application/json; charset=utf-8", _json(wert), wert=wert)


def _message(error: Exception, keyed: bool = False) -> str:
    """What an error says to the person. A T stays a T, so _fehler can say it in the app language; otherwise the text
    as before: str() of the error, of its first argument for a KeyError, whose own str() would quote it."""
    first = error.args[0] if error.args else None
    if isinstance(first, ui_texts.T):
        return first
    return str(first) if keyed and error.args else str(error)


def _header_name(name: str) -> str:
    """Own files can have any name; a header only takes plain characters and must not end early."""
    return UNSAFE_IN_HEADER.sub("_", name)


def datei_antwort(pfad: pathlib.Path, typ: str | None = None) -> Antwort:
    if not pfad.is_file():
        raise NichtGefunden(f"{pfad.name} nicht gefunden")
    return Antwort(HTTPStatus.OK, typ or mimetypes.guess_type(pfad.name)[0] or "application/octet-stream",
                   pfad.read_bytes(), (("Content-Disposition", f'inline; filename="{_header_name(pfad.name)}"'),))


Route = Callable[[Any, dict[str, str], Any], Antwort]
Activity = Callable[[str], ContextManager[Any]]


class Server(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 32  # a browser opens several connections at once

    def __init__(self, kontext: Any, routen_get: dict[str, Route], routen_post: dict[str, Route],
                 seiten: dict[str, str], port: int = 0, grenzen: dict[str, int] | None = None,
                 hidden_links: tuple[str, ...] = (), activity: Activity | None = None,
                 stand_ins: dict[str, tuple[str, str]] | None = None) -> None:
        self.kontext = kontext
        self.routen_get = routen_get
        self.routen_post = routen_post
        self.seiten = seiten  # Pfad -> Dateiname in seiten/
        self.grenzen = dict(grenzen or {})  # Pfad -> grösste Anfrage, wo MAX_BODY nicht reicht
        self.hidden_links = hidden_links  # links in the fixed menu of the pages to pages that are switched off
        # page -> (route it needs, file shown while that route is missing); decided per request, since the
        # desktop app and its tests register routes after the server is built (#308)
        self.stand_ins = dict(stand_ins or {})
        self.activity = activity or (lambda path: contextlib.nullcontext())  # the desktop app watches for open pages (G36)
        self.token = secrets.token_urlsafe(32)
        self.session = secrets.token_urlsafe(32)
        super().__init__(("127.0.0.1", port), Handler)

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.server_address[1]}/"

    @property
    def entry_url(self) -> str:
        """The address to open: other accounts on this computer reach the port too, so a page needs proof."""
        return f"{self.url}?t={self.token}"


class Handler(BaseHTTPRequestHandler):
    server: Server

    def _senden(self, antwort: Antwort) -> None:
        self.send_response(antwort.status)
        self.send_header("Content-Type", antwort.typ)
        self.send_header("Content-Length", str(len(antwort.inhalt)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        if not any(name == "Content-Security-Policy" for name, _ in antwort.kopf):
            self.send_header("Content-Security-Policy", CSP)
        for name, wert in antwort.kopf:
            self.send_header(name, wert)
        self.end_headers()
        self.wfile.write(antwort.inhalt)

    def _language(self) -> str:
        """The app language of the data folder this server serves; it answers the extension's requests too."""
        return ui_texts.sprache(self.server.kontext)

    def _fehler(self, status: int, meldung: str, action: str | None = None) -> None:
        text = ui_texts.uebersetze(meldung, self._language())
        self._senden(json_antwort({"fehler": text, **({"aktion": action} if action else {})}, status))

    def _in_language(self, antwort: Antwort) -> Antwort:
        """A JSON answer with its T messages in the app language; in German it goes out as the route encoded it."""
        language = self._language()
        if antwort.wert is None or language == ui_texts.GERMAN:
            return antwort
        return dataclasses.replace(antwort, inhalt=_json(ui_texts.translate_marked(antwort.wert, language)))

    def _host_erlaubt(self) -> bool:
        port = self.server.server_address[1]
        return self.headers.get("Host", "") in (f"127.0.0.1:{port}", f"localhost:{port}")

    def _token_gueltig(self, token: str | None) -> bool:
        # Als Bytes vergleichen: compare_digest wirft sonst bei Nicht-ASCII-Zeichen einen TypeError
        return token is not None and secrets.compare_digest(token.encode("utf-8"), self.server.token.encode("utf-8"))

    def _seite(self, datei: str) -> Antwort:
        pfad = SEITEN / datei
        if pfad.suffix == ".html":
            html = pfad.read_text(encoding="utf-8").replace("__TOKEN__", self.server.token)
            for link in self.server.hidden_links:
                html = html.replace(link, "")
            html = page_translation.translate(html, ui_texts.sprache(self.server.kontext))
            eigene = EIGENE_CSP.search(html)
            # frame-ancestors only counts in the header, a meta tag cannot carry it
            kopf = (("Content-Security-Policy", f"{eigene.group(1)}; {FRAMING}"),) if eigene else ()
            return Antwort(HTTPStatus.OK, "text/html; charset=utf-8", html.encode("utf-8"), kopf)
        return datei_antwort(pfad)

    def _translation_script(self, query: str) -> Antwort:
        """The catalog of one language for the scripts of a page (#414); like texte.js it holds nothing personal."""
        language = dict(urllib.parse.parse_qsl(query)).get("sprache")
        if language not in translation_catalog.LANGUAGES:
            raise NichtGefunden("Nicht gefunden")
        return Antwort(HTTPStatus.OK, "text/javascript; charset=utf-8",
                       translation_catalog.script(language).encode("utf-8"))

    def _page_file(self, path: str) -> str:
        needed = self.server.stand_ins.get(path)
        if needed and needed[0] not in self.server.routen_get:
            return needed[1]
        return self.server.seiten[path]

    def _session_cookie_name(self) -> str:
        return SESSION_COOKIE.format(port=self.server.server_address[1])

    def _has_session(self) -> bool:
        try:
            morsel = http.cookies.SimpleCookie(self.headers.get("Cookie", "")).get(self._session_cookie_name())
        except http.cookies.CookieError:
            return False
        return morsel is not None and secrets.compare_digest(morsel.value.encode("utf-8"),
                                                             self.server.session.encode("utf-8"))

    def _page_with_proof(self, teile: urllib.parse.SplitResult) -> Antwort:
        """A page holds the token. It goes out with the session; the link with the token starts the session."""
        datei = self._page_file(teile.path)
        if not datei.endswith(".html"):
            return self._seite(datei)
        query = urllib.parse.parse_qsl(teile.query, keep_blank_values=True)
        if self._token_gueltig(dict(query).get("t")):
            rest = urllib.parse.urlencode([(key, value) for key, value in query if key != "t"])
            cookie = (f"{self._session_cookie_name()}={self.server.session}; Path=/; HttpOnly; SameSite=Lax; "
                      f"Max-Age={SESSION_DAYS * 24 * 3600}")
            return Antwort(HTTPStatus.SEE_OTHER, "text/plain; charset=utf-8", b"",
                           (("Location", teile.path + (f"?{rest}" if rest else "")), ("Set-Cookie", cookie)))
        if self._has_session():
            return self._seite(datei)
        return Antwort(HTTPStatus.FORBIDDEN, "text/html; charset=utf-8", PAGE_LOCKED.encode("utf-8"))

    def do_GET(self) -> None:
        if not self._host_erlaubt():
            return self._fehler(HTTPStatus.FORBIDDEN, "Unbekannter Host")
        teile = urllib.parse.urlsplit(self.path)
        if teile.path in self.server.seiten:
            return self._senden(self._page_with_proof(teile))
        if teile.path == page_translation.SCRIPT_PATH:
            return self._run_route(lambda kontext, parameter, body: self._translation_script(teile.query), {}, None)
        route = self.server.routen_get.get(teile.path)
        if route is None:
            return self._fehler(HTTPStatus.NOT_FOUND, "Nicht gefunden")
        parameter = {k: v[-1] for k, v in urllib.parse.parse_qs(teile.query).items()}
        if not self._token_gueltig(parameter.pop("t", None)):
            return self._fehler(HTTPStatus.FORBIDDEN, "Ungültiges Token")
        self._ausfuehren(route, parameter, None)

    def do_POST(self) -> None:
        if not self._host_erlaubt():
            return self._fehler(HTTPStatus.FORBIDDEN, "Unbekannter Host")
        teile = urllib.parse.urlsplit(self.path)
        route = self.server.routen_post.get(teile.path)
        if route is None:
            return self._fehler(HTTPStatus.NOT_FOUND, "Nicht gefunden")
        if not self._token_gueltig(self.headers.get("X-Token")):
            return self._fehler(HTTPStatus.FORBIDDEN, "Ungültiges Token")
        if self.headers.get_content_type() != "application/json":
            return self._fehler(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "Erwartet application/json")
        try:
            laenge = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            laenge = -1
        grenze = self.server.grenzen.get(teile.path, MAX_BODY)
        if not 0 < laenge <= grenze:
            self._discard_body(laenge)
            return self._fehler(HTTPStatus.BAD_REQUEST, f"Anfrage leer oder grösser als {grenze} Bytes")
        try:
            body = json.loads(self.rfile.read(laenge))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return self._fehler(HTTPStatus.BAD_REQUEST, "Ungültiges JSON")
        parameter = {k: v[-1] for k, v in urllib.parse.parse_qs(teile.query).items()}
        self._ausfuehren(route, parameter, body)

    def _discard_body(self, length: int) -> None:
        """Read what the browser is still sending; if it cannot finish, it never sees the answer."""
        remaining = min(length, MAX_DISCARD)
        while remaining > 0:
            chunk = self.rfile.read(min(remaining, DISCARD_CHUNK))
            if not chunk:
                break
            remaining -= len(chunk)
        self.close_connection = True

    def _ausfuehren(self, route: Route, parameter: dict, body: Any) -> None:
        with self.server.activity(urllib.parse.urlsplit(self.path).path):
            self._run_route(route, parameter, body)

    def _run_route(self, route: Route, parameter: dict, body: Any) -> None:
        try:
            antwort = route(self.server.kontext, parameter, body)
        except KeyError as fehler:  # NichtGefunden among them
            return self._fehler(HTTPStatus.NOT_FOUND, _message(fehler, keyed=True))
        except ValueError as fehler:
            return self._fehler(HTTPStatus.BAD_REQUEST, _message(fehler), getattr(fehler, "action", None))
        except StatusError as fehler:
            return self._fehler(fehler.status, _message(fehler))
        except Exception:
            log.exception("Fehler bei %s %s", self.command, self.path)
            return self._fehler(HTTPStatus.INTERNAL_SERVER_ERROR, "Interner Fehler, Details in der Konsole")
        self._senden(self._in_language(antwort))

    def log_message(self, format: str, *args) -> None:
        log.debug(format, *args)


def pflicht(parameter: dict, name: str) -> str:
    wert = parameter.get(name)
    if not wert:
        raise ValueError(f"Parameter {name} fehlt")
    return wert
