"""Cut with one click or allow three pages, for this application only (G92, #323).

When tightening is not enough, the check names how many lines are over and offers the cuts of lebenslauf/cuts.py to
tick, with «Drei Seiten erlauben»; there is no «So lassen» for the CV. What the person chooses lives in
bewerbungen/<id>/kuerzungen.yaml and goes over the chosen variant or the base CV at each build, never into Meine Angaben
or a variant. The step Lebenslauf lists what is left out, with «Zurückholen». All data is invented.
"""
import datetime
import json
import pathlib
import types

import pytest
import yaml

import build
import cut_choice
import cv_cuts
import layout_check
import page_limit
import pdf_boxes
import pruefung
import routes_apply
import unterlagen
from register import Register
from sample_folder import BRIEF_ID
from test_app import get, post, server  # noqa: F401  (server is a fixture)

TODAY = datetime.date(2026, 10, 25)
FIRST_CUT = "1 Stichpunkt bei «Software-Entwicklerin, Beispiel AG» (2019–heute)"
DESKTOP = pathlib.Path(__file__).resolve().parents[2] / "desktop"


@pytest.fixture
def three_pages(monkeypatch):
    """The built CV measures three pages and about seven lines too many, whatever is built."""
    pages = {"lebenslauf.pdf": 3}
    monkeypatch.setattr(pruefung, "_seiten", lambda pdf: ["Text " * 100] * pages.get(pdf.name, 1))
    monkeypatch.setattr(layout_check, "lines_beyond", lambda pdf, limit: 7)
    return pages


def _over(findings):
    return [f for f in findings if f.kuerzen]


def _built(folder, tmp_path, entry=None):
    entry = entry or Register(folder).hole(BRIEF_ID)
    unterlagen.baue(folder, entry, tmp_path / "build")
    return entry


# The finding


def test_the_lines_over_are_the_content_lines_on_the_pages_beyond_the_limit(tmp_path):
    cv = yaml.safe_load((build.ROOT / "data" / "beispiel.yaml").read_text(encoding="utf-8"))
    cv["work"] += [{"position": f"Sachbearbeiterin {n}", "name": f"Muster {n} AG", "startDate": f"{1990 + n}-01",
                    "endDate": f"{1991 + n}-12", "highlights": [f"Auswertung {n}.{k} für das Team" for k in range(4)]}
                   for n in range(16)]
    (tmp_path / "cv.yaml").write_text(yaml.safe_dump(cv, allow_unicode=True), encoding="utf-8")
    pdf = build.main([str(tmp_path / "cv.yaml"), "--lebenslauf-seiten", "3", "--build-dir", str(tmp_path / "b"),
                      "-o", str(tmp_path / "cv.pdf")])
    pages = len(pdf_boxes.read(pdf))
    assert pages == 3, "the sample needs a third page"

    # lines alike but for their digits are content, not a running header: the type area tells them apart
    third = [box for page in pdf_boxes.read(pdf) if page.number == 3 for box in page.text
             if box.text.startswith("Auswertung")]
    assert len(third) >= 5, "the sample needs list lines on the third page"
    assert layout_check.lines_beyond(pdf, 2) >= len(third)
    assert layout_check.lines_beyond(pdf, 3) == 0


def test_the_check_names_the_lines_over_and_offers_the_cuts_with_three_pages(datenordner, tmp_path, three_pages):
    entry = _built(datenordner, tmp_path)

    found = _over(pruefung.pruefe(datenordner, entry, TODAY))

    assert len(found) == 1
    finding = found[0]
    assert finding.text == "Lebenslauf: 3 Seiten, erlaubt sind höchstens 2. Auch enger gesetzt sind es etwa 7 Zeilen zu viel."
    assert finding.kuerzen["zeilen"] == 7
    assert finding.kuerzen["optionen"][0]["text"] == FIRST_CUT
    assert "Abschnitt «Interessen»" in [o["text"] for o in finding.kuerzen["optionen"]]
    assert finding.kuerzen["drei_seiten"] is True
    assert "So lassen" not in finding.text and "Einstellungen" not in finding.text


def test_the_cv_finding_cannot_be_confirmed_with_so_lassen(server, three_pages, monkeypatch):  # noqa: F811
    monkeypatch.setattr(routes_apply.apply, "blocker", lambda daten, entry: None)  # link, approval: all else is fine
    monkeypatch.setattr(pruefung, "pruefe_anschreiben_text", lambda *args, **kwargs: [])  # the faked pages are no letter
    folder = server.kontext.daten
    entry = Register(folder).hole(BRIEF_ID)
    unterlagen.baue(folder, entry, server.kontext.build)
    finding = _over(pruefung.pruefe(folder, entry, TODAY))[0]

    status, answer = post(server, "/api/pruefung/bestaetigen", {"id": BRIEF_ID, "schluessel": finding.schluessel})

    assert status == 400 and "nicht mehr" in answer["fehler"]
    problem = routes_apply._problem(server.kontext, entry)
    assert problem.startswith("Prüfung: Lebenslauf: 3 Seiten") and "So lassen" not in problem
    assert routes_apply.CUT_FIRST in problem


def test_the_last_page_fill_of_a_cv_being_cut_waits_until_three_pages_are_allowed(datenordner, tmp_path, three_pages,
                                                                                  monkeypatch):
    fill = layout_check.Breach(3, "fuellung", "nur zu 27 % gefüllt, verlangt ist mindestens ein Drittel.")
    monkeypatch.setattr(layout_check, "check", lambda pdf, part, headings=(): [fill] if part == "lebenslauf" else [])
    entry = _built(datenordner, tmp_path)
    page_three = "Lebenslauf, Seite 3: nur zu 27 %"

    being_cut = [f.text for f in pruefung.pruefe(datenordner, entry, TODAY)]
    cut_choice.store_choice(datenordner, entry, [], True)
    three_allowed = [f.text for f in pruefung.pruefe(datenordner, entry, TODAY)]

    assert not any(text.startswith(page_three) for text in being_cut), "the page being cut asks for no «So lassen»"
    assert any(text.startswith(page_three) for text in three_allowed)


def test_a_dossier_gets_the_same_finding(datenordner, tmp_path, three_pages):
    register = Register(datenordner)
    register.speichere({**register.hole(BRIEF_ID), "unterlagen": "dossier"})

    entry = _built(datenordner, tmp_path)

    assert _over(pruefung.pruefe(datenordner, entry, TODAY))[0].kuerzen["optionen"][0]["text"] == FIRST_CUT


def test_an_own_pdf_gets_no_cuts(datenordner, tmp_path, three_pages):
    (datenordner / "dokumente").mkdir()
    (datenordner / unterlagen.OWN_CV).write_bytes(b"%PDF-1.4 kein echtes PDF")
    register = Register(datenordner)
    register.speichere({**register.hole(BRIEF_ID), "variante": ""})

    assert not _over(pruefung.pruefe(datenordner, register.hole(BRIEF_ID), TODAY))


# Choosing

def _choose(server, body):  # noqa: F811
    return post(server, "/api/kuerzungen", {"id": BRIEF_ID, **body})


def test_cutting_stores_for_this_application_only_and_builds_anew(server, three_pages):  # noqa: F811
    folder = server.kontext.daten
    entry = Register(folder).hole(BRIEF_ID)
    unterlagen.baue(folder, entry, server.kontext.build)
    cv_before = (folder / "cv.yaml").read_text(encoding="utf-8")
    job_before = (folder / "jobs" / "daten.yaml").read_text(encoding="utf-8")
    pdf = unterlagen.pdf_pfade(folder, BRIEF_ID)["lebenslauf"]
    built_before = pdf.stat().st_mtime_ns
    first = _over(pruefung.pruefe(folder, entry, TODAY))[0].kuerzen["optionen"][0]["id"]

    status, answer = _choose(server, {"weglassen": [first]})

    assert status == 200 and answer["neu_erstellt"] is True, answer
    stored = yaml.safe_load((folder / "bewerbungen" / BRIEF_ID / cv_cuts.FILE).read_text(encoding="utf-8"))
    assert stored["stichpunkte"][0]["behalten"] == 1
    assert (folder / "cv.yaml").read_text(encoding="utf-8") == cv_before
    assert (folder / "jobs" / "daten.yaml").read_text(encoding="utf-8") == job_before
    assert pdf.stat().st_mtime_ns != built_before
    assert [e["text"] for e in answer["kuerzungen"]["weggelassen"]] == [FIRST_CUT]
    assert server.kontext.ablage.liste(folder / "bewerbungen" / BRIEF_ID / cv_cuts.FILE)


def test_still_over_the_finding_returns_with_the_next_cut_first(server, three_pages):  # noqa: F811
    folder = server.kontext.daten
    entry = Register(folder).hole(BRIEF_ID)
    unterlagen.baue(folder, entry, server.kontext.build)
    first = _over(pruefung.pruefe(folder, entry, TODAY))[0].kuerzen["optionen"][0]

    _choose(server, {"weglassen": [first["id"]]})

    again = _over(pruefung.pruefe(folder, Register(folder).hole(BRIEF_ID), TODAY))[0].kuerzen["optionen"]
    assert first["id"] not in [o["id"] for o in again]
    assert again[0]["text"] != first["text"]


def test_the_cuts_go_over_the_chosen_variant_at_each_build(datenordner):
    entry = Register(datenordner).hole(BRIEF_ID)
    cv = unterlagen.tailored_cv(datenordner, entry)
    cut_choice.store_choice(datenordner, entry, [cut_choice.options(datenordner, entry)[0].id], None)

    tailored = unterlagen.tailored_cv(datenordner, entry)

    station = next(s for s in tailored["work"] if s["position"] == "Software-Entwicklerin")
    assert len(station["highlights"]) == 1
    assert len(next(s for s in cv["work"] if s["position"] == "Software-Entwicklerin")["highlights"]) == 2
    assert tailored["basics"]["label"] == "Data Engineer", "the variant still counts"


def test_the_builds_get_the_cuts_and_the_pages_of_the_application(datenordner, tmp_path, monkeypatch):
    entry = Register(datenordner).hole(BRIEF_ID)
    cut_choice.store_choice(datenordner, entry, [cut_choice.options(datenordner, entry)[0].id], True)
    calls = []
    monkeypatch.setattr(unterlagen.lebenslauf_modul, "main", lambda args: calls.append(args))
    monkeypatch.setattr(unterlagen.dossier_modul, "main", lambda args: calls.append(args) or _Result(datenordner))

    unterlagen.build_cv(datenordner, entry, tmp_path / "build")
    unterlagen.baue(datenordner, {**entry, "unterlagen": "dossier"}, tmp_path / "build")

    cut_file = str(unterlagen.bewerbungsordner(datenordner, BRIEF_ID) / cv_cuts.FILE)
    assert len(calls) == 2
    for args in calls:
        assert args[args.index("--kuerzungen") + 1] == cut_file
        assert args[args.index("--lebenslauf-seiten") + 1] == "3"
    assert page_limit.load(datenordner) == 2, "the setting for all applications stays"


class _Result:
    def __init__(self, folder):
        self.cv = self.letter = self.dossier = folder / "x.pdf"


def test_allowing_three_pages_holds_for_this_application_only(server, three_pages):  # noqa: F811
    folder = server.kontext.daten
    unterlagen.baue(folder, Register(folder).hole(BRIEF_ID), server.kontext.build)

    status, answer = _choose(server, {"drei_seiten": True})

    assert status == 200 and answer["kuerzungen"]["drei_seiten"] is True
    assert not _over(pruefung.pruefe(folder, Register(folder).hole(BRIEF_ID), TODAY))
    assert page_limit.load(folder) == 2
    assert not (folder / page_limit.FILE).exists()


def test_with_three_pages_allowed_and_still_over_three_is_no_more_offered(datenordner, tmp_path, three_pages):
    three_pages["lebenslauf.pdf"] = 4
    entry = Register(datenordner).hole(BRIEF_ID)
    cut_choice.store_choice(datenordner, entry, [], True)
    _built(datenordner, tmp_path, entry)

    finding = _over(pruefung.pruefe(datenordner, entry, TODAY))[0]

    assert finding.text.startswith("Lebenslauf: 4 Seiten, erlaubt sind höchstens 3.")
    assert finding.kuerzen["drei_seiten"] is False and finding.kuerzen["optionen"]


@pytest.fixture
def no_cut_left(three_pages, monkeypatch):
    """Three pages allowed, still four, and nothing left to cut (#330)."""
    three_pages["lebenslauf.pdf"] = 4
    monkeypatch.setattr(cut_choice, "options", lambda daten, entry: [])
    return three_pages


def _kept_over(findings):
    return [f for f in findings if f.cv_over]


def test_with_three_pages_and_no_cut_left_the_finding_names_the_lines_and_waits(datenordner, tmp_path, no_cut_left,
                                                                                monkeypatch):
    monkeypatch.setattr(routes_apply.apply, "blocker", lambda daten, entry: None)
    monkeypatch.setattr(pruefung, "pruefe_anschreiben_text", lambda *args, **kwargs: [])
    entry = Register(datenordner).hole(BRIEF_ID)
    cut_choice.store_choice(datenordner, entry, [], True)
    _built(datenordner, tmp_path, entry)

    found = pruefung.pruefe(datenordner, entry, TODAY)

    assert not _over(found)
    [finding] = _kept_over(found)
    assert finding.text == ("Lebenslauf: 4 Seiten, erlaubt sind höchstens 3. Auch enger gesetzt sind es etwa 7 Zeilen "
                            "zu viel. Weiter kürzen lässt sich mit «Lebenslauf erstellen», nur für diese Bewerbung, "
                            "oder unter «Meine Angaben», für alle.")
    assert finding.schluessel and not finding.bestaetigt
    assert finding.cv_over == {"lines": 7, "pages": 4}
    problem = routes_apply._problem(types.SimpleNamespace(daten=datenordner, heute=lambda: TODAY), entry)
    assert problem == f"Prüfung: {finding.text} {routes_apply.CONFIRM_FIRST}", "no form opens before «So lassen»"


def test_so_lassen_confirms_a_cv_over_three_pages_with_no_cut_left(server, no_cut_left, monkeypatch):  # noqa: F811
    monkeypatch.setattr(routes_apply.apply, "blocker", lambda daten, entry: None)
    monkeypatch.setattr(pruefung, "pruefe_anschreiben_text", lambda *args, **kwargs: [])
    folder = server.kontext.daten
    entry = Register(folder).hole(BRIEF_ID)
    cut_choice.store_choice(folder, entry, [], True)
    unterlagen.baue(folder, entry, server.kontext.build)
    finding = _kept_over(pruefung.pruefe(folder, entry, TODAY))[0]

    status, answer = post(server, "/api/pruefung/bestaetigen", {"id": BRIEF_ID, "schluessel": finding.schluessel})

    assert status == 200, answer
    [confirmed] = [f for f in answer["befunde"] if f["cv_over"]]
    assert confirmed["bestaetigt"] and confirmed["stufe"] == "hinweis"
    assert routes_apply._problem(server.kontext, entry) is None


def test_the_last_page_fill_of_a_cv_over_three_pages_is_no_finding_of_its_own(datenordner, tmp_path, no_cut_left,
                                                                              monkeypatch):
    fill = layout_check.Breach(4, "fuellung", "nur zu 12 % gefüllt, verlangt ist mindestens ein Drittel.")
    monkeypatch.setattr(layout_check, "check", lambda pdf, part, headings=(): [fill] if part == "lebenslauf" else [])
    entry = Register(datenordner).hole(BRIEF_ID)
    cut_choice.store_choice(datenordner, entry, [], True)
    _built(datenordner, tmp_path, entry)

    texts = [f.text for f in pruefung.pruefe(datenordner, entry, TODAY)]

    assert not any(text.startswith("Lebenslauf, Seite 4") for text in texts), "one «So lassen» for the CV over its limit"


def test_choosing_nothing_or_an_unknown_cut_is_refused(server, three_pages):  # noqa: F811
    folder = server.kontext.daten
    unterlagen.baue(folder, Register(folder).hole(BRIEF_ID), server.kontext.build)

    assert _choose(server, {"weglassen": []}) == (400, {"fehler": cut_choice.NONE_CHOSEN})
    assert _choose(server, {"weglassen": ["stichpunkte:unbekannt"]}) == (400, {"fehler": cut_choice.UNKNOWN})
    assert not (folder / "bewerbungen" / BRIEF_ID / cv_cuts.FILE).exists()


def test_after_sending_nothing_is_cut(server, three_pages):  # noqa: F811
    folder = server.kontext.daten
    register = Register(folder)
    register.speichere({**register.hole(BRIEF_ID), "versand": {"datum": "2026-10-25", "dateien": {}}})

    assert _choose(server, {"drei_seiten": True}) == (400, {"fehler": unterlagen.SENT_STAYS})


# What is left out, in the step Lebenslauf


def test_the_application_lists_what_is_left_out_and_brings_it_back(server, three_pages):  # noqa: F811
    folder = server.kontext.daten
    entry = Register(folder).hole(BRIEF_ID)
    unterlagen.baue(folder, entry, server.kontext.build)
    first = _over(pruefung.pruefe(folder, entry, TODAY))[0].kuerzen["optionen"][0]["id"]
    _choose(server, {"weglassen": [first], "drei_seiten": True})

    _, _, body = get(server, "/api/bewerbung", id=BRIEF_ID)
    shown = json.loads(body)["kuerzungen"]
    assert shown == {"weggelassen": [{"id": first, "text": FIRST_CUT}], "drei_seiten": True}

    status, answer = post(server, "/api/kuerzungen/zurueckholen", {"id": BRIEF_ID, "kuerzung": first})
    assert status == 200 and answer["kuerzungen"] == {"weggelassen": [], "drei_seiten": True}
    status, answer = post(server, "/api/kuerzungen/zurueckholen", {"id": BRIEF_ID, "kuerzung": cut_choice.THREE_PAGES})
    assert answer["kuerzungen"] == {"weggelassen": [], "drei_seiten": False} and answer["neu_erstellt"] is True
    station = next(s for s in unterlagen.tailored_cv(folder, entry)["work"] if s["position"] == "Software-Entwicklerin")
    assert len(station["highlights"]) == 2


def test_the_page_loads_the_cut_scripts_and_has_the_list_in_the_step_lebenslauf(server):  # noqa: F811
    _, _, body = get(server, "/bewerbung", id=BRIEF_ID)
    page = body.decode("utf-8")

    for script in ("/kuerzen-logik.js", "/kuerzen.js"):
        assert get(server, script)[0] == 200
        assert page.index(script) < page.index("/bewerbung.js")
    step = page[page.index('id="s-lebenslauf"'):page.index('id="s-anschreiben"')]
    assert 'id="weggelassen"' in step and 'id="weggelassen-liste"' in step
    assert 'id="lebenslauf-titel" tabindex="-1"' in step, "the focus can go back to the step"


def test_taking_back_an_unknown_cut_is_refused(server):  # noqa: F811
    status, answer = post(server, "/api/kuerzungen/zurueckholen", {"id": BRIEF_ID, "kuerzung": "stichpunkte:x"})

    assert status == 400 and answer["fehler"] == cut_choice.UNKNOWN


def test_neither_the_extension_nor_claude_reach_the_cuts():
    for name in ("native_host.py", "mcp_tools.py"):
        assert "/api/kuerzungen" not in (DESKTOP / name).read_text(encoding="utf-8")
