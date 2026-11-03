"""The only way to the AI: every request is pseudonymized, checked and logged here (MIN-334, MIN-338).

`Gateway.ask` masks the person's files and the prompt (rules and instructions are fixed texts of the app and
stay as they are), adds e-mails, phones and contact persons found in these texts, refuses to send if
anything personal is left, calls the Messages API, restores the answer and writes model, tokens and cost
(never content) to the usage log. Rules and files go first in the system prompt with `cache_control`, so
they are cached across tasks; the task instructions follow after it.
"""
import dataclasses
import datetime
import json

import anthropic

from ai import errors
from ai.personal import secrets_found_in
from ai.pseudonym import Pseudonymizer, PseudonymError
from ai.usage import Usage, UsageLog, cost_usd

CACHE = {"type": "ephemeral"}


@dataclasses.dataclass(frozen=True)
class Request:
    task: str
    model: str
    rules: str  # fixed text of the app, not masked
    context: str  # the person's files, stable: masked and cached
    instructions: str  # what this task does, fixed text of the app
    prompt: str  # the variable part, e.g. the job ad: masked
    max_tokens: int
    schema: dict | None = None  # JSON schema for structured answers


@dataclasses.dataclass(frozen=True)
class Answer:
    text: str
    data: object | None
    model: str
    usage: Usage
    cost_usd: float | None


class Gateway:
    def __init__(self, client, pseudonymizer: Pseudonymizer, log: UsageLog,
                 now=lambda: datetime.datetime.now().astimezone()) -> None:
        if not isinstance(pseudonymizer, Pseudonymizer):
            raise TypeError("Gateway needs a Pseudonymizer; there are no calls without one")
        self._client = client
        self._pseudonymizer = pseudonymizer
        self._log = log
        self._now = now

    def ask(self, request: Request) -> Answer:
        pseudonymizer = self._pseudonymizer.extended(secrets_found_in([request.context, request.prompt]))
        context, prompt = pseudonymizer.mask(request.context), pseudonymizer.mask(request.prompt)
        try:
            pseudonymizer.check_clean([context, prompt])
        except PseudonymError as error:
            raise errors.AiError(str(error)) from error
        try:
            response = self._client.messages.create(**self._payload(request, context, prompt))
        except anthropic.AnthropicError as error:
            raise errors.from_sdk(error) from error
        usage = Usage.from_response(getattr(response, "usage", None))
        model = getattr(response, "model", None) or request.model
        self._log.record(task=request.task, model=model, usage=usage, fields=pseudonymizer.fields,
                         request_id=getattr(response, "_request_id", None), now=self._now())
        return self._answer(request, pseudonymizer, response, model, usage)

    @staticmethod
    def _payload(request: Request, context: str, prompt: str) -> dict:
        payload = {
            "model": request.model,
            "max_tokens": request.max_tokens,
            "system": [
                {"type": "text", "text": request.rules + "\n\n" + context, "cache_control": CACHE},
                {"type": "text", "text": request.instructions},
            ],
            "messages": [{"role": "user", "content": prompt}],
        }
        if request.schema is not None:
            payload["output_config"] = {"format": {"type": "json_schema", "schema": request.schema}}
        return payload

    @staticmethod
    def _answer(request: Request, pseudonymizer: Pseudonymizer, response, model: str, usage: Usage) -> Answer:
        stop = getattr(response, "stop_reason", None)
        if stop == "refusal":
            raise errors.AiError(errors.REFUSED)
        if stop == "max_tokens":
            raise errors.AiError(errors.TOO_LONG)
        text = "".join(block.text for block in response.content if getattr(block, "type", None) == "text")
        try:
            if request.schema is None:
                return Answer(pseudonymizer.unmask(text), None, model, usage, cost_usd(model, usage))
            data = pseudonymizer.unmask_data(json.loads(text))
            return Answer(json.dumps(data, ensure_ascii=False), data, model, usage, cost_usd(model, usage))
        except json.JSONDecodeError as error:
            raise errors.AiError(errors.BAD_ANSWER) from error
        except PseudonymError as error:
            raise errors.AiError(str(error)) from error
