"""The comparison of models and efforts for the search-term review (#274): what it sends, counts, prints and keeps."""
import json
import shutil

import pytest

import measure_terms
from ai import consent
from dateien import schreibe_yaml
from test_ai_tasks import FakeMessages, VORLAGEN
from test_optimize_terms import REPLY, sample_hits


class Client:
    """Answers like the API; one model may stop at max_tokens, as Haiku did before #274."""

    def __init__(self, cut_off: str | None = None):
        self.messages = self
        self.calls, self.cut_off = [], cut_off

    def create(self, **payload):
        self.calls.append(payload)
        stop = "max_tokens" if payload["model"] == self.cut_off else "end_turn"
        return FakeMessages(reply=REPLY, stop_reason=stop).create(**payload)


@pytest.fixture
def daten(datenordner):
    shutil.copy(VORLAGEN / "suchprofil.md", datenordner / "suchprofil.md")
    shutil.copytree(VORLAGEN / "anschreiben", datenordner / "anschreiben", dirs_exist_ok=True)
    schreibe_yaml(datenordner / "suche" / "treffer.yaml", sample_hits())
    return datenordner


@pytest.fixture
def ai(daten, monkeypatch):
    client = Client(cut_off="claude-haiku-5-5")
    monkeypatch.setattr(consent, "require", lambda *_: None)
    monkeypatch.setattr(measure_terms, "find_connection", lambda: None)
    monkeypatch.setattr(measure_terms, "make_client", lambda _: client)
    return client


def test_a_combination_is_model_and_effort():
    assert measure_terms.combination("claude-sonnet-5-5:medium") == ("claude-sonnet-5-5", "medium")
    for wrong in ("claude-sonnet-5-5", "claude-sonnet-5-5:sehr", "gpt:medium"):
        with pytest.raises(ValueError):
            measure_terms.combination(wrong)


def test_without_yes_only_the_plan_is_shown(daten, capsys, monkeypatch):
    monkeypatch.setattr(measure_terms, "make_client", lambda _: pytest.fail("no AI without --ja"))
    assert measure_terms.main([str(daten), "--runden", "2"]) == 0
    out = capsys.readouterr().out
    assert "--ja" in out and f"{2 * len(measure_terms.COMBINATIONS)} KI-Aufrufe" in out


def test_each_combination_is_sent_with_its_model_effort_and_room_to_think(daten, ai):
    found = measure_terms.measure(daten, [("claude-haiku-5-5", "high"), ("claude-sonnet-5-5", "low")], rounds=2,
                                  cost_limit=5)

    sent = [(call["model"], call["output_config"]["effort"]) for call in ai.calls]
    assert sent == [("claude-haiku-5-5", "high")] * 2 + [("claude-sonnet-5-5", "low")] * 2
    assert all(call["max_tokens"] == measure_terms.ROOM for call in ai.calls)
    haiku, sonnet = found.runs[:2], found.runs[2:]
    assert all(run.cut_off and run.proposal is None for run in haiku)
    assert all(run.kept == 3 and run.replaced == 1 and run.output_tokens == 800 for run in sonnet)


def test_it_stops_at_the_cost_limit_and_keeps_what_it_has(daten, ai):
    found = measure_terms.measure(daten, [("claude-sonnet-5-5", "medium")], rounds=5, cost_limit=0.000001)
    assert len(found.runs) == 1 and found.stopped == measure_terms.LIMIT_REACHED


def test_the_report_gives_numbers_per_combination_and_no_terms(daten, ai):
    found = measure_terms.measure(daten, [("claude-haiku-5-5", "medium"), ("claude-sonnet-5-5", "medium")], rounds=1,
                                  cost_limit=5)
    text = measure_terms.report(found)
    assert "claude-haiku-5-5 medium" in text and "abgebrochen 1 von 1" in text
    assert "claude-sonnet-5-5 medium" in text and "Änderungen 3.0" in text
    assert "Backend" not in text and "Verkauf" not in text, "terms of the person stay in the data folder"


def test_the_proposals_stay_in_the_data_folder_and_nothing_else_changes(daten, ai, capsys):
    before = (daten / "suchprofil.md").read_text(encoding="utf-8")
    assert measure_terms.main([str(daten), "--modell", "claude-sonnet-5-5:medium", "--runden", "1", "--ja"]) == 0
    saved = sorted((daten / ".ki").glob("begriffsmessung-*.json"))
    assert len(saved) == 1
    runs = json.loads(saved[0].read_text(encoding="utf-8"))["laeufe"]
    assert runs[0]["modell"] == "claude-sonnet-5-5"
    assert ["Backend", "Frontend"] in [change["add"] for change in runs[0]["vorschlag"]["changes"]]
    assert (daten / "suchprofil.md").read_text(encoding="utf-8") == before
    assert str(saved[0]) in capsys.readouterr().out
