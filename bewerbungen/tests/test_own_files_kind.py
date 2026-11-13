"""The kind of a certificate or reference can change on „Lebenslauf und Dateien“ (#264): the app guesses it from the
name, the person corrects it, and the file moves to the folder of its kind."""
import json

import pytest

from register import Register
from test_app import get, post, server  # noqa: F401  (server is a fixture)
from test_own_files import PDF, new_entry, upload

CERTIFICATE = "dokumente/zertifikate/Arbeitszeugnis Beispiel AG.pdf"
REFERENCE = "dokumente/zeugnisse/Arbeitszeugnis Beispiel AG.pdf"


def change(s, datei, art):
    return post(s, "/api/dateien/art", {"datei": datei, "art": art})


def test_a_certificate_becomes_a_reference_unchanged(server):  # noqa: F811
    upload(server, "zertifikat", "Arbeitszeugnis Beispiel AG.pdf")

    status, answer = change(server, CERTIFICATE, "zeugnis")

    daten = server.kontext.daten
    assert status == 200
    assert (daten / REFERENCE).read_bytes() == PDF
    assert not (daten / CERTIFICATE).exists()
    assert [f["datei"] for f in answer["zeugnis"]] == [REFERENCE]
    assert answer["zertifikat"] == []


def test_the_move_can_be_undone_from_the_drafts(server):  # noqa: F811
    placed_by_hand = server.kontext.daten / CERTIFICATE
    placed_by_hand.parent.mkdir(parents=True)
    placed_by_hand.write_bytes(PDF)

    change(server, CERTIFICATE, "zeugnis")

    before = json.loads(get(server, "/api/entwuerfe", datei=CERTIFICATE)[2])["entwuerfe"]
    after = json.loads(get(server, "/api/entwuerfe", datei=REFERENCE)[2])["entwuerfe"]
    assert [d["beschreibung"] for d in before] == ["Stand vor: Arbeitszeugnis Beispiel AG.pdf als Zeugnis eingeordnet"]
    assert [d["beschreibung"] for d in after] == ["Arbeitszeugnis Beispiel AG.pdf als Zeugnis eingeordnet"]


def test_a_chosen_certificate_no_longer_goes_along_once_it_is_a_reference(server):  # noqa: F811
    upload(server, "zertifikat", "Arbeitszeugnis Beispiel AG.pdf")
    upload(server, "zertifikat", "Python.pdf")
    entry = new_entry(server)
    both = [CERTIFICATE, "dokumente/zertifikate/Python.pdf"]
    post(server, "/api/zertifikate", {"id": entry["id"], "dateien": both})

    change(server, CERTIFICATE, "zeugnis")

    assert Register(server.kontext.daten).hole(entry["id"])["zertifikate"] == [both[1]]


def test_a_reference_becomes_a_certificate(server):  # noqa: F811
    upload(server, "zeugnis", "Diplom.pdf")

    status, answer = change(server, "dokumente/zeugnisse/Diplom.pdf", "zertifikat")

    assert status == 200
    assert [f["datei"] for f in answer["zertifikat"]] == ["dokumente/zertifikate/Diplom.pdf"]


def test_the_same_kind_changes_nothing(server):  # noqa: F811
    upload(server, "zertifikat", "Python.pdf")

    status, answer = change(server, "dokumente/zertifikate/Python.pdf", "zertifikat")

    assert status == 200
    assert [f["datei"] for f in answer["zertifikat"]] == ["dokumente/zertifikate/Python.pdf"]


def test_a_file_of_the_same_name_in_the_other_kind_is_never_replaced(server):  # noqa: F811
    upload(server, "zertifikat", "Arbeitszeugnis Beispiel AG.pdf")
    upload(server, "zeugnis", "arbeitszeugnis beispiel ag.PDF", PDF + b"other")

    status, answer = change(server, CERTIFICATE, "zeugnis")

    daten = server.kontext.daten
    assert status == 400 and "gleichen Namen" in answer["fehler"]
    assert (daten / CERTIFICATE).read_bytes() == PDF
    assert (daten / "dokumente/zeugnisse/arbeitszeugnis beispiel ag.PDF").read_bytes() == PDF + b"other"


@pytest.mark.parametrize("datei, art", [
    ("dokumente/lebenslauf.pdf", "zertifikat"), ("cv.yaml", "zeugnis"),
    ("dokumente/zertifikate/../../cv.yaml", "zeugnis"), (CERTIFICATE, "lebenslauf"), (CERTIFICATE, "anderes"),
    (None, "zeugnis")])
def test_only_listed_certificates_and_references_change_kind(server, datei, art):  # noqa: F811
    upload(server, "lebenslauf", "cv.pdf")
    upload(server, "zertifikat", "Arbeitszeugnis Beispiel AG.pdf")

    assert change(server, datei, art)[0] == 400

    daten = server.kontext.daten
    assert (daten / "dokumente/lebenslauf.pdf").is_file() and (daten / CERTIFICATE).is_file()
    assert (daten / "cv.yaml").is_file()
