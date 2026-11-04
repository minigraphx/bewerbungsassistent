"""Reading text from uploaded documents, locally and defensively (MIN-367)."""
import io
import pathlib
import zipfile

import pytest

import import_documents
import read_documents
from archive import Document


def make_pdf(*pages: str) -> bytes:
    """A small valid PDF with one line of text per page."""
    objects = []
    kids = " ".join(f"{3 + 2 * i} 0 R" for i in range(len(pages)))
    objects.append("<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>")
    font = 3 + 2 * len(pages)
    for index, text in enumerate(pages):
        content = f"BT /F1 12 Tf 50 700 Td ({text}) Tj ET"
        objects.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents {4 + 2 * index} 0 R "
                       f"/Resources << /Font << /F1 {font} 0 R >> >> >>")
        objects.append(f"<< /Length {len(content)} >>\nstream\n{content}\nendstream")
    objects.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    body, offsets = "%PDF-1.4\n", []
    for number, item in enumerate(objects, 1):
        offsets.append(len(body))
        body += f"{number} 0 obj\n{item}\nendobj\n"
    start = len(body)
    table = "".join(f"{offset:010d} 00000 n \n" for offset in offsets)
    body += (f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n{table}"
             f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n")
    return body.encode("latin-1")


WORD = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def make_docx(xml_body: "str | bytes | None" = None, paragraphs: tuple[str, ...] = ()) -> bytes:
    inner = "".join(f"<w:p><w:r><w:t>{p}</w:t></w:r></w:p>" for p in paragraphs)
    xml = xml_body or f'<?xml version="1.0"?><w:document xmlns:w="{WORD}"><w:body>{inner}</w:body></w:document>'
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", xml)
    return buffer.getvalue()


def write(tmp_path: pathlib.Path, name: str, data: bytes) -> pathlib.Path:
    path = tmp_path / name
    path.write_bytes(data)
    return path


def test_pdf_text_with_page_marks(tmp_path):
    text = read_documents.read_text(write(tmp_path, "cv.pdf", make_pdf("Beispiel AG 2019", "Bachelor Informatik")))
    assert "[Seite 1]" in text and "Beispiel AG 2019" in text
    assert "[Seite 2]" in text and "Bachelor Informatik" in text


def test_pdf_without_text_is_named_as_a_scan(tmp_path):
    with pytest.raises(read_documents.NotReadable, match="Scan"):
        read_documents.read_text(write(tmp_path, "scan.pdf", make_pdf("")))


def test_broken_pdf_is_not_readable(tmp_path):
    with pytest.raises(read_documents.NotReadable):
        read_documents.read_text(write(tmp_path, "kaputt.pdf", b"%PDF-1.4 erfunden"))


def test_docx_paragraphs_tabs_and_breaks(tmp_path):
    xml = (f'<w:document xmlns:w="{WORD}"><w:body><w:p><w:r><w:t>Stationen</w:t></w:r></w:p>'
           "<w:p><w:r><w:t>2019</w:t><w:tab/><w:t>Beispiel AG</w:t><w:br/><w:t>Bern</w:t></w:r></w:p>"
           "</w:body></w:document>")
    text = read_documents.read_text(write(tmp_path, "cv.docx", make_docx(xml)))
    assert text == "Stationen\n2019\tBeispiel AG\nBern"


@pytest.mark.parametrize("xml", [
    f'<!DOCTYPE w [<!ENTITY a "aaaa">]><w:document xmlns:w="{WORD}"><w:body><w:p><w:r><w:t>&a;</w:t></w:r></w:p></w:body></w:document>',
    "kein xml",
])
def test_docx_with_entities_or_broken_xml_is_refused(tmp_path, xml):
    with pytest.raises(read_documents.NotReadable):
        read_documents.read_text(write(tmp_path, "boese.docx", make_docx(xml)))


def test_docx_that_unpacks_too_large_is_refused_without_reading(tmp_path, monkeypatch):
    monkeypatch.setattr(read_documents, "MAX_DOCX_XML_BYTES", 100)
    data = make_docx(paragraphs=("x" * 1000,))
    with pytest.raises(read_documents.NotReadable, match="zu gross"):
        read_documents.read_text(write(tmp_path, "gross.docx", data))


def test_not_a_zip_docx_is_refused(tmp_path):
    with pytest.raises(read_documents.NotReadable):
        read_documents.read_text(write(tmp_path, "falsch.docx", b"kein zip"))


def test_docx_without_document_part_is_refused(tmp_path):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("anders.xml", "<a/>")
    with pytest.raises(read_documents.NotReadable):
        read_documents.read_text(write(tmp_path, "leer.docx", buffer.getvalue()))


@pytest.mark.parametrize("raw", ["Grüsse aus Bern".encode("utf-8"), "Grüsse aus Bern".encode("cp1252"),
                                 "﻿Grüsse aus Bern".encode("utf-8")])
def test_text_files_in_utf8_or_windows_encoding(tmp_path, raw):
    assert read_documents.read_text(write(tmp_path, "brief.txt", raw)) == "Grüsse aus Bern"


@pytest.mark.parametrize("name,hint", [("alt.doc", "PDF"), ("zeugnis.jpg", "von Hand"), ("zeugnis.png", "von Hand")])
def test_old_word_and_images_are_never_read(tmp_path, name, hint):
    with pytest.raises(read_documents.NotReadable, match=hint):
        read_documents.read_text(write(tmp_path, name, b"egal"))


def store(folder, category, name, data):
    import datetime
    import_documents.store_documents(folder, (Document(category, name, data),), datetime.date(2026, 11, 4))


def test_collect_reads_the_cv_first_and_lists_what_it_skipped(tmp_path):
    store(tmp_path, "zeugnisse", "zeugnis.jpg", b"bild")
    store(tmp_path, "zeugnisse", "zeugnis.txt", "Zeugnis Beispiel AG".encode())
    store(tmp_path, "anschreiben-bisher", "brief.txt", "Mit freundlichen Grüssen".encode())
    store(tmp_path, "lebenslauf-bisher", "cv.pdf", make_pdf("Lebenslauf"))

    reading = read_documents.collect_texts(tmp_path, import_documents.pending_documents(tmp_path))

    assert [t.name for t in reading.texts] == ["cv.pdf", "brief.txt", "zeugnis.txt"]
    assert [(s.name, "von Hand" in s.reason) for s in reading.skipped] == [("zeugnis.jpg", True)]


def test_collect_cuts_long_documents_and_stops_at_the_total(tmp_path, monkeypatch):
    monkeypatch.setattr(read_documents, "MAX_CHARS_PER_DOCUMENT", 10)
    monkeypatch.setattr(read_documents, "MAX_CHARS_TOTAL", 15)
    store(tmp_path, "lebenslauf-bisher", "a.txt", b"a" * 30)
    store(tmp_path, "zeugnisse", "b.txt", b"b" * 30)
    store(tmp_path, "zeugnisse", "c.txt", b"c" * 30)

    reading = read_documents.collect_texts(tmp_path, import_documents.pending_documents(tmp_path))

    assert [(t.name, len(t.text), t.shortened) for t in reading.texts] == [("a.txt", 10, True), ("b.txt", 5, True)]
    assert [s.name for s in reading.skipped] == ["c.txt"]


@pytest.mark.parametrize("raw", ["Grüsse 079 000 00 00".encode("utf-16"), b"\xff\xfe" + "Grüsse 079 000 00 00".encode("utf-16-le"),
                                 b"\xfe\xff" + "Grüsse 079 000 00 00".encode("utf-16-be")])
def test_utf16_text_files_are_decoded(tmp_path, raw):
    assert read_documents.read_text(write(tmp_path, "notepad.txt", raw)) == "Grüsse 079 000 00 00"


def test_invisible_characters_cannot_hide_personal_values(tmp_path):
    raw = "07​9 000­ 00 00\x00\nZeile\tzwei".encode("utf-8")
    assert read_documents.read_text(write(tmp_path, "versteckt.txt", raw)) == "079 000 00 00\nZeile\tzwei"


def test_docx_in_utf16_cannot_hide_a_doctype(tmp_path):
    xml = f'<!DOCTYPE w [<!ENTITY a "aaaa">]><w:document xmlns:w="{WORD}"><w:body/></w:document>'
    with pytest.raises(read_documents.NotReadable):
        read_documents.read_text(write(tmp_path, "boese.docx", make_docx(xml.encode("utf-16"))))


def test_docx_with_an_odd_encoding_declaration_still_reads(tmp_path):
    xml = (f'<?xml version="1.0" encoding="gbk"?><w:document xmlns:w="{WORD}"><w:body><w:p><w:r><w:t>Bern</w:t>'
           "</w:r></w:p></w:body></w:document>")
    assert read_documents.read_text(write(tmp_path, "selten.docx", make_docx(xml))) == "Bern"


def test_one_strange_file_does_not_stop_the_others(tmp_path, monkeypatch):
    store(tmp_path, "lebenslauf-bisher", "a.txt", b"Lebenslauf")
    store(tmp_path, "zeugnisse", "b.pdf", b"%PDF")

    def explode(path):
        raise ValueError("unerwartet")

    monkeypatch.setitem(read_documents.READERS, "pdf", explode)
    reading = read_documents.collect_texts(tmp_path, import_documents.pending_documents(tmp_path))
    assert [t.name for t in reading.texts] == ["a.txt"] and reading.skipped[0].reason == read_documents.BROKEN
