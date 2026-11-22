"""Example titles per title filter term from the person's last run, for Erweitert › Titelfilter (G104). Invented data."""
import datetime
import json

import yaml

import hits
import query_log
import search_plan
import title_examples
import title_filter
from test_app import get, post, server  # noqa: F401  (server is a fixture)

TODAY = datetime.date(2026, 11, 20)
POSITIVE = ("Software", "Kurs")
EXCLUDE = ("Sales (ganzes Wort)", "Praktikum")
QUERY = {"portal": "jobs.ch", "stichwort": "Software", "ort": "Bern"}


def check(number: int, title: str) -> tuple[str, str, title_filter.Verdict]:
    return f"jobs.ch:t-{number}", title, title_filter.verdict(title, EXCLUDE, POSITIVE)


def test_each_term_counts_the_titles_it_let_through_or_kept_out_with_three_examples():
    checks = [check(1, "Softwareentwickler:in"), check(2, "Software Engineer"), check(3, "Software Tester"),
              check(4, "Kursleiter Software"), check(5, "Sales Manager B2B"), check(6, "Buchhalter"),
              check(7, "Praktikum Software")]
    tally = title_examples.noted({}, checks)
    run = title_examples.summary({"titelfilter": title_examples.closed(tally)}, POSITIVE, EXCLUDE)
    software, kurs = run["positiv"]
    assert software == {"begriff": "Software", "anzahl": 4,
                        "beispiele": ["Softwareentwickler:in", "Software Engineer", "Software Tester"]}
    assert kurs == {"begriff": "Kurs", "anzahl": 1, "beispiele": ["Kursleiter Software"]}
    assert run["ausschluss"] == [{"begriff": "Sales (ganzes Wort)", "anzahl": 1, "beispiele": ["Sales Manager B2B"]},
                                 {"begriff": "Praktikum", "anzahl": 1, "beispiele": ["Praktikum Software"]}]
    assert run["ohne_begriff"] == {"anzahl": 1, "beispiele": ["Buchhalter"]}
    assert run["lauf"] is True


def test_a_title_found_by_two_queries_counts_once():
    tally = title_examples.noted(title_examples.noted({}, [check(1, "Software Engineer")]), [check(1, "Software Engineer")])
    assert title_examples.summary({"titelfilter": title_examples.closed(tally)}, POSITIVE, EXCLUDE)["positiv"][0]["anzahl"] == 1


def test_a_term_without_titles_and_a_run_from_before_say_so():
    empty = title_examples.summary({"titelfilter": title_examples.closed({})}, POSITIVE, EXCLUDE)
    assert empty["lauf"] is True
    assert empty["positiv"][1] == {"begriff": "Kurs", "anzahl": 0, "beispiele": []}
    before = title_examples.summary({"datum": "2026-11-19", "abfragen": []}, POSITIVE, EXCLUDE)
    assert before["lauf"] is False
    assert title_examples.summary(None, POSITIVE, EXCLUDE)["lauf"] is False


def test_without_positive_terms_nothing_is_screened_for_a_missing_term():
    assert title_examples.summary({"titelfilter": title_examples.closed({})}, (), EXCLUDE)["ohne_begriff"] is None


def test_the_log_data_is_checked_before_it_counts():
    raw = {"titelfilter": {"positiv": {"Software": {"anzahl": "viele", "beispiele": ["x"]}, "Kurs": {"anzahl": 2, "beispiele": [3, "ok"]}},
                           "ausschluss": ["kaputt"], "ohne_begriff": {"anzahl": -1, "beispiele": []}}}
    run = title_examples.summary(raw, POSITIVE, EXCLUDE)
    assert run["positiv"] == [{"begriff": "Software", "anzahl": 0, "beispiele": []},
                              {"begriff": "Kurs", "anzahl": 2, "beispiele": ["ok"]}]
    assert run["ausschluss"][0]["anzahl"] == 0 and run["ohne_begriff"]["anzahl"] == 0


def test_the_examples_belong_to_the_run_they_were_seen_in(tmp_path):
    log = query_log.QueryLog(tmp_path)
    log.note_titles([check(1, "Software Engineer"), check(2, "Sales Manager B2B")])
    log.close_run({"jobs.ch": [{**{k: v for k, v in QUERY.items() if k != "portal"}, "treffer": 2}]}, TODAY)
    [run] = log.runs()
    assert run["titelfilter"]["positiv"]["Software"] == {"anzahl": 1, "beispiele": ["Software Engineer"]}
    assert "gesehen" not in run["titelfilter"]
    log.close_run({"jobs.ch": [{"stichwort": "Software", "ort": "Bern", "treffer": 0}]}, TODAY)
    assert log.runs()[-1]["titelfilter"] == {"positiv": {}, "ausschluss": {}, "ohne_begriff": {"anzahl": 0, "beispiele": []}}


def test_screening_tells_the_verdict_of_each_title_it_checks(tmp_path):
    seen = []
    listing = [{"portal": "jobs.ch", "portal_id": f"s-{n}", "stelle": title, "firma": "Beispiel AG", "ort": "Bern",
                "link": f"https://www.jobs.ch/de/stellenangebote/detail/s-{n}/", "alter_tage": 2}
               for n, title in enumerate(["Softwareentwickler", "Sales Manager", "Buchhalter"])]
    hits.Hits(tmp_path).screen(listing, EXCLUDE, 45, [], title_positive=POSITIVE,
                               on_title_checked=lambda hit, found: seen.append((hit["stelle"], found)))
    assert [(title, found.passed_by, found.excluded_by, found.without_term) for title, found in seen] == [
        ("Softwareentwickler", ("Software",), (), False), ("Sales Manager", (), ("Sales (ganzes Wort)",), False),
        ("Buchhalter", (), (), True)]
    assert hits.Hits(tmp_path / "leer").screen(listing, (), 45, [], on_title_checked=lambda *_: seen.append(1)) and len(seen) == 3


PROFILE = """# Suchprofil

## Region
- Kantone (job-room): BE
- Orte (jobs.ch): Bern

## Keywords
- Kernliste: Software, Kursleiter

## Titelfilter
- Positiv: Software, Kurs
- Ausschluss: Sales (ganzes Wort), Praktikum
"""


def ad(number: int, title: str) -> dict:
    return {"portal": "jobs.ch", "portal_id": f"r-{number}", "stelle": title, "firma": "Beispiel AG", "ort": "Bern",
            "link": f"https://www.jobs.ch/de/stellenangebote/detail/r-{number}/", "alter_tage": 2,
            "abfragen": [{"stichwort": "Software", "ort": "Bern"}]}


def test_after_a_run_the_yield_route_has_the_examples_per_term(server):  # noqa: F811
    (server.kontext.daten / search_plan.PROFILE).write_text(PROFILE, encoding="utf-8")
    status, shown = get_examples(server)
    assert status == 200 and shown["lauf"] is False, "examples come after the next run"
    listing = [ad(1, "Softwareentwickler:in (80–100 %)"), ad(2, "Sales Manager B2B"), ad(3, "Salesforce Software"),
               ad(4, "Buchhalter")]
    assert post(server, "/api/suche/sichten", {"treffer": listing})[0] == 200
    summary = {"jobs.ch": {"treffer": 4, "neu": 2, "problem": "", "abfragen": [{"stichwort": "Software", "ort": "Bern", "treffer": 4}]}}
    assert post(server, "/api/suche/abschluss", {"portale": summary})[0] == 200
    status, shown = get_examples(server)
    assert shown["lauf"] is True
    assert shown["positiv"][0] == {"begriff": "Software", "anzahl": 2,
                                   "beispiele": ["Softwareentwickler:in (80–100 %)", "Salesforce Software"]}
    assert shown["ausschluss"][0] == {"begriff": "Sales (ganzes Wort)", "anzahl": 1, "beispiele": ["Sales Manager B2B"]}
    assert shown["ohne_begriff"] == {"anzahl": 1, "beispiele": ["Buchhalter"]}
    logged = yaml.safe_load((server.kontext.daten / "suche" / query_log.RUNS_FILE).read_text(encoding="utf-8"))
    assert logged[-1]["titelfilter"]["ausschluss"]["Sales (ganzes Wort)"]["anzahl"] == 1


def get_examples(server) -> tuple[int, dict]:  # noqa: F811
    status, _, content = get(server, "/api/suche/ertrag")
    return status, json.loads(content)["titelfilter"]
