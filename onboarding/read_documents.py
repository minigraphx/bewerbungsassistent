"""Read the text of uploaded documents on this computer, before anything goes to the AI (MIN-367).

The files come from outside: PDF through pypdf, Word `.docx` through `word/document.xml` with the standard
library (declared and real size bounded, no DTD or entities), text directly. Old `.doc` files and images are
not read: an image cannot be pseudonymized, so it never goes to the AI. Reasons are German and meant for the
person; they name neither Sie nor Du, because both kinds of search use them.
"""
import dataclasses
import logging
import pathlib
import unicodedata
import xml.etree.ElementTree as ElementTree
import zipfile
import zlib

from pypdf import PdfReader

import paths  # noqa: F401  (makes the module bewerbungen importable)
from dateien import im_ordner
from documents import extension

log = logging.getLogger(__name__)

MAX_PDF_PAGES = 60
MAX_DOCX_XML_BYTES = 20_000_000
MAX_CHARS_PER_DOCUMENT = 40_000
MAX_CHARS_TOTAL = 120_000
CATEGORY_ORDER = ("lebenslauf-bisher", "anschreiben-bisher", "zeugnisse", "zertifikate")
DOCUMENT_XML = "word/document.xml"
FLAG_ENCRYPTED = 0x1
WORD_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
FORBIDDEN_XML = ("<!DOCTYPE", "<!ENTITY")
UTF16_MARKS = (b"\xff\xfe", b"\xfe\xff")
KEPT_CONTROLS = "\n\t"

OLD_WORD = "Altes Word-Format: als PDF speichern und neu hochladen, oder die Angaben von Hand ergänzen."
IMAGE = "Bild: Darin lässt sich nichts unkenntlich machen, darum geht es nicht an die KI. Angaben von Hand ergänzen."
SCAN = "Enthält keinen lesbaren Text, vermutlich ein Scan. Angaben von Hand ergänzen."
ENCRYPTED = "Die Datei ist mit einem Passwort geschützt. Ohne Schutz speichern und neu hochladen."
BROKEN = "Die Datei liess sich nicht lesen. Als PDF speichern und neu hochladen, oder die Angaben von Hand ergänzen."
TOO_LARGE = "Die Datei ist ausgepackt zu gross. Als PDF speichern und neu hochladen."
UNKNOWN_TYPE = "Dieser Dateityp lässt sich nicht lesen."
TOO_MUCH = "Nicht gelesen: Zusammen sind die Unterlagen zu lang. Die wichtigsten zuerst hochladen oder diese Angaben von Hand ergänzen."


class NotReadable(Exception):
    """The document cannot be read; the message says why and what to do, in German."""


@dataclasses.dataclass(frozen=True)
class DocumentText:
    category: str
    name: str
    datei: str
    text: str
    shortened: bool


@dataclasses.dataclass(frozen=True)
class SkippedDocument:
    name: str
    reason: str


@dataclasses.dataclass(frozen=True)
class Reading:
    texts: tuple[DocumentText, ...]
    skipped: tuple[SkippedDocument, ...]


def _read_pdf(path: pathlib.Path) -> str:
    try:
        reader = PdfReader(str(path))
        if reader.is_encrypted:
            raise NotReadable(ENCRYPTED)
        pages = [(number, page.extract_text() or "") for number, page in enumerate(reader.pages[:MAX_PDF_PAGES], 1)]
    except NotReadable:
        raise
    except Exception as error:  # noqa: BLE001  (pypdf raises many kinds of errors on damaged files)
        log.warning("PDF nicht lesbar: %s", type(error).__name__)
        raise NotReadable(BROKEN) from error
    if not any(text.strip() for _, text in pages):
        raise NotReadable(SCAN)
    return "\n".join(f"[Seite {number}]\n{text.strip()}" for number, text in pages if text.strip())


def _document_xml(path: pathlib.Path) -> bytes:
    try:
        with zipfile.ZipFile(path) as archive:
            info = archive.getinfo(DOCUMENT_XML)
            if info.flag_bits & FLAG_ENCRYPTED:
                raise NotReadable(ENCRYPTED)
            if info.file_size > MAX_DOCX_XML_BYTES:
                raise NotReadable(TOO_LARGE)
            with archive.open(info) as handle:
                data = handle.read(MAX_DOCX_XML_BYTES + 1)
    except (zipfile.BadZipFile, KeyError, zlib.error, NotImplementedError, EOFError, OSError, RuntimeError) as error:
        raise NotReadable(BROKEN) from error
    if len(data) > MAX_DOCX_XML_BYTES:
        raise NotReadable(TOO_LARGE)
    return data


def _paragraph_text(paragraph: ElementTree.Element) -> str:
    parts = []
    for node in paragraph.iter():
        if node.tag == f"{WORD_NS}t":
            parts.append(node.text or "")
        elif node.tag == f"{WORD_NS}tab":
            parts.append("\t")
        elif node.tag in (f"{WORD_NS}br", f"{WORD_NS}cr"):
            parts.append("\n")
    return "".join(parts)


def _xml_text(data: bytes) -> str:
    """Decoded first: the check for a DTD must see the same text the parser sees, also in UTF-16."""
    try:
        return data.decode("utf-16" if data.startswith(UTF16_MARKS) else "utf-8-sig")
    except UnicodeDecodeError as error:
        raise NotReadable(BROKEN) from error


def _read_docx(path: pathlib.Path) -> str:
    xml = _xml_text(_document_xml(path))
    if any(mark in xml for mark in FORBIDDEN_XML):
        raise NotReadable(BROKEN)
    try:
        root = ElementTree.fromstring(xml)
    except (ElementTree.ParseError, ValueError) as error:
        raise NotReadable(BROKEN) from error
    lines = [_paragraph_text(p) for p in root.iter(f"{WORD_NS}p")]
    text = "\n".join(line for line in lines if line.strip())
    if not text.strip():
        raise NotReadable(SCAN)
    return text


def _read_plain(path: pathlib.Path) -> str:
    data = path.read_bytes()
    if data.startswith(UTF16_MARKS):
        return data.decode("utf-16", errors="replace")
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp1252", errors="replace")


def _visible(text: str) -> str:
    """Without control and invisible format characters: inside a phone number they would hide it from the masking."""
    return "".join(c for c in text if c in KEPT_CONTROLS or unicodedata.category(c) not in ("Cc", "Cf"))


READERS = {"pdf": _read_pdf, "docx": _read_docx, "txt": _read_plain}
NOT_READ = {"doc": OLD_WORD, "jpg": IMAGE, "jpeg": IMAGE, "png": IMAGE}


def read_text(path: pathlib.Path) -> str:
    """The text of one document, or NotReadable with the reason."""
    kind = extension(path.name)
    if kind in NOT_READ:
        raise NotReadable(NOT_READ[kind])
    reader = READERS.get(kind)
    if reader is None:
        raise NotReadable(UNKNOWN_TYPE)
    return _visible(reader(path))


def _order(document: dict) -> int:
    category = document["category"]
    return CATEGORY_ORDER.index(category) if category in CATEGORY_ORDER else len(CATEGORY_ORDER)


def collect_texts(data_dir: pathlib.Path, documents: list[dict]) -> Reading:
    """Read pending documents, the CV first, within the limits; everything not read is named with its reason."""
    texts, skipped = [], []
    room = MAX_CHARS_TOTAL
    for document in sorted(documents, key=_order):
        name = document["name"]
        try:
            text = read_text(im_ordner(data_dir, document["datei"])).strip()
        except NotReadable as reason:
            skipped.append(SkippedDocument(name, str(reason)))
            continue
        except Exception as error:  # noqa: BLE001  (one strange file must not stop the others)
            log.warning("Unterlage nicht lesbar: %s", type(error).__name__)
            skipped.append(SkippedDocument(name, BROKEN))
            continue
        if room <= 0:
            skipped.append(SkippedDocument(name, TOO_MUCH))
            continue
        allowed = min(MAX_CHARS_PER_DOCUMENT, room)
        texts.append(DocumentText(document["category"], name, document["datei"], text[:allowed], len(text) > allowed))
        room -= len(texts[-1].text)
    return Reading(tuple(texts), tuple(skipped))
