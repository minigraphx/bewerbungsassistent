"""One drop area on „Meine Angaben“ (G84, #270): the person corrects the guessed kind of a pending document.

The kind is the folder under `dokumente/`; changing it moves the file and its entry in `neu.yaml`, within the limits
of form.json. Invented names and contents only.
"""
import base64
import json

import pytest
import yaml

import validation
from test_angaben import PDF, call, consent_given, install_client, prefill_reply, started, upload  # noqa: F401  (fixtures)

KIND_ROUTE = "/api/angaben/unterlage-art"
FORM = validation.load_form()
LIMITS = {c["id"]: c["maxFiles"] for c in FORM["documents"]["categories"]}


def pending(folder) -> list[dict]:
    return yaml.safe_load((folder / "dokumente" / "neu.yaml").read_text(encoding="utf-8"))


def change(server, datei, category, track="job"):
    return call(server, KIND_ROUTE, {"datei": datei, "category": category, "track": track})


def test_changing_the_kind_moves_the_file_and_its_pending_entry(started):
    server, folder, _ = started
    upload(server, name="Scan_001.pdf", category="zertifikate")
    upload(server, name="cv.pdf", category="lebenslauf-bisher", data=PDF + b"cv")
    before = pending(folder)

    status, answer = change(server, "dokumente/zertifikate/Scan_001.pdf", "zeugnisse")

    assert status == 200, answer
    assert answer["datei"] == "dokumente/zeugnisse/Scan_001.pdf"
    assert [(u["category"], u["name"]) for u in answer["unterlagen"]] == [("zeugnisse", "Scan_001.pdf"),
                                                                           ("lebenslauf-bisher", "cv.pdf")]
    assert (folder / "dokumente" / "zeugnisse" / "Scan_001.pdf").read_bytes() == PDF
    assert not (folder / "dokumente" / "zertifikate" / "Scan_001.pdf").exists()
    after = pending(folder)
    assert [e["datei"] for e in after] == ["dokumente/zeugnisse/Scan_001.pdf", "dokumente/lebenslauf-bisher/cv.pdf"]
    assert after[0]["eingang"] == before[0]["eingang"]


def test_the_next_prefill_sends_the_file_under_its_new_kind(started, monkeypatch):
    server, _, _ = started
    messages = install_client(monkeypatch, prefill_reply())
    upload(server, name="Notizen.txt", category="zertifikate", data="Entwicklerin bei Muster GmbH seit 2019".encode())
    change(server, "dokumente/zertifikate/Notizen.txt", "lebenslauf-bisher")

    status, _ = call(server, "/api/angaben/vorbefuellen", {"track": "job", "data": {"person": {"name": "Erika Beispiel"}}})

    sent = json.dumps(messages.calls[0]["messages"], ensure_ascii=False)
    assert status == 200
    assert "Unterlage 1: Bisheriger Lebenslauf" in sent and "Zertifikate und Diplome" not in sent


def test_a_full_kind_refuses_the_change_and_nothing_moves(started):
    server, folder, _ = started
    for number in range(LIMITS["zeugnisse"]):
        upload(server, name=f"Zeugnis {number}.pdf", category="zeugnisse", data=PDF + str(number).encode())
    upload(server, name="Scan.pdf", category="zertifikate")

    status, answer = change(server, "dokumente/zertifikate/Scan.pdf", "zeugnisse")

    assert status == 400 and "höchstens 20" in answer["fehler"]
    assert (folder / "dokumente" / "zertifikate" / "Scan.pdf").is_file()
    assert "dokumente/zertifikate/Scan.pdf" in [e["datei"] for e in pending(folder)]


def test_an_image_cannot_become_a_cv(started):
    server, folder, _ = started
    upload(server, name="Foto.jpg", category="zertifikate", data=b"\xff\xd8erfunden")

    status, answer = change(server, "dokumente/zertifikate/Foto.jpg", "lebenslauf-bisher")

    assert status == 400 and "Dateityp" in answer["fehler"]
    assert (folder / "dokumente" / "zertifikate" / "Foto.jpg").is_file()


def test_a_file_of_the_same_name_in_the_new_folder_is_never_overwritten(started):
    server, folder, _ = started
    kept = folder / "dokumente" / "zeugnisse" / "Scan.pdf"
    kept.parent.mkdir(parents=True)
    kept.write_bytes(b"schon abgelegt")
    upload(server, name="Scan.pdf", category="zertifikate")

    status, answer = change(server, "dokumente/zertifikate/Scan.pdf", "zeugnisse")

    assert status == 400 and answer["fehler"] == "Unter Zeugnisse liegt schon eine Datei namens Scan.pdf."
    assert kept.read_bytes() == b"schon abgelegt"
    assert (folder / "dokumente" / "zertifikate" / "Scan.pdf").read_bytes() == PDF


def kinds_record(folder) -> dict:
    record = folder / "dokumente" / "arten.yaml"
    return yaml.safe_load(record.read_text(encoding="utf-8")) or {} if record.is_file() else {}


def test_a_moved_file_leaves_no_kind_behind_in_the_record_of_kinds(started):
    server, folder, _ = started
    upload(server, name="Scan.pdf", category="zertifikate")
    upload(server, name="Diplom_alt.pdf", category="zertifikate", data=PDF + b"alt")
    record = folder / "dokumente" / "arten.yaml"
    record.write_text("dokumente/zertifikate/Scan.pdf: diplom\ndokumente/zertifikate/Diplom_alt.pdf: diplom\n",
                      encoding="utf-8")

    status, answer = change(server, "dokumente/zertifikate/Scan.pdf", "zeugnisse")

    assert status == 200, answer
    assert kinds_record(folder) == {"dokumente/zertifikate/Diplom_alt.pdf": "diplom"}


def test_an_unreadable_record_of_kinds_stops_the_change_before_the_file_moves(started):
    server, folder, _ = started
    upload(server, name="Scan.pdf", category="zertifikate")
    (folder / "dokumente" / "arten.yaml").write_text("- keine: [Liste\n", encoding="utf-8")

    status, answer = change(server, "dokumente/zertifikate/Scan.pdf", "zeugnisse")

    assert status == 400 and "arten.yaml" in answer["fehler"]
    assert (folder / "dokumente" / "zertifikate" / "Scan.pdf").is_file()


@pytest.mark.parametrize("datei, category", [
    ("dokumente/zertifikate/gibt-es-nicht.pdf", "zeugnisse"),
    ("cv.yaml", "zeugnisse"),
    ("dokumente/zertifikate/Scan.pdf", "gibt-es-nicht"),
    ("dokumente/zertifikate/Scan.pdf", "../.."),
    (["dokumente/zertifikate/Scan.pdf"], "zeugnisse"),
])
def test_only_pending_documents_change_and_only_to_a_known_kind(started, datei, category):
    server, folder, _ = started
    upload(server, name="Scan.pdf", category="zertifikate")
    (folder / "cv.yaml").write_text("basics: {}\n", encoding="utf-8")

    status, answer = call(server, KIND_ROUTE, {"datei": datei, "category": category})

    assert status == 400 and answer["fehler"]
    assert (folder / "dokumente" / "zertifikate" / "Scan.pdf").is_file() and (folder / "cv.yaml").is_file()


def test_the_same_kind_changes_nothing(started):
    server, folder, _ = started
    upload(server, name="Scan.pdf", category="zertifikate")

    status, answer = change(server, "dokumente/zertifikate/Scan.pdf", "zertifikate")

    assert status == 200 and answer["datei"] == "dokumente/zertifikate/Scan.pdf"
    assert (folder / "dokumente" / "zertifikate" / "Scan.pdf").is_file()


@pytest.mark.parametrize("category", sorted(LIMITS))
def test_each_kind_still_takes_only_its_number_of_files(started, category):
    server, folder, _ = started
    for number in range(LIMITS[category]):
        assert upload(server, name=f"datei {number}.pdf", category=category, data=PDF + str(number).encode())[0] == 200

    status, answer = upload(server, name="eine zu viel.pdf", category=category, data=PDF + b"x")

    assert status == 400 and f"höchstens {LIMITS[category]}" in answer["fehler"]
    assert not (folder / "dokumente" / category / "eine zu viel.pdf").exists()


def test_a_file_above_15_mb_is_refused(started):
    server, folder, _ = started
    too_big = b"x" * (FORM["documents"]["maxFileBytes"] + 1)

    status, _ = call(server, "/api/angaben/unterlage",
                     {"category": "zertifikate", "name": "gross.pdf", "data": base64.b64encode(too_big).decode()})

    assert status in (400, 413)
    assert not (folder / "dokumente" / "zertifikate" / "gross.pdf").exists()
