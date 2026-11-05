"""What a form got (MIN-346): the record of a dispatch takes that version, even if the file changed afterwards."""
import base64
import json

import pytest

import apply
import form_copy
import letter_approval
import routes_apply
import unterlagen
import versand
from register import Register
from test_app import get, post, server  # noqa: F401  (server is a fixture)
from test_apply import ready
from test_own_files import upload
from test_own_letter import PDF, REMOVE, details, upload_letter

EARLIER = b"%PDF-1.4 earlier version"
LATER = b"%PDF-1.4 later version, longer"
ZIP_EARLIER = b"PK earlier"
ZIP_LATER = b"PK later"


def folder_of(s, entry) -> object:
    return s.kontext.daten / "bewerbungen" / entry["id"]


def hand_over(s, entry, key="lebenslauf", part=0):
    return get(s, "/api/bewerben/datei", id=entry["id"], schluessel=key, teil=str(part))


def built_cv(s, entry, data):
    (folder_of(s, entry) / "lebenslauf.pdf").write_bytes(data)


def sent_file(s, entry, kind) -> bytes:
    k = s.kontext
    return (k.daten / Register(k.daten).hole(entry["id"])["versand"]["dateien"][kind]).read_bytes()


def send_from_form(s, entry):
    return post(s, "/api/bewerben/abgeschickt", {"id": entry["id"]})


def send_from_page(s, entry, **body):
    return post(s, f"/api/versand?id={entry['id']}", {"datum": s.kontext.heute().isoformat(), **body})


def test_the_form_button_records_what_the_form_got(server):  # noqa: F811
    entry = ready(server)
    built_cv(server, entry, EARLIER)
    hand_over(server, entry)
    built_cv(server, entry, LATER)

    status, answer = send_from_form(server, entry)

    assert status == 200 and sent_file(server, entry, "lebenslauf") == EARLIER
    assert any("Lebenslauf" in hint for hint in answer["hinweise"])


def test_no_note_when_the_form_has_what_counts(server):  # noqa: F811
    entry = ready(server)
    built_cv(server, entry, EARLIER)
    hand_over(server, entry)

    status, answer = send_from_form(server, entry)

    assert status == 200 and sent_file(server, entry, "lebenslauf") == EARLIER and answer["hinweise"] == []


def test_a_file_that_never_went_to_the_form_is_recorded_as_it_is_now(server):  # noqa: F811
    entry = ready(server)
    built_cv(server, entry, EARLIER)
    hand_over(server, entry)

    send_from_form(server, entry)

    assert sent_file(server, entry, "anschreiben") == b"%PDF-1.4 letter"


def test_the_page_records_the_current_version_unless_told_otherwise(server):  # noqa: F811
    entry = ready(server)
    built_cv(server, entry, EARLIER)
    hand_over(server, entry)
    built_cv(server, entry, LATER)

    assert send_from_page(server, entry)[0] == 200
    assert sent_file(server, entry, "lebenslauf") == LATER


def test_the_page_can_record_what_the_form_got(server):  # noqa: F811
    entry = ready(server)
    built_cv(server, entry, EARLIER)
    hand_over(server, entry)
    built_cv(server, entry, LATER)

    assert send_from_page(server, entry, fassung_formular=True)[0] == 200
    assert sent_file(server, entry, "lebenslauf") == EARLIER


@pytest.mark.parametrize("value", ["true", 1, "ja", None])
def test_only_a_clear_yes_takes_the_version_of_the_form(server, value):  # noqa: F811
    entry = ready(server)
    built_cv(server, entry, EARLIER)
    hand_over(server, entry)
    built_cv(server, entry, LATER)

    send_from_page(server, entry, fassung_formular=value)

    assert sent_file(server, entry, "lebenslauf") == LATER


def test_a_later_handover_replaces_the_earlier_one(server):  # noqa: F811
    entry = ready(server)
    built_cv(server, entry, EARLIER)
    hand_over(server, entry)
    built_cv(server, entry, LATER)
    hand_over(server, entry)  # the person reloaded the form

    answer = send_from_form(server, entry)[1]

    assert sent_file(server, entry, "lebenslauf") == LATER and answer["hinweise"] == []


def test_a_cover_letter_replaced_after_the_handover(server):  # noqa: F811
    entry = ready(server)
    hand_over(server, entry, "anschreiben")
    upload_letter(server, entry["id"], PDF)

    assert send_from_form(server, entry)[0] == 200
    assert sent_file(server, entry, "anschreiben") == b"%PDF-1.4 letter"


def test_a_file_removed_after_the_handover_is_still_recorded(server):  # noqa: F811
    entry = ready(server)
    upload(server, "lebenslauf", "cv.pdf", EARLIER + b"x" * 300)
    (folder_of(server, entry) / "lebenslauf.pdf").unlink()
    hand_over(server, entry)
    post(server, "/api/dateien/entfernen", {"datei": unterlagen.OWN_CV})

    assert send_from_form(server, entry)[0] == 200
    assert sent_file(server, entry, "lebenslauf") == EARLIER + b"x" * 300


def test_the_certificates_are_recorded_as_the_form_got_them(server):  # noqa: F811
    entry = ready(server)
    packed = folder_of(server, entry) / "zertifikate.zip"
    packed.write_bytes(ZIP_EARLIER)
    hand_over(server, entry, "zertifikate")
    packed.write_bytes(ZIP_LATER)

    answer = send_from_form(server, entry)[1]

    assert sent_file(server, entry, "zertifikate") == ZIP_EARLIER
    assert any("Zertifikate" in hint for hint in answer["hinweise"])


def test_all_parts_of_a_file_come_from_the_same_version(server, monkeypatch):  # noqa: F811
    monkeypatch.setattr(apply, "PART_BYTES", 6)
    entry = ready(server)
    built_cv(server, entry, EARLIER)

    first = json.loads(hand_over(server, entry, part=0)[2])
    built_cv(server, entry, LATER)
    rest = [json.loads(hand_over(server, entry, part=number)[2]) for number in range(1, first["teile"])]

    joined = b"".join(base64.b64decode(part["daten"]) for part in [first, *rest])
    assert joined == EARLIER


def _open_form(s, entry):
    return post(s, "/api/bewerben/stand", {"id": entry["id"], "stand": "geoeffnet"})


def test_a_new_form_starts_without_the_files_of_an_abandoned_one(server):  # noqa: F811
    entry = ready(server)
    packed = folder_of(server, entry) / "zertifikate.zip"
    packed.write_bytes(ZIP_EARLIER)
    hand_over(server, entry, "zertifikate")
    packed.unlink()  # the person no longer chose any certificate

    assert _open_form(server, entry)[0] == 200
    answer = send_from_form(server, entry)[1]

    assert "zertifikate" not in Register(server.kontext.daten).hole(entry["id"])["versand"]["dateien"]
    assert answer["hinweise"] == []


def test_an_abandoned_form_no_longer_counts_as_different(server):  # noqa: F811
    entry = ready(server)
    built_cv(server, entry, EARLIER)
    hand_over(server, entry)
    built_cv(server, entry, LATER)

    _open_form(server, entry)

    assert details(server, entry["id"])["formular_abweichend"] == []


def test_filling_the_open_form_keeps_what_it_got(server):  # noqa: F811
    entry = ready(server)
    built_cv(server, entry, EARLIER)
    hand_over(server, entry)
    built_cv(server, entry, LATER)

    post(server, "/api/bewerben/stand", {"id": entry["id"], "stand": "ausgefuellt"})
    send_from_form(server, entry)

    assert sent_file(server, entry, "lebenslauf") == EARLIER


def test_a_copy_that_cannot_be_removed_does_not_stop_a_new_form(server, monkeypatch):  # noqa: F811
    entry = ready(server)
    hand_over(server, entry)

    def fail(*_):
        raise OSError("busy")

    monkeypatch.setattr(form_copy.shutil, "rmtree", fail)

    assert _open_form(server, entry)[0] == 200


def test_a_later_part_without_a_first_one_is_refused(server, monkeypatch):  # noqa: F811
    monkeypatch.setattr(apply, "PART_BYTES", 6)
    entry = ready(server)
    built_cv(server, entry, EARLIER)

    assert hand_over(server, entry, part=1)[0] == 400


@pytest.mark.parametrize("send", [send_from_form, send_from_page])
def test_the_copies_are_gone_after_the_dispatch(server, send):  # noqa: F811
    entry = ready(server)
    hand_over(server, entry)
    assert form_copy.copies(server.kontext.daten, entry["id"])

    assert send(server, entry)[0] == 200

    assert form_copy.copies(server.kontext.daten, entry["id"]) == {}


def test_a_copy_that_cannot_be_removed_only_gives_a_note(server, monkeypatch):  # noqa: F811
    entry = ready(server)
    hand_over(server, entry)

    def fail(*_):
        raise OSError("busy")

    monkeypatch.setattr(form_copy.shutil, "rmtree", fail)
    status, answer = send_from_form(server, entry)

    assert status == 200 and any("Kopie" in hint for hint in answer["hinweise"])
    assert Register(server.kontext.daten).hole(entry["id"])["status"] == "Beworben"


def test_a_sent_application_gets_no_new_copy(server):  # noqa: F811
    entry = ready(server)
    send_from_form(server, entry)

    assert hand_over(server, entry)[0] == 400
    assert form_copy.copies(server.kontext.daten, entry["id"]) == {}


def test_the_copy_is_made_under_the_lock(server, monkeypatch):  # noqa: F811
    entry = ready(server)
    keep, read = form_copy.keep, apply.read_part
    seen = []

    def watching(*arguments):
        seen.append(server.kontext.sperre.locked())
        return keep(*arguments)

    def reading(*arguments):
        seen.append(server.kontext.sperre.locked())
        return read(*arguments)

    monkeypatch.setattr(form_copy, "keep", watching)
    monkeypatch.setattr(apply, "read_part", reading)
    hand_over(server, entry)

    assert seen == [True, True]  # a dispatch can neither come before the copy nor remove it while it is read


def test_a_copy_that_cannot_be_written_says_so(server, monkeypatch):  # noqa: F811
    entry = ready(server)

    def fail(*_):
        raise OSError("disk full")

    monkeypatch.setattr(form_copy, "schreibe_atomar", fail)
    status, _, content = hand_over(server, entry)

    assert status == 400 and json.loads(content)["fehler"] == form_copy.NOT_KEPT


def test_references_are_not_copied(server):  # noqa: F811
    entry = ready(server)
    upload(server, "zeugnis", "Zeugnis.pdf", PDF)
    key = next(f["schluessel"] for f in json.loads(get(server, "/api/bewerben/daten", id=entry["id"])[2])["dateien"]
               if f["schluessel"].startswith("zeugnis-"))

    assert hand_over(server, entry, key)[0] == 200
    assert form_copy.copies(server.kontext.daten, entry["id"]) == {}


def _reference_keys(s, entry) -> dict[str, str]:
    files = json.loads(get(s, "/api/bewerben/daten", id=entry["id"])[2])["dateien"]
    return {f["name"]: f["schluessel"] for f in files if f["schluessel"].startswith("zeugnis-")}


def test_the_key_of_a_reference_stays_when_others_come_and_go(server):  # noqa: F811
    entry = ready(server)
    upload(server, "zeugnis", "B.pdf", PDF + b"b")
    key = _reference_keys(server, entry)["B.pdf"]

    upload(server, "zeugnis", "A.pdf", PDF + b"a")  # sorts before B

    assert _reference_keys(server, entry)["B.pdf"] == key
    part = json.loads(hand_over(server, entry, key)[2])
    assert base64.b64decode(part["daten"]) == PDF + b"b"


def test_the_key_of_a_reference_that_is_gone_finds_no_other_file(server):  # noqa: F811
    entry = ready(server)
    upload(server, "zeugnis", "A.pdf", PDF + b"a")
    upload(server, "zeugnis", "B.pdf", PDF + b"b")
    gone = _reference_keys(server, entry)["A.pdf"]

    post(server, "/api/dateien/entfernen", {"datei": f"{apply.REFERENCES_FOLDER}/A.pdf"})

    assert hand_over(server, entry, gone)[0] == 400


def test_the_page_learns_what_differs_from_the_form(server):  # noqa: F811
    entry = ready(server)
    built_cv(server, entry, EARLIER)
    assert details(server, entry["id"])["formular_abweichend"] == []

    hand_over(server, entry)
    assert details(server, entry["id"])["formular_abweichend"] == []

    built_cv(server, entry, LATER)
    assert details(server, entry["id"])["formular_abweichend"] == ["lebenslauf"]

    built_cv(server, entry, EARLIER)
    assert details(server, entry["id"])["formular_abweichend"] == []


def test_a_sent_application_shows_no_difference(server):  # noqa: F811
    entry = ready(server)
    hand_over(server, entry)
    built_cv(server, entry, LATER)
    send_from_page(server, entry)

    assert details(server, entry["id"])["formular_abweichend"] == []


def test_changing_the_own_letter_says_when_a_form_has_another_one(server):  # noqa: F811
    entry = ready(server)
    assert upload_letter(server, entry["id"], PDF)[1]["formular_abweichend"] == []
    assert post(server, REMOVE, {"id": entry["id"]})[1]["formular_abweichend"] == []

    hand_over(server, entry, "anschreiben")

    assert upload_letter(server, entry["id"], PDF)[1]["formular_abweichend"] == ["anschreiben"]
    assert post(server, REMOVE, {"id": entry["id"]})[1]["formular_abweichend"] == []  # the built letter counts again


def test_a_draft_is_a_source_if_its_letter_went_to_the_form(server):  # noqa: F811
    entry = ready(server)
    data = server.kontext.daten
    source = unterlagen.letter_source(data, entry["id"])
    source.write_text("betreff: Test\n", encoding="utf-8")
    letter_approval.approve(data, entry, server.kontext.heute())  # a draft goes to a form only once approved (MIN-369)
    hand_over(server, entry, "anschreiben")
    upload_letter(server, entry["id"], PDF)
    current = Register(data).hole(entry["id"])
    sent_letter = form_copy.copies(data, entry["id"])["anschreiben"]

    assert source in versand._datenquellen(data, current, sent_letter)
    assert source not in versand._datenquellen(data, current, unterlagen.own_letter(data, current))


def test_the_form_state_is_left_alone_when_recording(server):  # noqa: F811
    entry = ready(server)
    hand_over(server, entry)
    send_from_form(server, entry)

    assert Register(server.kontext.daten).hole(entry["id"])["ausfuellen"] == routes_apply.SENT
