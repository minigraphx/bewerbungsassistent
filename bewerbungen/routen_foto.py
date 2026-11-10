"""API-Routen für den Fotoausschnitt (früher lebenslauf/foto_editor.py, MIN-301). Speichern legt Entwürfe an.

Hochladen (#128): wer am Anfang kein Foto gegeben hat, gibt es hier, als JPG oder PNG ohne Metadaten.
"""
import base64
import binascii
import mimetypes
import pathlib
import tempfile

import typst

import pfade  # noqa: F401  (macht das Modul lebenslauf importierbar)
import fotoausschnitt
import photo_file
from dateien import schreibe_atomar
from server import Antwort, json_antwort

MAX_PHOTO_BYTES = 10_000_000
UPLOAD_ROUTE = "/api/foto/hochladen"
BODY_LIMITS = {UPLOAD_ROUTE: int(MAX_PHOTO_BYTES * 4 / 3) + 10_000}  # base64 and the JSON around it
PHOTO_NAME = "foto"  # foto.jpg or foto.png in the data folder, as the skill einstieg puts it
NO_CV = "Es gibt noch keinen Lebenslauf. Bitte zuerst die Angaben erfassen, dann das Foto."
DESCRIPTION = "Foto hochgeladen"


def _cv(k):
    return k.daten / "cv.yaml"


def _vorschau(k) -> fotoausschnitt.Vorschau:
    foto, _ = fotoausschnitt.lies_foto(_cv(k))
    schluessel = ("foto-vorschau", str(foto))
    if schluessel not in k.cache:
        k.cache[schluessel] = fotoausschnitt.Vorschau(foto, k.build)
    return k.cache[schluessel]


def vorhanden(k, parameter, body):
    return json_antwort({"vorhanden": fotoausschnitt.hat_foto(_cv(k)), "max_groesse": MAX_PHOTO_BYTES})


def optionen(k, parameter, body):
    return json_antwort(fotoausschnitt.lies_foto(_cv(k))[1])


def bild(k, parameter, body):
    foto, _ = fotoausschnitt.lies_foto(_cv(k))
    return Antwort(200, mimetypes.guess_type(foto.name)[0] or "application/octet-stream", foto.read_bytes())


def vorschau(k, parameter, body):
    return Antwort(200, "image/png", _vorschau(k).png(fotoausschnitt.optionen_aus_anfrage(parameter)))


def speichern(k, parameter, body):
    if not isinstance(body, dict):
        raise ValueError("Optionen erwartet")
    k.mit_entwurf(_cv(k), "Fotoausschnitt geändert", lambda: fotoausschnitt.speichere_optionen(_cv(k), body))
    return json_antwort(fotoausschnitt.lies_foto(_cv(k))[1])


def _photo_bytes(body) -> bytes:
    data = body.get("daten") if isinstance(body, dict) else None
    if not isinstance(data, str):
        raise ValueError(photo_file.FORMAT)
    try:
        return base64.b64decode(data, validate=True)
    except binascii.Error as error:
        raise ValueError(photo_file.UNREADABLE) from error


def _check_size(data: bytes) -> None:
    if len(data) > MAX_PHOTO_BYTES:
        raise ValueError(f"Das Foto ist zu gross: höchstens {MAX_PHOTO_BYTES / 1_000_000:g} MB.")


def _check_decodes(k, name: str, data: bytes) -> None:
    """Typst sets the photo in the CV, so it must read it; a file can look right in its first bytes and still not."""
    k.build.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=k.build) as folder:
        (pathlib.Path(folder) / name).write_bytes(data)
        document = pathlib.Path(folder) / "probe.typ"
        document.write_text(f'#set page(width: auto, height: auto, margin: 0pt)\n#image("{name}", width: 1cm)\n',
                            encoding="utf-8")
        try:
            typst.compile(str(document), root=folder, format="png", ppi=1)
        except typst.TypstError as error:
            raise ValueError(photo_file.UNREADABLE) from error


def _store(k, photo: pathlib.Path, data: bytes) -> None:
    """Photo and CV change together; drafts of both before and after, as `mit_entwurf` does for one file."""
    cv = _cv(k)
    with k.sperre:
        for path in (cv, photo):
            if path.is_file():
                k.ablage.speichere(path, f"Stand vor: {DESCRIPTION}")
        schreibe_atomar(photo, data)
        fotoausschnitt.speichere_foto(cv, photo.name)
        for key in [key for key in k.cache if isinstance(key, tuple) and key[0] == "foto-vorschau"]:
            del k.cache[key]  # the preview read the old photo
        for path in (photo, cv):
            k.ablage.speichere(path, DESCRIPTION)


def hochladen(k, parameter, body):
    data = _photo_bytes(body)
    _check_size(data)
    if not _cv(k).is_file():
        raise ValueError(NO_CV)
    extension, clean = photo_file.without_metadata(data)
    name = f"{PHOTO_NAME}.{extension}"
    _check_decodes(k, name, clean)
    _store(k, k.daten / name, clean)
    return json_antwort(fotoausschnitt.lies_foto(_cv(k))[1])


GET = {
    "/api/foto/vorhanden": vorhanden,
    "/api/foto/optionen": optionen,
    "/api/foto/bild": bild,
    "/api/foto/vorschau.png": vorschau,
}
POST = {
    "/api/foto/speichern": speichern,
    UPLOAD_ROUTE: hochladen,
}
