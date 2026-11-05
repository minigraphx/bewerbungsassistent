"""Errors of AI calls as short German messages for the app. Access keys never appear in a message."""
import logging
import re

import anthropic

log = logging.getLogger("bewerbungsbegleiter")


class AiError(Exception):
    """An AI call did not work; `str(error)` is shown to the person as is."""

    def __init__(self, message: str, *, retry_after: int | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class AnswerError(AiError):
    """What is in this request, or what came back, is the problem: one by one it may still work. `cost_usd` is what
    the call cost when it reached the AI; None if it was not sent."""

    def __init__(self, message: str, *, cost_usd: float | None = None) -> None:
        super().__init__(message)
        self.cost_usd = cost_usd


NOT_SET_UP = ("Die KI ist noch nicht eingerichtet. In der App die Einladung einlösen "
              "oder unter „Erweiterte Einstellungen“ einen eigenen Schlüssel eintragen.")
ACCESS_DENIED = ("Der Zugang zur KI gilt nicht mehr. Mit eigenem Schlüssel: bitte in den erweiterten Einstellungen "
                 "prüfen. Sonst bei der Person melden, die Sie im Pilot begleitet.")
NO_CREDIT = ("Das Guthaben bei Anthropic reicht nicht mehr. Mit eigenem Schlüssel: bitte dort aufladen. "
             "Sonst bei der Person melden, die Sie im Pilot begleitet.")
BUDGET_USED = "Das Budget für die KI ist für diesen Monat aufgebraucht. Ab dem nächsten Monat geht es wieder."
RATE_LIMITED = "Die KI ist gerade ausgelastet. Bitte in {seconds} Sekunden nochmals versuchen."
TIMEOUT = "Die KI hat nicht rechtzeitig geantwortet. Bitte nochmals versuchen."
OFFLINE = "Keine Verbindung zur KI. Ist der Rechner mit dem Internet verbunden?"
SERVER = "Bei der KI ist gerade ein Fehler aufgetreten. Bitte später nochmals versuchen."
REJECTED_REQUEST = "Die Anfrage an die KI war ungültig. Bitte melden; die Unterlagen sind unverändert."
REFUSED = "Die KI hat diese Anfrage abgelehnt. Bitte den Text prüfen, zum Beispiel das Inserat."
TOO_LONG = "Die Antwort der KI war zu lang und ist unvollständig. Bitte nochmals versuchen."
BAD_ANSWER = "Die Antwort der KI liess sich nicht lesen. Bitte nochmals versuchen."
DEFAULT_RETRY_SECONDS = 60
BUDGET_STATUS = 402  # the mediation (MIN-344) answers 402 when the monthly budget is used up
MAX_LOGGED_REASON = 400
LONG_TOKEN = re.compile(r"[A-Za-z0-9_-]{24,}")  # a key or an access never reaches the log, not even inside a message
NO_CREDIT_WORDS = "credit balance"  # how the API says it, with status 400, to someone with an own key (MIN-348)


def from_sdk(error: Exception) -> AiError:
    """Translate an exception of the Anthropic SDK; the original stays as __cause__ for the log."""
    if isinstance(error, anthropic.APITimeoutError):
        return AiError(TIMEOUT)
    if isinstance(error, anthropic.APIConnectionError):
        return AiError(OFFLINE)
    if isinstance(error, (anthropic.AuthenticationError, anthropic.PermissionDeniedError)):
        return AiError(ACCESS_DENIED)
    if isinstance(error, anthropic.RateLimitError):
        seconds = _retry_after(error)
        return AiError(RATE_LIMITED.format(seconds=seconds), retry_after=seconds)
    if isinstance(error, anthropic.APIStatusError):
        if error.status_code == BUDGET_STATUS:
            return AiError(BUDGET_USED)
        if error.status_code >= 500:
            return AiError(SERVER)
        log.warning("KI-Anfrage abgelehnt, Status %s: %s", error.status_code, _reason(error))
        if NO_CREDIT_WORDS in str(error.message).lower():
            return AiError(NO_CREDIT)
        return AiError(REJECTED_REQUEST)
    return AiError(SERVER)


def _reason(error: anthropic.APIStatusError) -> str:
    """What the API says about a refused request: about its form, never its content. Only for the log."""
    return LONG_TOKEN.sub("…", str(error.message))[:MAX_LOGGED_REASON]


def _retry_after(error: anthropic.APIStatusError) -> int:
    try:
        return max(1, int(error.response.headers.get("retry-after", DEFAULT_RETRY_SECONDS)))
    except (TypeError, ValueError):
        return DEFAULT_RETRY_SECONDS
