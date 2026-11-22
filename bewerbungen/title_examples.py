"""Example titles per title filter term (G104), from the person's own last search run, for Erweitert › Titelfilter.

While screening, the app notes for each title the filter looked at which positive terms let it through, which
exclusions kept it out, or that it had none of the positive terms; per term the count and up to three titles. The
tally waits beside the query log until the run ends and then belongs to that run (`query_log`). A title that two
queries found counts once. Nothing here is fixed text: every example is a title of the run, and only the last run
counts, so a changed term starts again from nothing.
"""
from hits import bounded_text
from title_filter import Verdict

MAX_EXAMPLES = 3
MAX_SEEN = 5000  # titles of one run remembered to count each once; beyond that one may count twice
POSITIVE, EXCLUDE, WITHOUT, SEEN, KEY = "positiv", "ausschluss", "ohne_begriff", "gesehen", "titelfilter"


def _examples(value) -> list[str]:
    return [item for item in value if isinstance(item, str)][:MAX_EXAMPLES] if isinstance(value, list) else []


def _bucket(raw) -> dict:
    """One term's entry as the file has it; the file is data the person may have edited, so an entry without a
    count counts nothing and shows nothing."""
    count = raw.get("anzahl") if isinstance(raw, dict) else None
    if type(count) is not int or count < 0:
        return {"anzahl": 0, "beispiele": []}
    return {"anzahl": count, "beispiele": _examples(raw.get("beispiele"))}


def _terms(raw) -> dict[str, dict]:
    return {term: _bucket(entry) for term, entry in raw.items() if isinstance(term, str)} if isinstance(raw, dict) else {}


def _with_title(bucket: dict | None, title: str) -> dict:
    found = _bucket(bucket)
    examples = found["beispiele"] if len(found["beispiele"]) >= MAX_EXAMPLES else [*found["beispiele"], title]
    return {"anzahl": found["anzahl"] + 1, "beispiele": examples}


def _with_terms(terms: dict[str, dict], names: tuple[str, ...], title: str) -> dict[str, dict]:
    return {**terms, **{name: _with_title(terms.get(name), title) for name in names}}


def closed(tally) -> dict:
    """The tally as it belongs to a run: the terms and the titles without a term, without the titles seen."""
    raw = tally if isinstance(tally, dict) else {}
    return {POSITIVE: _terms(raw.get(POSITIVE)), EXCLUDE: _terms(raw.get(EXCLUDE)), WITHOUT: _bucket(raw.get(WITHOUT))}


def noted(tally, checks: list[tuple[str, str, Verdict]]) -> dict:
    """The tally with these titles, each (hit key, title, verdict); a key already seen in this run adds nothing."""
    raw = tally if isinstance(tally, dict) else {}
    seen = [key for key in raw.get(SEEN, []) if isinstance(key, str)] if isinstance(raw.get(SEEN), list) else []
    current = {**closed(raw), SEEN: seen}
    for key, raw_title, found in checks:
        if key in current[SEEN]:
            continue
        title = bounded_text(raw_title, "stelle")
        current = {POSITIVE: _with_terms(current[POSITIVE], found.passed_by, title),
                   EXCLUDE: _with_terms(current[EXCLUDE], found.excluded_by, title),
                   WITHOUT: _with_title(current[WITHOUT], title) if found.without_term else current[WITHOUT],
                   SEEN: [*current[SEEN], key][-MAX_SEEN:]}
    return current


def _entries(recorded: dict[str, dict], terms: tuple[str, ...]) -> list[dict]:
    """Per term of the profile now, in its order, what the run recorded for it; a term the run did not know has none."""
    by_name = {name.casefold(): bucket for name, bucket in recorded.items()}
    return [{"begriff": term, **by_name.get(term.casefold(), {"anzahl": 0, "beispiele": []})} for term in terms]


def summary(run: dict | None, positive: tuple[str, ...], exclude: tuple[str, ...]) -> dict:
    """What the page shows: `lauf` false until a run has recorded examples, then per term the count and examples,
    and the titles kept out for want of a positive term (None without positive terms)."""
    recorded = run.get(KEY) if isinstance(run, dict) else None
    tally = closed(recorded)
    return {"lauf": isinstance(recorded, dict), "positiv": _entries(tally[POSITIVE], positive),
            "ausschluss": _entries(tally[EXCLUDE], exclude), "ohne_begriff": tally[WITHOUT] if positive else None}
