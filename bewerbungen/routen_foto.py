"""API-Routen für den Fotoausschnitt (früher lebenslauf/foto_editor.py, MIN-301). Speichern legt Entwürfe an.

Hochladen (#128): wer am Anfang kein Foto gegeben hat, gibt es hier, als JPG oder PNG ohne Metadaten.
Mehrere Fotos (#129): jedes Hochladen fügt eines hinzu; welches aktiv ist und wo die übrigen liegen, sagt `photos.py`.
Ob neue Unterlagen das aktive Foto zeigen (G62), sagt `photo_shown.py`.
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
import photo_shown
import photos
from server import Antwort, json_antwort

MAX_PHOTO_BYTES = 10_000_000
UPLOAD_ROUTE = "/api/foto/hochladen"
BODY_LIMITS = {UPLOAD_ROUTE: int(MAX_PHOTO_BYTES * 4 / 3) + 10_000}  # base64 and the JSON around it
NO_CV = "Es gibt noch keinen Lebenslauf. Bitte zuerst die Angaben erfassen, dann das Foto."


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


def liste(k, parameter, body):
    return json_antwort({"fotos": photos.listing(k.daten), "max_groesse": MAX_PHOTO_BYTES,
                         photo_shown.FIELD: photo_shown.load(k.daten)})


def bild(k, parameter, body):
    """The active photo, or with `datei` one of the listed ones (for the list on the page)."""
    if parameter.get("datei"):
        foto = k.daten / photos.listed(k.daten, parameter["datei"])["datei"]
    else:
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


def _forget_previews(k) -> None:
    for key in [key for key in k.cache if isinstance(key, tuple) and key[0] == "foto-vorschau"]:
        del k.cache[key]


def hochladen(k, parameter, body):
    data = _photo_bytes(body)
    _check_size(data)
    if not _cv(k).is_file():
        raise ValueError(NO_CV)
    extension, clean = photo_file.without_metadata(data)
    name = photos.upload_name(k.daten, extension, clean)
    _check_decodes(k, pathlib.Path(name).name, clean)
    photos.add(k, name, clean)
    _forget_previews(k)
    return json_antwort(fotoausschnitt.lies_foto(_cv(k))[1])


def aktiv(k, parameter, body):
    if not isinstance(body, dict):
        raise ValueError("datei erwartet")
    return json_antwort(photos.activate(k, body.get("datei")))


def shown(k, parameter, body):
    """„Im Lebenslauf zeigen“ (G62): only new documents follow it."""
    return json_antwort(photo_shown.as_dict(photo_shown.save(k, body)))


def loeschen(k, parameter, body):
    if not isinstance(body, dict):
        raise ValueError("datei erwartet")
    photos.delete(k, body.get("datei"))
    return json_antwort({"fotos": photos.listing(k.daten)})


GET = {
    "/api/foto/vorhanden": vorhanden,
    "/api/foto/liste": liste,
    "/api/foto/optionen": optionen,
    "/api/foto/bild": bild,
    "/api/foto/vorschau.png": vorschau,
}
POST = {
    "/api/foto/speichern": speichern,
    UPLOAD_ROUTE: hochladen,
    "/api/foto/aktiv": aktiv,
    "/api/foto/loeschen": loeschen,
    "/api/foto/zeigen": shown,
}
