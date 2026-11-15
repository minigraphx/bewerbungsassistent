"""Saving „Was Sie nicht sehen wollen“ on Suche einstellen (#303, G65): profile and company list together or neither.

Only invented companies and terms. A refusal names the part that could not be saved and leaves both files as they were.
"""
import pathlib

import pytest
import yaml

import excluded_companies
from test_ai_tasks import VORLAGEN
from test_app import post, server  # noqa: F401  (server is a fixture)

ROUTE = "/api/suche/was-nicht"
JOB = (VORLAGEN / "suchprofil.md").read_text(encoding="utf-8")
APPRENTICESHIP = (VORLAGEN / "suchprofil-lehrstelle.md").read_text(encoding="utf-8")


def setup(s, profile: str, companies: list[str]) -> tuple[pathlib.Path, pathlib.Path]:
    path = s.kontext.daten / "suchprofil.md"
    path.write_text(profile, encoding="utf-8")
    listed = s.kontext.daten / excluded_companies.FILE
    listed.write_text(yaml.safe_dump(companies, allow_unicode=True), encoding="utf-8")
    return path, listed


def stored(listed: pathlib.Path) -> list[str]:
    return yaml.safe_load(listed.read_text(encoding="utf-8"))


def test_profile_and_companies_are_saved_in_one_request(server):  # noqa: F811
    path, listed = setup(server, JOB, ["Muster Bau AG"])

    status, answer = post(server, ROUTE, {"ausschluss": ["Schicht"], "titel_ausschluss": ["Praktikum"],
                                          "firmen": ["Beispiel Holz GmbH"]})

    assert status == 200, answer
    assert "Schicht" in path.read_text(encoding="utf-8") and "- Ausschluss: Praktikum" in path.read_text(encoding="utf-8")
    assert stored(listed) == ["Beispiel Holz GmbH"]
    assert [entry["name"] for entry in answer["firmen"]] == ["Beispiel Holz GmbH"]
    assert answer["werte"]["titel_ausschluss"] == ["Praktikum"]


def test_a_refused_company_leaves_the_profile_as_it_was_and_says_so(server):  # noqa: F811
    path, listed = setup(server, JOB, ["Muster Bau AG"])

    status, answer = post(server, ROUTE, {"ausschluss": ["Schicht"], "titel_ausschluss": [], "firmen": ["AG"]})

    assert status == 400
    assert answer["fehler"].startswith("Firmen:"), answer
    assert "Inserat und Titel bleiben wie vorher" in answer["fehler"]
    assert path.read_text(encoding="utf-8") == JOB
    assert stored(listed) == ["Muster Bau AG"]


def test_a_refused_profile_value_leaves_the_companies_as_they_were_and_says_so(server):  # noqa: F811
    path, listed = setup(server, JOB, ["Muster Bau AG"])
    too_many = [f"Begriff {n}" for n in range(40)]

    status, answer = post(server, ROUTE, {"ausschluss": too_many, "titel_ausschluss": [], "firmen": ["Beispiel Holz"]})

    assert status == 400
    assert answer["fehler"].startswith("Inserat und Titel:"), answer
    assert "Die Firmen bleiben wie vorher" in answer["fehler"]
    assert path.read_text(encoding="utf-8") == JOB
    assert stored(listed) == ["Muster Bau AG"]


def test_when_the_companies_cannot_be_written_the_profile_goes_back(server, monkeypatch):  # noqa: F811
    path, listed = setup(server, JOB, ["Muster Bau AG"])

    def broken(*_):
        raise OSError("Datenträger voll")
    monkeypatch.setattr(excluded_companies, "schreibe_yaml", broken)

    status, answer = post(server, ROUTE, {"ausschluss": ["Schicht"], "titel_ausschluss": [], "firmen": ["Beispiel Holz"]})

    assert status == 500, answer
    assert path.read_text(encoding="utf-8") == JOB
    assert stored(listed) == ["Muster Bau AG"]


def test_when_the_profile_cannot_go_back_the_message_names_the_part_not_saved(server, monkeypatch):  # noqa: F811
    import routes_frame
    path, listed = setup(server, JOB, ["Muster Bau AG"])
    written = []

    def first_only(target, content):
        if written:
            raise OSError("Datenträger voll")
        written.append(content)
        target.write_bytes(content)
    monkeypatch.setattr(routes_frame, "schreibe_atomar", first_only)
    monkeypatch.setattr(excluded_companies, "schreibe_yaml", lambda *_: (_ for _ in ()).throw(OSError("voll")))

    status, answer = post(server, ROUTE, {"ausschluss": ["Schicht"], "titel_ausschluss": [], "firmen": ["Beispiel Holz"]})

    assert status == 400
    assert "Die Firmen sind nicht gespeichert" in answer["fehler"], answer
    assert "Inserat und Titel sind gespeichert" in answer["fehler"]
    assert stored(listed) == ["Muster Bau AG"]


def test_an_apprenticeship_saves_only_the_companies(server):  # noqa: F811
    path, listed = setup(server, APPRENTICESHIP, [])

    status, answer = post(server, ROUTE, {"firmen": ["Muster Schreinerei"]})

    assert status == 200, answer
    assert path.read_text(encoding="utf-8") == APPRENTICESHIP
    assert stored(listed) == ["Muster Schreinerei"]


@pytest.mark.parametrize("body", [{"ausschluss": ["Schicht"]}, {"firmen": "Muster Bau"}, []])
def test_odd_bodies_change_nothing(server, body):  # noqa: F811
    path, listed = setup(server, JOB, ["Muster Bau AG"])

    assert post(server, ROUTE, body)[0] == 400
    assert path.read_text(encoding="utf-8") == JOB
    assert stored(listed) == ["Muster Bau AG"]


def test_neither_the_extension_nor_claude_reach_the_route():
    desktop = pathlib.Path(__file__).resolve().parents[2] / "desktop"
    for name in ("native_host.py", "mcp_tools.py"):
        assert ROUTE not in (desktop / name).read_text(encoding="utf-8"), name
