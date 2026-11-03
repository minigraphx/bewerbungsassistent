"""What the mediation passes on: only approved models, text, bounded output, no tools (MIN-344).

The mediation is meant for the app's tasks, not as general access to Claude. A request is checked
against an allow-list of fields; content may only be text, so images and documents never pass.
"""
import dataclasses

from pricing import PRICES_USD

ALLOWED_FIELDS = {"model", "max_tokens", "system", "messages", "output_config", "stream", "thinking",
                  "temperature", "stop_sequences"}
TEXT_BLOCK_FIELDS = {"type", "text", "cache_control"}
ROLES = {"user", "assistant"}
MAX_MESSAGES = 20


class PolicyError(ValueError):
    """The request is not allowed; the message is returned to the app."""


@dataclasses.dataclass(frozen=True)
class Policy:
    models: frozenset[str] = frozenset(PRICES_USD)
    max_output_tokens: int = 16_000

    def check(self, payload: object) -> dict:
        """The payload as it may be sent upstream; PolicyError otherwise."""
        if not isinstance(payload, dict):
            raise PolicyError("JSON object expected")
        extra = sorted(set(payload) - ALLOWED_FIELDS)
        if extra:
            raise PolicyError(f"fields not allowed: {', '.join(extra)}")
        if payload.get("model") not in self.models:
            raise PolicyError(f"model not allowed: {payload.get('model')!r}")
        tokens = payload.get("max_tokens")
        if not isinstance(tokens, int) or isinstance(tokens, bool) or not 0 < tokens <= self.max_output_tokens:
            raise PolicyError(f"max_tokens must be between 1 and {self.max_output_tokens}")
        if "stream" in payload and not isinstance(payload["stream"], bool):
            raise PolicyError("stream must be true or false")
        _check_system(payload.get("system"))
        _check_messages(payload.get("messages"))
        return payload


def _check_text_blocks(blocks: object, where: str) -> None:
    if isinstance(blocks, str):
        return
    if not isinstance(blocks, list) or not blocks:
        raise PolicyError(f"{where}: text or a list of text blocks expected")
    for block in blocks:
        if not isinstance(block, dict) or block.get("type") != "text" or not isinstance(block.get("text"), str):
            raise PolicyError(f"{where}: only text blocks are allowed")
        if set(block) - TEXT_BLOCK_FIELDS:
            raise PolicyError(f"{where}: unknown fields in a text block")


def _check_system(system: object) -> None:
    if system is not None:
        _check_text_blocks(system, "system")


def _check_messages(messages: object) -> None:
    if not isinstance(messages, list) or not 0 < len(messages) <= MAX_MESSAGES:
        raise PolicyError(f"messages: 1 to {MAX_MESSAGES} messages expected")
    for message in messages:
        if not isinstance(message, dict) or set(message) != {"role", "content"} or message["role"] not in ROLES:
            raise PolicyError("messages: each message needs exactly role and content")
        _check_text_blocks(message["content"], "messages")
