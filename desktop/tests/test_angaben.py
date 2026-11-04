"""Page „Meine Angaben“ (MIN-366): the template inside the app; state and documents go to the data folder."""
import base64
import concurrent.futures
import json
import pathlib
import threading
import urllib.error
import urllib.request

import pytest
import yaml

import app
import routes_angaben
import routes_setup
import settings

CASES = pathlib.Path(__file__).resolve().parents[2] / "onboarding" / "tests" / "cases.json"
PDF = b"%PDF-1.4 erfunden"


def valid_bundle() -> dict:
    return json.loads(CASES.read_text(encoding="utf-8"))["bases"]["job"]


@pytest.fixture
def started(tmp_path):
    paths = settings.Paths(tmp_path / "app")
    folder = tmp_path / "daten"
    folder.mkdir()
    settings.remember_data_dir(paths, folder)
    server = app.erstelle_server(folder)

    def switch(chosen):
        server.kontext = app.erstelle_kontext(chosen)

    state = routes_setup.Setup(paths=paths, switch=switch, suggestion=folder)
    get_routes, post_routes, limits = routes_angaben.make_routes(state)
    server.routen_get.update(get_routes)
    server.routen_post.update(post_routes)
    server.grenzen.update(limits)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield server, folder, paths
    server.shutdown()
    server.server_close()


def call(server, path, body=None):
    url = f"{server.url.rstrip('/')}{path}"
    if body is None:
        request = urllib.request.Request(f"{url}?t={server.token}")
    else:
        request = urllib.request.Request(url, json.dumps(body).encode(), method="POST",
                                         headers={"Content-Type": "application/json", "X-Token": server.token})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def upload(server, name="lebenslauf.pdf", category="lebenslauf-bisher", data=PDF):
    return call(server, "/api/angaben/unterlage",
                {"category": category, "name": name, "data": base64.b64encode(data).decode()})


def test_page_is_the_template_with_its_own_policy(started):
    server, _, _ = started
    with urllib.request.urlopen(f"{server.url}angaben", timeout=10) as response:
        html = response.read().decode("utf-8")
        policies = response.headers.get_all("Content-Security-Policy")

    assert len(policies) == 1 and "connect-src 'self'" in policies[0] and "script-src 'sha256-" in policies[0]
    assert 'data-app="1"' in html and f'content="{server.token}"' in html and "__TOKEN__" not in html


def test_other_pages_keep_the_strict_policy(started):
    server, _, _ = started
    with urllib.request.urlopen(f"{server.url}einrichtung", timeout=10) as response:
        assert "script-src 'self'" in response.headers["Content-Security-Policy"]


def test_state_is_kept_in_the_data_folder(started):
    server, folder, _ = started
    assert call(server, "/api/angaben/stand") == (200, {"stand": None, "unterlagen": [], "vorhanden": []})

    state = {"track": "job", "data": {"person": {"name": "Erika Beispiel"}}, "step": 2}
    assert call(server, "/api/angaben/stand", {"stand": state})[0] == 200

    assert call(server, "/api/angaben/stand")[1]["stand"] == state
    assert "dokumente/" in (folder / ".gitignore").read_text(encoding="utf-8")
    assert not list(folder.glob("*.json"))  # not next to the files the person edits


@pytest.mark.parametrize("state", ["text", ["liste"], None])
def test_wrong_state_is_refused(started, state):
    assert call(started[0], "/api/angaben/stand", {"stand": state})[0] == 400


def test_state_can_be_discarded(started):
    server, _, _ = started
    call(server, "/api/angaben/stand", {"stand": {"track": "job", "data": {}, "step": 0}})

    assert call(server, "/api/angaben/stand-loeschen", {})[0] == 200
    assert call(server, "/api/angaben/stand")[1]["stand"] is None


def test_nothing_works_before_a_data_folder_is_chosen(started):
    server, folder, paths = started
    settings.save(paths, {})

    status, answer = call(server, "/api/angaben/stand")

    assert status == 400 and "Datenordner" in answer["fehler"]


def test_document_goes_to_the_data_folder_and_the_pending_list(started):
    server, folder, _ = started

    status, answer = upload(server)

    assert status == 200
    assert answer["unterlagen"] == [{"category": "lebenslauf-bisher", "name": "lebenslauf.pdf", "size": len(PDF),
                                     "datei": "dokumente/lebenslauf-bisher/lebenslauf.pdf"}]
    assert (folder / "dokumente" / "lebenslauf-bisher" / "lebenslauf.pdf").read_bytes() == PDF
    pending = yaml.safe_load((folder / "dokumente" / "neu.yaml").read_text(encoding="utf-8"))
    assert [e["datei"] for e in pending] == ["dokumente/lebenslauf-bisher/lebenslauf.pdf"]


def test_documents_larger_than_a_normal_request_are_accepted(started):
    server, folder, _ = started
    big = b"x" * (3 * 1024 * 1024)

    assert upload(server, data=big)[0] == 200
    assert (folder / "dokumente" / "lebenslauf-bisher" / "lebenslauf.pdf").stat().st_size == len(big)


def test_other_routes_keep_the_normal_limit(started):
    server, _, _ = started

    status, _answer = call(server, "/api/angaben/stand", {"stand": {"track": "job", "data": {"x": "y" * (3 * 1024 * 1024)}}})

    assert status == 400


@pytest.mark.parametrize("name, category, needle", [
    ("lebenslauf.exe", "lebenslauf-bisher", "Dateityp"),
    ("../boese.pdf", "lebenslauf-bisher", "Dateiname"),
    ("a/b.pdf", "lebenslauf-bisher", "Dateiname"),
    ("cv.pdf", "gibt-es-nicht", "Art"),
])
def test_wrong_documents_are_refused(started, name, category, needle):
    server, folder, _ = started

    status, answer = upload(server, name=name, category=category)

    assert status == 400 and needle in answer["fehler"]
    assert not (folder / "dokumente" / "neu.yaml").exists()


def test_broken_base64_is_refused(started):
    status, _ = call(started[0], "/api/angaben/unterlage", {"category": "zeugnisse", "name": "z.pdf", "data": "%%%"})

    assert status == 400


def test_same_document_is_not_stored_twice(started):
    server, _, _ = started
    upload(server)

    status, answer = upload(server)

    assert status == 400 and "schon dabei" in answer["fehler"]


def test_pending_document_can_be_removed(started):
    server, folder, _ = started
    upload(server)
    rel = "dokumente/lebenslauf-bisher/lebenslauf.pdf"

    status, answer = call(server, "/api/angaben/unterlage-entfernen", {"datei": rel})

    assert status == 200 and answer["unterlagen"] == []
    assert not (folder / rel).exists()


@pytest.mark.parametrize("rel", ["cv.yaml", "../geheim.txt", "dokumente/neu.yaml"])
def test_only_pending_documents_can_be_removed(started, rel):
    server, folder, _ = started
    (folder / "cv.yaml").write_text("basics: {}\n", encoding="utf-8")

    assert call(server, "/api/angaben/unterlage-entfernen", {"datei": rel})[0] == 400
    assert (folder / "cv.yaml").exists()


def test_take_over_writes_the_basics(started):
    server, folder, _ = started

    status, answer = call(server, "/api/angaben/uebernehmen", {"bundle": valid_bundle()})

    assert status == 200 and answer["unvollstaendig"] is False and "cv.yaml" in answer["geschrieben"]
    assert (folder / "suchprofil.md").is_file()
    assert "cv.yaml" in call(server, "/api/angaben/stand")[1]["vorhanden"]


def test_existing_basics_are_only_replaced_on_request(started):
    server, folder, _ = started
    call(server, "/api/angaben/uebernehmen", {"bundle": valid_bundle()})
    before = (folder / "cv.yaml").read_text(encoding="utf-8")
    (folder / "cv.yaml").write_text(before + "# von Hand\n", encoding="utf-8")

    status, answer = call(server, "/api/angaben/uebernehmen", {"bundle": valid_bundle()})
    assert status == 409 and answer["vorhanden"] is True and "--force" not in answer["fehler"]
    assert "# von Hand" in (folder / "cv.yaml").read_text(encoding="utf-8")

    assert call(server, "/api/angaben/uebernehmen", {"bundle": valid_bundle(), "ersetzen": True})[0] == 200
    assert "# von Hand" not in (folder / "cv.yaml").read_text(encoding="utf-8")


def test_missing_answers_are_refused_without_documents(started):
    server, folder, _ = started
    bundle = {**valid_bundle(), "data": {}}

    status, _ = call(server, "/api/angaben/uebernehmen", {"bundle": bundle})

    assert status == 400 and not (folder / "cv.yaml").exists()


def test_missing_answers_are_kept_when_documents_are_there(started):
    server, folder, _ = started
    upload(server)
    bundle = {**valid_bundle(), "data": {}}

    status, answer = call(server, "/api/angaben/uebernehmen", {"bundle": bundle})

    assert status == 200 and answer["unvollstaendig"] is True and answer["geschrieben"] == []
    assert not (folder / "cv.yaml").exists()
    assert json.loads((folder / "dokumente" / "einstieg.json").read_text(encoding="utf-8"))["track"] == "job"
    assert [u["name"] for u in call(server, "/api/angaben/stand")[1]["unterlagen"]] == ["lebenslauf.pdf"]


def test_complete_answers_leave_no_outdated_copy_behind(started):
    server, data, _ = started
    upload(server)
    missing = {**valid_bundle(), "data": {}}
    assert call(server, "/api/angaben/uebernehmen", {"bundle": missing, "ersetzen": False})[0] == 200
    assert (data / "dokumente" / "einstieg.json").is_file()

    status, answer = call(server, "/api/angaben/uebernehmen", {"bundle": valid_bundle(), "ersetzen": False})

    assert status == 200 and answer["unvollstaendig"] is False
    assert not (data / "dokumente" / "einstieg.json").exists()
    assert "einstieg.json" not in (data / "dokumente" / "neu.yaml").read_text(encoding="utf-8")


def test_page_cannot_be_framed_by_other_sites(started):
    server, _, _ = started
    with urllib.request.urlopen(f"{server.url}angaben", timeout=10) as response:
        policy = response.headers["Content-Security-Policy"]

    assert "frame-ancestors 'self'" in policy


def test_parallel_uploads_all_reach_the_pending_list(started):
    server, folder, _ = started
    names = [f"zeugnis-{number}.pdf" for number in range(8)]

    def send(name):
        return upload(server, name=name, category="zeugnisse", data=PDF + name.encode())

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(names)) as pool:
        answers = list(pool.map(send, names))

    assert all(status == 200 for status, _ in answers), answers
    assert sorted(u["name"] for u in call(server, "/api/angaben/stand")[1]["unterlagen"]) == sorted(names)


def test_unknown_kind_of_track_only_changes_the_wording(started):
    server, _, _ = started

    status, answer = call(server, "/api/angaben/unterlage",
                          {"track": ["job"], "category": "gibt-es-nicht", "name": "a.pdf", "data": "JVBERg=="})

    assert status == 400 and answer["fehler"]


def test_broken_state_file_does_not_block_the_page(started):
    server, folder, _ = started
    (folder / "dokumente").mkdir(exist_ok=True)
    (folder / "dokumente" / "angaben-stand.json").write_text("{kaputt", encoding="utf-8")

    status, answer = call(server, "/api/angaben/stand")

    assert status == 200 and answer["stand"] is None
