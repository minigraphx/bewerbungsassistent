"""The AI suggests stations, order and summary for „Lebenslauf erstellen“ (#293, G75); invented data only.

Only the ad, the chosen stations of Meine Angaben and the sentences of its summary go to the AI, each station and
sentence with a label that is new for every request. The answer names labels only, so a suggestion can leave out,
move up and shorten, never add: a recommendation that names anything this request did not send is dropped whole.
The AI is simulated; nothing goes to the network.
"""
import json
import re

import pytest
import yaml

import routes_ai
from ai import cv_suggestions
from ai.connection import ACCESS_VARIABLE, KEY_VARIABLE, URL_VARIABLE
from ai.errors import SETUP_ACTION
from register import Register
from sample_folder import BRIEF_ID
from test_ai_tasks import FakeMessages
from test_app import get, post, server  # noqa: F401  (server is a fixture)

ROUTE = "/api/lebenslauf/erstellen"
AD = ("Stelle: Data Engineer\nFirma: Beispiel AG\n\nWir suchen eine Person für Datenpipelines mit Airflow und SQL. "
      "Kontakt: Frau Petra Beispielfrau, petra@example.ch")
FIRST = "Software-Entwicklerin mit zehn Jahren Praxis in Python und TypeScript."
SECOND = "Baut Webanwendungen und Datenpipelines und gibt ihr Wissen in internen Schulungen weiter."
STATION = re.compile(r"^(S\d+-[0-9a-f]{4}): (.*)$")
SENTENCE = re.compile(r"^(K\d+-[0-9a-f]{4}): (.*)$")

# The AI names stations by their title and sentences by their text here; LabelledMessages turns them into the labels
# of the request it got. Anything it cannot find stays as it is: a label of no station or sentence.
REPLY = [
    {"reason": "Das Inserat verlangt Datenpipelines.", "leave_out": ["Kleines Spiel in Godot"],
     "move_up": ["datenatlas"], "summary": []},
    {"reason": "Die Stelle ist keine Webstelle.", "leave_out": ["Junior-Entwicklerin"], "move_up": [],
     "summary": [SECOND, FIRST]},
]
INVENTED = {"reason": "Erfundene Station.", "leave_out": ["kurs-tools"], "move_up": ["S9-dead"], "summary": []}


def payload_lines(payload: dict, pattern: re.Pattern) -> dict[str, str]:
    content = payload["messages"][0]["content"]
    return {found.group(2): found.group(1) for line in content.split("\n") if (found := pattern.match(line))}


def station_titles(payload: dict) -> dict[str, str]:
    """title → label; a station line is „label: section · title · place · time“."""
    return {line.split(" · ")[1]: label for line, label in payload_lines(payload, STATION).items()}


class LabelledMessages(FakeMessages):
    def __init__(self, recommendations=None, **kwargs):
        super().__init__(**kwargs)
        self.recommendations = REPLY if recommendations is None else recommendations

    def create(self, **payload):
        titles, sentences = station_titles(payload), payload_lines(payload, SENTENCE)

        def labels(names, known):
            return [known.get(name, name) for name in names]

        self.reply = {"recommendations": [
            {**r, "leave_out": labels(r["leave_out"], titles), "move_up": labels(r["move_up"], titles),
             "summary": labels(r["summary"], sentences)} for r in self.recommendations]}
        return super().create(**payload)


class Client:
    def __init__(self, **kwargs):
        self.messages = LabelledMessages(**kwargs)


@pytest.fixture
def with_ad(server):  # noqa: F811
    (server.kontext.daten / "bewerbungen" / BRIEF_ID / "stelle.md").write_text(AD, encoding="utf-8")
    return server


@pytest.fixture
def connected(monkeypatch):
    for name in (URL_VARIABLE, ACCESS_VARIABLE):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(KEY_VARIABLE, "sk-test")


@pytest.fixture
def ai(monkeypatch, connected):
    client = Client()
    monkeypatch.setattr(routes_ai, "new_client", lambda: client)
    return client


def form(s) -> dict:
    status, _, body = get(s, ROUTE, id=BRIEF_ID)
    assert status == 200, body
    return json.loads(body)


def suggest(s, stand: str | None = None) -> dict:
    status, answer = post(s, f"{ROUTE}/vorschlag", {"id": BRIEF_ID, "stand": stand or form(s)["stand"]})
    assert status == 200, answer
    return answer


def station_index(s, section: str, title: str) -> int:
    rows = next(part for part in form(s)["abschnitte"] if part["abschnitt"] == section)["stationen"]
    return next(row["index"] for row in rows if row["titel"] == title)


# What goes to the AI


def test_only_the_ad_the_chosen_stations_and_the_summary_sentences_go_to_the_ai(with_ad, ai):
    suggest(with_ad)

    [call] = ai.messages.calls
    assert [part["text"] for part in call["system"]] == [cv_suggestions.RULES + "\n\n", cv_suggestions.INSTRUCTIONS]
    content = call["messages"][0]["content"]
    assert "Wir suchen eine Person für Datenpipelines mit Airflow und SQL." in content
    titles = station_titles(call)
    assert set(titles) == {"Software-Entwicklerin", "Junior-Entwicklerin", "Bachelor Informatik",
                           "Kursleiterin Programmieren", "datenatlas", "kurs-tools", "Kleines Spiel in Godot",
                           "Machine Learning Grundlagen"}
    assert "  - Aufbau von Datenpipelines mit Airflow" in content
    assert set(payload_lines(call, SENTENCE)) == {FIRST, SECOND}
    items = call["output_config"]["format"]["schema"]["properties"]["recommendations"]["items"]["properties"]
    assert sorted(items["leave_out"]["items"]["enum"]) == sorted(titles.values())
    assert sorted(items["summary"]["items"]["enum"]) == sorted(payload_lines(call, SENTENCE).values())


def test_nothing_else_about_the_person_goes_along(with_ad, ai):
    suggest(with_ad)

    sent = json.dumps(ai.messages.calls, ensure_ascii=False)
    for value in ("Erika", "erika@example.ch", "079 000 00 00", "Musterweg", "www.example.ch", "github.com",
                  "Web und Daten", "Muttersprache", "Wandern", "pandas", "Vue.js, Django",
                  "Petra", "petra@example.ch"):
        assert value not in sent, value
    daten = with_ad.kontext.daten
    letter = yaml.safe_load((daten / "bewerbungen" / BRIEF_ID / "anschreiben.yaml").read_text(encoding="utf-8"))
    assert letter["text"].strip().split("\n")[0][:40] not in sent


def test_a_station_left_out_by_the_person_is_not_sent(with_ad, ai):
    chosen = {"work": [0], "projects": [0], "education": [], "teaching": [], "certificates": []}
    status, _ = post(with_ad, ROUTE, {"id": BRIEF_ID, "stand": form(with_ad)["stand"], "stationen": chosen,
                                      "design": "zweispaltig"})
    assert status == 200

    suggest(with_ad)

    assert set(station_titles(ai.messages.calls[0])) == {"Software-Entwicklerin", "datenatlas"}


# The suggestion


def test_each_recommendation_bundles_its_changes_with_a_reason_and_the_app_names_them(with_ad, ai):
    answer = suggest(with_ad)

    first, second = answer["empfehlungen"]
    godot, atlas = station_index(with_ad, "projects", "Kleines Spiel in Godot"), station_index(with_ad, "projects", "datenatlas")
    assert first["weglassen"] == [{"abschnitt": "projects", "index": godot}]
    assert first["voran"] == [{"abschnitt": "projects", "index": atlas}]
    assert first["kurzprofil"] is None
    assert first["grund"] == "Das Inserat verlangt Datenpipelines."
    assert first["was"] == "«Kleines Spiel in Godot» weglassen, «datenatlas» nach vorne"
    assert second["weglassen"] == [{"abschnitt": "work", "index": 1}]
    assert second["kurzprofil"] == f"{SECOND} {FIRST}"
    assert second["was"] == "«Junior-Entwicklerin, Muster GmbH» weglassen, Kurzprofil umgestellt"
    assert [r["nummer"] for r in answer["empfehlungen"]] == [0, 1]


def test_a_recommendation_with_a_station_that_does_not_exist_is_dropped_whole(with_ad, monkeypatch, connected):
    client = Client(recommendations=[INVENTED, *REPLY])
    monkeypatch.setattr(routes_ai, "new_client", lambda: client)

    answer = suggest(with_ad)

    assert [r["grund"] for r in answer["empfehlungen"]] == [r["reason"] for r in REPLY]
    assert "S9-dead" not in json.dumps(answer, ensure_ascii=False)


def test_an_invented_answer_keeps_only_what_meine_angaben_has():
    """Fed straight to the check in code, not left to the schema of the request."""
    labels = cv_suggestions.Labels(
        stations={"S1-aaaa": ("work", 0), "S2-bbbb": ("work", 1)}, sentences={"K1-cccc": FIRST, "K2-dddd": SECOND})
    answer = {"recommendations": [
        {"reason": "Station gibt es nicht.", "leave_out": ["S1-aaaa"], "move_up": ["S7-eeee"], "summary": []},
        {"reason": "Satz gibt es nicht.", "leave_out": [], "move_up": [], "summary": ["K2-dddd", "K9-ffff"]},
        {"reason": "Freier Text statt Kennung.", "leave_out": [], "move_up": [],
         "summary": ["Erfahrene Teamleiterin mit Budgetverantwortung."]},
        {"reason": "Weglassen und vorne zugleich.", "leave_out": ["S2-bbbb"], "move_up": ["S2-bbbb"], "summary": []},
        {"reason": "Gilt.", "leave_out": ["S2-bbbb"], "move_up": [], "summary": ["K1-cccc"]},
    ]}

    kept = cv_suggestions.cleaned(answer, labels)

    assert [r.reason for r in kept] == ["Gilt."]
    assert kept[0].leave_out == (("work", 1),) and kept[0].summary == FIRST


def test_at_most_five_recommendations_and_none_touches_what_an_earlier_one_changes():
    labels = cv_suggestions.Labels(stations={f"S{n}-aaaa": ("projects", n) for n in range(8)},
                                   sentences={"K1-cccc": FIRST, "K2-dddd": SECOND})
    answer = {"recommendations": [
        {"reason": f"Grund {n}", "leave_out": [f"S{n}-aaaa"], "move_up": [], "summary": []} for n in range(7)
    ] + [{"reason": "Schon weggelassen.", "leave_out": [], "move_up": ["S0-aaaa"], "summary": []}]}

    kept = cv_suggestions.cleaned(answer, labels)

    assert [r.reason for r in kept] == [f"Grund {n}" for n in range(5)]


def test_never_every_station_is_left_out_and_an_empty_recommendation_is_dropped():
    labels = cv_suggestions.Labels(stations={"S1-aaaa": ("work", 0), "S2-bbbb": ("work", 1)}, sentences={})
    answer = {"recommendations": [
        {"reason": "Eine weg.", "leave_out": ["S1-aaaa"], "move_up": [], "summary": []},
        {"reason": "Die letzte auch.", "leave_out": ["S2-bbbb"], "move_up": [], "summary": []},
        {"reason": "Nichts zu tun.", "leave_out": [], "move_up": [], "summary": []},
        {"reason": "", "leave_out": [], "move_up": ["S2-bbbb"], "summary": []},
    ]}

    assert [r.reason for r in cv_suggestions.cleaned(answer, labels)] == ["Eine weg."]


def test_the_summary_in_its_order_is_no_change():
    labels = cv_suggestions.Labels(stations={"S1-aaaa": ("work", 0)}, sentences={"K1-cccc": FIRST, "K2-dddd": SECOND})
    answer = {"recommendations": [{"reason": "Wie vorher.", "leave_out": [], "move_up": [],
                                   "summary": ["K1-cccc", "K2-dddd"]}]}

    assert cv_suggestions.cleaned(answer, labels) == ()


def test_a_suggestion_writes_nothing(with_ad, ai):
    daten = with_ad.kontext.daten
    before = {path: path.read_bytes() for path in daten.rglob("*") if path.is_file()}

    suggest(with_ad)

    after = {path: path.read_bytes() for path in daten.rglob("*") if path.is_file() and ".ki" not in path.parts}
    assert {path: content for path, content in after.items() if before.get(path) != content} == {}


def test_opening_again_with_the_same_angaben_and_ad_does_not_ask_the_ai_again(with_ad, ai):
    first = suggest(with_ad)
    again = suggest(with_ad)

    assert len(ai.messages.calls) == 1
    assert again["empfehlungen"] == first["empfehlungen"]


# When there is no suggestion


def test_the_form_says_whether_the_ai_can_suggest(with_ad, connected):
    assert form(with_ad)["ki"] == "bereit"


def test_without_ai_the_form_says_so_and_the_panel_works_as_today(with_ad, monkeypatch):
    for name in (URL_VARIABLE, ACCESS_VARIABLE, KEY_VARIABLE):
        monkeypatch.delenv(name, raising=False)
    called = []
    monkeypatch.setattr(routes_ai, "new_client", lambda: called.append(1))

    answer = form(with_ad)
    status, saved = post(with_ad, ROUTE, {"id": BRIEF_ID, "stand": answer["stand"], "stationen": {"work": [0]},
                                          "design": "zweispaltig"})

    assert answer["ki"] == "aus"
    assert status == 200 and saved["variante"]["id"] == BRIEF_ID
    assert called == []


def test_asking_without_ai_set_up_opens_the_window_ki_einrichten(with_ad, monkeypatch):
    for name in (URL_VARIABLE, ACCESS_VARIABLE, KEY_VARIABLE):
        monkeypatch.delenv(name, raising=False)

    status, answer = post(with_ad, f"{ROUTE}/vorschlag", {"id": BRIEF_ID, "stand": form(with_ad)["stand"]})

    assert status == 400 and answer["aktion"] == SETUP_ACTION


def test_without_an_ad_there_is_nothing_to_suggest(server, ai):  # noqa: F811
    assert form(server)["ki"] == "ohne_inserat"
    status, answer = post(server, f"{ROUTE}/vorschlag", {"id": BRIEF_ID, "stand": form(server)["stand"]})

    assert status == 400 and "Stellentext" in answer["fehler"]
    assert ai.messages.calls == []


def test_changed_angaben_or_a_sent_application_get_no_suggestion(with_ad, ai):
    status, answer = post(with_ad, f"{ROUTE}/vorschlag", {"id": BRIEF_ID, "stand": "alt"})
    assert status == 400 and "geändert" in answer["fehler"]

    register = Register(with_ad.kontext.daten)
    register.speichere({**register.hole(BRIEF_ID), "versand": {"datum": "2026-10-26", "art": "elektronisch"}})
    status, _ = post(with_ad, f"{ROUTE}/vorschlag", {"id": BRIEF_ID, "stand": form(with_ad)["stand"]})
    assert status == 400
    assert ai.messages.calls == []


def test_the_text_for_the_ai_can_be_read_without_sending_it(with_ad, ai):
    status, _, body = get(with_ad, f"{ROUTE}/text", id=BRIEF_ID)

    assert status == 200
    text = json.loads(body)["text"]
    assert text.startswith(cv_suggestions.RULES) and "datenatlas" in text and FIRST in text
    assert "petra@example.ch" not in text
    assert ai.messages.calls == []
