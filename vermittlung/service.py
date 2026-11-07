"""HTTP service of the mediation (MIN-344): same interface as the Messages API, one access per person.

  POST /v1/messages              Messages API (also streaming), access in x-api-key or Authorization: Bearer
  POST /v1/invitations/redeem    {"code", "device", "consent"} → {"access"}; the app keeps the access in the keychain
  GET  /v1/account               month, spent and budget of the person
  GET  /health                   for the container

Contents are passed through and never stored or logged. Runs behind a TLS proxy (Caddy).
"""
import dataclasses
import datetime
import http.server
import json
import logging
from typing import Callable

from limits import ParallelLimiter, RateLimiter
from policy import Policy, PolicyError
from pricing import cost_usd
from store import Access, Store, StoreError, month_of
from upstream import JSON_TYPE, Upstream, error_body

MAX_BODY = 2 * 1024 * 1024
MAX_LOGGED_REASON = 200
DEFAULT_AT_ONCE = 5  # the app runs three checks of a job at once, plus what the person starts meanwhile
BUSY_RETRY_SECONDS = 5
log = logging.getLogger("vermittlung")


def _error_type(body: bytes) -> str:
    """Only the type: the message of an error can quote the request, and the logs hold no contents."""
    try:
        kind = json.loads(body)["error"]["type"]
    except (ValueError, KeyError, TypeError):
        return "unknown"
    return kind[:MAX_LOGGED_REASON] if isinstance(kind, str) else "unknown"


@dataclasses.dataclass
class Mediation:
    store: Store
    upstream: Upstream
    policy: Policy = dataclasses.field(default_factory=Policy)
    calls: RateLimiter = dataclasses.field(default_factory=lambda: RateLimiter(10))
    redeems: RateLimiter = dataclasses.field(default_factory=lambda: RateLimiter(5))
    parallel: ParallelLimiter = dataclasses.field(default_factory=lambda: ParallelLimiter(DEFAULT_AT_ONCE))
    now: Callable[[], datetime.datetime] = lambda: datetime.datetime.now(datetime.timezone.utc)
    trust_proxy: bool = False


class Failure(Exception):
    def __init__(self, status: int, kind: str, message: str, retry_after: int | None = None) -> None:
        super().__init__(message)
        self.status, self.kind, self.retry_after = status, kind, retry_after


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "vermittlung"
    sys_version = ""

    @property
    def mediation(self) -> Mediation:
        return self.server.mediation  # type: ignore[attr-defined]

    def do_GET(self) -> None:  # noqa: N802
        self._guarded({"/health": self._health, "/v1/account": self._account})

    def do_POST(self) -> None:  # noqa: N802
        self._guarded({"/v1/messages": self._messages, "/v1/invitations/redeem": self._redeem})

    def _guarded(self, routes: dict) -> None:
        route = routes.get(self.path.split("?", 1)[0])
        try:
            if route is None:
                raise Failure(404, "not_found_error", "not found")
            route()
        except Failure as failure:
            # ascii(): the reason can quote field names of the request, and one line stays one line
            log.info("refused with %s %s: %s", failure.status, failure.kind, ascii(str(failure)[:MAX_LOGGED_REASON]))
            headers = {"retry-after": str(failure.retry_after)} if failure.retry_after else {}
            self._send(failure.status, error_body(failure.kind, str(failure)), headers=headers)
        except BrokenPipeError:
            log.info("client closed the connection")
        except Exception:
            log.exception("internal error on %s", self.path)
            self._send(500, error_body("api_error", "internal error"))

    # routes

    def _health(self) -> None:
        self._send(200, b'{"ok": true}')

    def _account(self) -> None:
        access = self._access()
        month = month_of(self.mediation.now())
        self._send_json(200, {"month": month, "spent_usd": self.mediation.store.spent(access.person, month),
                              "budget_usd": access.budget_usd})

    def _redeem(self) -> None:
        wait = self.mediation.redeems.acquire(self._client_address())
        if wait:
            raise Failure(429, "rate_limit_error", "too many attempts", wait)
        body = self._body()
        if not isinstance(body, dict) or not isinstance(body.get("code"), str):
            raise Failure(400, "invalid_request_error", "code expected")
        try:
            token = self.mediation.store.redeem(body["code"], str(body.get("device") or ""), self.mediation.now(),
                                                str(body.get("consent") or ""))
        except StoreError as error:
            raise Failure(400, "invalid_request_error", str(error)) from error
        self._send_json(200, {"access": token})

    def _messages(self) -> None:
        access = self._access()
        wait = self.mediation.calls.acquire(access.person)
        if wait:
            raise Failure(429, "rate_limit_error", "too many requests", wait)
        with self.mediation.parallel.slot(access.person) as free:
            if not free:
                raise Failure(429, "rate_limit_error", "too many requests at once", BUSY_RETRY_SECONDS)
            if self.mediation.store.spent(access.person, month_of(self.mediation.now())) >= access.budget_usd:
                raise Failure(402, "budget_exceeded", "monthly budget used up")
            try:
                payload = self.mediation.policy.check(self._body())
            except PolicyError as error:
                raise Failure(400, "invalid_request_error", str(error)) from error
            self._forward(access, payload)

    # helpers

    def _forward(self, access: Access, payload: dict) -> None:
        with self.mediation.upstream.send(payload) as reply:
            headers = {key: value for key, value in (("request-id", reply.request_id),
                                                     ("retry-after", reply.retry_after)) if value}
            try:
                if reply.content_type.startswith("text/event-stream"):
                    self._send_stream(reply.status, reply.content_type, reply.chunks, headers)
                else:
                    body = b"".join(reply.chunks)
                    if reply.status >= 400:
                        log.warning("upstream answered %s %s, request %s", reply.status, _error_type(body), reply.request_id)
                    self._send(reply.status, body, reply.content_type, headers)
            finally:
                if reply.status < 400 or reply.usage.output_tokens:
                    self.mediation.store.record_usage(access, payload["model"], reply.usage,
                                                      cost_usd(payload["model"], reply.usage), reply.status,
                                                      reply.request_id, self.mediation.now())

    def _access(self) -> Access:
        token = self.headers.get("x-api-key") or ""
        bearer = self.headers.get("authorization") or ""
        if not token and bearer.lower().startswith("bearer "):
            token = bearer[7:].strip()
        access = self.mediation.store.authenticate(token, self.mediation.now()) if token else None
        if access is None:
            raise Failure(401, "authentication_error", "access not valid")
        return access

    def _client_address(self) -> str:
        forwarded = self.headers.get("x-forwarded-for") if self.mediation.trust_proxy else None
        return forwarded.split(",")[-1].strip() if forwarded else self.client_address[0]

    def _body(self) -> object:
        try:
            length = int(self.headers.get("content-length") or 0)
        except ValueError:
            length = -1
        if not 0 < length <= MAX_BODY:
            raise Failure(413 if length > MAX_BODY else 400, "invalid_request_error", "body missing or too large")
        try:
            return json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise Failure(400, "invalid_request_error", "invalid JSON") from error

    def _send_json(self, status: int, data: dict) -> None:
        self._send(status, json.dumps(data).encode("utf-8"))

    def _send(self, status: int, body: bytes, content_type: str = JSON_TYPE, headers: dict | None = None) -> None:
        self.send_response(status)
        self.send_header("content-type", content_type)
        self.send_header("content-length", str(len(body)))
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def _send_stream(self, status: int, content_type: str, chunks, headers: dict) -> None:
        self.send_response(status)
        self.send_header("content-type", content_type)
        self.send_header("cache-control", "no-cache")
        for key, value in headers.items():
            self.send_header(key, value)
        self.end_headers()  # HTTP/1.0 without length: the stream ends when the connection closes
        for chunk in chunks:
            self.wfile.write(chunk)
            self.wfile.flush()

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        log.debug(format, *args)  # no paths with codes, no bodies


class Server(http.server.ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], mediation: Mediation) -> None:
        super().__init__(address, Handler)
        self.mediation = mediation
