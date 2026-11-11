"""Checking the search terms (#210, G45): the app counts, the AI proposes, the person decides what changes."""
import json
import shutil

import pytest

import routes_ai
import search_plan
import search_terms
import term_changes
import term_evidence
from ai.connection import ACCESS_VARIABLE, KEY_VARIABLE, URL_VARIABLE
from dateien import schreibe_yaml
from test_ai_tasks import FakeMessages, VORLAGEN
from test_app import get, post, server  # noqa: F401  (server is a fixture)

POOR = ["Process Engineer", "Manufacturing Engineer", "EMSR-Engineer"]
REPLY = {"summary": "Ein Begriff im Titelfilter ist zu allgemein.", "changed": "", "changes": [
    {"area": "keywords", "remove": [], "add": ["Fullstack Entwickler"], "reason": "Steht so im Lebenslauf."},
    {"area": "positive", "remove": ["Engineer"], "add": ["Backend", "Frontend"], "reason": "Bringt viele Industriestellen."},
    {"area": "exclude", "remove": [], "add": ["Verkauf"], "reason": "Verkaufsstellen passen nicht."},
    {"area": "positive", "remove": ["Gibtsnicht"], "add": [], "reason": "Nicht im Profil."},
    {"area": "keywords", "remove": [], "add": ["Java Entwickler"], "reason": "Java ist ausgeschlossen."},
    {"area": "keywords", "remove": [], "add": ["Python"], "reason": "Wird schon gesucht."},
    {"area": "positive", "remove": ["Engineer"], "add": ["Gibtsnicht, mit Komma"], "reason": "Halber Ersatz."},
    {"area": "region", "remove": [], "add": ["Zürich"], "reason": "Kein Bereich der Suche."},
]}


def hit(number: int, title: str, grade: float | None, day: str = "2026-10-20") -> dict:
    found = {"id": f"jobs-ch-{number:012d}", "portal": "jobs.ch", "portal_id": str(number), "stelle": title,
             "firma": f"Muster {number} AG", "link": f"https://www.jobs.ch/de/stellenangebote/detail/{number}/",
             "gefunden_am": day, "zustand": "neu"}
    return {**found, "bewertung": {"note": grade}} if grade is not None else found


def sample_hits(poor: int = 12, fine_engineers: int = 3, others: int = 25) -> list[dict]:
    """Engineers that came in only through „Engineer“, most of them poor, and others that match two terms."""
    engineers = [hit(i, POOR[i % 3], 2.5) for i in range(poor)]
    engineers += [hit(100 + i, "Senior Engineer", 4.5) for i in range(fine_engineers)]
    rest = [hit(300 + i, "Python Entwickler", 5, "2026-10-25") for i in range(others)]
    return [*engineers, *rest, hit(999, "Engineer ohne Note", None)]


TERMS = ("Python", "Software", "Entwickler", "Developer", "Engineer", "Daten", "Data", "Web", "Learning", "Trainer")


# Counted by the app


def test_the_term_that_alone_lets_in_many_poor_hits_is_named_with_its_numbers():
    hits = [*sample_hits(), *(hit(400 + i, "Data Engineer Python", 5) for i in range(10))]
    found = term_evidence.strongest(hits, TERMS)
    assert found is not None and found.term == "Engineer"
    assert (len(found.ids), found.below, found.rated) == (15, 12, 50)
    assert set(found.examples) == set(POOR) and found.too_general


@pytest.mark.parametrize("hits", [
    sample_hits(others=10),  # fewer than 30 rated hits
    sample_hits(poor=6),  # fewer than 10 hits only through the term
    sample_hits(poor=10, fine_engineers=5),  # 10 of 15 below 4: under 70 %
    sample_hits(poor=10, others=60),  # 13 of 73: under 20 % of all
])
def test_no_hint_below_the_thresholds(hits):
    assert term_evidence.strongest(hits, TERMS) is None


def test_only_the_strongest_case_is_named():
    hits = [*sample_hits(), *(hit(500 + i, "Web Trainer Fitness", 2) for i in range(11))]
    assert term_evidence.strongest(hits, ("Engineer", "Web Trainer", "Python")).term == "Engineer"
    assert term_evidence.strongest(hits, ("Engineer", "Fitness", "Python")).term == "Engineer"


def test_a_title_with_two_terms_came_in_through_neither_alone():
    found = term_evidence.evidence([hit(1, "Python Data Engineer", 2)], TERMS)
    assert found == {}


# Title filter in the profile


def profile() -> str:
    return (VORLAGEN / "suchprofil.md").read_text(encoding="utf-8")


def test_one_term_of_a_slash_group_goes_and_the_others_stay():
    text = search_terms.without_title_term(profile(), "positiv", "Engineer")
    assert "Engineer" not in search_plan.title_terms(text, "positiv")
    assert {"Entwickler", "Developer"} <= set(search_plan.title_terms(text, "positiv"))


def test_a_title_term_is_added_to_its_line_or_a_new_section():
    text = search_terms.with_title_term(profile(), "ausschluss", "Verkauf")
    assert search_plan.title_terms(text, "ausschluss")[-1] == "Verkauf"
    assert search_terms.with_title_term(text, "ausschluss", "verkauf") == text
    bare = search_terms.with_title_term("# Suchprofil\n\n## Keywords\n- Kernliste: Python\n", "positiv", "Python")
    assert search_plan.parse(bare).title_positive == ("Python",)


# Routes


@pytest.fixture
def job_search(server, monkeypatch):  # noqa: F811
    daten = server.kontext.daten
    shutil.copy(VORLAGEN / "suchprofil.md", daten / "suchprofil.md")
    shutil.copytree(VORLAGEN / "anschreiben", daten / "anschreiben", dirs_exist_ok=True)
    schreibe_yaml(daten / "suche" / "treffer.yaml", sample_hits())
    for name in (URL_VARIABLE, ACCESS_VARIABLE):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(KEY_VARIABLE, "sk-test")
    return server


class Client:
    def __init__(self, reply=REPLY):
        self.messages = FakeMessages(reply=reply)


@pytest.fixture
def ai(monkeypatch):
    client = Client()
    monkeypatch.setattr(routes_ai, "new_client", lambda: client)
    return client


def profile_of(s) -> str:
    return (s.kontext.daten / "suchprofil.md").read_text(encoding="utf-8")


def propose(s, body=None) -> dict:
    status, answer = post(s, "/api/suchbegriffe/vorschlag", body or {})
    assert status == 200, answer
    return answer


def test_the_hint_names_the_term_and_can_be_hidden(job_search):
    _, _, content = get(job_search, "/api/suchbegriffe/hinweis")
    answer = json.loads(content)
    assert answer["hinweis"]["begriff"] == "Engineer" and answer["hinweis"]["anzahl"] == 15
    assert answer["kosten_usd"] >= 0.01 and answer["treffer"] == 40
    assert post(job_search, "/api/suchbegriffe/ausblenden", {"begriff": "Engineer"})[0] == 200
    assert json.loads(get(job_search, "/api/suchbegriffe/hinweis")[2])["hinweis"] is None


def test_the_text_for_the_ai_has_placeholders_and_is_not_sent(job_search, ai):
    status, _, content = get(job_search, "/api/suchbegriffe/text")
    answer = json.loads(content)
    assert status == 200 and "Process Engineer" in answer["text"] and "<treffer>" in answer["text"]
    assert "{{" in answer["text"] and answer["kosten_usd"] >= 0.01
    assert ai.messages.calls == []


def test_only_changes_that_hold_come_back_with_evidence_counted_by_the_app(job_search, ai):
    before = profile_of(job_search)
    answer = propose(job_search)
    sentences = [change["satz"] for change in answer["aenderungen"]]
    assert sentences == ["«Engineer» ersetzen durch Backend und Frontend", "Suchbegriff «Fullstack Entwickler» aufnehmen",
                         "«Verkauf» ausschliessen"]
    first = answer["aenderungen"][0]
    assert first["beleg"]["anzahl"] == 15 and first["beleg"]["unter"] == 12 and first["zu_allgemein"]
    assert first["grund"] == "Bringt viele Industriestellen."
    assert answer["grenzen"]["zeile"] == "Danach: 6 von 15 Suchbegriffen · bis 12 von 30 Suchen pro Portal"
    assert "Engineer" not in answer["endstand"]["positiv"] and answer["entfaellt"] == ["Engineer"]
    assert profile_of(job_search) == before, "nothing changes without adoption"
    sent = json.dumps(ai.messages.calls, ensure_ascii=False)
    assert ai.messages.calls[0]["model"] == "claude-haiku-5-5" and "<treffer>" in sent and "Stilprofil" not in sent


def test_the_evidence_link_finds_exactly_those_hits(job_search):
    _, _, content = get(job_search, "/api/suchbegriffe/beleg", begriff="Engineer")
    assert sorted(json.loads(content)["ids"]) == sorted(h["id"] for h in sample_hits()[:15])


def test_the_chosen_changes_are_written_after_a_draft_and_can_be_undone(job_search, ai):
    before = profile_of(job_search)
    proposal = propose(job_search)
    status, outcome = post(job_search, "/api/suchbegriffe/endstand", {"vorschlag": proposal["vorschlag"], "gewaehlt": [0]})
    assert status == 200 and outcome["endstand"]["suchbegriffe"] == list(term_changes.terms_of(before).keywords)
    status, done = post(job_search, "/api/suchbegriffe/uebernehmen", {"vorschlag": proposal["vorschlag"], "gewaehlt": [0, 2]})
    assert status == 200 and done["anzahl"] == 2
    after = profile_of(job_search)
    assert "Backend" in search_plan.title_terms(after, "positiv") and "Engineer" not in search_plan.title_terms(after, "positiv")
    assert "Verkauf" in search_plan.title_terms(after, "ausschluss")
    assert "Fullstack Entwickler" not in search_plan.job_terms(after), "only what was ticked"
    drafts = job_search.kontext.ablage.liste(job_search.kontext.daten / "suchprofil.md")
    assert any(draft.datei and draft.beschreibung.startswith("Stand vor") for draft in drafts)
    status, _ = post(job_search, "/api/suchbegriffe/rueckgaengig", {"vorher": done["vorher"], "nachher": done["nachher"]})
    assert status == 200 and profile_of(job_search) == before


def test_nothing_ticked_is_refused(job_search, ai):
    proposal = propose(job_search)
    _, outcome = post(job_search, "/api/suchbegriffe/endstand", {"vorschlag": proposal["vorschlag"], "gewaehlt": []})
    assert outcome["grenzen"]["gesperrt"] == term_changes.NOTHING_CHOSEN
    status, answer = post(job_search, "/api/suchbegriffe/uebernehmen", {"vorschlag": proposal["vorschlag"], "gewaehlt": []})
    assert status == 400 and answer["fehler"] == term_changes.NOTHING_CHOSEN


def test_a_change_beyond_the_limits_is_refused(job_search, ai):
    path = job_search.kontext.daten / "suchprofil.md"
    full = ", ".join(f"Begriff{n}" for n in range(search_plan.MAX_KEYWORDS))
    path.write_text(profile().replace("Python, TypeScript, Softwareentwickler, Data Engineer, E-Learning", full), encoding="utf-8")
    before = profile_of(job_search)
    proposal = propose(job_search)
    index = next(c["nummer"] for c in proposal["aenderungen"] if c["bereich"] == "keywords")
    _, outcome = post(job_search, "/api/suchbegriffe/endstand", {"vorschlag": proposal["vorschlag"], "gewaehlt": [index]})
    assert "16 Suchbegriffe" in outcome["grenzen"]["gesperrt"]
    status, answer = post(job_search, "/api/suchbegriffe/uebernehmen", {"vorschlag": proposal["vorschlag"], "gewaehlt": [index]})
    assert status == 400 and "höchstens 15" in answer["fehler"] and profile_of(job_search) == before


def test_a_proposal_is_stale_once_the_terms_changed(job_search, ai):
    proposal = propose(job_search)
    assert post(job_search, "/api/beruf/aufnehmen", {"beruf": "Datenanalyse"})[0] == 200
    _, outcome = post(job_search, "/api/suchbegriffe/endstand", {"vorschlag": proposal["vorschlag"], "gewaehlt": [0]})
    assert outcome["veraltet"]
    status, answer = post(job_search, "/api/suchbegriffe/uebernehmen", {"vorschlag": proposal["vorschlag"], "gewaehlt": [0]})
    assert status == 400 and answer["fehler"].startswith("Vorschlag veraltet")


def test_a_revision_gets_the_former_proposal_and_what_the_person_wrote(job_search, ai):
    first = propose(job_search)
    ai.messages.reply = {**REPLY, "changed": "«Engineer» bleibt.", "changes": REPLY["changes"][1:3]}
    assert post(job_search, "/api/suchbegriffe/vorschlag", {"vorher": first["vorschlag"]})[0] == 400
    second = propose(job_search, {"vorher": first["vorschlag"], "hinweis": "Engineer behalten, ich baue Anlagen."})
    assert second["runde"] == 2 and second["geaendert"] == "«Engineer» bleibt." and len(second["aenderungen"]) == 2
    assert second["kosten_bisher"] > second["kosten_usd"] > 0
    sent = ai.messages.calls[-1]["messages"][0]["content"]
    assert "Letzter Vorschlag" in sent and "<hinweis>\nEngineer behalten, ich baue Anlagen.\n</hinweis>" in sent


def test_a_failed_call_says_that_nothing_changed(job_search, monkeypatch):
    monkeypatch.setattr(routes_ai, "new_client", lambda: Client(reply="kein JSON"))
    status, answer = post(job_search, "/api/suchbegriffe/vorschlag", {})
    assert status == 400 and answer["fehler"].startswith("Kein Vorschlag.")
    assert "Am Suchprofil hat sich nichts geändert." in answer["fehler"]


def test_only_for_a_job_search(job_search, ai):
    shutil.copy(VORLAGEN / "suchprofil-lehrstelle.md", job_search.kontext.daten / "suchprofil.md")
    status, answer = post(job_search, "/api/suchbegriffe/vorschlag", {})
    assert status == 400 and "Stellensuche" in answer["fehler"] and ai.messages.calls == []
    assert json.loads(get(job_search, "/api/suchbegriffe/hinweis")[2])["verfuegbar"] is False
