"""Lokaler HTTP-Server des Bewerbungsassistenten: nur 127.0.0.1, Token pro Start, Host-Prüfung gegen
DNS-Rebinding, Content-Security-Policy ohne Inline-Skripte.

Routen sind Funktionen `(kontext, parameter, body) -> Antwort`. Seiten (HTML) brauchen kein Token, alle
`/api/`-Routen schon: GET als Parameter `t`, POST als Header `X-Token` mit JSON-Body.
"""
import dataclasses
import json
import logging
import mimetypes
import pathlib
import secrets
import urllib.parse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable

SEITEN = pathlib.Path(__file__).resolve().parent / "seiten"
MAX_BODY = 2 * 1024 * 1024
CSP = ("default-src 'self'; img-src 'self' blob: data:; frame-src 'self' blob:; object-src 'self'; "
       "style-src 'self'; script-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'self'")
log = logging.getLogger("bewerbungsassistent")


class NichtGefunden(KeyError):
    pass


@dataclasses.dataclass(frozen=True)
class Antwort:
    status: int
    typ: str
    inhalt: bytes
    kopf: tuple[tuple[str, str], ...] = ()


def json_antwort(wert: Any, status: int = HTTPStatus.OK) -> Antwort:
    return Antwort(status, "application/json; charset=utf-8", json.dumps(wert, ensure_ascii=False).encode("utf-8"))


def datei_antwort(pfad: pathlib.Path, typ: str | None = None) -> Antwort:
    if not pfad.is_file():
        raise NichtGefunden(f"{pfad.name} nicht gefunden")
    return Antwort(HTTPStatus.OK, typ or mimetypes.guess_type(pfad.name)[0] or "application/octet-stream",
                   pfad.read_bytes(), (("Content-Disposition", f'inline; filename="{pfad.name}"'),))


Route = Callable[[Any, dict[str, str], Any], Antwort]


class Server(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, kontext: Any, routen_get: dict[str, Route], routen_post: dict[str, Route],
                 seiten: dict[str, str], port: int = 0) -> None:
        self.kontext = kontext
        self.routen_get = routen_get
        self.routen_post = routen_post
        self.seiten = seiten  # Pfad -> Dateiname in seiten/
        self.token = secrets.token_urlsafe(32)
        super().__init__(("127.0.0.1", port), Handler)

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.server_address[1]}/"


class Handler(BaseHTTPRequestHandler):
    server: Server

    def _senden(self, antwort: Antwort) -> None:
        self.send_response(antwort.status)
        self.send_header("Content-Type", antwort.typ)
        self.send_header("Content-Length", str(len(antwort.inhalt)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", CSP)
        for name, wert in antwort.kopf:
            self.send_header(name, wert)
        self.end_headers()
        self.wfile.write(antwort.inhalt)

    def _fehler(self, status: int, meldung: str) -> None:
        self._senden(json_antwort({"fehler": meldung}, status))

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
            return Antwort(HTTPStatus.OK, "text/html; charset=utf-8", html.encode("utf-8"))
        return datei_antwort(pfad)

    def do_GET(self) -> None:
        if not self._host_erlaubt():
            return self._fehler(HTTPStatus.FORBIDDEN, "Unbekannter Host")
        teile = urllib.parse.urlsplit(self.path)
        if teile.path in self.server.seiten:
            return self._senden(self._seite(self.server.seiten[teile.path]))
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
        if not 0 < laenge <= MAX_BODY:
            return self._fehler(HTTPStatus.BAD_REQUEST, f"Anfrage leer oder grösser als {MAX_BODY} Bytes")
        try:
            body = json.loads(self.rfile.read(laenge))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return self._fehler(HTTPStatus.BAD_REQUEST, "Ungültiges JSON")
        parameter = {k: v[-1] for k, v in urllib.parse.parse_qs(teile.query).items()}
        self._ausfuehren(route, parameter, body)

    def _ausfuehren(self, route: Route, parameter: dict, body: Any) -> None:
        try:
            antwort = route(self.server.kontext, parameter, body)
        except NichtGefunden as fehler:
            return self._fehler(HTTPStatus.NOT_FOUND, str(fehler.args[0] if fehler.args else fehler))
        except KeyError as fehler:
            return self._fehler(HTTPStatus.NOT_FOUND, str(fehler.args[0] if fehler.args else fehler))
        except ValueError as fehler:
            return self._fehler(HTTPStatus.BAD_REQUEST, str(fehler))
        except Exception:
            log.exception("Fehler bei %s %s", self.command, self.path)
            return self._fehler(HTTPStatus.INTERNAL_SERVER_ERROR, "Interner Fehler, Details in der Konsole")
        self._senden(antwort)

    def log_message(self, format: str, *args) -> None:
        log.debug(format, *args)


def pflicht(parameter: dict, name: str) -> str:
    wert = parameter.get(name)
    if not wert:
        raise ValueError(f"Parameter {name} fehlt")
    return wert
