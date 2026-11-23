"""Errors of AI calls as short messages for the app, German with the catalog's French and English (#416). Access keys
never appear in a message."""
import logging
import re

import anthropic

from amount_text import NBSP
from ui_texts import T

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


class SetupNeeded(AiError):
    """The AI is not set up or not agreed to: the page opens the window „KI einrichten“ (G60)."""


class InputRefused(AiError):
    """The value the person entered is wrong in itself: its form, a code the mediation does not take, a key Anthropic
    refuses. Only this is an input error of the routes that take a code or a key (G97, #350)."""


class CreditUsedUp(AiError):
    """The mediation refused because the budget is used up; `ai.budget.used_up_error` names the day it renews."""


class LocalProblem(AiError):
    """This computer or the app's own setup failed (the keychain, the address of the mediation), not the value and
    not the service."""


SETUP_ACTION = "ki-einrichten"  # what the answer of a route tells the page to open
# Each message is a T, so the server says it in the app language wherever it is raised (#416).
NOT_SET_UP = T("Die KI ist noch nicht eingerichtet. Unter „KI einrichten“ den Einladungscode, "
               "das eigene Claude-Abo oder einen eigenen Schlüssel wählen.")
ACCESS_DENIED = T("Der Zugang zur KI gilt nicht mehr. Mit eigenem Schlüssel: bitte in den erweiterten Einstellungen "
                  "prüfen. Sonst bitte einen neuen Einladungscode anfordern.")
NO_CREDIT = T("Das Guthaben bei Anthropic reicht nicht mehr. Mit eigenem Schlüssel: bitte dort aufladen. "
              "Sonst bitte später nochmals versuchen.")
# The monthly budget (G98), filled by ai.budget with the month and day the mediation names (credit_used)
CREDIT_USED = ("Das KI-Budget für {month} ist aufgebraucht. Die KI geht wieder ab {renews}; "
               "alles andere funktioniert weiterhin.")
# A mediation that names no renewal still counts a one-time credit (G80)
CREDIT_USED_ONCE = T("Das Guthaben des Einladungscodes ist aufgebraucht. Bitte einen neuen Code anfordern und unter "
                     "Einstellungen, KI, Budget und Sprache einlösen. Alles andere funktioniert weiterhin.")
RATE_LIMITED = "Die KI ist gerade ausgelastet. Bitte in {seconds} nochmals versuchen."
TIMEOUT = T("Die KI hat nicht rechtzeitig geantwortet. Bitte nochmals versuchen.")
OFFLINE = T("Keine Verbindung zur KI. Ist der Rechner mit dem Internet verbunden?")
SERVER = T("Bei der KI ist gerade ein Fehler aufgetreten. Bitte später nochmals versuchen.")
REJECTED_REQUEST = T("Die Anfrage an die KI war ungültig. Bitte melden; die Unterlagen sind unverändert.")
REFUSED = T("Die KI hat diese Anfrage abgelehnt. Bitte den Text prüfen, zum Beispiel das Inserat.")
TOO_LONG = T("Die Antwort der KI war zu lang und ist unvollständig. Bitte nochmals versuchen.")
BAD_ANSWER = T("Die Antwort der KI liess sich nicht lesen. Bitte nochmals versuchen.")
DEFAULT_RETRY_SECONDS = 60
CREDIT_STATUS = 402  # the mediation answers 402 once the budget of the month is used up (G98)
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
        return AiError(T(RATE_LIMITED, seconds=_seconds(seconds)), retry_after=seconds)
    if isinstance(error, anthropic.APIStatusError):
        if error.status_code == CREDIT_STATUS:
            return CreditUsedUp(CREDIT_USED_ONCE)
        if error.status_code >= 500:
            return AiError(SERVER)
        log.warning("KI-Anfrage abgelehnt, Status %s: %s", error.status_code, _reason(error))
        if NO_CREDIT_WORDS in str(error.message).lower():
            return AiError(NO_CREDIT)
        return AiError(REJECTED_REQUEST)
    return AiError(SERVER)


def credit_used(month: str, renews: str) -> T:
    """The used-up budget of the month (G98); month and day may be T, then they follow the app language too."""
    return T(CREDIT_USED, month=month, renews=renews)


def _seconds(count: int) -> T:
    """„30 Sekunden“ as amount_text.seconds_text writes it, in the app language."""
    if count == 1:
        return T("{anzahl}{nbsp}Sekunde", anzahl=count, nbsp=NBSP)
    return T("{anzahl}{nbsp}Sekunden", anzahl=count, nbsp=NBSP)


def _reason(error: anthropic.APIStatusError) -> str:
    """What the API says about a refused request: about its form, never its content. Only for the log."""
    return LONG_TOKEN.sub("…", str(error.message))[:MAX_LOGGED_REASON]


def _retry_after(error: anthropic.APIStatusError) -> int:
    try:
        return max(1, int(error.response.headers.get("retry-after", DEFAULT_RETRY_SECONDS)))
    except (TypeError, ValueError):
        return DEFAULT_RETRY_SECONDS
