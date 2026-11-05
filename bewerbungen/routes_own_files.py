"""Routes of the page „Meine Dateien“ (MIN-346). Neither the extension nor Claude reach them."""
import base64
import binascii
import pathlib

import certificates
import own_files
from dateien import schreibe_atomar
from server import datei_antwort, json_antwort, pflicht

BASE64_OVERHEAD = 4 / 3
JSON_OVERHEAD_BYTES = 10_000
UPLOAD_ROUTE = "/api/dateien/hochladen"
BODY_LIMITS = {UPLOAD_ROUTE: int(own_files.MAX_FILE_BYTES * BASE64_OVERHEAD) + JSON_OVERHEAD_BYTES}
UNREADABLE = "Die Datei liess sich nicht lesen. Bitte nochmals versuchen."


def _body(body: object) -> dict:
    if not isinstance(body, dict):
        raise ValueError("Die Anfrage hat eine unbekannte Form.")
    return body


def _decoded(request: dict) -> bytes:
    data = request.get("daten")
    if not isinstance(data, str):
        raise ValueError(UNREADABLE)
    try:
        return base64.b64decode(data, validate=True)
    except binascii.Error as error:
        raise ValueError(UNREADABLE) from error


def refresh_chosen(k, rel: str) -> None:
    """A chosen certificate that changed goes along as it is now, one that is gone no longer goes along.

    Call with `k.sperre` held, in the same turn as the change of the file: what the entries say is read here, so a
    dispatch recorded just before is kept, and none can come between the file and its ZIP.
    """
    if not rel.startswith(f"{certificates.FOLDER}/"):
        return
    register = k.register()
    affected = own_files.chosen_by_unsent(register.alle(), rel)
    if not affected:
        return
    description = f"Zertifikat {pathlib.PurePosixPath(rel).name} geändert"
    k.ablage.speichere(register.pfad, f"Stand vor: {description}")
    there = set(certificates.available(k.daten))
    for entry in affected:
        choice = [path for path in entry["zertifikate"] if path in there]
        certificates.write_zip(k.daten, entry["id"], choice)
        register.speichere({**entry, "zertifikate": choice})
    k.ablage.speichere(register.pfad, description)


def overview(k, parameter, body):
    return json_antwort({**own_files.listing(k.daten), "max_groesse": own_files.MAX_FILE_BYTES})


def upload(k, parameter, body):
    request = _body(body)
    data = _decoded(request)
    name = own_files.clean_name(request.get("name"))
    kind = request.get("art")
    own_files.check_upload(kind, name, data)
    rel = own_files.relative_target(k.daten, kind, name)
    path = k.daten / rel

    def write():
        schreibe_atomar(path, data)
        refresh_chosen(k, rel)

    k.mit_entwurf(path, f"{name} hochgeladen", write)
    return json_antwort(own_files.listing(k.daten))


def show(k, parameter, body):
    path = own_files.checked_listed(k.daten, pflicht(parameter, "datei"))
    return datei_antwort(path, own_files.content_type_to_show(path))


def remove(k, parameter, body):
    rel = _body(body).get("datei")
    path = own_files.checked_listed(k.daten, rel)

    def write():
        path.unlink(missing_ok=True)
        refresh_chosen(k, rel)

    k.mit_entwurf(path, f"{path.name} entfernt", write)
    return json_antwort(own_files.listing(k.daten))


GET = {"/api/dateien": overview, "/api/dateien/ansehen": show}
POST = {UPLOAD_ROUTE: upload, "/api/dateien/entfernen": remove}
