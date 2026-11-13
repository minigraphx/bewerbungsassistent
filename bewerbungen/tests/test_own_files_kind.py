"""The kind of a certificate or reference can change on „Lebenslauf und Dateien“ (#264): the app guesses it from the
name, the person corrects it, and the file moves to the folder of its kind."""
import json
import zipfile

import pytest

import certificates
import proof_kinds

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
    assert [d["beschreibung"] for d in before] == ["Stand vor: Arbeitszeugnis Beispiel AG.pdf als Arbeitszeugnis eingeordnet"]
    assert [d["beschreibung"] for d in after] == ["Arbeitszeugnis Beispiel AG.pdf als Arbeitszeugnis eingeordnet"]


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


# G63 (#282): Arbeitszeugnis, Diplom and Zertifikat. Diplomas share the folder of the certificates, so the choice per
# application and its ZIP stay; what tells them apart is recorded per file.
DIPLOMA = "dokumente/zertifikate/Diplom Informatik.pdf"


def kinds_of(answer):
    return {kind: [f["datei"] for f in answer[kind]] for kind in ("zeugnis", "diplom", "zertifikat")}


def test_a_diploma_is_listed_as_a_diploma(server):  # noqa: F811
    status, answer = upload(server, "diplom", "Diplom Informatik.pdf")

    assert status == 200
    assert (server.kontext.daten / DIPLOMA).read_bytes() == PDF
    assert kinds_of(answer) == {"zeugnis": [], "diplom": [DIPLOMA], "zertifikat": []}
    assert kinds_of(get_listing(server))["diplom"] == [DIPLOMA]


def get_listing(s):
    return json.loads(get(s, "/api/dateien")[2])


def test_a_file_filed_before_keeps_its_kind(server):  # noqa: F811
    daten = server.kontext.daten
    for rel in (DIPLOMA, "dokumente/zeugnisse/Diplom Englisch.pdf"):
        (daten / rel).parent.mkdir(parents=True, exist_ok=True)
        (daten / rel).write_bytes(PDF)

    assert kinds_of(get_listing(server)) == {"zeugnis": ["dokumente/zeugnisse/Diplom Englisch.pdf"], "diplom": [],
                                             "zertifikat": [DIPLOMA]}


def test_a_certificate_becomes_a_diploma_in_place_and_its_zip_stays(server):  # noqa: F811
    upload(server, "zertifikat", "Diplom Informatik.pdf")
    entry = new_entry(server)
    post(server, "/api/zertifikate", {"id": entry["id"], "dateien": [DIPLOMA]})
    zip_before = certificates.zip_path(server.kontext.daten, entry["id"]).read_bytes()

    status, answer = change(server, DIPLOMA, "diplom")

    daten = server.kontext.daten
    assert status == 200
    assert kinds_of(answer) == {"zeugnis": [], "diplom": [DIPLOMA], "zertifikat": []}
    assert (daten / DIPLOMA).read_bytes() == PDF
    assert Register(daten).hole(entry["id"])["zertifikate"] == [DIPLOMA]
    assert certificates.zip_path(daten, entry["id"]).read_bytes() == zip_before
    assert json.loads(get(server, "/api/zertifikate", id=entry["id"])[2])["verfuegbar"] == [DIPLOMA]


def test_the_kind_of_a_diploma_can_be_undone_from_the_drafts(server):  # noqa: F811
    upload(server, "zertifikat", "Diplom Informatik.pdf")

    change(server, DIPLOMA, "diplom")
    change(server, DIPLOMA, "zertifikat")

    drafts = json.loads(get(server, "/api/entwuerfe", datei=proof_kinds.FILE)[2])["entwuerfe"]
    assert {d["beschreibung"] for d in drafts} >= {"Diplom Informatik.pdf als Diplom eingeordnet",
                                                  "Diplom Informatik.pdf als Zertifikat eingeordnet"}
    assert kinds_of(get_listing(server))["zertifikat"] == [DIPLOMA]


def test_a_diploma_becomes_a_reference_and_back(server):  # noqa: F811
    upload(server, "diplom", "Diplom Informatik.pdf")
    reference = "dokumente/zeugnisse/Diplom Informatik.pdf"

    assert kinds_of(change(server, DIPLOMA, "zeugnis")[1]) == {"zeugnis": [reference], "diplom": [], "zertifikat": []}
    assert kinds_of(change(server, reference, "diplom")[1]) == {"zeugnis": [], "diplom": [DIPLOMA], "zertifikat": []}


def test_a_diploma_that_is_removed_and_added_again_takes_the_new_kind(server):  # noqa: F811
    upload(server, "diplom", "Diplom Informatik.pdf")
    post(server, "/api/dateien/entfernen", {"datei": DIPLOMA})

    assert proof_kinds.load(server.kontext.daten) == {}
    assert kinds_of(upload(server, "zertifikat", "Diplom Informatik.pdf")[1])["zertifikat"] == [DIPLOMA]


def test_uploading_a_file_again_keeps_the_kind_the_person_gave_it(server):  # noqa: F811
    upload(server, "zertifikat", "Diplom Informatik.pdf")
    change(server, DIPLOMA, "diplom")

    status, answer = upload(server, "zertifikat", "diplom informatik.PDF", PDF + b"neu")

    assert status == 200
    assert kinds_of(answer)["diplom"] == [DIPLOMA]
    assert (server.kontext.daten / DIPLOMA).read_bytes() == PDF + b"neu"


def test_a_changed_diploma_refreshes_the_zip_of_an_unsent_application(server):  # noqa: F811
    upload(server, "diplom", "Diplom Informatik.pdf")
    entry = new_entry(server)
    post(server, "/api/zertifikate", {"id": entry["id"], "dateien": [DIPLOMA]})

    upload(server, "diplom", "Diplom Informatik.pdf", PDF + b"neu")

    packed = zipfile.ZipFile(certificates.zip_path(server.kontext.daten, entry["id"]))
    assert packed.read("Diplom Informatik.pdf") == PDF + b"neu"


def test_an_unreadable_record_of_kinds_is_named(server):  # noqa: F811
    record = server.kontext.daten / proof_kinds.FILE
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text("- [kaputt", encoding="utf-8")

    status, _, body = get(server, "/api/dateien")

    assert status == 400 and "arten.yaml" in json.loads(body)["fehler"]
