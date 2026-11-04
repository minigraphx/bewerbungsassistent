"""Routes for the certificates of an application (MIN-346): list with suggestion, and saving the choice with its ZIP."""
import certificates
import unterlagen
from server import json_antwort, pflicht


def _ad_text(k, application_id: str) -> str:
    path = unterlagen.bewerbungsordner(k.daten, application_id) / "stelle.md"
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def overview(k, parameter, body):
    wanted = pflicht(parameter, "id")
    entry = k.register().hole(wanted)
    files = certificates.available(k.daten)
    return json_antwort({"verfuegbar": files, "vorschlag": certificates.suggest(files, _ad_text(k, wanted)),
                         "gewaehlt": entry.get("zertifikate")})


def save(k, parameter, body):
    if not isinstance(body, dict) or not isinstance(body.get("id"), str):
        raise ValueError("Bewerbung mit id erwartet")
    choice = certificates.checked_choice(k.daten, body.get("dateien"))
    register = k.register()
    wanted = body["id"]

    def write():
        certificates.write_zip(k.daten, wanted, choice)
        return register.speichere({**register.hole(wanted), "zertifikate": choice})

    entry = k.mit_entwurf(register.pfad, f"Zertifikate für {wanted} gewählt", write)
    return json_antwort({"gewaehlt": entry["zertifikate"]})


GET = {"/api/zertifikate": overview}
POST = {"/api/zertifikate": save}
