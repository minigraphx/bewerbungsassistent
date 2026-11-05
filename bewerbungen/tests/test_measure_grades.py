"""The measurement of how much the AI's grade varies (MIN-389): what it rates, what it prints, what it leaves alone."""
import json
import re
import shutil

import pytest

import measure_grades
from ai import errors
from hits import Hits
from test_ai_tasks import FakeClient, VORLAGEN, gateway_for, rating_entry

RATE_REPLY = {"grade": 4, "summary": "Passt.", "fits": [], "hooks": [], "new_gaps": [], "suspicious_lines": []}


class Measured:
    """Answers one by one or as a package, with grades from a list."""

    def __init__(self, single=(4,), package=(5,), fail_at=None):
        self.messages = self
        self.calls, self.single, self.package, self.fail_at = [], list(single), list(package), fail_at

    def create(self, **payload):
        self.calls.append(payload)
        if self.fail_at == len(self.calls):
            raise errors.AiError("Budget aufgebraucht.")
        labels = re.findall(r'kennung="([^"]+)"', payload["messages"][0]["content"])
        if labels:
            grade = self.package[(len(self.calls) - 1) % len(self.package)]
            return FakeClient(reply={"ratings": [rating_entry(label, grade) for label in labels]}).messages.create(**payload)
        grade = self.single[(len(self.calls) - 1) % len(self.single)]
        return FakeClient(reply={**RATE_REPLY, "grade": grade}).messages.create(**payload)


@pytest.fixture
def daten(datenordner):
    shutil.copy(VORLAGEN / "suchprofil.md", datenordner / "suchprofil.md")
    shutil.copytree(VORLAGEN / "anschreiben", datenordner / "anschreiben", dirs_exist_ok=True)
    return datenordner


def with_hits(daten, grades):
    store = Hits(daten)
    (store.folder).mkdir(parents=True, exist_ok=True)
    hits = [{"id": f"job-{n}", "firma": f"Firma {n}", "stelle": "Rolle", "portal": "x", "link": f"https://example.ch/{n}",
             **({"bewertung": {"note": grade}} if grade else {})} for n, grade in enumerate(grades)]
    store._write(hits)
    for hit in hits:
        path = store._text_path(hit["id"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"Inserat {hit['id']}", encoding="utf-8")
    return store


def test_the_choice_spreads_over_the_grades_and_needs_a_text(daten):
    store = with_hits(daten, [1, 2, 3, 4, 5, 6, None])
    store._text_path("job-0").unlink()

    chosen = measure_grades.choose(store, count=3)

    assert len(chosen) == 3
    assert "job-0" not in chosen and "job-6" not in chosen
    assert "job-1" in chosen and "job-5" in chosen


def test_a_named_ad_is_always_measured(daten):
    store = with_hits(daten, [3, 3, 3, 3])
    store.update("job-2", bewerbung_id="meine-bewerbung")

    assert measure_grades.choose(store, count=1, wanted=["meine-bewerbung"]) == ["job-2"]


def test_an_unknown_named_ad_is_refused(daten):
    with pytest.raises(ValueError, match="gibt-es-nicht"):
        measure_grades.choose(with_hits(daten, [3]), count=1, wanted=["gibt-es-nicht"])


def test_it_rates_one_by_one_and_in_packages_and_keeps_both_apart(daten):
    store = with_hits(daten, [3, 4])
    client = Measured(single=(3, 4), package=(5,))
    gateway, material = gateway_for(daten, client)

    found = measure_grades.measure(gateway, material, store, ["job-0", "job-1"], rounds=2, cost_limit=100)

    assert len(client.calls) == 2 * 2 + 2
    assert set(found.single) == {"job-0", "job-1"} and all(len(v) == 2 for v in found.single.values())
    assert all(v == [5, 5] for v in found.package.values())
    assert found.stopped == ""


def test_a_package_changes_its_order_between_rounds(daten):
    store = with_hits(daten, [3, 3, 3, 3, 3, 3, 3, 3])
    client = Measured()
    gateway, material = gateway_for(daten, client)
    ids = [f"job-{n}" for n in range(8)]

    measure_grades.measure(gateway, material, store, ids, rounds=4, cost_limit=100)

    orders = {tuple(re.findall(r"Inserat (job-\d)", c["messages"][0]["content"]))
              for c in client.calls if "kennung=" in c["messages"][0]["content"]}
    assert len(orders) > 1


def test_it_stops_at_the_cost_limit_and_keeps_what_it_has(daten):
    store = with_hits(daten, [3, 3])
    client = Measured()
    gateway, material = gateway_for(daten, client)

    found = measure_grades.measure(gateway, material, store, ["job-0", "job-1"], rounds=3, cost_limit=0.000001)

    assert len(client.calls) == 1 and found.stopped == measure_grades.LIMIT_REACHED


def test_an_error_stops_the_run_and_keeps_what_it_has(daten):
    store = with_hits(daten, [3, 3])
    gateway, material = gateway_for(daten, Measured(fail_at=2))

    found = measure_grades.measure(gateway, material, store, ["job-0", "job-1"], rounds=3, cost_limit=100)

    assert "Budget" in found.stopped and sum(len(v) for v in found.single.values()) == 1


def test_the_measurement_leaves_hits_and_register_alone(daten):
    store = with_hits(daten, [3, 4])
    before = (store.folder / "treffer.yaml").read_bytes()
    gateway, material = gateway_for(daten, Measured(single=(1,), package=(1,)))

    measure_grades.measure(gateway, material, store, ["job-0", "job-1"], rounds=1, cost_limit=100)

    assert (store.folder / "treffer.yaml").read_bytes() == before


def test_the_report_names_no_company_and_gives_the_numbers():
    found = measure_grades.Measurement(single={"firma-x": [3.5, 4.5], "firma-y": [4, 4]},
                                       package={"firma-x": [4.5, 4.5], "firma-y": [5, 4]}, cost_usd=1.25, stopped="")

    report = measure_grades.report(found, {"firma-x": 4.5, "firma-y": None})

    assert "firma" not in report
    assert "A" in report and "3.5 4.5" in report
    assert "Grösste Spanne einzeln: 1.0" in report
    assert "Einzeln ab 1 Note Spanne: 1 von 2" in report
    assert "Paket minus einzeln im Schnitt: +0.50" in report
    assert "1.25 USD" in report


def test_without_consent_only_the_plan_is_shown(daten, capsys, monkeypatch):
    with_hits(daten, [3, 4])
    monkeypatch.setattr(measure_grades, "make_client", lambda _: pytest.fail("no AI without consent"))

    assert measure_grades.main([str(daten), "--anzahl", "2", "--runden", "2"]) == 0

    out = capsys.readouterr().out
    assert "2 Inserate" in out and "--ja" in out and "Firma" not in out


def test_the_result_with_ids_stays_in_the_data_folder(daten, capsys, monkeypatch):
    with_hits(daten, [3, 4])
    monkeypatch.setattr(measure_grades, "find_connection", lambda: None)
    monkeypatch.setattr(measure_grades, "make_client", lambda _: Measured())

    assert measure_grades.main([str(daten), "--anzahl", "2", "--runden", "1", "--ja"]) == 0

    saved = list((daten / ".ki").glob("notenmessung-*.json"))
    assert len(saved) == 1 and "job-0" in json.loads(saved[0].read_text(encoding="utf-8"))["einzeln"]
    assert "job-0" not in capsys.readouterr().out
