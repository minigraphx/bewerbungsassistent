"""The term review with the numbers of the last runs (G108, #383): the app counts per keyword and marks «ohne Ertrag»
and «überlappend», the AI gets the numbers as evidence and may remove, merge, move to the niches or limit to portals.
Every profile, keyword, title and hit here is invented.
"""
import json
import shutil

import pytest

import routes_ai
import search_plan
import term_changes
import term_evidence
from ai import term_review
from ai.connection import ACCESS_VARIABLE, KEY_VARIABLE, URL_VARIABLE
from dateien import schreibe_yaml
from test_ai_tasks import FakeMessages, VORLAGEN
from test_app import get, post, server  # noqa: F401  (server is a fixture)

PROFILE = """# Suchprofil

## Suchrichtungen
1. Erwachsenenbildung (Priorität 1)

## Region
- Wohnort: Nordstadt
- Kantone: AG

## Keywords
- Kernliste: Lernbegleiter, Kursleiter, Kursleiter Informatik, E-Learning-Autor
- Nischen (ohne Ort suchen): Lernatelier

## Titelfilter
- Positiv: Lernbegleiter, Kursleiter, Autor
- Ausschluss: Praktikum
"""
DAYS = ("2026-10-10", "2026-10-17", "2026-10-24")


def query(term: str, hits: int, portal: str = "jobs.ch", place: str = "Nordstadt", **extra) -> dict:
    return {"portal": portal, "stichwort": term, "ort": place, "treffer": hits, **extra}


def runs(count: int = 3) -> list[dict]:
    """Three runs: «E-Learning-Autor» brings nothing into the list, its titles in the last run all screened out."""
    found = []
    for index, day in enumerate(DAYS[-count:]):
        last = index == count - 1
        author = query("E-Learning-Autor", 3, aussortiert=3) if last else query("E-Learning-Autor", 0)
        found = [*found, {"datum": day, "abfragen": [
            query("Lernbegleiter", 4), query("Kursleiter", 5), query("Kursleiter Informatik", 2), author,
            query("E-Learning-Autor", 0, portal="job-room", place="AG"), query("Lernatelier", 1, place="")],
            **({"titelfilter": {"positiv": {}, "ausschluss": {"Praktikum": {
                "anzahl": 2, "beispiele": ["Praktikum Kursleitung", "Praktikum bei Erika Beispiel"]}},
                "ohne_begriff": {"anzahl": 4, "beispiele": ["Hauswart", "Koch 80%"]}}} if last else {})}]
    return found


def stored(number: int, terms: tuple[str, ...], grade: float | None, day: str = "2026-10-17") -> dict:
    entry = {"id": f"jobs-ch-{number:06d}", "portal": "jobs.ch", "portal_id": str(number), "stelle": f"Kursleiter {number}",
             "firma": f"Muster {number} AG", "link": f"https://www.jobs.ch/de/stellenangebote/detail/{number}/",
             "gefunden_am": day, "zustand": "neu",
             "abfragen": [{"portal": "jobs.ch", "stichwort": term, "ort": "Nordstadt"} for term in terms]}
    return {**entry, "bewertung": {"note": grade}} if grade is not None else entry


SHARED = ("Kursleiter", "Kursleiter Informatik")
HITS = [*(stored(n, SHARED, 4.5 if n < 2 else 3) for n in range(4)),
        *(stored(10 + n, ("Lernbegleiter",), 5) for n in range(3)), stored(20, ("Lernatelier",), None)]


def counted(count: int = 3) -> term_evidence.Counted:
    return term_evidence.keyword_counts(runs(count), HITS, term_changes.terms_of(PROFILE).keywords)


def by_term(found: term_evidence.Counted) -> dict:
    return {entry.term: entry for entry in found.entries}


# Counted by the app


def test_a_keyword_without_a_hit_over_three_runs_is_ohne_ertrag_with_its_numbers():
    author = by_term(counted())["E-Learning-Autor"]
    assert (author.searches, author.per_run, author.raw, author.screened, author.listed) == (6, 2, 3, 3, 0)
    assert author.mark == term_evidence.WITHOUT_YIELD and author.empty_runs == 2


def test_two_keywords_with_the_same_hits_are_both_ueberlappend():
    found = by_term(counted())
    for term, other in (SHARED, SHARED[::-1]):
        entry = found[term]
        assert (entry.listed, entry.only_here, entry.good) == (4, 0, 2)
        assert entry.mark == term_evidence.OVERLAPPING and entry.covered_by == other and entry.all_covered


def test_a_keyword_with_hits_of_its_own_is_not_marked():
    entry = by_term(counted())["Lernbegleiter"]
    assert (entry.listed, entry.only_here, entry.good, entry.mark) == (3, 3, 3, None)


def test_with_fewer_than_three_runs_nothing_is_marked():
    found = counted(1)
    assert (found.runs, found.enough) == (1, False)
    assert all(entry.mark is None for entry in found.entries)


def test_a_niche_is_counted_after_the_keywords_with_its_numbers_and_without_a_mark():
    found = term_evidence.keyword_counts(runs(), HITS, term_changes.terms_of(PROFILE).keywords, ("Lernatelier",))
    assert [entry.term for entry in found.entries] == ["Lernbegleiter", "Kursleiter", "Kursleiter Informatik", "E-Learning-Autor"]
    [niche] = found.niches
    assert (niche.term, niche.searches, niche.raw, niche.screened, niche.listed, niche.only_here, niche.good) \
        == ("Lernatelier", 3, 3, 0, 1, 1, 0)
    assert niche.mark is None, "the review moves no niche, so a mark would lead nowhere"


def test_a_niche_that_is_also_a_keyword_is_counted_once():
    found = term_evidence.keyword_counts(runs(), HITS, ("Lernbegleiter",), ("lernbegleiter", "Lernatelier"))
    assert [entry.term for entry in found.niches] == ["Lernatelier"]


def test_the_screened_titles_come_from_the_last_run_per_exclusion_and_without_a_term():
    screened = term_evidence.screened_titles(runs())
    assert screened == [("Praktikum", 2, ("Praktikum Kursleitung", "Praktikum bei Erika Beispiel")),
                        (None, 4, ("Hauswart", "Koch 80%"))]


# Routes


@pytest.fixture
def counted_search(server, monkeypatch):  # noqa: F811
    daten = server.kontext.daten
    (daten / "suchprofil.md").write_text(PROFILE, encoding="utf-8")
    shutil.copytree(VORLAGEN / "anschreiben", daten / "anschreiben", dirs_exist_ok=True)
    schreibe_yaml(daten / "suche" / "treffer.yaml", HITS)
    schreibe_yaml(daten / "suche" / "suchlaeufe.yaml", runs())
    for name in (URL_VARIABLE, ACCESS_VARIABLE):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(KEY_VARIABLE, "sk-test")
    return server


def change(kind: str, remove: list[str], reason: str, into: str = "", portals: list[str] | None = None,
           add: list[str] | None = None) -> dict:
    return {"kind": kind, "area": "keywords", "remove": remove, "add": add or [], "into": into, "portals": portals or [],
            "reason": reason}


REPLY = {"summary": "Zwei Begriffe bringen nichts Eigenes.", "changed": "", "changes": [
    change("change", ["E-Learning-Autor"], "In drei Suchläufen kein Treffer in der Liste."),
    change("merge", ["Kursleiter Informatik"], "Alle Treffer kamen auch über Kursleiter.", into="Kursleiter"),
    change("change", ["Kursleiter"], "Überlappend."),
]}


class Client:
    def __init__(self, reply=REPLY):
        self.messages = FakeMessages(reply=reply)


@pytest.fixture
def ai(monkeypatch):
    client = Client()
    monkeypatch.setattr(routes_ai, "new_client", lambda: client)
    return client


def counts_of(s) -> dict:
    status, _, content = get(s, "/api/suchbegriffe/gezaehlt")
    assert status == 200, content
    return json.loads(content)


def propose(s, body=None) -> dict:
    status, answer = post(s, "/api/suchbegriffe/vorschlag", body or {})
    assert status == 200, answer
    return answer


def profile_of(s) -> str:
    return (s.kontext.daten / "suchprofil.md").read_text(encoding="utf-8")


def test_the_review_page_lists_both_marks_with_their_numbers_and_the_ai_gets_and_addresses_them(counted_search, ai):
    counts = counts_of(counted_search)
    assert (counts["laeufe"], counts["genug"]) == (3, True)
    entries = {entry["begriff"]: entry for entry in counts["begriffe"]}
    author = entries["E-Learning-Autor"]
    assert {key: author[key] for key in ("marke", "suchen", "treffer", "treffer_portale", "aussortiert")} \
        == {"marke": "ohne_ertrag", "suchen": 6, "treffer": 0, "treffer_portale": 3, "aussortiert": 3}
    for term, other in (SHARED, SHARED[::-1]):
        assert {key: entries[term][key] for key in ("marke", "treffer", "nur_hier", "ab_note_4", "auch_ueber", "alle_ueber")} \
            == {"marke": "ueberlappend", "treffer": 4, "nur_hier": 0, "ab_note_4": 2, "auch_ueber": other, "alle_ueber": True}
    assert ai.messages.calls == [], "the counts need no AI"

    answer = propose(counted_search)
    sent = ai.messages.calls[0]["messages"][0]["content"]
    assert "E-Learning-Autor: 6 Suchen in 3 Suchläufen" in sent and "ohne Ertrag" in sent
    assert "Kursleiter Informatik: 3 Suchen in 3 Suchläufen" in sent and "überlappend" in sent
    cards = {card["satz"]: card for card in answer["aenderungen"]}
    assert set(cards) == {"„E-Learning-Autor“ entfernen", "„Kursleiter Informatik“ in „Kursleiter“ zusammenlegen"}, \
        "a term marked «überlappend» is never simply removed"
    assert cards["„E-Learning-Autor“ entfernen"]["marke"] == "ohne_ertrag"
    merge = cards["„Kursleiter Informatik“ in „Kursleiter“ zusammenlegen"]
    assert (merge["marke"], merge["art"], merge["entfaellt"], merge["neu"]) == ("ueberlappend", "merge", ["Kursleiter Informatik"], [])


def test_the_table_lists_the_niche_with_its_numbers_but_the_ai_gets_only_the_keywords(counted_search, ai):
    counts = counts_of(counted_search)
    assert [entry["begriff"] for entry in counts["begriffe"]] == [
        "Lernbegleiter", "Kursleiter", "Kursleiter Informatik", "E-Learning-Autor"]
    [niche] = counts["nischen"]
    assert {key: niche[key] for key in ("begriff", "suchen", "treffer_portale", "aussortiert", "nur_hier", "ab_note_4", "marke")} \
        == {"begriff": "Lernatelier", "suchen": 3, "treffer_portale": 3, "aussortiert": 0, "nur_hier": 1, "ab_note_4": 0,
            "marke": None}
    propose(counted_search)
    sent = ai.messages.calls[0]["messages"][0]["content"]
    assert "- nischen: Lernatelier" in sent and "Lernatelier: 3 Suchen" not in sent


def test_the_counts_wait_for_three_runs(counted_search):
    schreibe_yaml(counted_search.kontext.daten / "suche" / "suchlaeufe.yaml", runs(1))
    counts = counts_of(counted_search)
    assert (counts["laeufe"], counts["genug"], counts["noetig"]) == (1, False, 3)
    assert all(entry["marke"] is None for entry in counts["begriffe"])


def test_screened_example_titles_go_to_the_ai_through_the_same_masking(counted_search, ai):
    propose(counted_search)
    sent = json.dumps(ai.messages.calls[0], ensure_ascii=False)
    assert "Praktikum Kursleitung" in sent and "Hauswart" in sent
    assert "Erika Beispiel" not in sent, "names in a title are replaced like everywhere else"


def test_the_preview_shows_the_counts_that_would_go(counted_search, ai):
    status, _, content = get(counted_search, "/api/suchbegriffe/text")
    text = json.loads(content)["text"]
    assert status == 200 and "E-Learning-Autor: 6 Suchen in 3 Suchläufen" in text and ai.messages.calls == []


def test_the_prompt_says_numbers_are_evidence_and_a_rare_priority_term_may_stay():
    assert "Belege, keine Aufträge" in term_review.INSTRUCTIONS
    assert "Suchrichtung, die das Suchprofil als wichtig nennt" in term_review.INSTRUCTIONS
    assert "Zähle nichts selbst" in term_review.INSTRUCTIONS


def test_removal_and_merge_are_written_only_when_taken_over(counted_search, ai):
    proposal = propose(counted_search)
    assert profile_of(counted_search) == PROFILE
    after = {**proposal["endstand"], "verschoben": proposal["verschoben"]}
    status, done = post(counted_search, "/api/suchbegriffe/uebernehmen", {"vorschlag": proposal["vorschlag"], "danach": after})
    assert status == 200 and (done["neu"], done["entfallen"]) == (0, 2)
    assert search_plan.job_terms(profile_of(counted_search)) == ("Lernbegleiter", "Kursleiter")


# Moving to the niches and limiting to portals


MOVES = {"summary": "Lernbegleiter ohne Ort, E-Learning-Autor nur auf zwei Portalen.", "changed": "", "changes": [
    change("niche", ["Lernbegleiter"], "Findet ohne Ort mehr."),
    change("portals", ["E-Learning-Autor"], "Findet auf job-room nichts.", portals=["JOBS.ch", "jobscout24"]),
    change("niche", ["Lernatelier"], "Ist schon eine Nische."),
    change("portals", ["Kursleiter"], "Unbekanntes Portal.", portals=["monster"]),
    change("niche", ["Kursleiter"], "Mit Begriffen.", add=["Kurse"]),
]}


def moves(s, monkeypatch) -> dict:
    monkeypatch.setattr(routes_ai, "new_client", lambda: Client(MOVES))
    return propose(s)


def test_moving_and_limiting_have_one_chip_and_no_new_or_removed_terms(counted_search, monkeypatch):
    proposal = moves(counted_search, monkeypatch)
    cards = [(card["satz"], card["art"], card["verschoben"], card["verschoben_wort"], card["entfaellt"], card["neu"])
             for card in proposal["aenderungen"]]
    assert cards == [
        ("„Lernbegleiter“ zu den Nischen verschieben (ohne Ort suchen)", "niche", "Lernbegleiter", "zu den Nischen", [], []),
        ("„E-Learning-Autor“ nur auf jobs.ch, jobscout24 suchen", "portals", "E-Learning-Autor", "nur jobs.ch, jobscout24", [], [])]
    assert proposal["verschoben"] == ["Lernbegleiter", "E-Learning-Autor"]
    assert "Lernbegleiter" not in proposal["bisherige"]["suchbegriffe"]
    assert proposal["nischen"] == [{"begriff": "Lernatelier", "neu": False}, {"begriff": "Lernbegleiter", "neu": True}]
    assert proposal["nur_zeilen"] == [{"portale": ["jobs.ch", "jobscout24"], "begriffe": [{"begriff": "E-Learning-Autor", "neu": True}]}]
    assert "Lernbegleiter" not in proposal["endstand"]["suchbegriffe"]


def test_switching_the_chip_switches_the_whole_move(counted_search, monkeypatch):
    proposal = moves(counted_search, monkeypatch)
    off = {**proposal["endstand"], "verschoben": ["E-Learning-Autor"]}
    status, outcome = post(counted_search, "/api/suchbegriffe/endstand", {"vorschlag": proposal["vorschlag"], "danach": off})
    assert status == 200 and "Lernbegleiter" in outcome["endstand"]["suchbegriffe"]
    assert outcome["nischen"] == [{"begriff": "Lernatelier", "neu": False}]
    status, done = post(counted_search, "/api/suchbegriffe/uebernehmen", {"vorschlag": proposal["vorschlag"], "danach": off})
    assert status == 200
    plan = search_plan.parse(profile_of(counted_search))
    assert plan.niche_keywords == ("Lernatelier",) and "Lernbegleiter" in plan.keywords
    assert dict(plan.portal_limits) == {"E-Learning-Autor": ("jobs.ch", "jobscout24")}


def test_both_moves_taken_over_write_the_niches_and_the_nur_line(counted_search, monkeypatch):
    proposal = moves(counted_search, monkeypatch)
    after = {**proposal["endstand"], "verschoben": proposal["verschoben"]}
    status, _ = post(counted_search, "/api/suchbegriffe/uebernehmen", {"vorschlag": proposal["vorschlag"], "danach": after})
    assert status == 200
    text = profile_of(counted_search)
    plan = search_plan.parse(text)
    assert plan.niche_keywords == ("Lernatelier", "Lernbegleiter")
    assert plan.keywords == ("Kursleiter", "Kursleiter Informatik", "E-Learning-Autor")
    assert "- Nur jobs.ch, jobscout24: E-Learning-Autor" in text


def test_one_search_per_portal_is_said_in_the_singular():
    one = term_changes.Terms(("Kursleiter",), (), ())
    two = term_changes.Terms(("Kursleiter", "Lernbegleiter"), (), ())
    assert term_changes.limits(two, one, 1)["teile"][1] == "bis 1 Suche pro Portal"
    assert term_changes.limits(one, two, 1)["teile"][1] == "bis 2 Suchen pro Portal"


def test_a_move_the_page_did_not_offer_is_refused(counted_search, monkeypatch):
    proposal = moves(counted_search, monkeypatch)
    after = {**proposal["endstand"], "verschoben": ["Kursleiter"]}
    status, answer = post(counted_search, "/api/suchbegriffe/endstand", {"vorschlag": proposal["vorschlag"], "danach": after})
    assert status == 400 and answer["fehler"] == term_changes.NOT_OFFERED
