"""Forward a checked request to Anthropic with the official SDK and read the usage on the way (MIN-344).

The body is passed through unchanged (JSON or the SSE stream), so the app sees the Messages API as is.
Usage comes from the JSON answer or from the `message_start` and `message_delta` events of a stream.
"""
import contextlib
import dataclasses
import json
from typing import Iterator

import anthropic

from pricing import Usage

TIMEOUT_SECONDS = 600.0
MAX_RETRIES = 2
JSON_TYPE = "application/json"


@dataclasses.dataclass
class Reply:
    """What goes back to the app; `usage` is complete once `chunks` is exhausted."""
    status: int
    content_type: str
    request_id: str | None
    chunks: Iterator[bytes]
    usage: Usage = dataclasses.field(default_factory=Usage)
    retry_after: str | None = None


def error_body(kind: str, message: str) -> bytes:
    return json.dumps({"type": "error", "error": {"type": kind, "message": message}}).encode("utf-8")


class SseUsage:
    """Collects usage from server-sent events while the bytes pass through."""

    def __init__(self) -> None:
        self._buffer = b""
        self.usage = Usage()

    def feed(self, chunk: bytes) -> None:
        self._buffer += chunk.replace(b"\r\n", b"\n")
        while b"\n\n" in self._buffer:
            event, self._buffer = self._buffer.split(b"\n\n", 1)
            self._event(event)

    def _event(self, event: bytes) -> None:
        for line in event.split(b"\n"):
            if not line.startswith(b"data:"):
                continue
            try:
                data = json.loads(line[5:].strip())
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            if not isinstance(data, dict):
                continue
            if data.get("type") == "message_start" and isinstance(data.get("message"), dict):
                self.usage = self.usage.merge(Usage.from_dict(data["message"].get("usage")))
            elif data.get("type") == "message_delta":
                self.usage = self.usage.merge(Usage.from_dict(data.get("usage")))


class Upstream:
    def __init__(self, client: anthropic.Anthropic) -> None:
        self._client = client

    @classmethod
    def from_key(cls, api_key: str) -> "Upstream":
        return cls(anthropic.Anthropic(api_key=api_key, timeout=TIMEOUT_SECONDS, max_retries=MAX_RETRIES))

    @contextlib.contextmanager
    def send(self, payload: dict) -> Iterator[Reply]:
        stack = contextlib.ExitStack()
        try:  # only opening is guarded here; errors while reading the stream go to the caller
            response = stack.enter_context(self._client.messages.with_streaming_response.create(**payload))
        except anthropic.APIStatusError as error:
            body = json.dumps(error.body).encode("utf-8") if isinstance(error.body, dict) else \
                error_body("api_error", "upstream error")
            yield Reply(error.status_code, JSON_TYPE, error.response.headers.get("request-id"), iter([body]),
                        retry_after=error.response.headers.get("retry-after"))
            return
        except anthropic.APITimeoutError:
            yield Reply(504, JSON_TYPE, None, iter([error_body("timeout_error", "upstream timeout")]))
            return
        except anthropic.APIConnectionError:
            yield Reply(502, JSON_TYPE, None, iter([error_body("api_error", "upstream not reachable")]))
            return
        with stack:
            reply = Reply(response.status_code, response.headers.get("content-type", JSON_TYPE),
                          response.request_id, iter(()))
            reply.chunks = self._pass_through(reply, response.iter_bytes(), bool(payload.get("stream")))
            yield reply

    @staticmethod
    def _pass_through(reply: Reply, chunks: Iterator[bytes], stream: bool) -> Iterator[bytes]:
        if stream:
            sse = SseUsage()
            try:
                for chunk in chunks:
                    sse.feed(chunk)
                    reply.usage = sse.usage
                    yield chunk
            finally:
                reply.usage = sse.usage
            return
        body = b"".join(chunks)
        try:
            data = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            data = None
        reply.usage = Usage.from_dict(data.get("usage")) if isinstance(data, dict) else Usage()
        yield body
