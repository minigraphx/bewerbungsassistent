"""Entwürfe und Versionen grouped by what the person knows (#120), without the job ads (stelle.md)."""
import json
import re

import draft_groups
from register import Register
from sample_folder import BRIEF_ID
from unterlagen import OWN_CV
from test_app import get, server  # noqa: F401  (server is a fixture)


def drafts(s, *files_and_notes):
    """Saves a draft of each (file, note) in turn, after adding the note to the file as a comment line."""
    k = s.kontext
    saved = []
    for rel, note in files_and_notes:
        path = k.daten / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        before = path.read_text(encoding="utf-8") if path.exists() else ""
        path.write_text(f"{before}# {note}\n", encoding="utf-8")
        saved.append(k.ablage.speichere(path, note))
    return saved


def groups(s) -> list[dict]:
    status, _, content = get(s, "/api/entwuerfe")
    assert status == 200
    return json.loads(content)["gruppen"]


def test_job_ads_are_not_shown(server):
    drafts(server, (f"bewerbungen/{BRIEF_ID}/stelle.md", "Inserat"), ("cv.yaml", "Lebenslauf"))

    status, _, content = get(server, "/api/entwuerfe")
    answer = json.loads(content)

    assert not any(e["datei"].endswith("stelle.md") for e in answer["entwuerfe"])
    assert not any(d.endswith("stelle.md") for d in answer["dateien"])
    shown = [f for g in answer["gruppen"] for d in g["dokumente"] for f in d["fassungen"]]
    assert [f["beschreibung"] for f in shown] == ["Lebenslauf"]


def test_groups_in_the_order_the_person_knows(server):
    drafts(server, ("suchprofil.md", "Suchprofil"), ("anschreiben/stil.md", "Stil"),
           (f"bewerbungen/{BRIEF_ID}/anschreiben.yaml", "Brief"), ("jobs/daten.yaml", "Zuschnitt"),
           ("cv.yaml", "Angaben"), ("anschreiben/bausteine.md", "Bausteine"), ("bewerbungen.yaml", "Register"))

    found = groups(server)

    assert [g["art"] for g in found] == ["lebenslauf", "anschreiben", "stil", "suchprofil", "weitere"]
    assert [g["titel"] for g in found] == ["Lebenslauf", "Anschreiben", "Stil und Bausteine", "Suchprofil", "Weitere"]
    titles = {g["art"]: [d["titel"] for d in g["dokumente"]] for g in found}
    assert titles["lebenslauf"] == ["Lebenslauf", "Lebenslauf-Zuschnitt daten"]  # the newest change first
    assert titles["anschreiben"] == ["Anschreiben Beispiel AG"]
    assert titles["stil"] == ["Textbausteine", "Stilprofil"]
    assert titles["weitere"] == ["Bewerbungsregister (Daten)"]


def test_each_letter_is_its_own_document_named_after_the_company(server):
    other = Register(server.kontext.daten).neu(firma="Muster AG", stelle="Sachbearbeiterin")
    drafts(server, (f"bewerbungen/{BRIEF_ID}/anschreiben.yaml", "eins"), (f"bewerbungen/{other['id']}/anschreiben.yaml", "zwei"))

    letters = next(g for g in groups(server) if g["art"] == "anschreiben")["dokumente"]

    assert sorted(d["titel"] for d in letters) == ["Anschreiben Beispiel AG", "Anschreiben Muster AG"]
    assert {f["titel"] for d in letters for f in d["fassungen"]} == {"Anschreiben Beispiel AG", "Anschreiben Muster AG"}


def test_the_newest_version_comes_first(server):
    first, second, third = drafts(server, ("cv.yaml", "eins"), ("cv.yaml", "zwei"), ("cv.yaml", "drei"))

    cv = groups(server)[0]["dokumente"][0]

    assert [f["id"] for f in cv["fassungen"]] == [third.id, second.id, first.id]


def test_a_broken_register_leaves_the_folder_name(server):
    drafts(server, (f"bewerbungen/{BRIEF_ID}/anschreiben.yaml", "Brief"))
    (server.kontext.daten / "bewerbungen.yaml").write_text("- [kaputt\n", encoding="utf-8")

    letters = next(g for g in groups(server) if g["art"] == "anschreiben")["dokumente"]

    assert [d["titel"] for d in letters] == [f"Anschreiben {BRIEF_ID}"]


def test_the_file_of_a_job_ad_still_answers_when_asked_for(server):
    """The editor of a job ad on Inhalte als Text lists its own drafts."""
    drafts(server, (f"bewerbungen/{BRIEF_ID}/stelle.md", "Inserat"))

    status, _, content = get(server, "/api/entwuerfe", datei=f"bewerbungen/{BRIEF_ID}/stelle.md")

    assert [e["beschreibung"] for e in json.loads(content)["entwuerfe"]] == ["Inserat"]
    assert json.loads(content)["gruppen"] == []


def test_a_document_of_a_removed_application_keeps_its_folder_name():
    assert draft_groups.document_title("bewerbungen/alt-ag-tester/anschreiben.yaml", {}) == "Anschreiben alt-ag-tester"


def test_the_page_shows_groups_with_older_versions_folded(server):
    status, _, page = get(server, "/entwuerfe")
    html = page.decode("utf-8")
    script = get(server, "/entwuerfe.js")[2].decode("utf-8")
    logic = get(server, "/entwuerfe-logik.js")[2].decode("utf-8")

    assert status == 200 and 'id="gruppen"' in html and "<table" not in html
    assert re.search(r'"details"', script) and "Ältere Fassungen" in logic
    assert 'id="datei"' not in html  # no file names on the page


def test_the_own_cv_from_meine_dateien_is_a_lebenslauf(server):
    drafts(server, (OWN_CV, "Eigenes PDF"), ("cv.yaml", "Angaben"))

    found = groups(server)

    assert [g["art"] for g in found] == ["lebenslauf"]
    assert [d["titel"] for d in found[0]["dokumente"]] == ["Lebenslauf", "Eigener Lebenslauf (PDF)"]
    assert draft_groups.category(OWN_CV) == "lebenslauf"
