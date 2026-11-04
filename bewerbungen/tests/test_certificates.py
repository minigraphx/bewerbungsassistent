"""Certificates per application (MIN-346): suggestion from the ad, the choice in the register, one ZIP file."""
import hashlib
import json
import zipfile

import pytest

import app
import certificates
from register import Register
from test_app import get, post, server  # noqa: F401  (server is a fixture)


def folder_with(tmp_path, *names):
    target = tmp_path / "dokumente" / "zertifikate"
    target.mkdir(parents=True)
    for name in names:
        (target / name).write_bytes(name.encode("utf-8"))
    return tmp_path


def test_lists_the_certificates_and_nothing_else(tmp_path):
    data = folder_with(tmp_path, "Scrum Master.pdf", "Python Kurs.pdf", ".versteckt.pdf")
    (data / "dokumente" / "zeugnisse").mkdir()
    (data / "dokumente" / "zeugnisse" / "Zeugnis.pdf").write_bytes(b"x")
    (data / "dokumente" / "zertifikate" / "link.pdf").symlink_to(data / "dokumente" / "zeugnisse" / "Zeugnis.pdf")

    assert certificates.available(data) == ["dokumente/zertifikate/Python Kurs.pdf", "dokumente/zertifikate/Scrum Master.pdf"]


def test_no_folder_means_no_certificates(tmp_path):
    assert certificates.available(tmp_path) == []


def test_suggests_what_the_ad_asks_for_with_a_reason(tmp_path):
    data = folder_with(tmp_path, "Scrum Master.pdf", "Python Kurs.pdf", "Staplerfahrer.pdf")

    found = certificates.suggest(certificates.available(data), "Sie arbeiten agil als Scrum Master und mit python.")

    assert [f["datei"] for f in found] == ["dokumente/zertifikate/Python Kurs.pdf", "dokumente/zertifikate/Scrum Master.pdf"]
    assert "Scrum" in found[1]["grund"] and "Inserat" in found[1]["grund"]


def test_general_words_in_a_file_name_suggest_nothing(tmp_path):
    data = folder_with(tmp_path, "Zertifikat Kurs 2021.pdf", "Diplom.pdf")

    assert certificates.suggest(certificates.available(data), "Kurs mit Diplom und Zertifikat 2021") == []


def test_part_of_a_word_is_no_match(tmp_path):
    data = folder_with(tmp_path, "Java Grundlagen.pdf")

    assert certificates.suggest(certificates.available(data), "Kenntnisse in JavaScript") == []


def test_choice_outside_the_certificates_is_refused(tmp_path):
    data = folder_with(tmp_path, "Scrum.pdf")

    for bad in (["cv.yaml"], ["dokumente/zertifikate/../../cv.yaml"], ["dokumente/zertifikate/fehlt.pdf"], "text", [1]):
        with pytest.raises(ValueError):
            certificates.checked_choice(data, bad)


def entry(data):
    return Register(data).neu(firma="Muster AG", stelle="Data Engineer")


def test_zip_has_exactly_the_chosen_files_with_readable_names(tmp_path):
    data = folder_with(tmp_path, "Scrum Master.pdf", "Python Kurs.pdf")
    bewerbung = entry(data)

    path = certificates.write_zip(data, bewerbung["id"], ["dokumente/zertifikate/Scrum Master.pdf"])

    with zipfile.ZipFile(path) as archive:
        assert archive.namelist() == ["Scrum Master.pdf"]
        assert archive.read("Scrum Master.pdf") == b"Scrum Master.pdf"


def test_same_choice_gives_the_same_file_so_a_sent_copy_is_not_kept_twice(tmp_path):
    data = folder_with(tmp_path, "A.pdf", "B.pdf")
    bewerbung = entry(data)
    choice = ["dokumente/zertifikate/A.pdf", "dokumente/zertifikate/B.pdf"]

    first = hashlib.sha256(certificates.write_zip(data, bewerbung["id"], choice).read_bytes()).hexdigest()
    (data / "dokumente" / "zertifikate" / "A.pdf").touch()
    second = hashlib.sha256(certificates.write_zip(data, bewerbung["id"], list(reversed(choice))).read_bytes()).hexdigest()

    assert first == second


def test_no_choice_removes_the_file(tmp_path):
    data = folder_with(tmp_path, "A.pdf")
    bewerbung = entry(data)
    path = certificates.write_zip(data, bewerbung["id"], ["dokumente/zertifikate/A.pdf"])

    assert certificates.write_zip(data, bewerbung["id"], []) is None
    assert not path.exists()


def test_upload_name_comes_from_the_cv_and_is_a_safe_file_name(tmp_path):
    (tmp_path / "cv.yaml").write_text('basics: {name: "Erika / Beispiel"}\n', encoding="utf-8")

    assert certificates.upload_name(tmp_path) == "Zertifikate_Erika_Beispiel.zip"


def test_upload_name_without_a_cv(tmp_path):
    assert certificates.upload_name(tmp_path) == "Zertifikate.zip"


def test_register_keeps_the_choice_and_the_form_link(tmp_path):
    register = Register(tmp_path)
    created = register.neu(firma="A", stelle="B", zertifikate=["dokumente/zertifikate/A.pdf"], formular_link="https://a.example/form")

    assert register.hole(created["id"])["zertifikate"] == ["dokumente/zertifikate/A.pdf"]
    assert register.hole(created["id"])["formular_link"] == "https://a.example/form"


def test_register_keeps_an_empty_choice_apart_from_no_choice_yet(tmp_path):
    register = Register(tmp_path)
    created = register.neu(firma="A", stelle="B", zertifikate=[])

    assert register.hole(created["id"])["zertifikate"] == []


@pytest.mark.parametrize("fields", [{"zertifikate": "text"}, {"zertifikate": [1]}, {"formular_link": "javascript:alert(1)"}, {"ausfuellen": "kaputt"}])
def test_register_refuses_bad_values(tmp_path, fields):
    with pytest.raises(ValueError):
        Register(tmp_path).neu(firma="A", stelle="B", **fields)


def with_certificates(server):
    data = server.kontext.daten
    target = data / "dokumente" / "zertifikate"
    target.mkdir(parents=True, exist_ok=True)
    (target / "Scrum Master.pdf").write_bytes(b"scrum")
    (target / "Stapler.pdf").write_bytes(b"stapler")
    return server, data


@pytest.fixture
def app_with(server):  # noqa: F811
    s, data = with_certificates(server)
    entry = s.kontext.register().neu(firma="Vorbild AG", stelle="Scrum Master")
    folder = data / "bewerbungen" / entry["id"]
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "stelle.md").write_text("Wir suchen eine Scrum Master.", encoding="utf-8")
    return s, data, entry["id"]


def test_page_gets_list_suggestion_and_no_choice_yet(app_with):
    s, _, wanted = app_with

    answer = json.loads(get(s, "/api/zertifikate", id=wanted)[2])

    assert answer["verfuegbar"] == ["dokumente/zertifikate/Scrum Master.pdf", "dokumente/zertifikate/Stapler.pdf"]
    assert [v["datei"] for v in answer["vorschlag"]] == ["dokumente/zertifikate/Scrum Master.pdf"]
    assert answer["gewaehlt"] is None


def test_saving_a_choice_writes_register_and_zip(app_with):
    s, data, wanted = app_with

    status, answer = post(s, "/api/zertifikate", {"id": wanted, "dateien": ["dokumente/zertifikate/Stapler.pdf"]})

    assert status == 200 and answer["gewaehlt"] == ["dokumente/zertifikate/Stapler.pdf"]
    assert s.kontext.register().hole(wanted)["zertifikate"] == ["dokumente/zertifikate/Stapler.pdf"]
    with zipfile.ZipFile(data / "bewerbungen" / wanted / "zertifikate.zip") as archive:
        assert archive.namelist() == ["Stapler.pdf"]


def test_a_bad_choice_changes_nothing(app_with):
    s, data, wanted = app_with

    assert post(s, "/api/zertifikate", {"id": wanted, "dateien": ["cv.yaml"]})[0] == 400
    assert "zertifikate" not in s.kontext.register().hole(wanted)
    assert not (data / "bewerbungen" / wanted / "zertifikate.zip").exists()


def test_saving_the_form_of_the_page_cannot_change_choice_or_form_state(app_with):
    s, _, wanted = app_with
    post(s, "/api/zertifikate", {"id": wanted, "dateien": ["dokumente/zertifikate/Stapler.pdf"]})
    stale = {"id": wanted, "firma": "Vorbild AG", "stelle": "Scrum Master", "zertifikate": [], "ausfuellen": "abgeschickt"}

    post(s, "/api/bewerbung", stale)

    entry = s.kontext.register().hole(wanted)
    assert entry["zertifikate"] == ["dokumente/zertifikate/Stapler.pdf"] and "ausfuellen" not in entry


def test_the_zip_goes_along_with_a_dispatch_and_stays_out_of_git(app_with):
    s, data, wanted = app_with
    post(s, "/api/zertifikate", {"id": wanted, "dateien": ["dokumente/zertifikate/Stapler.pdf"]})
    (data / "bewerbungen" / wanted / "lebenslauf.pdf").write_bytes(b"%PDF-1.4 x")

    status, answer = post(s, "/api/versand", {"datum": "2026-11-04", "art": "elektronisch"}, id=wanted)

    assert status == 200
    sent = answer["bewerbung"]["versand"]["dateien"]
    assert sent["zertifikate"].startswith("versendet/") and sent["zertifikate"].endswith(".zip")
    assert (data / sent["zertifikate"]).is_file()
    assert "bewerbungen/*/*.zip" in app.GITIGNORE
    assert get(s, "/api/versendet", datei=sent["zertifikate"])[0] == 200
