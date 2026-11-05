"""One PDF for a form with one field, and a folder with all files of an application (MIN-346)."""
import base64
import io
import json
import struct
import zlib

import pytest
from pypdf import PdfReader, PdfWriter

import apply
import form_copy
import merged_pdf
import routes_apply
from register import Register
from test_app import get, post, server  # noqa: F401  (server is a fixture)
from test_apply import ready
from test_own_files import upload
from test_own_letter import details

FOLDER_ROUTE = "/api/bewerben/ordner"


def real_png() -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    header = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(b"\x00\xff\xff\xff")) + chunk(b"IEND", b"")


def pdf_with_pages(pages: int) -> bytes:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=200, height=200)
    stream = io.BytesIO()
    writer.write(stream)
    return stream.getvalue()


def folder_of(s, entry):
    return s.kontext.daten / "bewerbungen" / entry["id"]


def with_documents(s, cv=1, letter=2):
    entry = ready(s)
    (folder_of(s, entry) / "lebenslauf.pdf").write_bytes(pdf_with_pages(cv))
    (folder_of(s, entry) / "anschreiben.pdf").write_bytes(pdf_with_pages(letter))
    return entry


def choose_certificate(s, entry, name, data):
    upload(s, "zertifikat", name, data)
    register = Register(s.kontext.daten)
    register.speichere({**register.hole(entry["id"]), "zertifikate": [f"dokumente/zertifikate/{name}"]})


def keys_of(s, entry) -> dict[str, str]:
    files = json.loads(get(s, "/api/bewerben/daten", id=entry["id"])[2])["dateien"]
    return {f["schluessel"]: f["name"] for f in files}


def part_of(s, entry, key, part=0):
    status, _, content = get(s, "/api/bewerben/datei", id=entry["id"], schluessel=key, teil=str(part))
    return status, json.loads(content)


def pages_of(data: bytes) -> int:
    return len(PdfReader(io.BytesIO(data)).pages)


def test_everything_goes_into_one_pdf_letter_first(server):  # noqa: F811
    entry = with_documents(server, cv=1, letter=2)
    upload(server, "zeugnis", "Zeugnis.pdf", pdf_with_pages(3))
    choose_certificate(server, entry, "Kurs.pdf", pdf_with_pages(4))

    status, part = part_of(server, entry, merged_pdf.ALL)

    assert status == 200 and part["typ"] == "application/pdf" and part["name"].startswith("Unterlagen")
    assert pages_of(base64.b64decode(part["daten"])) == 1 + 2 + 3 + 4
    paths = merged_pdf.sources(server.kontext.daten, Register(server.kontext.daten).hole(entry["id"]))[merged_pdf.ALL]
    assert [p.name for p in paths] == ["anschreiben.pdf", "lebenslauf.pdf", "Zeugnis.pdf", "Kurs.pdf"]


def test_the_proofs_are_references_and_chosen_certificates(server):  # noqa: F811
    entry = with_documents(server)
    upload(server, "zeugnis", "Zeugnis.pdf", pdf_with_pages(3))
    choose_certificate(server, entry, "Kurs.pdf", pdf_with_pages(4))
    upload(server, "zertifikat", "NichtGewaehlt.pdf", pdf_with_pages(5))

    status, part = part_of(server, entry, merged_pdf.PROOFS)

    assert status == 200 and pages_of(base64.b64decode(part["daten"])) == 3 + 4


def test_an_image_becomes_a_page(server):  # noqa: F811
    entry = with_documents(server, cv=1, letter=1)
    upload(server, "zeugnis", "Zeugnis.png", real_png())

    status, part = part_of(server, entry, merged_pdf.ALL)

    assert status == 200 and pages_of(base64.b64decode(part["daten"])) == 3


def test_one_pdf_is_only_offered_when_there_is_something_to_join(server):  # noqa: F811
    entry = with_documents(server)
    assert merged_pdf.ALL in keys_of(server, entry) and merged_pdf.PROOFS not in keys_of(server, entry)

    upload(server, "zeugnis", "A.pdf", pdf_with_pages(1))
    assert merged_pdf.PROOFS not in keys_of(server, entry)
    upload(server, "zeugnis", "B.pdf", pdf_with_pages(1))
    assert merged_pdf.PROOFS in keys_of(server, entry)

    (folder_of(server, entry) / "anschreiben.pdf").unlink()
    (server.kontext.daten / "dokumente" / "zeugnisse" / "A.pdf").unlink()
    (server.kontext.daten / "dokumente" / "zeugnisse" / "B.pdf").unlink()
    assert merged_pdf.ALL not in keys_of(server, entry)


def test_a_file_that_cannot_be_joined_is_named_and_nothing_goes_out(server):  # noqa: F811
    entry = with_documents(server)
    (folder_of(server, entry) / "anschreiben.pdf").write_bytes(b"%PDF-1.4 kaputt")

    status, part = part_of(server, entry, merged_pdf.ALL)

    assert status == 400 and "anschreiben.pdf" in part["fehler"]
    assert form_copy.copies(server.kontext.daten, entry["id"]) == {}


def test_a_type_without_a_page_is_named(server):  # noqa: F811
    entry = with_documents(server)
    folder = server.kontext.daten / "dokumente" / "zeugnisse"
    folder.mkdir(parents=True)
    (folder / "Zeugnis.docx").write_bytes(b"PK word")

    status, part = part_of(server, entry, merged_pdf.ALL)

    assert status == 400 and "Zeugnis.docx" in part["fehler"]


def test_the_record_names_the_joined_pdf_the_form_got(server):  # noqa: F811
    entry = with_documents(server)
    _, part = part_of(server, entry, merged_pdf.ALL)

    status, answer = post(server, "/api/bewerben/abgeschickt", {"id": entry["id"]})

    saved = Register(server.kontext.daten).hole(entry["id"])["versand"]["dateien"]
    assert status == 200 and answer["hinweise"] == []
    assert (server.kontext.daten / saved[merged_pdf.ALL]).read_bytes() == base64.b64decode(part["daten"])
    assert "lebenslauf" in saved


def test_a_changed_source_counts_as_another_version(server):  # noqa: F811
    entry = with_documents(server)
    part_of(server, entry, merged_pdf.ALL)
    assert details(server, entry["id"])["formular_abweichend"] == []

    (folder_of(server, entry) / "lebenslauf.pdf").write_bytes(pdf_with_pages(7))

    assert details(server, entry["id"])["formular_abweichend"] == [merged_pdf.ALL]
    answer = post(server, "/api/bewerben/abgeschickt", {"id": entry["id"]})[1]
    assert any("Unterlagen" in hint for hint in answer["hinweise"])
    saved = Register(server.kontext.daten).hole(entry["id"])["versand"]["dateien"]
    assert pages_of((server.kontext.daten / saved[merged_pdf.ALL]).read_bytes()) == 1 + 2


def test_all_parts_come_from_the_same_joined_pdf(server, monkeypatch):  # noqa: F811
    monkeypatch.setattr(apply, "PART_BYTES", 300)
    entry = with_documents(server)
    _, first = part_of(server, entry, merged_pdf.ALL)
    (folder_of(server, entry) / "lebenslauf.pdf").write_bytes(pdf_with_pages(7))

    rest = [part_of(server, entry, merged_pdf.ALL, number)[1] for number in range(1, first["teile"])]

    joined = b"".join(base64.b64decode(part["daten"]) for part in [first, *rest])
    assert first["teile"] > 1 and pages_of(joined) == 3


@pytest.fixture
def revealed(monkeypatch):
    """Tests never open a window of the file manager."""
    shown = []
    monkeypatch.setattr(routes_apply.ordner, "reveal", lambda folder, platform: shown.append(folder))
    return shown


def test_the_folder_holds_all_files_and_is_shown(server, revealed):  # noqa: F811
    entry = with_documents(server)
    upload(server, "zeugnis", "Zeugnis Muster.pdf", pdf_with_pages(1))

    status, answer = post(server, FOLDER_ROUTE, {"id": entry["id"]})

    folder = folder_of(server, entry) / form_copy.HAND_FOLDER
    names = {path.name for path in folder.iterdir()}
    assert status == 200 and revealed == [folder] and answer["ordner"] == str(folder)
    assert "Zeugnis Muster.pdf" in names and any(n.startswith("Lebenslauf") for n in names)
    assert any(n.startswith("Anschreiben") for n in names) and any(n.startswith("Unterlagen") for n in names)
    assert sorted(answer["dateien"]) == sorted(names)


def test_the_folder_shows_what_counts_now(server, revealed):  # noqa: F811
    entry = with_documents(server)
    upload(server, "zeugnis", "Alt.pdf", pdf_with_pages(1))
    post(server, FOLDER_ROUTE, {"id": entry["id"]})

    (server.kontext.daten / "dokumente" / "zeugnisse" / "Alt.pdf").unlink()
    post(server, FOLDER_ROUTE, {"id": entry["id"]})

    assert "Alt.pdf" not in {p.name for p in (folder_of(server, entry) / form_copy.HAND_FOLDER).iterdir()}


def test_the_folder_says_nothing_about_what_a_form_got(server, revealed):  # noqa: F811
    entry = with_documents(server)
    post(server, FOLDER_ROUTE, {"id": entry["id"]})

    assert form_copy.copies(server.kontext.daten, entry["id"]) == {}


def test_a_join_that_fails_leaves_the_single_files(server, revealed):  # noqa: F811
    entry = with_documents(server)
    (folder_of(server, entry) / "anschreiben.pdf").write_bytes(b"%PDF-1.4 kaputt")

    status, answer = post(server, FOLDER_ROUTE, {"id": entry["id"]})

    assert status == 200 and any(n.startswith("Lebenslauf") for n in answer["dateien"])
    assert not any(n.startswith("Unterlagen") for n in answer["dateien"])
    assert any("anschreiben.pdf" in hint for hint in answer["hinweise"])


def test_a_folder_that_does_not_open_still_gives_the_path(server, monkeypatch):  # noqa: F811
    entry = with_documents(server)

    def fail(*_):
        raise ValueError("Der Ordner liess sich nicht öffnen")

    monkeypatch.setattr(routes_apply.ordner, "reveal", fail)
    status, answer = post(server, FOLDER_ROUTE, {"id": entry["id"]})

    assert status == 200 and answer["ordner"] and answer["hinweise"]


def test_no_folder_after_the_dispatch_and_it_goes_away_with_it(server, revealed):  # noqa: F811
    entry = with_documents(server)
    post(server, FOLDER_ROUTE, {"id": entry["id"]})
    post(server, "/api/bewerben/abgeschickt", {"id": entry["id"]})

    assert not (folder_of(server, entry) / form_copy.HAND_FOLDER).exists()
    assert post(server, FOLDER_ROUTE, {"id": entry["id"]})[0] == 400
    assert revealed == [folder_of(server, entry) / form_copy.HAND_FOLDER]


def test_no_folder_without_files(server, revealed):  # noqa: F811
    entry = Register(server.kontext.daten).neu(firma="Leer AG", stelle="Test")

    assert post(server, FOLDER_ROUTE, {"id": entry["id"]})[0] == 400
    assert revealed == []


@pytest.mark.parametrize("body", [{}, {"id": 5}, []])
def test_the_folder_route_checks_its_input(server, revealed, body):  # noqa: F811
    assert post(server, FOLDER_ROUTE, body)[0] == 400


def test_a_new_form_leaves_the_folder_alone(server, revealed):  # noqa: F811
    entry = with_documents(server)
    post(server, FOLDER_ROUTE, {"id": entry["id"]})

    post(server, "/api/bewerben/stand", {"id": entry["id"], "stand": "geoeffnet"})

    assert (folder_of(server, entry) / form_copy.HAND_FOLDER).is_dir()


def test_unchanged_sources_are_not_joined_again(server, monkeypatch):  # noqa: F811
    """A second frame asking at the same time must not swap the file under the parts of the first."""
    entry = with_documents(server)
    first = part_of(server, entry, merged_pdf.ALL)
    built = []
    monkeypatch.setattr(merged_pdf, "build", lambda paths: built.append(paths) or b"%PDF-neu")

    assert part_of(server, entry, merged_pdf.ALL) == first and built == []


def test_a_changed_source_is_joined_again(server, monkeypatch):  # noqa: F811
    entry = with_documents(server)
    part_of(server, entry, merged_pdf.ALL)
    (folder_of(server, entry) / "lebenslauf.pdf").write_bytes(pdf_with_pages(4))
    built = []
    monkeypatch.setattr(merged_pdf, "build", lambda paths: built.append(paths) or b"%PDF-neu")

    part_of(server, entry, merged_pdf.ALL)

    assert len(built) == 1


def test_a_copy_that_vanishes_during_a_poll_counts_as_changed(server):  # noqa: F811
    entry = with_documents(server)
    daten = server.kontext.daten
    part_of(server, entry, merged_pdf.ALL)
    kept = {merged_pdf.ALL: form_copy.copy_path(daten, entry["id"], merged_pdf.ALL)}
    form_copy.forget(daten, entry["id"])

    assert merged_pdf.changed(daten, Register(daten).hole(entry["id"]), kept) == [merged_pdf.ALL]


def test_a_file_named_like_a_generated_one_does_not_replace_it(server, revealed):  # noqa: F811
    entry = with_documents(server)
    name = keys_of(server, entry)["lebenslauf"]
    upload(server, "zeugnis", name, pdf_with_pages(3))

    _, answer = post(server, FOLDER_ROUTE, {"id": entry["id"]})

    folder = folder_of(server, entry) / form_copy.HAND_FOLDER
    assert len(answer["dateien"]) == len(set(answer["dateien"])) == len(list(folder.iterdir()))
    assert pages_of((folder / name).read_bytes()) == 1


def test_the_folder_goes_even_when_the_copies_cannot(server, monkeypatch):  # noqa: F811
    entry = with_documents(server)
    daten = server.kontext.daten
    form_copy.hand_folder(daten, entry["id"]).mkdir(parents=True)

    def refuse(*_):
        raise OSError("gesperrt")

    monkeypatch.setattr(form_copy, "forget", refuse)

    with pytest.raises(OSError):
        form_copy.forget_all(daten, entry["id"])

    assert not form_copy.hand_folder(daten, entry["id"]).exists()
