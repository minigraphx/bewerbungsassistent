"""Routes for the title word proposed from dismissed hits (#225, G66), only for job searches and only for the page.

Everything is counted by the app (`dismissed_words.py`); no route calls the AI. Adopting takes only a word that is a
proposal at that moment and adds it to the title exclusion of the profile, with drafts before and after. Neither the
extension nor Claude reach the routes: they are not listed in desktop/native_host.py or desktop/mcp_tools.py.
"""
import dismissed_words
import excluded_companies
import preferences
import search_frame
import search_plan
from dateien import schreibe_atomar
from hits import HIDDEN_WORDS, Hits
from server import json_antwort

GONE = "Dieser Vorschlag gilt nicht mehr. Die Seite zeigt jetzt den aktuellen Stand."
ADOPTED = "Suche einstellen: «{word}» im Titel ausgeschlossen"


def _job_profile(k) -> str | None:
    """The profile of a job search, or None: an apprenticeship has no title filter."""
    path = k.daten / search_plan.PROFILE
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    if search_frame.kind_of(text) != search_plan.KIND_JOB or preferences.strictest_kind(k.daten) == preferences.APPRENTICESHIP:
        return None
    return text


def _shown_hits(k) -> list[dict]:
    """The hits the list shows; those of an excluded company are out of sight and do not count."""
    return excluded_companies.shown(Hits(k.daten).all(), excluded_companies.keys(k.daten))


def _proposals(k, text: str, hidden: dict[str, int]) -> list[dismissed_words.Proposal]:
    return dismissed_words.proposals(_shown_hits(k), search_plan.title_terms(text, "positiv"),
                                     search_plan.title_terms(text, "ausschluss"), hidden)


def _proposal(k, wanted) -> tuple[str, dismissed_words.Proposal]:
    """The proposal the page names, also one put aside; anything else is refused."""
    text = _job_profile(k)
    if text is None:
        raise ValueError(search_plan.NO_PROFILE)
    found = next((p for p in _proposals(k, text, {})
                  if isinstance(wanted, str) and p.word.casefold() == wanted.strip().casefold()), None)
    if found is None:
        raise ValueError(GONE)
    return text, found


def listing(k, parameter, body):
    text = _job_profile(k)
    found = _proposals(k, text, Hits(k.daten).settings()[HIDDEN_WORDS]) if text is not None else []
    return json_antwort({"vorschlaege": [p.as_dict() for p in found]})


def evidence(k, parameter, body):
    """The dismissed hits behind „Die Stellen ansehen“."""
    word = parameter.get("wort", "") if isinstance(parameter.get("wort"), str) else ""
    ids = dismissed_words.with_word(_shown_hits(k), word.strip()) if word.strip() else ()
    return json_antwort({"wort": word.strip(), "ids": list(ids)})


def adopt(k, parameter, body):
    body = body if isinstance(body, dict) else {}
    text, proposal = _proposal(k, body.get("wort"))
    path = k.daten / search_plan.PROFILE

    def added(current_text: str) -> str:
        current = search_frame.values(current_text)["titel_ausschluss"]
        return search_frame.with_values(current_text, {"titel_ausschluss": [*current, proposal.word]})

    added(text)  # refuse before any draft is made, e.g. with too many title words

    def write() -> str:
        text = path.read_text(encoding="utf-8")
        changed = added(text)
        if changed != text:
            schreibe_atomar(path, changed.encode("utf-8"))
        return changed

    changed = k.mit_entwurf(path, ADOPTED.format(word=proposal.word), write)
    return json_antwort({"wort": proposal.word, "titel_ausschluss": search_frame.values(changed)["titel_ausschluss"]})


def not_now(k, parameter, body):
    body = body if isinstance(body, dict) else {}
    _, proposal = _proposal(k, body.get("wort"))
    Hits(k.daten).hide_word(proposal.word, len(proposal.ids))
    return json_antwort({"wort": proposal.word})


GET = {"/api/suche/verworfen-woerter": listing, "/api/suche/verworfen-woerter/beleg": evidence}
POST = {"/api/suche/verworfen-woerter/ausschliessen": adopt, "/api/suche/verworfen-woerter/nicht-jetzt": not_now}
