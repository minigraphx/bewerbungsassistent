"""Files the person uploads and uses as they are: a CV as PDF, certificates, references."""
import base64
import dataclasses
import json
import threading
import zipfile

import pytest

import apply
import certificates
import dateien
import own_files
import pruefung
import unterlagen
import versand
from register import Register
from test_app import get, post, server  # noqa: F401  (server is a fixture)

PDF = b"%PDF-1.4\n" + b"x" * 300
PNG = b"\x89PNG\r\n\x1a\n" + b"x" * 50


class CountingLock:
    """A file and what depends on it change in one go: a second turn would let a dispatch come between them."""

    def __init__(self):
        self.times = 0
        self.lock = threading.Lock()

    def __enter__(self):
        self.lock.acquire()
        self.times += 1

    def __exit__(self, *args):
        self.lock.release()


def upload(s, art, name, data=PDF):
    return post(s, "/api/dateien/hochladen", {"art": art, "name": name, "daten": base64.b64encode(data).decode()})


def new_entry(s, **fields):
    _, entry = post(s, "/api/bewerbung/neu", {"firma": "Eigen AG", "stelle": "Tester"})
    if fields:
        _, entry = post(s, "/api/bewerbung", {"id": entry["id"], **fields})
    return entry


def test_an_upload_lands_in_the_folder_of_its_kind_unchanged(server):  # noqa: F811
    assert upload(server, "zertifikat", "Scrum Master.pdf")[0] == 200
    assert upload(server, "zeugnis", "Zeugnis 2020.png", PNG)[0] == 200
    assert upload(server, "lebenslauf", "mein cv.pdf")[0] == 200

    daten = server.kontext.daten
    assert (daten / "dokumente/zertifikate/Scrum Master.pdf").read_bytes() == PDF
    assert (daten / "dokumente/zeugnisse/Zeugnis 2020.png").read_bytes() == PNG
    assert (daten / own_files.CV_FILE).read_bytes() == PDF


def test_the_list_says_what_is_there(server):  # noqa: F811
    upload(server, "lebenslauf", "mein cv.pdf")
    upload(server, "zertifikat", "Scrum Master.pdf")

    found = json.loads(get(server, "/api/dateien")[2])

    assert [f["datei"] for f in found["lebenslauf"]] == [own_files.CV_FILE]
    assert [f["name"] for f in found["zertifikat"]] == ["Scrum Master.pdf"]
    assert found["zertifikat"][0]["groesse"] == len(PDF)
    assert found["zeugnis"] == []


@pytest.mark.parametrize("art, name, data", [
    ("lebenslauf", "cv.docx", PDF), ("lebenslauf", "cv.pdf", b"<html>kein pdf</html>"), ("lebenslauf", "cv.png", PNG),
    ("zertifikat", "seite.html", b"<html></html>"), ("zertifikat", "bild.svg", b"<svg></svg>"), ("zertifikat", "falsch.png", PDF),
    ("anderes", "x.pdf", PDF), ("zertifikat", "", PDF), ("zertifikat", "...", PDF), ("zertifikat", ".pdf", PDF),
    ("zertifikat", "NUL.pdf", PDF), ("zertifikat", "nul.x.pdf", PDF), ("zertifikat", "CON .pdf", PDF)])
def test_what_is_refused_stays_out(server, art, name, data):  # noqa: F811
    assert upload(server, art, name, data)[0] == 400
    assert not (server.kontext.daten / "dokumente").exists() or not list((server.kontext.daten / "dokumente").rglob("*.*"))


@pytest.mark.parametrize("name", ["../../cv.pdf", "..\\..\\cv.pdf", "/etc/cv.pdf", "ordner/cv.pdf", "C:\\tmp\\cv.pdf"])
def test_a_name_never_leads_out_of_the_folder(server, name):  # noqa: F811
    assert upload(server, "zertifikat", name)[0] == 200
    assert (server.kontext.daten / "dokumente/zertifikate/cv.pdf").is_file()
    assert not (server.kontext.daten / "cv.pdf").exists()


def test_a_file_above_the_limit_is_refused_with_a_clear_message(server, monkeypatch):  # noqa: F811
    monkeypatch.setattr(own_files, "MAX_FILE_BYTES", 100)
    status, answer = upload(server, "lebenslauf", "cv.pdf")
    assert status == 400 and "zu gross" in answer["fehler"]


def test_a_large_file_fits_through_the_server(server):  # noqa: F811
    assert upload(server, "lebenslauf", "cv.pdf", b"%PDF-" + b"x" * (own_files.MAX_FILE_BYTES - 5))[0] == 200


def test_only_listed_files_can_be_seen_or_removed(server):  # noqa: F811
    upload(server, "zertifikat", "A.pdf")

    assert get(server, "/api/dateien/ansehen", datei="dokumente/zertifikate/A.pdf")[0] == 200
    for other in ("cv.yaml", "bewerbungen.yaml", "dokumente/zertifikate/../../cv.yaml"):
        assert get(server, "/api/dateien/ansehen", datei=other)[0] == 400
        assert post(server, "/api/dateien/entfernen", {"datei": other})[0] == 400
    assert (server.kontext.daten / "cv.yaml").is_file()

    assert post(server, "/api/dateien/entfernen", {"datei": "dokumente/zertifikate/A.pdf"})[0] == 200
    assert not (server.kontext.daten / "dokumente/zertifikate/A.pdf").exists()


def test_a_page_in_the_folder_can_be_removed_but_never_runs_from_here(server):  # noqa: F811
    folder = server.kontext.daten / "dokumente/zertifikate"
    folder.mkdir(parents=True)
    (folder / "alt.html").write_text("<script>alert(1)</script>", encoding="utf-8")

    assert get(server, "/api/dateien/ansehen", datei="dokumente/zertifikate/alt.html")[0] == 400
    assert post(server, "/api/dateien/entfernen", {"datei": "dokumente/zertifikate/alt.html"})[0] == 200


@pytest.mark.parametrize("name", ["Zeugnis Müller.pdf", "Prüfung Łódź 🎓.pdf", 'a"b.pdf'])
def test_any_name_can_be_shown(server, name):  # noqa: F811
    assert upload(server, "zertifikat", name)[0] == 200
    listed = json.loads(get(server, "/api/dateien")[2])["zertifikat"][0]["datei"]
    status, kind, content = get(server, "/api/dateien/ansehen", datei=listed)
    assert (status, kind, content) == (200, "application/pdf", PDF)


def test_a_removed_certificate_no_longer_goes_along(server):  # noqa: F811
    upload(server, "zertifikat", "A.pdf")
    upload(server, "zertifikat", "B.pdf")
    entry = new_entry(server)
    both = ["dokumente/zertifikate/A.pdf", "dokumente/zertifikate/B.pdf"]
    assert post(server, "/api/zertifikate", {"id": entry["id"], "dateien": both})[0] == 200

    post(server, "/api/dateien/entfernen", {"datei": both[0]})

    daten = server.kontext.daten
    assert Register(daten).hole(entry["id"])["zertifikate"] == [both[1]]
    assert zipfile.ZipFile(certificates.zip_path(daten, entry["id"])).namelist() == ["B.pdf"]


def test_a_replaced_certificate_goes_along_as_it_is_now(server):  # noqa: F811
    upload(server, "zertifikat", "A.pdf", PDF + b"alt")
    entry = new_entry(server)
    post(server, "/api/zertifikate", {"id": entry["id"], "dateien": ["dokumente/zertifikate/A.pdf"]})

    upload(server, "zertifikat", "A.pdf", PDF + b"neu")

    assert zipfile.ZipFile(certificates.zip_path(server.kontext.daten, entry["id"])).read("A.pdf") == PDF + b"neu"


def test_what_was_sent_stays_as_it_was(server):  # noqa: F811
    upload(server, "lebenslauf", "cv.pdf")
    upload(server, "zertifikat", "A.pdf")
    entry = new_entry(server)
    chosen = ["dokumente/zertifikate/A.pdf"]
    post(server, "/api/zertifikate", {"id": entry["id"], "dateien": chosen})
    versand.erfasse_versand(server.kontext.daten, entry["id"], server.kontext.heute(), server.kontext.versionierung)

    post(server, "/api/dateien/entfernen", {"datei": chosen[0]})

    assert Register(server.kontext.daten).hole(entry["id"])["zertifikate"] == chosen


def test_an_uploaded_cv_counts_as_a_start(server):  # noqa: F811
    (server.kontext.daten / "cv.yaml").unlink()
    assert json.loads(get(server, "/api/grundlagen")[2])["lebenslauf"] is False
    upload(server, "lebenslauf", "cv.pdf")
    assert json.loads(get(server, "/api/grundlagen")[2])["lebenslauf"] is True


def test_a_request_without_a_proper_path_is_refused(server):  # noqa: F811
    for wrong in ([], {}, None, 1):
        assert post(server, "/api/dateien/entfernen", {"datei": wrong})[0] == 400


def test_certificates_follow_inside_the_lock_so_nothing_recorded_meanwhile_is_lost(server, monkeypatch):  # noqa: F811
    upload(server, "zertifikat", "A.pdf")
    entry = new_entry(server)
    post(server, "/api/zertifikate", {"id": entry["id"], "dateien": ["dokumente/zertifikate/A.pdf"]})
    lock = CountingLock()
    monkeypatch.setattr(server, "kontext", dataclasses.replace(server.kontext, sperre=lock))

    upload(server, "zertifikat", "A.pdf", PDF + b"neu")
    assert lock.times == 1
    post(server, "/api/dateien/entfernen", {"datei": "dokumente/zertifikate/A.pdf"})
    assert lock.times == 2


def test_a_chosen_file_deleted_by_hand_does_not_stop_the_next_upload(server):  # noqa: F811
    upload(server, "zertifikat", "A.pdf")
    upload(server, "zertifikat", "B.pdf")
    entry = new_entry(server)
    both = ["dokumente/zertifikate/A.pdf", "dokumente/zertifikate/B.pdf"]
    post(server, "/api/zertifikate", {"id": entry["id"], "dateien": both})
    (server.kontext.daten / both[1]).unlink()

    assert upload(server, "zertifikat", "A.pdf", PDF + b"neu")[0] == 200

    assert Register(server.kontext.daten).hole(entry["id"])["zertifikate"] == [both[0]]


def test_the_same_name_in_other_letters_replaces_the_file(server):  # noqa: F811
    upload(server, "zertifikat", "Scrum.pdf", PDF + b"alt")
    entry = new_entry(server)
    post(server, "/api/zertifikate", {"id": entry["id"], "dateien": ["dokumente/zertifikate/Scrum.pdf"]})

    upload(server, "zertifikat", "SCRUM.PDF", PDF + b"neu")

    found = json.loads(get(server, "/api/dateien")[2])["zertifikat"]
    assert [f["name"] for f in found] == ["Scrum.pdf"]
    assert zipfile.ZipFile(certificates.zip_path(server.kontext.daten, entry["id"])).read("Scrum.pdf") == PDF + b"neu"


def test_a_certificate_brought_back_goes_along_as_it_was(server):  # noqa: F811
    upload(server, "zertifikat", "A.pdf", PDF + b"alt")
    entry = new_entry(server)
    post(server, "/api/zertifikate", {"id": entry["id"], "dateien": ["dokumente/zertifikate/A.pdf"]})
    upload(server, "zertifikat", "A.pdf", PDF + b"neu")
    daten = server.kontext.daten
    old = next(e for e in server.kontext.ablage.liste(daten / "dokumente/zertifikate/A.pdf")
               if server.kontext.ablage.inhalt(e.id) == PDF + b"alt")

    assert post(server, "/api/entwurf/wiederherstellen", {"id": old.id})[0] == 200

    assert zipfile.ZipFile(certificates.zip_path(daten, entry["id"])).read("A.pdf") == PDF + b"alt"


def test_a_failed_write_leaves_nothing_in_the_folder(server, monkeypatch):  # noqa: F811
    folder = server.kontext.daten / "dokumente/zertifikate"

    def refuse(*args):
        raise OSError("Datei ist offen")

    monkeypatch.setattr(dateien.os, "replace", refuse)
    with pytest.raises(OSError):
        dateien.schreibe_atomar(folder / "A.pdf", PDF)

    assert list(folder.iterdir()) == []


def test_a_sent_application_keeps_showing_what_was_sent(server):  # noqa: F811
    entry = new_entry(server)
    upload(server, "lebenslauf", "cv.pdf", PDF + b"alt")
    versand.erfasse_versand(server.kontext.daten, entry["id"], server.kontext.heute(), server.kontext.versionierung)

    upload(server, "lebenslauf", "cv.pdf", PDF + b"neu")

    assert get(server, "/api/pdf", id=entry["id"], art="lebenslauf")[2] == PDF + b"alt"
    assert json.loads(get(server, "/api/bewerbung", id=entry["id"])[2])["eigener_lebenslauf"] is False


def test_a_replaced_or_removed_file_can_be_brought_back(server):  # noqa: F811
    upload(server, "lebenslauf", "cv.pdf", PDF + b"alt")
    upload(server, "lebenslauf", "cv.pdf", PDF + b"neu")
    path = server.kontext.daten / own_files.CV_FILE
    post(server, "/api/dateien/entfernen", {"datei": own_files.CV_FILE})
    assert not path.exists()
    assert {server.kontext.ablage.inhalt(e.id) for e in server.kontext.ablage.liste(path)} >= {PDF + b"alt", PDF + b"neu"}


def test_an_own_cv_makes_an_application_ready_without_building(server):  # noqa: F811
    entry = new_entry(server, link="https://www.jobs.ch/de/stellenangebote/detail/1/")
    daten = server.kontext.daten
    assert apply.blocker(daten, entry) == apply.NO_CV

    upload(server, "lebenslauf", "cv.pdf")

    assert apply.blocker(daten, entry) is None
    assert apply.uploads(daten, entry)["lebenslauf"].path == daten / own_files.CV_FILE


def test_a_chosen_variant_goes_before_the_own_cv(server):  # noqa: F811
    entry = new_entry(server, link="https://www.jobs.ch/de/stellenangebote/detail/1/", variante="daten")
    upload(server, "lebenslauf", "cv.pdf")
    assert apply.blocker(server.kontext.daten, entry) == apply.NO_CV


def test_building_uses_the_own_cv_and_a_new_upload_counts_at_once(server, tmp_path):  # noqa: F811
    entry = new_entry(server)
    daten = server.kontext.daten
    upload(server, "lebenslauf", "cv.pdf", PDF + b"1")

    built = unterlagen.baue(daten, entry, tmp_path / "build")
    assert built["lebenslauf"] == daten / own_files.CV_FILE
    assert not unterlagen.pdf_pfade(daten, entry["id"])["lebenslauf"].exists()

    upload(server, "lebenslauf", "cv.pdf", PDF + b"2")
    assert unterlagen.wirksame_pdfs(daten, entry)["lebenslauf"].read_bytes() == PDF + b"2"


def test_the_page_of_the_application_shows_the_own_cv(server):  # noqa: F811
    entry = new_entry(server)
    upload(server, "lebenslauf", "cv.pdf")

    details = json.loads(get(server, "/api/bewerbung", id=entry["id"])[2])

    assert details["pdfs"]["lebenslauf"] is True and details["eigener_lebenslauf"] is True
    assert get(server, "/api/pdf", id=entry["id"], art="lebenslauf")[2] == PDF


def test_a_scan_is_only_a_hint_when_the_person_uses_it_as_it_is(server):  # noqa: F811
    entry = new_entry(server)
    upload(server, "lebenslauf", "scan.pdf", _pdf_without_text())
    findings = pruefung.pruefe(server.kontext.daten, entry, server.kontext.heute())
    assert not [f for f in findings if f.stufe == "fehler"]
    assert any("kaum Text" in f.text and f.stufe == "hinweis" for f in findings)


def test_a_broken_file_is_still_an_error(server):  # noqa: F811
    entry = new_entry(server)
    upload(server, "lebenslauf", "kaputt.pdf")
    findings = pruefung.pruefe(server.kontext.daten, entry, server.kontext.heute())
    assert [f for f in findings if f.stufe == "fehler"]


def test_sending_keeps_a_copy_of_the_own_cv(server):  # noqa: F811
    entry = new_entry(server)
    upload(server, "lebenslauf", "cv.pdf")

    versand.erfasse_versand(server.kontext.daten, entry["id"], server.kontext.heute(), server.kontext.versionierung)

    sent = Register(server.kontext.daten).hole(entry["id"])["versand"]["dateien"]["lebenslauf"]
    assert (server.kontext.daten / sent).read_bytes() == PDF


def test_certificates_uploaded_here_can_be_chosen_for_an_application(server):  # noqa: F811
    entry = new_entry(server)
    upload(server, "zertifikat", "Scrum Master.pdf")
    found = json.loads(get(server, "/api/zertifikate", id=entry["id"])[2])
    assert found["verfuegbar"] == ["dokumente/zertifikate/Scrum Master.pdf"]


def test_the_form_values_work_without_a_cv_in_the_app(server):  # noqa: F811
    (server.kontext.daten / "cv.yaml").unlink()
    assert isinstance(apply.form_values(server.kontext.daten), dict)


def test_a_form_can_be_opened_with_nothing_but_the_uploaded_cv(server):  # noqa: F811
    (server.kontext.daten / "cv.yaml").unlink()
    entry = new_entry(server, link="https://www.jobs.ch/de/stellenangebote/detail/1/")
    scan = _pdf_without_text()
    upload(server, "lebenslauf", "cv.pdf", scan)
    upload(server, "zeugnis", "Zeugnis.png", PNG)

    assert post(server, "/api/bewerben/start", {"ids": [entry["id"]]})[1]["abgelehnt"] == []
    answer = json.loads(get(server, "/api/bewerben/daten", id=entry["id"])[2])
    assert answer["werte"] == {}
    assert {f["schluessel"] for f in answer["dateien"]} == {"lebenslauf", "zeugnis-0"}
    part = json.loads(get(server, "/api/bewerben/datei", id=entry["id"], schluessel="lebenslauf")[2])
    assert base64.b64decode(part["daten"]) == scan


def _pdf_without_text() -> bytes:
    import io

    from pypdf import PdfWriter
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    stream = io.BytesIO()
    writer.write(stream)
    return stream.getvalue()
