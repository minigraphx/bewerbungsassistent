"""API-Routen für den Fotoausschnitt (früher lebenslauf/foto_editor.py, MIN-301). Speichern legt Entwürfe an."""
import mimetypes

import pfade  # noqa: F401  (macht das Modul lebenslauf importierbar)
import fotoausschnitt
from server import Antwort, json_antwort


def _cv(k):
    return k.daten / "cv.yaml"


def _vorschau(k) -> fotoausschnitt.Vorschau:
    foto, _ = fotoausschnitt.lies_foto(_cv(k))
    schluessel = ("foto-vorschau", str(foto))
    if schluessel not in k.cache:
        k.cache[schluessel] = fotoausschnitt.Vorschau(foto, k.build)
    return k.cache[schluessel]


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


GET = {
    "/api/foto/optionen": optionen,
    "/api/foto/bild": bild,
    "/api/foto/vorschau.png": vorschau,
}
POST = {
    "/api/foto/speichern": speichern,
}
