"""Rule-based pre-check of an ad before rating (G33), with invented ads, profile and cv.yaml."""
import json

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


def test_the_person_comes_from_cv_yaml_and_the_profile():
    assert PERSON.languages == {"deutsch": 7, "englisch": 5, "französisch": 2}
    assert PERSON.degree == 3
    assert PERSON.excluded == ("Java", ".NET")


def test_a_language_above_the_persons_level_fails():
    reason = check("Ihr Profil: Python, SQL. Sehr gute Französischkenntnisse (C1) in Wort und Schrift.")
    assert reason == "Verlangt Französisch auf Niveau C1, vorhanden ist A2."


def test_a_language_at_or_below_the_level_or_only_welcome_passes():
    assert check("Fliessend Deutsch und gute Englischkenntnisse.") == ""
    assert check("Deutsch fliessend; Französisch von Vorteil.") == ""
    assert check("Französisch: Grundkenntnisse reichen.") == ""


def test_a_language_the_person_does_not_speak_fails():
    assert check("Verhandlungssicheres Italienisch ist Pflicht.") == "Verlangt Italienisch auf Niveau C2, vorhanden ist keine Angabe."


def test_an_ad_without_a_level_keeps_the_hit():
    assert check("Wir arbeiten in der ganzen Deutschschweiz. Französisch ist im Team verbreitet.") == ""


def test_a_mandatory_degree_the_person_lacks_fails():
    assert check("Sie bringen einen Masterabschluss in Informatik mit.") == "Verlangt Master, vorhanden ist Bachelor."
    assert check("Abgeschlossenes Doktorat (PhD) in Physik.") == "Verlangt Doktorat, vorhanden ist Bachelor."


def test_a_degree_with_an_alternative_or_at_the_level_passes():
    assert check("Master in Informatik oder gleichwertige Erfahrung.") == ""
    assert check("Abgeschlossenes Hochschulstudium (Bachelor oder Master).") == ""
    assert check("Erfahrung als Scrum Master und mit Master Data ist ein Plus. Sie arbeiten mit dem Product Owner.") == ""


def test_an_excluded_technology_as_main_requirement_fails():
    assert check("Wir suchen Verstärkung.", title="Senior Java Developer") == "Schwerpunkt Java, im Suchprofil ausgeschlossen."
    assert check("Mehrjährige Erfahrung mit .NET und C# ist Voraussetzung.") == "Schwerpunkt .NET, im Suchprofil ausgeschlossen."


def test_an_excluded_technology_on_the_side_passes():
    assert check("Python im Zentrum. Java-Kenntnisse sind von Vorteil.") == ""
    assert check("Unser Stack: Python, Java, Go.") == ""


def test_missing_person_data_keeps_every_hit():
    nobody = precheck.person_of({}, "# Suchprofil\n")
    assert precheck.check("Senior Java Developer", "Master Pflicht. Sehr gute Französischkenntnisse (C1).", nobody) == ""


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
