"""Personal data is replaced before any AI call and restored afterwards (MIN-334)."""
import pytest
import yaml

import build
from ai.personal import secrets_from_application, secrets_from_building_blocks, secrets_from_cv
from ai.pseudonym import PLACEHOLDER, PseudonymError, Pseudonymizer, Secret

CV = yaml.safe_load((build.ROOT / "data" / "beispiel.yaml").read_text(encoding="utf-8"))
VALUES = ["Erika Beispiel", "erika@example.ch", "079 000 00 00", "www.example.ch", "Musterweg 1", "3000",
          "https://github.com/example"]


def make(*extra):
    return Pseudonymizer(secrets_from_cv(CV) + list(extra))


def test_every_personal_value_of_the_cv_is_replaced():
    text = "Erika Beispiel, Musterweg 1, 3000 Bern, erika@example.ch, 079 000 00 00, www.example.ch, https://github.com/example"

    masked = make().mask(text)

    assert all(v not in masked for v in VALUES)
    assert "Bern" in masked  # the town stays, it matters for the commute
    assert masked.startswith("{{NAME}}, {{ADDRESS}}, {{POSTAL_CODE}} Bern")


def test_unmask_gives_back_the_same_text():
    p = make()
    text = "Mit freundlichen Grüssen\nErika Beispiel\nerika@example.ch · 079 000 00 00"

    assert p.unmask(p.mask(text)) == text


def test_first_name_alone_and_other_spellings_are_found():
    p = make()

    masked = p.mask("Liebe Grüsse, Erika. ERIKA BEISPIEL, Tel. 0790000000 oder 079.000.00.00")

    assert "Erika" not in masked and "ERIKA" not in masked
    assert "0790000000" not in masked and "079.000.00.00" not in masked
    p.check_clean(masked)


def test_values_in_the_job_ad_and_building_blocks_are_replaced_too():
    ad = "Bei Fragen hilft Petra Meier (petra.meier@firma.ch). Bewerbungen von Erika Beispiel bevorzugt."
    entry = {"kontaktperson": "Frau Petra Meier", "kontakt": "petra.meier@firma.ch"}
    blocks = "## Rahmen\n- Referenz: Hans Muster, Beispiel AG\n"
    p = make(*secrets_from_application(entry), *secrets_from_building_blocks(blocks))

    masked = p.mask(ad + "\n" + blocks)

    for value in ["Petra", "Meier", "petra.meier@firma.ch", "Erika", "Hans Muster"]:
        assert value not in masked
    p.check_clean(masked)


def test_check_clean_refuses_text_with_a_personal_value():
    with pytest.raises(PseudonymError, match="NAME"):
        make().check_clean(["Anschreiben von Erika Beispiel"])


def test_unknown_placeholder_in_the_answer_is_an_error():
    with pytest.raises(PseudonymError, match="FIRMA"):
        make().unmask("Sehr geehrte Damen und Herren der {{FIRMA}}")


def test_placeholders_written_slightly_differently_are_restored():
    assert make().unmask("Gruss, {{ name_first }}") == "Gruss, Erika"


def test_placeholder_syntax_in_the_input_cannot_trick_the_restore():
    p = make()

    masked = p.mask("Vorlage: {{NAME}} einsetzen")

    assert "{{NAME}}" not in masked
    assert p.unmask(masked) == "Vorlage: { {NAME}} einsetzen"


def test_three_part_names_get_distinct_placeholders():
    p = Pseudonymizer([Secret("NAME", "Anna Maria Beispiel"), Secret("NAME_LAST", "Maria Beispiel"),
                       Secret("NAME_LAST", "Beispiel")])

    assert p.unmask(p.mask("Anna Maria Beispiel; Maria Beispiel; Beispiel")) == "Anna Maria Beispiel; Maria Beispiel; Beispiel"
    assert len(p.fields) == 3


def test_birth_date_in_details_and_school_of_minors():
    cv = {"basics": {"name": "Lea Muster", "details": ["Geboren am 3.4.2010"]},
          "education": [{"institution": "Oberstufenschule Beispielstadt"}]}

    adult = Pseudonymizer(secrets_from_cv(cv))
    minor = Pseudonymizer(secrets_from_cv(cv, minor=True))

    assert "{{BIRTH_DATE}}" in adult.mask("Geboren am 3.4.2010")
    assert "Oberstufenschule" in adult.mask("Oberstufenschule Beispielstadt")
    assert minor.mask("Oberstufenschule Beispielstadt") == "{{SCHOOL_1}}"


def test_fields_name_what_was_replaced_without_values():
    fields = make().fields

    assert {"NAME", "EMAIL", "PHONE", "ADDRESS"} <= set(fields)
    assert not any("@" in f or "Erika" in f for f in fields)


def test_json_like_data_is_restored_everywhere():
    p = make()
    data = {"text": "{{NAME}}", "list": ["{{EMAIL}}", 3], "nested": {"a": "{{PHONE}}"}}

    assert p.unmask_data(data) == {"text": "Erika Beispiel", "list": ["erika@example.ch", 3],
                                   "nested": {"a": "079 000 00 00"}}


# Variants found in the review (MIN-334)


@pytest.mark.parametrize("detail, written", [
    ("geboren 1. Mai 2011", "1. Mai 2011"), ("geboren 1. Mai 2011", "01.05.2011"), ("geboren am 3.4.2010", "2010-04-03"),
    ("Geburtsdatum: 03.04.10", "3.4.2010"), ("geboren 2011-05-01", "1.5.11"), ("geboren 2011-05-01", "1. Mai 2011"),
])
def test_birth_date_in_any_usual_format(detail, written):
    p = Pseudonymizer(secrets_from_cv({"basics": {"name": "Lea Muster", "details": [detail]}}))

    masked = p.mask(f"Geburtsdatum {written}, Lehrbeginn 2027")

    assert "{{BIRTH_DATE}}" in masked and "2027" in masked
    assert p.unmask(masked).startswith("Geburtsdatum ")


@pytest.mark.parametrize("braces", ["{{{EMAIL}}}", "{{{{EMAIL}}}}", "{{ EMAIL }}"])
def test_no_placeholder_can_come_from_the_input(braces):
    p = make()

    masked = p.mask(f"Bewerbungen an {braces}")

    assert not PLACEHOLDER.search(masked)
    assert "erika@example.ch" not in p.unmask(masked)


@pytest.mark.parametrize("written", ["+41 79 000 00 00", "0041 79 000 00 00", "+41 (0)79 000 00 00",
                                     "(079) 000 00 00", "079 / 000 00 00", "079-000-00-00"])
def test_phone_in_any_swiss_notation(written):
    masked = make().mask(f"Telefon {written} (mobil)")

    assert masked == "Telefon {{PHONE}} (mobil)"


@pytest.mark.parametrize("written", ["github.com/example", "https://github.com/example/", "www.github.com/example",
                                     "example.ch", "https://www.example.ch"])
def test_links_with_or_without_scheme(written):
    masked = make().mask(f"Siehe {written} für mehr")

    assert "example" not in masked


def test_contacts_in_the_ad_are_found_without_the_register():
    ad = "Auskunft: Frau Dr. Petra Meier, p.meier@firma.ch, 031 000 00 00. Meier freut sich auf Erikas Bewerbung."
    found = make()

    from ai.personal import secrets_found_in
    p = found.extended(secrets_found_in([ad]))
    masked = p.mask(ad)

    for value in ["Petra", "Meier", "p.meier@firma.ch", "031 000 00 00", "Erika"]:
        assert value not in masked
    p.check_clean([masked])
    assert p.unmask(masked) == ad


def test_contact_titles_and_two_ways_of_contact():
    secrets = secrets_from_application({"kontaktperson": "Frau Dr. Petra Meier und Herr Hans Muster",
                                        "kontakt": "petra.meier@firma.ch, 031 000 00 00"})
    by_field = {s.field: s.value for s in Pseudonymizer(secrets)._secrets}

    assert by_field["CONTACT_LAST"] == "Meier" and by_field["CONTACT_FIRST"] == "Petra"
    assert by_field["CONTACT_2_LAST"] == "Muster"
    assert by_field["CONTACT_EMAIL"] == "petra.meier@firma.ch" and by_field["CONTACT_PHONE"] == "031 000 00 00"


def test_middle_names_and_double_names_get_one_word_each():
    p = Pseudonymizer(secrets_from_cv({"basics": {"name": "Anna Maria Muster-Beispiel"}}))
    by_field = {s.field: s.value for s in p._secrets}

    assert by_field["NAME_LAST"] == "Muster-Beispiel" and by_field["NAME_MIDDLE"] == "Maria"
    assert "Muster" not in p.mask("Frau Muster und Herr Beispiel")


@pytest.mark.parametrize("text", ["Erika\nBeispiel", "ErikaBeispiel", "erika.beispiel@other.ch",
                                  "Mail an kontakt@firma.ch", "Ruf 044 000 00 00 an", "Musterweg1"])
def test_last_check_does_not_rely_on_the_masking_patterns(text):
    with pytest.raises(PseudonymError):
        make().check_clean([text])


def test_postal_code_that_looks_like_a_year_keeps_the_years():
    cv = {"basics": {"name": "Lea Muster", "location": {"postalCode": "2000", "city": "Neuchâtel"}}}

    assert Pseudonymizer(secrets_from_cv(cv)).mask("seit 2000 in 2000 Neuchâtel") == "seit 2000 in 2000 Neuchâtel"
