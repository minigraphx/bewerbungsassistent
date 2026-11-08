"""Validation of onboarding bundles against form.json; the same cases run in validate.js (node --test)."""
import pytest

import validation
from form_cases import CASES, apply_case, base_bundle, known_of


@pytest.mark.parametrize("case", CASES["cases"], ids=[c["name"] for c in CASES["cases"]])
def test_shared_case(form, case):
    errors = validation.validate_bundle(form, apply_case(case), known=known_of(case))

    found = sorted((e.path, e.code) for e in errors)
    expected = sorted((e["path"], e["code"]) for e in case["errors"])
    assert found == expected


def test_bundle_must_be_an_object(form):
    errors = validation.validate_bundle(form, ["no", "object"])

    assert [(e.path, e.code) for e in errors] == [("", "type")]


def test_messages_are_german_and_name_the_field(form):
    bundle = base_bundle("job")
    bundle["data"]["person"]["email"] = "erika(at)example.ch"

    [error] = validation.validate_bundle(form, bundle)
    message = validation.describe(form, "job", error)

    assert "E-Mail" in message
    assert "vorname.nachname@example.ch" in message


def test_messages_name_the_repeated_item(form):
    bundle = base_bundle("job")
    bundle["data"]["work"][1]["endDate"] = "2014"

    [error] = validation.validate_bundle(form, bundle)

    assert validation.describe(form, "job", error).startswith("Berufliche Stationen, Station 2, Bis")


def test_every_field_type_is_known(form):
    types = {f["type"] for s in form["sections"] for f in s["fields"]}

    assert types <= validation.FIELD_TYPES


@pytest.mark.parametrize("path", ["work.²", "work.0.highlights.²", "work.٣.position"])
def test_describe_ignores_non_ascii_digits(form, path):
    message = validation.describe(form, "job", validation.ValidationError(path, "unknown"))

    assert message.endswith("Gehört nicht zu dieser Vorlage.")
    assert "Zeile" not in message
