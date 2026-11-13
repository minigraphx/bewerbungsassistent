"""Routes of the page „Lebenslauf und Dateien“ and of the own cover letter (MIN-346). Neither the extension nor Claude reach them."""
import base64
import binascii
import pathlib

import certificates
import cv_design
import own_files
import unterlagen
import versand
from dateien import schreibe_atomar
from server import datei_antwort, json_antwort, pflicht

BASE64_OVERHEAD = 4 / 3
JSON_OVERHEAD_BYTES = 10_000
UPLOAD_ROUTE = "/api/dateien/hochladen"
LETTER_ROUTE = "/api/dateien/anschreiben"
BODY_LIMITS = {route: int(own_files.MAX_FILE_BYTES * BASE64_OVERHEAD) + JSON_OVERHEAD_BYTES
               for route in (UPLOAD_ROUTE, LETTER_ROUTE)}
KIND_NAMES = {own_files.CERTIFICATE_KIND: "Zertifikat", own_files.REFERENCE_KIND: "Zeugnis"}
UNREADABLE = "Die Datei liess sich nicht lesen. Bitte nochmals versuchen."
NO_APPLICATION = "Bewerbung mit id erwartet."


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


def change_kind(k, parameter, body):
    """A certificate becomes a reference or the other way round: the file moves to the folder of its kind."""
    request = _body(body)
    rel = request.get("datei")
    source = own_files.checked_listed(k.daten, rel)
    target_rel = own_files.kind_target(k.daten, rel, request.get("art"))
    if target_rel == rel:
        return json_antwort(own_files.listing(k.daten))
    target = k.daten / target_rel
    description = f"{source.name} als {KIND_NAMES[request['art']]} eingeordnet"

    def write():
        target.parent.mkdir(parents=True, exist_ok=True)
        source.rename(target)
        refresh_chosen(k, rel)
        k.ablage.speichere(target, description)

    k.mit_entwurf(source, description, write)
    return json_antwort(own_files.listing(k.daten))


def _letter_of(k, request: dict) -> tuple[dict, pathlib.Path]:
    wanted = request.get("id")
    if not isinstance(wanted, str):
        raise ValueError(NO_APPLICATION)
    entry = k.register().hole(wanted)
    return entry, unterlagen.own_letter_path(k.daten, entry["id"])


def _refuse_when_sent(k, entry_id: str) -> None:
    """Call with `k.sperre` held: a dispatch recorded just before takes this very file along."""
    if k.register().hole(entry_id).get("versand"):
        raise ValueError(unterlagen.SENT_STAYS)


def _letter_answer(k, entry: dict):
    """A form that already got a letter keeps it, so the person must know that it now holds another one."""
    return json_antwort({"formular_abweichend": versand.form_differs(k.daten, entry)})


def upload_letter(k, parameter, body):
    request = _body(body)
    data = _decoded(request)
    own_files.check_letter(own_files.clean_name(request.get("name")), data)
    entry, path = _letter_of(k, request)

    def write():
        _refuse_when_sent(k, entry["id"])
        schreibe_atomar(path, data)

    k.mit_entwurf(path, f"Eigenes Anschreiben {entry['firma']} hochgeladen", write)
    return _letter_answer(k, entry)


def remove_letter(k, parameter, body):
    entry, path = _letter_of(k, _body(body))

    def write():
        _refuse_when_sent(k, entry["id"])
        if not path.is_file():
            raise ValueError(own_files.NOT_THERE)
        path.unlink()

    k.mit_entwurf(path, f"Eigenes Anschreiben {entry['firma']} entfernt", write)
    return _letter_answer(k, entry)


def _design_answer(k):
    return json_antwort({"design": cv_design.load(k.daten), "designs": list(cv_design.CV_DESIGNS)})


def design(k, parameter, body):
    """G61: the design new CVs are built with."""
    return _design_answer(k)


def choose_design(k, parameter, body):
    """Saving builds nothing: what is built or sent stays as it is, the next build takes the new design."""
    chosen = cv_design.parse(_body(body).get("design"))
    k.mit_entwurf(k.daten / cv_design.FILE, cv_design.DRAFT, lambda: cv_design.save(k.daten, chosen))
    return _design_answer(k)


DESIGN_ROUTE = "/api/dateien/aussehen"
GET = {"/api/dateien": overview, "/api/dateien/ansehen": show, DESIGN_ROUTE: design}
POST = {UPLOAD_ROUTE: upload, "/api/dateien/entfernen": remove, "/api/dateien/art": change_kind, LETTER_ROUTE: upload_letter,
        "/api/dateien/anschreiben/entfernen": remove_letter, DESIGN_ROUTE: choose_design}
