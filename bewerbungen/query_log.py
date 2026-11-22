"""What each query of a search run brought (G103, #375): the log behind the yield on „Suche einstellen“.

At the end of a run the extension names every query per portal with the number of hits its result list had, so a
query that found nothing is kept too. While screening, the app counts per query the titles the title filter kept out,
with up to three examples; those wait in `suchlauf-offen.yaml` until the run ends and then belong to it. So do the
example titles per term of the title filter (G104, `title_examples`), waiting in `titelfilter-offen.yaml`. Only the
last three runs are kept, in `suche/suchlaeufe.yaml`, beside the hits and out of Git like them.
"""
import dataclasses
import datetime
import pathlib
import threading

import niche_region
import title_examples
from dateien import lies_yaml, schreibe_yaml
from hits import FOLDER, bounded_text, checked_query
from title_filter import Verdict

RUNS_FILE = "suchlaeufe.yaml"
PENDING_FILE = "suchlauf-offen.yaml"
TITLES_PENDING_FILE = "titelfilter-offen.yaml"  # G104: the example titles per term until the run ends
KEPT_RUNS = 3
MAX_QUERIES_PER_PORTAL = 2000
MAX_EXAMPLES = 3
UNRELATED = "ohne_pflichtbezug"  # G110: hits without a required word of their term, apart from the title filter's
UNRELATED_EXAMPLES = "pflicht_beispiele"
# G111: niche hits outside the region without remote work, with the places they lay at, apart from both above
OUTSIDE, OUTSIDE_PLACES = niche_region.COUNTED, niche_region.COUNTED_PLACES
MAX_OUTSIDE_PLACES = 30  # per query; a place beyond them still counts in OUTSIDE
CARRIED = ("aussortiert", "beispiele", UNRELATED, UNRELATED_EXAMPLES, OUTSIDE, OUTSIDE_PLACES)  # taken from the waiting file
_LOCK = threading.Lock()


def _count(value, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} muss eine Zahl sein")
    return value


def checked_queries(raw) -> list[dict]:
    """The queries of one portal from the summary of the extension: keyword, place and the hits its list had."""
    if not isinstance(raw, list):
        raise ValueError("abfragen muss eine Liste sein")
    if len(raw) > MAX_QUERIES_PER_PORTAL:
        raise ValueError(f"abfragen: höchstens {MAX_QUERIES_PER_PORTAL} pro Portal")
    return [{**checked_query(entry), "treffer": _count(entry.get("treffer"), "treffer")} for entry in raw]


def _key(query: dict) -> tuple[str, str, str]:
    return query["portal"], query["stichwort"], query["ort"]


def _pending_entries(raw) -> list[dict]:
    """The file is data: only entries with their portal, keyword, place and a count stay."""
    entries = raw.get("abfragen") if isinstance(raw, dict) else None
    if not isinstance(entries, list):
        return []
    return [entry for entry in entries if isinstance(entry, dict)
            and all(isinstance(entry.get(name), str) for name in ("portal", "stichwort", "ort"))
            and type(entry.get("aussortiert")) is int and isinstance(entry.get("beispiele"), list)]


def _screened(entry: dict | None, title: str, reason: str) -> dict:
    examples = entry["beispiele"] if entry else []
    example = {"stelle": bounded_text(title, "stelle"), "grund": bounded_text(reason, "grund")}
    return {**(entry or {}), "aussortiert": (entry["aussortiert"] if entry else 0) + 1,
            "beispiele": examples if len(examples) >= MAX_EXAMPLES else [*examples, example]}


def _unrelated(entry: dict | None, title: str) -> dict:
    """One more hit without a required word (G110), with up to three of their titles; the title filter's count stays."""
    old = entry or {"aussortiert": 0, "beispiele": []}
    examples = [e for e in old.get(UNRELATED_EXAMPLES, []) if isinstance(e, str)]
    count = old.get(UNRELATED) if type(old.get(UNRELATED)) is int else 0
    return {**old, UNRELATED: count + 1,
            UNRELATED_EXAMPLES: examples if len(examples) >= MAX_EXAMPLES else [*examples, bounded_text(title, "stelle")]}


def places_of(raw) -> dict[str, int]:
    """The places of the hits outside as a query keeps them; the file is data, so only names with a count stay."""
    if not isinstance(raw, dict):
        return {}
    return {name: count for name, count in raw.items() if isinstance(name, str) and type(count) is int and count > 0}


def _outside(entry: dict | None, place: str) -> dict:
    """One more niche hit outside the region (G111), counted at its place; the other counts stay."""
    old = entry or {"aussortiert": 0, "beispiele": []}
    count = old.get(OUTSIDE) if type(old.get(OUTSIDE)) is int else 0
    places = places_of(old.get(OUTSIDE_PLACES))
    name = niche_region.place_name(place)
    room = name in places or len(places) < MAX_OUTSIDE_PLACES
    return {**old, OUTSIDE: count + 1, OUTSIDE_PLACES: {**places, name: places.get(name, 0) + 1} if name and room else places}


def _run_entries(raw) -> list[dict]:
    return [run for run in raw if isinstance(run, dict) and isinstance(run.get("datum"), str)
            and isinstance(run.get("abfragen"), list)] if isinstance(raw, list) else []


@dataclasses.dataclass(frozen=True)
class QueryLog:
    data_dir: pathlib.Path

    @property
    def folder(self) -> pathlib.Path:
        return self.data_dir / FOLDER

    def runs(self) -> list[dict]:
        """The last runs with their queries, the oldest first."""
        return _run_entries(lies_yaml(self.folder / RUNS_FILE, []))

    def _pending(self) -> list[dict]:
        return _pending_entries(lies_yaml(self.folder / PENDING_FILE, {}))

    def note_screened(self, queries: list[dict], title: str, reason: str) -> None:
        """A title the title filter kept out, counted for each query that found it."""
        self._note(queries, lambda entry: _screened(entry, title, reason))

    def _note(self, queries: list[dict], counted) -> None:
        """One more of something for each query that found a hit; `counted` gives the query's new entry."""
        if not queries:
            return
        with _LOCK:
            entries = {_key(entry): entry for entry in self._pending()}
            changed = {_key(query): {"portal": query["portal"], "stichwort": query["stichwort"], "ort": query["ort"],
                                     **counted(entries.get(_key(query)))} for query in queries}
            schreibe_yaml(self.folder / PENDING_FILE, {"abfragen": list({**entries, **changed}.values())})

    def note_unrelated(self, queries: list[dict], title: str) -> None:
        """A hit not stored for want of a required word (G110), counted for each query that found it."""
        self._note(queries, lambda entry: _unrelated(entry, title))

    def note_outside(self, queries: list[dict], place: str) -> None:
        """A niche hit not stored because it lay outside the region without remote work (G111), with its place."""
        self._note(queries, lambda entry: _outside(entry, place))

    def note_titles(self, checks: list[tuple[str, str, Verdict]]) -> None:
        """Titles the title filter looked at, each (hit key, title, verdict), for the examples per term (G104)."""
        if not checks:
            return
        with _LOCK:
            tally = title_examples.noted(lies_yaml(self.folder / TITLES_PENDING_FILE, {}), checks)
            schreibe_yaml(self.folder / TITLES_PENDING_FILE, tally)

    def close_run(self, queries_by_portal: dict[str, list[dict]], today: datetime.date) -> dict | None:
        """The run with every query and what the title filter kept out of each, and the example titles per term of the
        title filter; None when no portal named its queries.

        The screen-outs and titles of the run are then gone from the waiting files, also when nothing was recorded."""
        with _LOCK:
            titles = title_examples.closed(lies_yaml(self.folder / TITLES_PENDING_FILE, {}))
            schreibe_yaml(self.folder / TITLES_PENDING_FILE, {})
            waiting = {_key(entry): entry for entry in self._pending()}
            queries = [{"portal": portal, **query} for portal, listed in queries_by_portal.items() for query in listed]
            # a query twice in one run (a trial beside the apprenticeship) carries the screen-outs once
            first = {_key(query): index for index, query in reversed(list(enumerate(queries)))}
            entries = [{**query, **({name: waiting[_key(query)][name] for name in CARRIED if name in waiting[_key(query)]}
                                    if first[_key(query)] == index and _key(query) in waiting else {})}
                       for index, query in enumerate(queries)]
            schreibe_yaml(self.folder / PENDING_FILE, {"abfragen": []})
            if not entries:
                return None
            run = {"datum": today.isoformat(), "abfragen": entries, title_examples.KEY: titles}
            schreibe_yaml(self.folder / RUNS_FILE, [*self.runs(), run][-KEPT_RUNS:])
            return run
