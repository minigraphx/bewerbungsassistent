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
    return {"aussortiert": (entry["aussortiert"] if entry else 0) + 1,
            "beispiele": examples if len(examples) >= MAX_EXAMPLES else [*examples, example]}


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
        if not queries:
            return
        with _LOCK:
            entries = {_key(entry): entry for entry in self._pending()}
            changed = {_key(query): {"portal": query["portal"], "stichwort": query["stichwort"], "ort": query["ort"],
                                     **_screened(entries.get(_key(query)), title, reason)} for query in queries}
            schreibe_yaml(self.folder / PENDING_FILE, {"abfragen": list({**entries, **changed}.values())})

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
            entries = [{**query, **({name: waiting[_key(query)][name] for name in ("aussortiert", "beispiele")}
                                    if first[_key(query)] == index and _key(query) in waiting else {})}
                       for index, query in enumerate(queries)]
            schreibe_yaml(self.folder / PENDING_FILE, {"abfragen": []})
            if not entries:
                return None
            run = {"datum": today.isoformat(), "abfragen": entries, title_examples.KEY: titles}
            schreibe_yaml(self.folder / RUNS_FILE, [*self.runs(), run][-KEPT_RUNS:])
            return run
