"""Names after French and English titles are replaced like those after „Frau“ and „Herr“ (#456, G10).

All names are invented. German results stay as they were: the German forms keep their own pattern.
"""
import pytest

from ai import personal
from ai.personal import secrets_from_application
from ai.pseudonym import Pseudonymizer


def found_values(text: str) -> set[str]:
    return {secret.value for secret in personal.secrets_found_in([text])}


def masked(text: str) -> str:
    return Pseudonymizer([]).extended(personal.secrets_found_in([text])).mask(text)


@pytest.mark.parametrize("text, names", [
    ("Contact : Madame Claire Exemple, responsable RH.", ["Claire", "Exemple"]),
    ("Monsieur Jean Exemple a travaillé chez nous.", ["Jean", "Exemple"]),
    ("Mme Claire Exemple, cheffe de projet", ["Claire", "Exemple"]),
    ("Mme. Claire Exemple", ["Claire", "Exemple"]),
    ("Mlle Claire Exemple", ["Claire", "Exemple"]),
    ("Mademoiselle Claire Exemple", ["Claire", "Exemple"]),
    ("M. Jean Exemple a signé ce certificat.", ["Jean", "Exemple"]),
    ("Pour tout renseignement, M. Exemple.", ["Exemple"]),
    ("M. Exemple répond volontiers.", ["Exemple"]),
    ("Contact: Mr John Sample, HR", ["John", "Sample"]),
    ("Contact: Mr. John Sample", ["John", "Sample"]),
    ("Mrs Jane Sample signed this reference.", ["Jane", "Sample"]),
    ("Ms. Jane Sample", ["Jane", "Sample"]),
    ("Ms Sample will be happy to help.", ["Sample"]),
    ("Mx Alex Sample", ["Alex", "Sample"]),
    ("Miss Jane Sample", ["Jane", "Sample"]),
    ("Madame Dr Claire Exemple", ["Claire", "Exemple"]),
    ("Mme Prof. Claire Exemple", ["Claire", "Exemple"]),
    ("M. Dr. Jean Exemple", ["Jean", "Exemple"]),
    ("Mr Dr John Sample", ["John", "Sample"]),
    ("Madame Élodie Exemple", ["Élodie", "Exemple"]),
    ("Monsieur Jean de Montexemple", ["Jean", "Montexemple"]),
    ("Monsieur de Montexemple", ["Montexemple"]),
    ("Madame Claire d'Exemple", ["Claire", "Exemple"]),
    ("Monsieur Jean Le Exemple", ["Jean", "Exemple"]),
    ("Mr John van Sample", ["John", "Sample"]),
    ("Madame Claire Exemple-Modèle", ["Claire", "Exemple-Modèle"]),
    ("- M. Exemple, chef d'équipe\n- Mme Modèle, RH", ["Exemple", "Modèle"]),
    ("Referenz: M. Muster, Teamleiter", ["Muster"]),
])
def test_names_after_french_and_english_titles_are_replaced(text, names):
    result = masked(text)

    for name in names:
        assert name not in result
    assert Pseudonymizer([]).extended(personal.secrets_found_in([text])).unmask(result) == text


@pytest.mark.parametrize("text", [
    "Monsieur Jean de Montexemple",
    "Monsieur Jean Le Exemple",
    "Mr John van Sample",
])
def test_particles_of_a_name_are_no_secret_of_their_own(text):
    """«de», «Le» or «van» would otherwise replace every such word in the text."""
    values = {value.lower() for value in found_values(text)}

    assert not values & {"de", "le", "van", "d'"}
    assert masked(f"{text}. Le poste de chef van la").endswith(". Le poste de chef van la")


@pytest.mark.parametrize("text", [
    "Madame, Monsieur,\nJe vous adresse ma candidature.",
    "Madame, Monsieur, nous avons le plaisir de vous informer",
    "Mesdames, Messieurs,",
    "Madame Monsieur,",
    "Dear Sir or Madam,",
    "Monsieur le Directeur, je postule",
    "Madame la Présidente,",
    "Monsieur Le Directeur",
    "Master of Science (M. Sc.) in Informatik",
    "M.Sc. ETH Zürich",
    "M.A. in Geschichte",
    "M. A. Universität Bern",
    "M. Eng. Maschinenbau",
    "M. Ed. Sekundarstufe I",
    "M. Phil. in Philosophie",
    "Version 2.M. Muster folgt",
    "Konfektionsgrösse M. Die Stelle ist befristet.",
    "Kategorie M. Wir bieten Ihnen viel.",
    "Abteilung M. Sie arbeiten im Team.",
    "Umsatz 2 Mrd. Franken",
    "MS Office und MSc",
    "Mr. Le Directeur",
    "Mme La Présidente",
    "Monsieur Directeur",
    "Dear Mr President,",
])
def test_salutations_degrees_and_abbreviations_are_no_names(text):
    assert personal.secrets_found_in([text]) == []
    assert masked(text) == text


@pytest.mark.parametrize("text, expected", [
    ("Auskunft: Frau Dr. Petra Meier", {"Petra Meier", "Petra", "Meier"}),
    ("Herr Muster freut sich auf Ihre Bewerbung", {"Muster"}),
    ("Frau Ihre Bewerbung", set()),
    ("Herr Prof. Hans Beispiel", {"Hans Beispiel", "Hans", "Beispiel"}),
    ("Frau Élodie Exemple", set()),
    ("Frau Petra Meier-Muster", {"Petra Meier-Muster", "Petra", "Meier-Muster", "Meier", "Muster"}),
    ("Sehr geehrte Damen und Herren", set()),
])
def test_german_results_stay_the_same(text, expected):
    assert found_values(text) == expected


@pytest.mark.parametrize("line, last", [
    ("Madame Claire Exemple", "Exemple"),
    ("Monsieur Jean Exemple", "Exemple"),
    ("Mme Claire Exemple", "Exemple"),
    ("M. Jean Exemple", "Exemple"),
    ("Mr John Sample", "Sample"),
    ("Ms. Jane Sample", "Sample"),
    ("Mx Alex Sample", "Sample"),
])
def test_recipients_with_french_and_english_titles_are_replaced(line, last):
    secrets = secrets_from_application({}, {"empfaenger": ["Exemple SA", line]})
    by_field = {secret.field: secret.value for secret in secrets}

    assert by_field["RECIPIENT_2_LAST"] == last
    assert "RECIPIENT_1" not in by_field


@pytest.mark.parametrize("line", ["Monsieur le Directeur", "Madame la Présidente", "Mme La Présidente"])
def test_a_recipient_named_by_function_is_no_name(line):
    assert secrets_from_application({}, {"empfaenger": ["Exemple SA", line]}) == []


@pytest.mark.parametrize("contact, first, last", [
    ("Madame Claire Exemple", "Claire", "Exemple"),
    ("Mr John Sample", "John", "Sample"),
    ("Mme Dr Claire Exemple", "Claire", "Exemple"),
])
def test_titles_are_stripped_from_a_contact_person(contact, first, last):
    by_field = {secret.field: secret.value for secret in secrets_from_application({"kontaktperson": contact})}

    assert by_field["CONTACT_FIRST"] == first and by_field["CONTACT_LAST"] == last
    assert by_field["CONTACT"] == f"{first} {last}"
