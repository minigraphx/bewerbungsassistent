"""Rules for uploaded documents (same cases as documents.test.cjs)."""
import pytest

import documents
from form_cases import CASES


@pytest.mark.parametrize("case", CASES["documentCases"], ids=lambda c: c["name"])
def test_shared_document_case(form, case):
    found = sorted(f"{e.path}|{e.code}" for e in documents.validate_documents(form, case["documents"]))
    assert found == sorted(f"{e['path']}|{e['code']}" for e in case["errors"])


def test_documents_must_be_a_list(form):
    assert [(e.path, e.code) for e in documents.validate_documents(form, {"a": 1})] == [("documents", "type")]


def test_messages_name_category_and_file(form):
    entries = [{"category": "zeugnisse", "name": "gross.pdf", "size": 20_000_000}]
    [error] = documents.validate_documents(form, entries)

    assert documents.describe(form, "job", entries, error) == "Arbeitszeugnisse, gross.pdf: Die Datei ist zu gross (höchstens 15 MB)."


@pytest.mark.parametrize("category, expected", [
    ("anschreiben-bisher", "Erlaubt sind PDF, Word (.docx, .doc) und Textdateien (.txt)."),
    ("zertifikate", "Erlaubt sind PDF, Word (.docx, .doc), Textdateien (.txt) und Bilder (.jpg, .png)."),
])
def test_wrong_type_names_what_the_category_accepts(form, category, expected):
    entries = [{"category": category, "name": "datei.exe", "size": 10}]
    [error] = documents.validate_documents(form, entries)

    assert documents.describe(form, "job", entries, error).endswith(f"Dieser Dateityp geht nicht. {expected}")


def test_every_category_names_known_file_types(form):
    types = form["documents"]["fileTypes"]
    for category in form["documents"]["categories"]:
        assert category["fileTypes"] and set(category["fileTypes"]) <= set(types)


def test_category_folders_are_safe_names(form):
    for category in form["documents"]["categories"]:
        assert documents.CATEGORY_ID.fullmatch(category["id"])
