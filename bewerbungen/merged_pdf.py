"""One PDF from several files (MIN-346), for a form with a single field for the documents.

Whatever a form gets is kept like any other file (`form_copy.py`). Next to the joined PDF lies a digest of its
sources: the PDF cannot be built again to compare it, the pages ask every few seconds.
"""
import hashlib
import io
import pathlib
import tempfile

import typst
from pypdf import PdfReader, PdfWriter

import certificates
import form_copy
from dateien import im_ordner, schreibe_atomar
from unterlagen import effective_dossier, wirksame_pdfs

ALL = "unterlagen"
PROOFS = "nachweise"
KEYS = (ALL, PROOFS)
FILE_LABELS = {ALL: "Unterlagen", PROOFS: "Nachweise"}
DOSSIER_LABEL = "Dossier"
MIN_SOURCES = 2  # one file needs no joining: it goes as it is
REFERENCES_FOLDER = "dokumente/zeugnisse"
IMAGES = (".jpg", ".jpeg", ".png")
IMAGE_PAGE = '#set page("a4", margin: 1cm)\n#image("{name}", width: 100%, height: 100%, fit: "contain")\n'
DIGEST_SUFFIX = ".stand"
CANNOT_JOIN = "„{name}“ lässt sich nicht in ein gemeinsames PDF packen. Bitte die Dateien einzeln hochladen."


def sources(data_dir: pathlib.Path, entry: dict) -> dict[str, list[pathlib.Path]]:
    """The files in each joined PDF, in the order a reader expects them. A chosen dossier already holds letter and CV."""
    pdfs = wirksame_pdfs(data_dir, entry)
    dossier = effective_dossier(data_dir, entry)
    main = [dossier] if dossier else [path for path in (pdfs["anschreiben"], pdfs["lebenslauf"]) if path.is_file()]
    references = [data_dir / rel for rel in certificates.files_in(data_dir, REFERENCES_FOLDER)]
    chosen = [im_ordner(data_dir, rel) for rel in entry.get("zertifikate") or []]
    proofs = [*references, *(path for path in chosen if path.is_file())]
    return {ALL: [*main, *proofs], PROOFS: proofs}


def offered(data_dir: pathlib.Path, entry: dict) -> list[str]:
    """A dossier alone is offered too: a form with one field for all documents wants it (G40)."""
    dossier = effective_dossier(data_dir, entry) is not None
    return [key for key, paths in sources(data_dir, entry).items()
            if len(paths) >= MIN_SOURCES or (key == ALL and dossier)]


def label(data_dir: pathlib.Path, entry: dict, key: str) -> str:
    """Name of the joined PDF for the employer: with a dossier it is the dossier, with proofs added or not."""
    return DOSSIER_LABEL if key == ALL and effective_dossier(data_dir, entry) else FILE_LABELS[key]


def _image_as_pdf(path: pathlib.Path) -> bytes:
    with tempfile.TemporaryDirectory() as folder:
        root = pathlib.Path(folder)
        image = root / f"bild{path.suffix.lower()}"
        image.write_bytes(path.read_bytes())
        page = root / "seite.typ"
        page.write_text(IMAGE_PAGE.format(name=image.name), encoding="utf-8")
        return typst.compile(str(page), root=str(root))


def _pages_of(path: pathlib.Path) -> PdfReader:
    data = _image_as_pdf(path) if path.suffix.lower() in IMAGES else path.read_bytes()
    reader = PdfReader(io.BytesIO(data))
    if reader.is_encrypted or not reader.pages:
        raise ValueError("encrypted or empty")
    return reader


def build(paths: list[pathlib.Path]) -> bytes:
    writer = PdfWriter()
    for path in paths:
        try:
            if path.suffix.lower() not in (".pdf", *IMAGES):
                raise ValueError("no pages")
            writer.append(_pages_of(path), import_outline=False)
        except Exception as error:  # noqa: BLE001 (a broken PDF raises nearly anything; the person needs the name of the file)
            raise ValueError(CANNOT_JOIN.format(name=path.name)) from error
    stream = io.BytesIO()
    writer.write(stream)
    return stream.getvalue()


def _digest(paths: list[pathlib.Path]) -> str:
    total = hashlib.sha256()
    try:
        for path in paths:
            total.update(hashlib.sha256(path.read_bytes()).digest())
    except OSError:  # gone meanwhile, so it is no longer what the form got
        return ""
    return total.hexdigest()


def _stored_digest(copy: pathlib.Path) -> str:
    try:
        return copy.with_suffix(DIGEST_SUFFIX).read_text(encoding="utf-8")
    except OSError:  # pages ask without the lock, and a dispatch removes the copies
        return ""


def keep(data_dir: pathlib.Path, entry: dict, key: str) -> pathlib.Path:
    """Joins the files and keeps the result as what the form got. Call with the lock held, like `form_copy.keep`."""
    paths = sources(data_dir, entry)[key]
    digest = _digest(paths)  # before joining: a file that changes meanwhile then counts as changed
    existing = form_copy.copy_path(data_dir, entry["id"], key)
    if digest and existing.is_file() and _stored_digest(existing) == digest:
        return existing  # another frame may be reading its parts
    target = form_copy.store(data_dir, entry["id"], key, build(paths))
    try:
        schreibe_atomar(target.with_suffix(DIGEST_SUFFIX), digest.encode("utf-8"))
    except OSError as error:
        raise ValueError(form_copy.NOT_KEPT) from error
    return target


def changed(data_dir: pathlib.Path, entry: dict, kept: dict[str, pathlib.Path]) -> list[str]:
    """The joined PDFs a form holds whose sources are no longer the ones that count."""
    current = sources(data_dir, entry)
    return [key for key in KEYS if key in kept and _stored_digest(kept[key]) != _digest(current[key])]
