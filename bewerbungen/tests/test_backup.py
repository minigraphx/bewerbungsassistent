"""Backup of the data folder as a ZIP (MIN-359): complete, inside the folder, and a calm reminder."""
import datetime
import io
import json
import os
import zipfile

import pytest

import backup
from app import erstelle_kontext
from register import Register
from test_app import get, post, server  # noqa: F401  (server is a fixture)

TODAY = datetime.date(2026, 11, 4)


def filled(folder):
    (folder / "cv.yaml").write_text("basics: {}\n", encoding="utf-8")
    Register(folder).neu(firma="Muster AG", stelle="Data Engineer")
    for rel in (".entwuerfe/objekte/abc", "versendet/brief.pdf", "dokumente/zeugnisse/z.pdf", ".ki/nutzung.jsonl",
                ".build/rest.pdf", ".git/HEAD", "bewerbungen/a/.git/config"):
        (folder / rel).parent.mkdir(parents=True, exist_ok=True)
        (folder / rel).write_text(rel, encoding="utf-8")
    return folder


def data_folder(parent):
    folder = parent / "daten"
    folder.mkdir()
    return filled(folder)


def names(data: bytes) -> set[str]:
    return set(zipfile.ZipFile(io.BytesIO(data)).namelist())


def test_the_zip_holds_the_data_without_build_and_git(tmp_path):
    found = names(backup.create(filled(tmp_path)))

    assert {"cv.yaml", "bewerbungen.yaml", ".entwuerfe/objekte/abc", "versendet/brief.pdf", "dokumente/zeugnisse/z.pdf", ".ki/nutzung.jsonl"} <= found
    assert not any(n.startswith((".build/", ".git/")) for n in found)
    assert "bewerbungen/a/.git/config" in found, "only the folders at the top are left out"


@pytest.mark.skipif(os.name == "nt", reason="symlinks need rights on Windows")
def test_symlinks_stay_out(tmp_path):
    folder = data_folder(tmp_path)
    secret = tmp_path / "geheim.txt"
    secret.write_text("geheim", encoding="utf-8")
    (tmp_path / "aussen").mkdir()
    (tmp_path / "aussen" / "x.txt").write_text("geheim", encoding="utf-8")
    (folder / "verweis.txt").symlink_to(secret)
    (folder / "ordner").symlink_to(tmp_path / "aussen", target_is_directory=True)

    data = backup.create(folder)

    assert not any(n.startswith(("verweis", "ordner")) for n in names(data))
    assert b"geheim" not in b"".join(zipfile.ZipFile(io.BytesIO(data)).read(n) for n in names(data))


def test_a_backup_works_after_unpacking_somewhere_else(tmp_path):
    source = data_folder(tmp_path)
    kontext = erstelle_kontext(source)
    kontext.mit_entwurf(source / "cv.yaml", "Test", lambda: (source / "cv.yaml").write_text("basics: {name: Neu}\n", encoding="utf-8"))
    target = tmp_path / "anderer-rechner"

    zipfile.ZipFile(io.BytesIO(backup.create(source))).extractall(target)
    copy = erstelle_kontext(target)

    assert [b["firma"] for b in copy.register().alle()] == ["Muster AG"]
    assert copy.ablage.liste() == kontext.ablage.liste() and copy.ablage.liste()
    assert (target / "versendet" / "brief.pdf").read_text(encoding="utf-8") == "versendet/brief.pdf"


def test_name_has_the_date():
    assert backup.file_name(TODAY) == "bewerbungsassistent-sicherung-2026-11-04.zip"


def entries(*sent):
    return [{"id": str(i), "eingetragen_am": "2026-10-30", "beworben_am": day} for i, day in enumerate(sent)]


def state(tmp_path, register, today=TODAY):
    return backup.reminder(tmp_path, register, today)


def test_an_empty_folder_needs_no_reminder(tmp_path):
    assert state(tmp_path, [])["faellig"] is False and state(tmp_path, [])["zuletzt"] is None


def test_new_entries_do_not_nag_at_once(tmp_path):
    assert state(tmp_path, [{"id": "a", "eingetragen_am": "2026-11-01"}])["faellig"] is False


def test_reminder_after_some_sent_applications(tmp_path):
    assert state(tmp_path, entries(*["2026-11-01"] * (backup.REMIND_AFTER_SENT - 1)))["faellig"] is False
    assert state(tmp_path, entries(*["2026-11-01"] * backup.REMIND_AFTER_SENT))["faellig"] is True


def test_reminder_when_a_never_saved_folder_gets_old(tmp_path):
    assert state(tmp_path, [{"id": "a", "eingetragen_am": "2026-09-01"}])["faellig"] is True


def test_a_backup_ends_the_reminder_and_only_later_sendings_count(tmp_path):
    register = entries(*["2026-11-01"] * backup.REMIND_AFTER_SENT)
    assert state(tmp_path, register)["faellig"] is True

    backup.mark_done(tmp_path, TODAY)

    after = state(tmp_path, register)
    assert after["faellig"] is False and after["zuletzt"] == "2026-11-04"
    assert state(tmp_path, entries(*["2026-11-05"] * backup.REMIND_AFTER_SENT), TODAY + datetime.timedelta(days=1))["faellig"] is True


def test_reminder_returns_after_some_days(tmp_path):
    backup.mark_done(tmp_path, TODAY)
    register = [{"id": "a", "eingetragen_am": "2026-09-01"}]

    assert state(tmp_path, register, TODAY + datetime.timedelta(days=backup.REMIND_AFTER_DAYS - 1))["faellig"] is False
    assert state(tmp_path, register, TODAY + datetime.timedelta(days=backup.REMIND_AFTER_DAYS))["faellig"] is True


@pytest.mark.parametrize("content", ["kaputt: [", "zuletzt: gestern\n", "- liste\n"])
def test_a_broken_note_counts_as_no_backup(tmp_path, content):
    (tmp_path / backup.NOTE_FILE).write_text(content, encoding="utf-8")

    assert state(tmp_path, [])["zuletzt"] is None


def test_odd_dates_in_the_register_do_not_break_it(tmp_path):
    assert state(tmp_path, [{"id": "a", "eingetragen_am": "kaputt", "beworben_am": 5}, {"id": "b"}])["faellig"] is False


def test_route_delivers_the_zip_as_a_download(server):  # noqa: F811
    status, kind, data = get(server, "/api/sicherung/datei")

    assert status == 200 and kind == "application/zip" and "bewerbungen.yaml" in names(data)


def test_route_needs_the_token(server):  # noqa: F811
    from test_app import anfrage
    assert anfrage(server, "GET", "/api/sicherung/datei")[0] in (401, 403)


def test_route_marks_a_backup_only_when_told(server):  # noqa: F811
    get(server, "/api/sicherung/datei")
    assert json.loads(get(server, "/api/sicherung/stand")[2])["zuletzt"] is None

    status, answer = post(server, "/api/sicherung/erledigt", {})

    assert status == 200 and answer["zuletzt"] and answer["faellig"] is False
    assert answer["datei"].startswith("bewerbungsassistent-sicherung-")


def test_a_file_from_before_1980_goes_in(tmp_path):
    folder = filled(data_folder(tmp_path))
    os.utime(folder / "cv.yaml", (0, 0))

    assert "cv.yaml" in zipfile.ZipFile(io.BytesIO(backup.create(folder))).namelist()


def test_a_file_that_vanishes_while_packing_is_left_out(tmp_path, monkeypatch):
    folder = filled(data_folder(tmp_path))
    gone = folder / "weg.tmp"
    real = backup._files
    monkeypatch.setattr(backup, "_files", lambda d: [gone, *real(d)])

    assert "cv.yaml" in zipfile.ZipFile(io.BytesIO(backup.create(folder))).namelist()


def test_a_file_that_cannot_be_read_stops_the_backup_with_its_name(tmp_path, monkeypatch):
    folder = filled(data_folder(tmp_path))
    real = zipfile.ZipFile.write

    def locked(self, path, *args, **kwargs):
        if str(path).endswith("brief.pdf"):
            raise PermissionError("locked")
        return real(self, path, *args, **kwargs)

    monkeypatch.setattr(zipfile.ZipFile, "write", locked)

    with pytest.raises(ValueError, match="brief.pdf"):
        backup.create(folder)


def test_an_earlier_backup_in_the_folder_is_not_packed_again(tmp_path):
    folder = filled(data_folder(tmp_path))
    (folder / backup.file_name(TODAY)).write_bytes(b"alt")
    (folder / "dokumente" / "bewerbungsassistent-sicherung-notiz.zip").write_bytes(b"eigene Datei")

    names = zipfile.ZipFile(io.BytesIO(backup.create(folder))).namelist()

    assert backup.file_name(TODAY) not in names
    assert "dokumente/bewerbungsassistent-sicherung-notiz.zip" in names


def test_compressed_files_are_stored_as_they_are(tmp_path):
    folder = filled(data_folder(tmp_path))

    archive = zipfile.ZipFile(io.BytesIO(backup.create(folder)))

    assert archive.getinfo("versendet/brief.pdf").compress_type == zipfile.ZIP_STORED
    assert archive.getinfo("cv.yaml").compress_type == zipfile.ZIP_DEFLATED
