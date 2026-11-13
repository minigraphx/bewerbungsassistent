"""Meine Angaben reads search profile, style profile and building blocks back into the form (#217).

A person whose basics came from the skill einstieg or were edited under „Inhalte als Text“ sees them on the page and
can change them; saving writes back only what changed, with drafts, and keeps the lines the form does not know.
All data is invented.
"""
import json
import pathlib

import pytest

from test_angaben import call, started  # noqa: F401  (fixture)

CASES = pathlib.Path(__file__).resolve().parents[2] / "onboarding" / "tests" / "cases.json"

PROFILE = """# Suchprofil

Von Hand geschrieben, für die Suche.

## Portale und Rhythmus
Wochentag: Montag
- Zeitfenster: 14 Tage

| Portal | Modus |
|---|---|
| job-room | automatisch |
| jobs.ch | mit Nutzer |
| jobscout24 | aus |
| ictjobs | automatisch |
| LinkedIn | mit Nutzer |

## Suchrichtungen
1. Software-Entwicklung (Priorität 1)
2. Datenanalyse (Priorität 2)
- Ausschluss: Vertrieb, Callcenter

## Region
- Wohnort: Thun
- Orte (jobs.ch, LinkedIn): Thun, Bern
- Pendelgrenze: 60 Minuten
- Kantone (job-room): BE, FR
- Remote: ja

## Keywords
- Kernliste: Python, Datenbanken
- Nischen (ohne Ort suchen): EdTech

## Titelfilter
- Positiv: Entwickler, Developer
- Ausschluss: Praktikum, Lehrstelle

## Rahmen
- Frühester Start: 1. April
- Pensum: 60–80 %
- Befristung möglich: nein

## Zielfirmen mit Karriereseite
- Beispiel Werke AG
"""

STYLE = """# Stilprofil

Von Hand.

## Ton
- Ruhig und genau.
- Aussagen mit konkreten Beispielen belegen; Lücken offen und knapp benennen, mit Lernbereitschaft.
- Schweizer Schreibweise (ss statt ß).
- Keine Superlative.

## Anrede und Form
- Immer Sie-Form: „Sehr geehrte Frau <Nachname>“, ohne Namen „Guten Tag“.
- Gruss: „Mit freundlichen Grüssen“; Ort im Datum: Thun.

## Typische Formulierungen
- Einstieg: „Ihr Inserat hat mich sofort angesprochen.“
- Schluss: „Ich freue mich auf ein Gespräch.“
- „Gerne zeige ich Ihnen Beispiele.“
"""

BLOCKS = """# Bausteine fürs Anschreiben

Von Hand.

## Stärken
- **Geduld** – Erkläre Kundinnen die Software Schritt für Schritt. *Beleg: Arbeitszeugnis.*
- Notiz von Hand ohne Form

## Lücken (offen benennen)
- Noch kein Cloud-Zertifikat

## Rahmen
- Kündigungsfrist: 2 Monate
- Referenz: Max Muster, 079 000 00 01
"""


def write_basics(folder: pathlib.Path) -> None:
    (folder / "suchprofil.md").write_text(PROFILE, encoding="utf-8")
    (folder / "anschreiben").mkdir(exist_ok=True)
    (folder / "anschreiben" / "stil.md").write_text(STYLE, encoding="utf-8")
    (folder / "anschreiben" / "bausteine.md").write_text(BLOCKS, encoding="utf-8")


def job_bundle() -> dict:
    return json.loads(CASES.read_text(encoding="utf-8"))["bases"]["job"]


def read_back(server) -> dict:
    status, answer = call(server, "/api/angaben/stand")
    assert status == 200
    return answer["grundlagen"]


def bundle_from(read: dict) -> dict:
    """What the page sends after opening on the read-back values: the CV parts of the test bundle, the rest from the
    files."""
    bundle = job_bundle()
    data = {key: value for key, value in bundle["data"].items()
            if key not in ("searchJob", "strengths", "gaps", "style", "frame")}
    return {**bundle, "data": {**data, **json.loads(json.dumps(read["daten"]))}}


def save(server, bundle: dict, base: dict) -> tuple[int, dict]:
    return call(server, "/api/angaben/uebernehmen", {"bundle": bundle, "grundlagen": base})


def drafts_of(folder: pathlib.Path, rel: str) -> list[str]:
    from ablage import Ablage
    return [draft.beschreibung for draft in Ablage(folder).liste(folder / rel)]


def test_the_search_profile_comes_back_into_the_form(started):
    server, folder, _ = started
    write_basics(folder)

    search = read_back(server)["daten"]["searchJob"]

    assert search["directions"] == ["Software-Entwicklung", "Datenanalyse"]
    assert search["exclusions"] == ["Vertrieb", "Callcenter"]
    assert (search["home"], search["commute"], search["remote"]) == ("Thun", "60 Minuten", "ja")
    assert search["cantons"] == ["BE", "FR"]
    assert search["keywords"] == ["Python", "Datenbanken"]
    assert search["titleExclude"] == ["Praktikum", "Lehrstelle"]
    assert (search["start"], search["workload"], search["temporary"]) == ("1. April", "60–80 %", "nein")
    assert search["targetCompanies"] == ["Beispiel Werke AG"]


def test_style_and_building_blocks_come_back_into_the_form(started):
    server, folder, _ = started
    write_basics(folder)

    data = read_back(server)["daten"]

    assert data["style"] == {"tone": "Ruhig und genau", "address": "Immer Sie-Form",
                             "greeting": "Mit freundlichen Grüssen", "place": "Thun",
                             "opening": "Ihr Inserat hat mich sofort angesprochen.",
                             "closing": "Ich freue mich auf ein Gespräch.",
                             "phrases": ["Gerne zeige ich Ihnen Beispiele."]}
    assert data["strengths"] == [{"strength": "Geduld", "example": "Erkläre Kundinnen die Software Schritt für Schritt.",
                                  "evidence": "Arbeitszeugnis"}]
    assert data["gaps"] == {"gaps": ["Noch kein Cloud-Zertifikat"]}
    assert data["frame"] == {"notice": "2 Monate", "reference": "Max Muster, 079 000 00 01"}


def test_lines_the_form_does_not_know_are_named_with_their_file(started):
    server, folder, _ = started
    write_basics(folder)

    other = read_back(server)["fremd"]

    lines = {(group["datei"], line) for group in other for line in group["zeilen"]}
    assert ("suchprofil.md", "- Orte (jobs.ch, LinkedIn): Thun, Bern") in lines
    assert ("suchprofil.md", "| LinkedIn | mit Nutzer |") in lines
    assert ("suchprofil.md", "Wochentag: Montag") in lines
    assert ("anschreiben/stil.md", "- Keine Superlative.") in lines
    assert ("anschreiben/bausteine.md", "- Notiz von Hand ohne Form") in lines
    assert ("suchprofil.md", "- Pensum: 60–80 %") not in lines  # the form shows it
    assert ("anschreiben/stil.md", "- Schweizer Schreibweise (ss statt ß).") not in lines  # the app writes it itself
    sections = {(group["datei"], group["abschnitt"]) for group in other}
    assert ("suchprofil.md", "searchJob") in sections and ("anschreiben/stil.md", "style") in sections


def test_saving_one_change_writes_only_that_line_with_drafts(started):
    server, folder, _ = started
    write_basics(folder)
    read = read_back(server)
    bundle = bundle_from(read)
    bundle["data"]["searchJob"]["workload"] = "100 %"

    status, answer = save(server, bundle, read["daten"])

    assert status == 200, answer
    assert (folder / "suchprofil.md").read_text(encoding="utf-8") == PROFILE.replace("- Pensum: 60–80 %", "- Pensum: 100 %")
    assert (folder / "anschreiben" / "stil.md").read_text(encoding="utf-8") == STYLE
    assert (folder / "anschreiben" / "bausteine.md").read_text(encoding="utf-8") == BLOCKS
    assert "suchprofil.md" in answer["geschrieben"] and "anschreiben/stil.md" not in answer["geschrieben"]
    assert len(drafts_of(folder, "suchprofil.md")) == 2  # before and after
    assert drafts_of(folder, "anschreiben/stil.md") == []


def test_saving_without_a_change_leaves_every_basic_as_it_is(started):
    server, folder, _ = started
    write_basics(folder)
    read = read_back(server)

    status, answer = save(server, bundle_from(read), read["daten"])

    assert status == 200, answer
    assert (folder / "suchprofil.md").read_text(encoding="utf-8") == PROFILE
    assert (folder / "anschreiben" / "stil.md").read_text(encoding="utf-8") == STYLE
    assert (folder / "anschreiben" / "bausteine.md").read_text(encoding="utf-8") == BLOCKS


def test_changes_in_lists_and_style_keep_the_unknown_lines(started):
    server, folder, _ = started
    write_basics(folder)
    read = read_back(server)
    bundle = bundle_from(read)
    bundle["data"]["searchJob"]["directions"] = ["Software-Entwicklung"]
    bundle["data"]["searchJob"]["commute"] = ""
    bundle["data"]["style"]["tone"] = "Kurz und direkt"
    bundle["data"]["strengths"].append({"strength": "Ordnung", "example": "Ablage neu aufgebaut.", "evidence": ""})

    status, answer = save(server, bundle, read["daten"])

    profile = (folder / "suchprofil.md").read_text(encoding="utf-8")
    style = (folder / "anschreiben" / "stil.md").read_text(encoding="utf-8")
    blocks = (folder / "anschreiben" / "bausteine.md").read_text(encoding="utf-8")
    assert status == 200, answer
    assert "Datenanalyse" not in profile and "1. Software-Entwicklung (Priorität 1)" in profile
    assert "Pendelgrenze" not in profile and "- Orte (jobs.ch, LinkedIn): Thun, Bern" in profile
    assert "- Positiv: Entwickler, Developer" in profile and "- Zeitfenster: 14 Tage" in profile
    assert style.startswith(STYLE.split("## Ton")[0]) and "- Kurz und direkt.\n" in style
    assert "- Keine Superlative." in style and "Ruhig und genau" not in style
    assert "- **Ordnung** – Ablage neu aufgebaut. *Beleg: eigene Angabe.*" in blocks
    assert "- Notiz von Hand ohne Form" in blocks and "- **Geduld**" in blocks


def test_a_term_added_on_the_search_page_meanwhile_stays(started):
    server, folder, _ = started
    write_basics(folder)
    read = read_back(server)
    profile = folder / "suchprofil.md"
    profile.write_text(PROFILE.replace("Python, Datenbanken", "Python, Datenbanken, Statistik"), encoding="utf-8")
    bundle = bundle_from(read)
    bundle["data"]["searchJob"]["workload"] = "100 %"

    status, answer = save(server, bundle, read["daten"])

    assert status == 200, answer
    assert "- Kernliste: Python, Datenbanken, Statistik" in profile.read_text(encoding="utf-8")


def test_an_apprenticeship_profile_comes_back_for_the_apprenticeship_track(started):
    server, folder, _ = started
    (folder / "suchprofil.md").write_text(
        "# Suchprofil Lehrstelle\n\n## Person\n- Begleitperson: Mutter\n\n## Gesucht\n- Schnupperlehren\n\n"
        "## Lehrbeginn\n- August 2027\n\n## Berufe (mit Priorität)\n1. Informatiker EFZ (Priorität 1)\n\n"
        "## Region\n- Wohnort: Biel\n- Schulweg: 30 Minuten\n- Umkreis: 10 km\n", encoding="utf-8")

    search = read_back(server)["daten"]["searchApprenticeship"]

    assert search == {"companion": "Mutter", "offers": "Schnupperlehren", "start": "August 2027",
                      "professions": ["Informatiker EFZ"], "home": "Biel", "commute": "30 Minuten", "radius": "10 km"}


def test_values_the_form_cannot_take_stay_in_the_file_only(started):
    server, folder, _ = started
    write_basics(folder)
    profile = folder / "suchprofil.md"
    profile.write_text(PROFILE.replace("- Remote: ja", "- Remote: am liebsten ganz"), encoding="utf-8")

    back = read_back(server)

    assert "remote" not in back["daten"]["searchJob"]
    assert "- Remote: am liebsten ganz" in {line for group in back["fremd"] for line in group["zeilen"]}


@pytest.mark.parametrize("base", ["text", ["a"], {"searchJob": "x"}])
def test_a_base_of_unknown_form_changes_nothing_it_cannot_read(started, base):
    server, folder, _ = started
    write_basics(folder)
    read = read_back(server)

    status, answer = save(server, bundle_from(read), base)

    assert status in (200, 400), answer
    assert (folder / "suchprofil.md").read_text(encoding="utf-8") == PROFILE


# #291: search window, portals and the positive title terms are fields of their own.

def test_window_portals_and_positive_titles_come_back_as_fields(started):
    server, folder, _ = started
    write_basics(folder)

    back = read_back(server)

    search = back["daten"]["searchJob"]
    assert search["window"] == "14"
    assert search["portalsOff"] == ["jobscout24"]
    assert search["titlePositive"] == ["Entwickler", "Developer"]
    lines = {line for group in back["fremd"] for line in group["zeilen"]}
    for known in ("- Zeitfenster: 14 Tage", "- Positiv: Entwickler, Developer", "| jobs.ch | mit Nutzer |",
                  "| jobscout24 | aus |", "| Portal | Modus |"):
        assert known not in lines


def test_a_profile_without_portal_rows_has_no_portal_switched_off(started):
    server, folder, _ = started
    (folder / "suchprofil.md").write_text(PROFILE.replace("| jobscout24 | aus |\n", ""), encoding="utf-8")

    search = read_back(server)["daten"]["searchJob"]

    assert search["portalsOff"] == []


@pytest.mark.parametrize("change, before, after", [
    (("window", "30"), "- Zeitfenster: 14 Tage", "- Zeitfenster: 30 Tage"),
    (("titlePositive", ["Entwickler", "Developer", "Data"]), "- Positiv: Entwickler, Developer",
     "- Positiv: Entwickler, Developer, Data"),
    (("portalsOff", ["jobscout24", "ictjobs"]), "| ictjobs | automatisch |", "| ictjobs | aus |"),
    (("portalsOff", []), "| jobscout24 | aus |", "| jobscout24 | automatisch |"),
])
def test_changing_one_of_them_writes_only_its_line_with_drafts(started, change, before, after):
    server, folder, _ = started
    write_basics(folder)
    read = read_back(server)
    bundle = bundle_from(read)
    bundle["data"]["searchJob"][change[0]] = change[1]

    status, answer = save(server, bundle, read["daten"])

    assert status == 200, answer
    assert (folder / "suchprofil.md").read_text(encoding="utf-8") == PROFILE.replace(before, after)
    assert len(drafts_of(folder, "suchprofil.md")) == 2  # before and after


def test_the_search_plan_reads_what_the_fields_wrote_into_a_profile_without_them(started):
    import search_plan
    server, folder, _ = started
    write_basics(folder)
    bare = PROFILE.split("## Portale und Rhythmus")[0] + "## Suchrichtungen" + PROFILE.split("## Suchrichtungen")[1]
    bare = bare.replace("- Positiv: Entwickler, Developer\n", "")
    (folder / "suchprofil.md").write_text(bare, encoding="utf-8")
    read = read_back(server)
    bundle = bundle_from(read)
    bundle["data"]["searchJob"] = {**bundle["data"]["searchJob"], "window": "30", "portalsOff": ["ictjobs"],
                                   "titlePositive": ["Entwickler"]}

    status, answer = save(server, bundle, read["daten"])

    assert status == 200, answer
    text = (folder / "suchprofil.md").read_text(encoding="utf-8")
    kept = [line for line in bare.split("\n") if line]
    assert [line for line in text.split("\n") if line in kept] == kept
    assert text.endswith("## Portale und Rhythmus\n- Zeitfenster: 30 Tage\n\n| Portal | Modus |\n|---|---|\n"
                         "| job-room | automatisch |\n| jobs.ch | automatisch |\n| jobscout24 | automatisch |\n"
                         "| ictjobs | aus |\n")
    assert "- Positiv: Entwickler\n" in text
    plan = search_plan.parse(text)
    assert plan.max_age_days == 30 and plan.title_positive == ("Entwickler",)
    assert plan.portals == ("job-room", "jobs.ch", "jobscout24")


@pytest.mark.parametrize("field, value", [("window", "90"), ("window", "zwei Wochen"),
                                          ("portalsOff", ["job-room", "jobs.ch", "jobscout24", "ictjobs"]),
                                          ("portalsOff", ["LinkedIn"])])
def test_values_the_search_cannot_take_are_refused(started, field, value):
    server, folder, _ = started
    write_basics(folder)
    read = read_back(server)
    bundle = bundle_from(read)
    bundle["data"]["searchJob"][field] = value

    status, answer = save(server, bundle, read["daten"])

    assert status == 400, answer
    assert (folder / "suchprofil.md").read_text(encoding="utf-8") == PROFILE


@pytest.mark.parametrize("line, row", [("- Zeitfenster: 90 Tage", None),
                                       (None, "| job-room | aus |\n| jobs.ch | aus |\n| jobscout24 | aus |\n| ictjobs | aus |\n")])
def test_a_window_or_portals_the_search_cannot_use_stay_in_the_file_only(started, line, row):
    server, folder, _ = started
    text = PROFILE.replace("- Zeitfenster: 14 Tage", line) if line else PROFILE
    if row:
        start = text.index("| job-room |")
        text = text[:start] + row + text[text.index("| LinkedIn |"):]
    (folder / "suchprofil.md").write_text(text, encoding="utf-8")

    back = read_back(server)

    field = "window" if line else "portalsOff"
    assert field not in back["daten"]["searchJob"]
    lines = {shown for group in back["fremd"] for shown in group["zeilen"]}
    assert (line or "| ictjobs | aus |") in lines


def test_switching_off_a_portal_without_a_row_adds_its_row_to_the_table(started):
    server, folder, _ = started
    write_basics(folder)
    profile = folder / "suchprofil.md"
    profile.write_text(PROFILE.replace("| ictjobs | automatisch |\n", ""), encoding="utf-8")
    read = read_back(server)
    bundle = bundle_from(read)
    bundle["data"]["searchJob"]["portalsOff"] = ["jobscout24", "ictjobs"]

    status, answer = save(server, bundle, read["daten"])

    assert status == 200, answer
    assert profile.read_text(encoding="utf-8") == PROFILE.replace("| ictjobs | automatisch |\n", "").replace(
        "| jobscout24 | aus |\n", "| jobscout24 | aus |\n| ictjobs | aus |\n")
