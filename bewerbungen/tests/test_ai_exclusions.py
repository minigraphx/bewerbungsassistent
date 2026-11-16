"""The AI proposes exclusion reasons from dismissed hits on Suche einstellen (#319, G86); invented hits only.

Only title, company, place and workload of the dismissed hits go to the AI, never anything about the person. Each
proposal names the hits it rests on, and the search profile changes only when the person adopts one, with drafts
before and after and an undo. The AI is simulated; nothing goes to the network.
"""
import json
import pathlib
import re
import shutil

import anthropic
import pytest

import routes_ai
import routes_rate_all
import search_frame
import search_plan
from ai import exclusion_reasons, tasks
from ai.connection import ACCESS_VARIABLE, KEY_VARIABLE, URL_VARIABLE
from ai.errors import CREDIT_USED, SETUP_ACTION
from dateien import schreibe_yaml
from hits import Hits
from sample_folder import BRIEF_ID
from test_ai_tasks import VORLAGEN, FakeMessages, response
from test_app import get, post, server  # noqa: F401  (server is a fixture)

ROOT = pathlib.Path(__file__).resolve().parents[2]
PAGES = ROOT / "bewerbungen" / "seiten"
ROUTE = "/api/suche/ki-ausschluesse"
JOB = (VORLAGEN / "suchprofil.md").read_text(encoding="utf-8")
SENT_KEYS = ("Titel", "Firma", "Ort", "Pensum")
NOT_FOR_THE_AI = {"link": "https://www.jobs.ch/de/stellenangebote/detail/geheim-123/", "portal_id": "geheim-123",
                  "bewertung": {"note": 2, "zusammenfassung": "Bewertungstext nur fuer die Person"},
                  "eigene_sterne": 1, "alter_tage": 4, "gefunden_am": "2026-10-20"}
AD_TEXT = "Inseratstext mit Kontakt Petra Beispielfrau, petra@example.ch"


def hit(number: int, title: str, company: str, place: str, workload: str, state: str = "verworfen") -> dict:
    return {"id": f"jobs-ch-d{number}", "portal": "jobs.ch", "stelle": title, "firma": company, "ort": place,
            "pensum": workload, "zustand": state, **NOT_FOR_THE_AI}


FIELD = [hit(1, "Aussendienst Berater Software", "Muster Handel AG", "Thun", "100%"),
         hit(2, "Software Verkaeufer im Aussendienst", "Probe Vertrieb GmbH", "Biel", "80-100%"),
         hit(3, "Aussendienst Techniker Web", "Muster Technik AG", "Olten", "100%")]
RETAIL = [hit(4, "Python Entwickler Detailhandel", "Muster Detail AG", "Lyss", "60%"),
          hit(5, "Web Entwickler Detailhandel Teilzeit", "Probe Laden AG", "Burgdorf", "40-60%")]
DISMISSED = FIELD + RETAIL
NOT_SENT = [hit(6, "Sales Manager Software", "Muster Sales AG", "Aarau", "100%"),  # caught by the title exclusion
            hit(7, "Data Engineer Logistik", "Ausgeschlossen AG", "Zug", "100%"),  # an excluded company
            hit(8, "Python Entwickler Bank", "Muster Bank AG", "Bern", "100%", "neu"),
            hit(9, "Data Engineer Energie", "Muster Energie AG", "Solothurn", "80%", "uebernommen")]

REPLY = [
    {"category": "titel", "value": "Aussendienst", "reason": "Alle drei Stellen sind im Aussendienst.",
     "hits": [h["stelle"] for h in FIELD]},
    {"category": "branche", "value": "Detailhandel", "reason": "Zwei Stellen sind im Detailhandel.",
     "hits": [h["stelle"] for h in RETAIL] + ["T99-beef"]},  # a label the AI made up is dropped
    {"category": "pensum", "value": "Pensum unter 80 %", "reason": "Nur eine Stelle.", "hits": [RETAIL[1]["stelle"]]},
    {"category": "titel", "value": "Sales", "reason": "Schon ausgeschlossen.", "hits": [FIELD[0]["stelle"], FIELD[1]["stelle"]]},
    {"category": "titel", "value": "Software", "reason": "Die Suche sucht danach.", "hits": [FIELD[0]["stelle"], FIELD[1]["stelle"]]},
    {"category": "ort", "value": "Arbeitsort Lyss", "reason": "Erfundene Treffer.", "hits": ["T98-dead", "T97-cafe"]},
    {"category": "titel", "value": "Techniker", "reason": "Nur ein Titel hat das Wort.",
     "hits": [FIELD[2]["stelle"], RETAIL[0]["stelle"]]},
]


def sent_rows(payload: dict) -> list[tuple[str, dict]]:
    """The hits of a request as (label, fields); fails if anything but the fixed header and the hits is in it."""
    content = payload["messages"][0]["content"]
    head, block = content.split("<treffer>\n", 1)
    assert head == exclusion_reasons.HEADER + "\n\n"
    body, tail = block.split("\n</treffer>", 1)
    assert tail == ""
    rows = []
    for line in body.split("\n"):
        label, rest = line.split(": ", 1)
        assert re.fullmatch(r"T\d+-[0-9a-f]{4}", label), line
        rows.append((label, dict(part.split(": ", 1) for part in rest.split(" · "))))
    return rows


class LabelledMessages(FakeMessages):
    """Answers like the AI: it names hits by the labels of the request it got, found here by title."""

    def __init__(self, proposals=REPLY, **kwargs):
        super().__init__(**kwargs)
        self.proposals = proposals

    def create(self, **payload):
        labels = {fields["Titel"]: label for label, fields in sent_rows(payload)}
        self.reply = {"proposals": [{**p, "hits": [labels.get(title, title) for title in p["hits"]]}
                                    for p in self.proposals]}
        return super().create(**payload)


class Client:
    def __init__(self, **kwargs):
        self.messages = LabelledMessages(**kwargs)


@pytest.fixture
def job_search(server, monkeypatch):  # noqa: F811
    daten = server.kontext.daten
    (daten / search_plan.PROFILE).write_text(JOB, encoding="utf-8")
    shutil.copytree(VORLAGEN / "anschreiben", daten / "anschreiben", dirs_exist_ok=True)
    store = Hits(daten)
    store._write(DISMISSED + NOT_SENT)
    (store.folder / "texte").mkdir(parents=True, exist_ok=True)
    for one in DISMISSED:
        (store.folder / "texte" / f"{one['id']}.txt").write_text(AD_TEXT, encoding="utf-8")
    schreibe_yaml(daten / "firmen-ausgeschlossen.yaml", ["Ausgeschlossen AG"])
    for name in (URL_VARIABLE, ACCESS_VARIABLE):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(KEY_VARIABLE, "sk-test")
    return server


@pytest.fixture
def ai(monkeypatch):
    client = Client()
    monkeypatch.setattr(routes_ai, "new_client", lambda: client)
    return client


def profile_of(s) -> str:
    return (s.kontext.daten / search_plan.PROFILE).read_text(encoding="utf-8")


def propose(s) -> dict:
    status, answer = post(s, f"{ROUTE}/vorschlag", {})
    assert status == 200, answer
    return answer


def overview(s) -> dict:
    status, _, content = get(s, ROUTE)
    assert status == 200
    return json.loads(content)


# What goes to the AI


def test_only_title_company_place_and_workload_of_dismissed_hits_go_to_the_ai(job_search, ai):
    propose(job_search)
    [call] = ai.messages.calls
    assert set(call) == {"model", "max_tokens", "system", "messages", "output_config"}
    assert [part["text"] for part in call["system"]] == [exclusion_reasons.RULES + "\n\n", exclusion_reasons.INSTRUCTIONS]
    assert [message["role"] for message in call["messages"]] == ["user"]
    rows = sent_rows(call)
    assert {key for _, fields in rows for key in fields} == set(SENT_KEYS)
    sent = sorted(tuple(fields[key] for key in SENT_KEYS) for _, fields in rows)
    assert sent == sorted((h["stelle"], h["firma"], h["ort"], h["pensum"]) for h in DISMISSED)
    labels = call["output_config"]["format"]["schema"]["properties"]["proposals"]["items"]["properties"]["hits"]["items"]
    assert sorted(labels["enum"]) == sorted(label for label, _ in rows)


def _long_lines(path: pathlib.Path) -> list[str]:
    lines = (line.strip().lstrip("-#> ").strip() for line in path.read_text(encoding="utf-8").splitlines())
    return [line for line in lines if len(line) >= 25]


def test_nothing_about_the_person_goes_along(job_search, ai):
    daten = job_search.kontext.daten
    propose(job_search)
    sent = json.dumps(ai.messages.calls, ensure_ascii=False)
    files = [daten / "cv.yaml", daten / search_plan.PROFILE, daten / "anschreiben" / "stil.md",
             daten / "anschreiben" / "bausteine.md", daten / "bewerbungen" / BRIEF_ID / "anschreiben.yaml"]
    for path in files:
        for line in _long_lines(path):
            assert line not in sent, (path.name, line)
    for value in ("Erika", "erika@example.ch", "079 000 00 00", "Musterweg", "Bildung ohne IT-Bezug", "Kernliste",
                  "geheim-123", "Bewertungstext", AD_TEXT, "Petra"):
        assert value not in sent, value
    for other in NOT_SENT:
        assert other["stelle"] not in sent and other["firma"] not in sent, other["id"]


def test_a_hit_that_names_the_person_is_masked_like_every_request(job_search, ai):
    named = hit(10, "Web Entwickler Aussendienst", "Erika Beispiel Consulting", "Thun", "100%")
    Hits(job_search.kontext.daten)._write(DISMISSED + [named])
    propose(job_search)
    sent = json.dumps(ai.messages.calls, ensure_ascii=False)
    assert "Erika" not in sent and "{{NAME" in sent


# Proposals


def test_each_proposal_names_the_hits_it_rests_on_and_only_those_the_ai_got(job_search, ai):
    answer = propose(job_search)
    shown = [(p["art"], p["wert"], [t["id"] for t in p["treffer"]]) for p in answer["vorschlaege"]]
    assert shown == [("titel_ausschluss", "Aussendienst", [h["id"] for h in FIELD]),
                     ("ausschluss", "Detailhandel", [h["id"] for h in RETAIL])]
    first = answer["vorschlaege"][0]
    assert first["ort"] == "Im Titel" and first["grund"] == "Alle drei Stellen sind im Aussendienst."
    assert first["treffer"][0] == {"id": FIELD[0]["id"], "stelle": FIELD[0]["stelle"], "firma": FIELD[0]["firma"],
                                   "ort": FIELD[0]["ort"], "pensum": FIELD[0]["pensum"]}
    assert answer["vorschlaege"][1]["ort"] == "Im Inserat" and answer["vorschlaege"][1]["kategorie"] == "Branche"


@pytest.mark.parametrize("data", ["kein JSON", {"proposals": "keine Liste"}, {"anderes": []}])
def test_an_answer_that_does_not_fit_the_schema_changes_nothing(job_search, monkeypatch, data):
    client = Client()
    client.messages.create = lambda **payload: FakeMessages(reply=data).create(**payload)
    monkeypatch.setattr(routes_ai, "new_client", lambda: client)
    status, answer = post(job_search, f"{ROUTE}/vorschlag", {})
    assert status == 400 and answer["fehler"].startswith("Kein Vorschlag.")
    assert profile_of(job_search) == JOB


def test_odd_entries_of_an_answer_are_left_out():
    labelled = exclusion_reasons.labelled(DISMISSED)
    by_title = {one["stelle"]: label for label, one in labelled.items()}
    two = [by_title[h["stelle"]] for h in RETAIL]
    entries = [None, "Text", {"category": "unbekannt", "value": "Detailhandel", "reason": "", "hits": two},
               {"category": "branche", "value": 3, "reason": "", "hits": two},
               {"category": "branche", "value": "Detailhandel, Verkauf", "reason": 5, "hits": two},
               {"category": "branche", "value": "detailhandel", "reason": "Doppelt.", "hits": two}]
    frame = exclusion_reasons.Frame(positive=("Python",), titles=(), ads=(), chars=60)
    found = exclusion_reasons.cleaned({"proposals": entries}, labelled, frame)
    assert [(p.value, p.reason, p.ids) for p in found] == [("Detailhandel", "", tuple(h["id"] for h in RETAIL))]


def test_nothing_changes_until_the_person_adopts_a_proposal(job_search, ai):
    propose(job_search)
    path = job_search.kontext.daten / search_plan.PROFILE
    assert profile_of(job_search) == JOB
    assert job_search.kontext.ablage.liste(path) == []


def test_adopting_writes_the_entry_with_drafts_and_undo_takes_it_out(job_search, ai):
    path = job_search.kontext.daten / search_plan.PROFILE
    answer = propose(job_search)
    status, done = post(job_search, f"{ROUTE}/uebernehmen", {"vorschlag": answer["vorschlag"], "nummer": 1})
    assert status == 200 and (done["art"], done["wert"]) == ("ausschluss", "Detailhandel")
    assert search_frame.values(profile_of(job_search))["ausschluss"][-1] == "Detailhandel"
    assert search_frame.values(profile_of(job_search))["titel_ausschluss"] == list(search_plan.title_terms(JOB, "ausschluss"))
    contents = [job_search.kontext.ablage.inhalt(entry.id) for entry in job_search.kontext.ablage.liste(path)]
    assert JOB.encode("utf-8") in contents and path.read_bytes() in contents
    status, undone = post(job_search, f"{ROUTE}/rueckgaengig", {"art": done["art"], "wert": done["wert"]})
    assert status == 200 and "Detailhandel" not in undone["werte"]["ausschluss"]
    assert search_frame.values(profile_of(job_search)) == search_frame.values(JOB)


def test_a_title_word_goes_to_the_title_filter(job_search, ai):
    answer = propose(job_search)
    status, done = post(job_search, f"{ROUTE}/uebernehmen", {"vorschlag": answer["vorschlag"], "nummer": 0})
    assert status == 200 and done["art"] == "titel_ausschluss"
    assert search_plan.title_terms(profile_of(job_search), "ausschluss")[-1] == "Aussendienst"


@pytest.mark.parametrize("body_for", [
    lambda proposal: {}, lambda proposal: {"vorschlag": "unbekannt", "nummer": 0}, lambda proposal: {"nummer": 0},
    lambda proposal: {"vorschlag": proposal, "nummer": 5}, lambda proposal: {"vorschlag": proposal, "nummer": True},
    lambda proposal: {"vorschlag": proposal, "nummer": "0"}])
def test_only_a_proposal_the_app_made_can_be_adopted(job_search, ai, body_for):
    answer = propose(job_search)
    status, refused = post(job_search, f"{ROUTE}/uebernehmen", body_for(answer["vorschlag"]))
    assert status == 400 and refused["fehler"]
    assert profile_of(job_search) == JOB


# Before the run


def test_the_overview_names_count_and_cost_before_the_run_without_calling_the_ai(job_search, ai):
    found = overview(job_search)
    assert found["verfuegbar"] and found["anzahl"] == len(DISMISSED) and found["mindestens"] == 3
    assert found["kosten"] >= 0.01 and found["waehrung"] == "USD" and found["dauer_minuten"] == 1
    assert found["guthaben"] is None and found["reicht_fuer"] is None
    assert ai.messages.calls == []


def test_the_overview_names_what_the_profile_excludes_so_shown_proposals_follow_other_cards(job_search, ai):
    answer = propose(job_search)
    post(job_search, f"{ROUTE}/uebernehmen", {"vorschlag": answer["vorschlag"], "nummer": 1})
    found = overview(job_search)
    assert found["vorhanden"]["ausschluss"] == [*search_frame.values(JOB)["ausschluss"], "Detailhandel"]
    assert found["vorhanden"]["titel_ausschluss"] == list(search_plan.title_terms(JOB, "ausschluss"))


def test_the_overview_names_the_credit_of_the_code(job_search, ai, monkeypatch):
    monkeypatch.setattr(routes_rate_all, "credit_left", lambda: 0.0)
    found = overview(job_search)
    assert found["guthaben"] == 0 and found["danach"] == 0


def test_the_text_for_the_ai_can_be_read_before_and_is_not_sent(job_search, ai):
    status, _, content = get(job_search, f"{ROUTE}/text")
    text = json.loads(content)["text"]
    assert status == 200 and exclusion_reasons.INSTRUCTIONS in text and FIELD[0]["stelle"] in text
    assert "Erika" not in text and ai.messages.calls == []


def test_too_few_dismissed_hits_show_an_empty_state_and_never_call_the_ai(job_search, ai):
    Hits(job_search.kontext.daten)._write(FIELD[:2] + NOT_SENT)
    found = overview(job_search)
    assert found["verfuegbar"] and found["anzahl"] == 2 and "kosten" not in found
    assert found["vorhanden"] == {"titel_ausschluss": list(search_plan.title_terms(JOB, "ausschluss")),
                                  "ausschluss": search_frame.values(JOB)["ausschluss"]}
    status, answer = post(job_search, f"{ROUTE}/vorschlag", {})
    assert status == 400 and "3" in answer["fehler"]
    assert ai.messages.calls == []


def test_without_ai_set_up_the_page_is_told_to_open_the_setup(job_search, monkeypatch):
    monkeypatch.delenv(KEY_VARIABLE, raising=False)
    status, answer = post(job_search, f"{ROUTE}/vorschlag", {})
    assert status == 400 and answer["aktion"] == SETUP_ACTION
    assert profile_of(job_search) == JOB


def test_used_up_credit_says_a_new_code_can_be_requested(job_search, monkeypatch):
    refused = anthropic.APIStatusError("x", response=response(402), body=None)
    client = Client(error=refused)
    monkeypatch.setattr(routes_ai, "new_client", lambda: client)
    status, answer = post(job_search, f"{ROUTE}/vorschlag", {})
    assert status == 400 and CREDIT_USED in answer["fehler"] and "anfordern" in answer["fehler"]


def test_only_for_a_job_search(job_search, ai):
    (job_search.kontext.daten / search_plan.PROFILE).write_text(
        (VORLAGEN / "suchprofil-lehrstelle.md").read_text(encoding="utf-8"), encoding="utf-8")
    assert overview(job_search) == {"verfuegbar": False}
    status, answer = post(job_search, f"{ROUTE}/vorschlag", {})
    assert status == 400 and "Stellensuche" in answer["fehler"] and ai.messages.calls == []


def test_the_task_has_its_model_and_a_name_in_the_cost_log():
    assert tasks.MODELS[exclusion_reasons.TASK] and tasks.MAX_TOKENS[exclusion_reasons.TASK]
    labels = (PAGES / "einstellungen-logik.js").read_text(encoding="utf-8")
    assert f"{exclusion_reasons.TASK}: " in labels


# Reach and page


def test_neither_the_extension_nor_claude_reach_the_routes():
    for name in ("native_host.py", "mcp_tools.py"):
        assert ROUTE not in (ROOT / "desktop" / name).read_text(encoding="utf-8"), name


def test_the_proposals_sit_in_the_card_what_you_do_not_want_to_see(job_search):
    html = (PAGES / "suche-einstellen.html").read_text(encoding="utf-8")
    card = html[html.index('id="karte-nicht"'):html.index('id="karte-wo"')]
    assert 'id="ki-ausschluesse"' in card
    script = (PAGES / "ki-ausschluesse.js").read_text(encoding="utf-8")
    ids = set(re.findall(r'id="([^"]+)"', html))
    assert set(re.findall(r'\$\("([^"$]+)"\)', script)) - ids == set()
    for name in ("ki-ausschluesse-logik.js", "ki-ausschluesse.js"):
        assert f'<script src="/{name}"></script>' in html
        assert get(job_search, f"/{name}")[0] == 200, name
