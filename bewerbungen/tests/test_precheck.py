"""Rule-based pre-check of an ad before rating (G33), unambiguous signals only, with invented ads, profile and cv.yaml."""
import json

import pytest
import yaml

import precheck
from test_app import get, post, server  # noqa: F401  (server is a fixture)

PROFILE = """# Suchprofil

## Region
- Kantone (job-room): BE
- Orte (jobs.ch): Bern
- PLZ (jobscout24): 3000

## Keywords
- Kernliste: Python, Daten

## Sprachen
- Deutsch (Muttersprache), Englisch (gut), Französisch (Grundkenntnisse)

## Abschluss und Erfahrung
- Bachelor Informatik, acht Jahre Praxis

## Ausschlüsse
- Technologien als Schwerpunkt: Java, .NET
"""
CV = {"basics": {"name": "Erika Beispiel"},
      "languages": [{"language": "Deutsch", "fluency": "Muttersprache"}, {"language": "Englisch", "fluency": "Sehr gut (C1)"}],
      "education": [{"studyType": "Bachelor", "area": "Informatik", "institution": "Beispiel-Hochschule"}]}
PERSON = precheck.person_of(CV, PROFILE)


def check(text: str, title: str = "Python Entwickler") -> str:
    return precheck.check(title, text, PERSON)


B2_ENGLISH = precheck.Person(languages={"deutsch": 7, "englisch": 4}, degree=3, excluded=("Java",))


def test_the_person_comes_from_cv_yaml_and_the_profile():
    assert PERSON.languages == {"deutsch": 7, "englisch": 5, "französisch": 2}
    assert PERSON.degree == 3
    assert PERSON.excluded == ("Java", ".NET")


@pytest.mark.parametrize(("text", "reason"), [
    ("Französisch C1 ist zwingend.", "Verlangt Französisch auf Niveau C1, vorhanden ist A2."),
    ("Sehr gute Französischkenntnisse (C1) sind Pflicht.", "Verlangt Französisch auf Niveau C1, vorhanden ist A2."),
    ("Vorausgesetzt: Französisch auf Niveau B2.", "Verlangt Französisch auf Niveau B2, vorhanden ist A2."),
    ("Italienisch B1 ist erforderlich.", "Verlangt Italienisch auf Niveau B1, vorhanden ist keine Angabe."),
    ("English C2 is required.", "Verlangt Englisch auf Niveau C2, vorhanden ist C1."),
    ("Englisch auf Muttersprachniveau ist zwingend.", "Verlangt Englisch auf Niveau Muttersprache, vorhanden ist C1."),
    ("Français niveau C1 obligatoire.", "Verlangt Französisch auf Niveau C1, vorhanden ist A2."),
    ("Deutsch und Französisch C1 sind zwingend.", "Verlangt Französisch auf Niveau C1, vorhanden ist A2."),
    ("Ein abgeschlossener Master ist zwingend.", "Verlangt Master, vorhanden ist Bachelor."),
    ("Master in Informatik vorausgesetzt.", "Verlangt Master, vorhanden ist Bachelor."),
    ("Doktorat in Informatik erforderlich.", "Verlangt Doktorat, vorhanden ist Bachelor."),
    ("Fundierte Java-Kenntnisse sind zwingend.", "Schwerpunkt Java, im Suchprofil ausgeschlossen."),
    ("Erfahrung mit .NET ist ein Muss, sie muss vorhanden sein.", "Schwerpunkt .NET, im Suchprofil ausgeschlossen."),
])
def test_an_explicit_requirement_the_person_does_not_meet_marks_the_hit(text, reason):
    assert check(text) == reason


def test_an_excluded_technology_in_the_title_marks_the_hit():
    assert check("Python, SQL.", title="Senior Java Developer") == "Schwerpunkt Java, im Suchprofil ausgeschlossen."
    assert check("Python, SQL.", title="JavaScript Developer") == ""


@pytest.mark.parametrize("text", [
    "Französisch A2 ist zwingend.",  # at the person's level
    "Deutsch auf Muttersprachniveau ist Pflicht.",
    "Deutsch oder Französisch auf Niveau C1 ist zwingend.",
    "Deutsch- oder Französischkenntnisse auf C1 sind Pflicht.",
    "Deutsch und/oder Französisch C1 erforderlich.",
    "Bachelor oder Master ist zwingend.",
    "Ein abgeschlossener Bachelor ist Voraussetzung.",
])
def test_an_explicit_requirement_the_person_meets_or_with_an_alternative_passes(text):
    assert check(text) == ""


UNMARKED = [
    # hedged
    "Französisch C1 von Vorteil.",
    "Französisch C1 ist wünschenswert.",
    "Idealerweise Französisch C1, aber keine Voraussetzung.",
    "Französisch C1 is nice to have.",
    "Französisch C1 ist ein Plus.",
    "Français C1 souhaité.",
    "Französisch C1 ist nicht zwingend.",
    "Ein Master ist keine Voraussetzung.",
    "Masterabschluss von Vorteil, aber nicht erforderlich.",
    "Master oder gleichwertige Erfahrung erforderlich.",
    "Java-Kenntnisse sind wünschenswert, aber nicht zwingend.",
    # a level given only as an adjective, even with a marker
    "Gute Französischkenntnisse sind zwingend.",
    "Fliessend Französisch ist Pflicht.",
    "Verhandlungssicheres Französisch erforderlich.",
    "Perfekte Französischkenntnisse in Wort und Schrift sind Voraussetzung.",
    # no marker
    "Französisch C1.",
    "Sehr gute Französischkenntnisse (C1) in Wort und Schrift.",
    "Abgeschlossener Master in Informatik.",
    "Sie bringen 5 Jahre Erfahrung mit Java mit.",
    "Seit 25 Jahren setzen wir auf Python und Java.",
    "Wir bieten Englischkurse bis zum Niveau C2.",
    "Weiterbildungsmöglichkeiten bis zum Doktorat.",
    # a technology listed among others
    "Kenntnisse in Python, Java und SQL sind erforderlich.",
    "Java oder Kotlin ist zwingend.",
    "Erfahrung mit Spring/Java ist Voraussetzung.",
    # the country is no language
    "Reisebereitschaft nach Deutschland ist zwingend, Englisch C1 von Vorteil.",
]


@pytest.mark.parametrize("text", UNMARKED)
def test_hedged_and_vague_phrasings_stay_unmarked(text):
    assert check(text) == ""


# The phrasings of the earlier rejects of #185: each one once marked a hit that fits the person.
EARLIER_REJECTS = [
    "Erfahrung als Scrum-Master in agilen Teams.",
    "Erfahrung als Scrum-Master ist zwingend.",
    "Pflege der Master-Data ist erforderlich.",
    "Muttersprache Deutsch oder Französisch, gute Englischkenntnisse.",
    "Deutsch oder Französisch als Muttersprache ist zwingend.",
    "Sehr gute Deutsch- oder Französischkenntnisse.",
    "Deutsch und/oder Französisch fliessend.",
    "Sie bauen Cloud-native Lösungen in einem englischsprachigen Team.",
    "Sie entwickeln mit React Native und kommunizieren in Englisch.",
    "Sie planen und begleiten Promotion-Aktionen am POS.",
    "Sales Promotion und Key Account Management sind Pflicht.",
    "Dann passen Sie perfekt in unser englischsprachiges Team.",
    "Wir unterstützen Ihre Weiterbildung bis zum Master.",
    "Sehr gute analytische Fähigkeiten sowie Englischkenntnisse.",
    "Ausgeprägte Kundenorientierung, sehr gute analytische Fähigkeiten und Englischkenntnisse.",
    "Ausgezeichnete analytische Fähigkeiten und Englisch.",
    "Sehr gute IT-Kenntnisse und Englisch.",
    "Gute organisatorische Fähigkeiten und Englischkenntnisse",
    "Sie arbeiten sehr gut organisiert und sprechen Englisch.",
    "Sie arbeiten selbstständig, perfektionistisch und kommunizieren auf Englisch.",
    "Abgeschlossenes Studium (Bachelor). Du betreust Master-Studierende bei ihren Arbeiten.",
]


@pytest.mark.parametrize("text", EARLIER_REJECTS)
def test_the_phrasings_of_earlier_rejects_stay_unmarked(text):
    assert check(text) == ""
    assert precheck.check("Analyst", text, B2_ENGLISH) == ""


def test_swiss_german_and_standard_german_in_cv_yaml_count_as_german():
    cv = {"languages": [{"language": "Schweizerdeutsch", "fluency": "Muttersprache"}, {"language": "Hochdeutsch", "fluency": "C2"}]}
    person = precheck.person_of(cv, "# Suchprofil\n")

    assert person.languages == {"deutsch": 7}
    assert precheck.check("Python Entwickler", "Deutsch auf Muttersprachniveau.", person) == ""


def test_missing_person_data_keeps_every_hit():
    nobody = precheck.person_of({}, "# Suchprofil\n")
    assert precheck.check("Senior Java Developer", "Master Pflicht. Französisch C1 ist zwingend.", nobody) == ""


def ad(number: int, title: str, text: str) -> dict:
    return {"portal": "jobs.ch", "portal_id": f"v-{number}", "stelle": title, "firma": "Beispiel AG", "ort": "Bern",
            "link": f"https://www.jobs.ch/de/stellenangebote/detail/v-{number}/", "alter_tage": 2, "text": text}


def test_received_hits_carry_the_reason_and_stay(server):  # noqa: F811
    daten = server.kontext.daten
    (daten / "suchprofil.md").write_text(PROFILE, encoding="utf-8")
    (daten / "cv.yaml").write_text(yaml.safe_dump(CV, allow_unicode=True), encoding="utf-8")
    failing = ad(1, "Data Engineer", "Sehr gute Französischkenntnisse (C1) sind Pflicht.")
    status, received = post(server, "/api/suche/treffer", {"treffer": [failing, ad(2, "Python Developer", "Python, SQL.")]})
    assert (status, received["neu"]) == (200, 2)
    listed = {hit["portal_id"]: hit for hit in json.loads(get(server, "/api/suche/liste")[2])["treffer"]}
    assert listed["v-1"]["vorpruefung"] == "Verlangt Französisch auf Niveau C1, vorhanden ist A2."
    assert "vorpruefung" not in listed["v-2"]
