"""Page „Meine Angaben“ (MIN-366): the template inside the app; state and documents go to the data folder."""
import base64
import concurrent.futures
import json
import pathlib
import threading
import types
import urllib.error
import urllib.request

import pytest
import yaml

import app
import routes_ai
from ai import consent
import read_documents
import routes_angaben
import routes_setup
import settings

CASES = pathlib.Path(__file__).resolve().parents[2] / "onboarding" / "tests" / "cases.json"
PDF = b"%PDF-1.4 erfunden"


def valid_bundle() -> dict:
    return json.loads(CASES.read_text(encoding="utf-8"))["bases"]["job"]


REAL_CONSENT_CHECK = consent.is_given


@pytest.fixture(autouse=True)
def consent_given(monkeypatch):
    monkeypatch.setattr(consent, "is_given", lambda *args: True)


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
    threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True).start()
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


def open_page(server, path):
    """Like a browser: in through the link with the token, then with the session."""
    browser = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
    return browser.open(f"{server.url}{path}?t={server.token}", timeout=10)


def test_page_is_the_template_with_its_own_policy(started):
    server, _, _ = started
    with open_page(server, "angaben") as response:
        html = response.read().decode("utf-8")
        policies = response.headers.get_all("Content-Security-Policy")

    assert len(policies) == 1 and "connect-src 'self'" in policies[0] and "script-src 'self' 'sha256-" in policies[0]
    assert 'data-app="1"' in html and f'content="{server.token}"' in html and "__TOKEN__" not in html


def test_other_pages_keep_the_strict_policy(started):
    server, _, _ = started
    with open_page(server, "einrichtung") as response:
        assert "script-src 'self'" in response.headers["Content-Security-Policy"]


def test_state_is_kept_in_the_data_folder(started):
    server, folder, _ = started
    derived = {"track": "job", "anrede": "sie", "rav": True, "gewaehlt": False}
    assert call(server, "/api/angaben/stand") == (200, {"stand": None, "unterlagen": [], "vorhanden": [], "wahl": derived,
                                                   "lebenslauf": None, "tags": []})

    state = {"track": "job", "data": {"person": {"name": "Erika Beispiel"}}, "step": 2}
    assert call(server, "/api/angaben/stand", {"stand": state})[0] == 200

    assert call(server, "/api/angaben/stand")[1]["stand"] == state
    assert "dokumente/" in (folder / ".gitignore").read_text(encoding="utf-8")
    assert not list(folder.glob("*.json"))  # not next to the files the person edits


def test_the_page_starts_in_the_track_the_setup_chose(started):
    server, folder, _ = started
    assert call(server, "/api/einrichtung/wahl", {"gesucht": "lehrstelle", "anrede": "du", "rav": False})[0] == 200

    assert call(server, "/api/angaben/stand")[1]["wahl"] == {"track": "apprenticeship", "anrede": "du", "rav": False, "gewaehlt": True}


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

    changed = valid_bundle()
    changed["data"]["person"]["name"] = "Erika Muster"
    assert call(server, "/api/angaben/uebernehmen", {"bundle": changed, "ersetzen": True})[0] == 200
    after = (folder / "cv.yaml").read_text(encoding="utf-8")
    assert "name: Erika Muster" in after and "# von Hand" in after  # merged, not rewritten (G23)


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
    with open_page(server, "angaben") as response:
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


class PrefillMessages:
    def __init__(self, reply):
        self.reply, self.calls = reply, []

    def create(self, **payload):
        self.calls.append(payload)
        usage = types.SimpleNamespace(input_tokens=100, output_tokens=50, cache_creation_input_tokens=0,
                                      cache_read_input_tokens=0)
        block = types.SimpleNamespace(type="text", text=json.dumps(self.reply, ensure_ascii=False))
        return types.SimpleNamespace(content=[block], usage=usage, stop_reason="end_turn", model=payload["model"],
                                     _request_id="req_test")


def prefill_reply() -> dict:
    fields = {"position": "Entwicklerin", "name": "Muster GmbH", "startDate": "2019"}
    return {"entries": [{"section": "work", "source": {"document": 1, "place": "Seite 1"},
                         "fields": [{"field": name, "value": value} for name, value in fields.items()]}],
            "suspicious_lines": []}


def install_client(monkeypatch, reply) -> PrefillMessages:
    messages = PrefillMessages(reply)
    monkeypatch.setattr(routes_ai, "new_client", lambda: types.SimpleNamespace(messages=messages))
    return messages


PREFILL_DATA = {"person": {"name": "Erika Beispiel"}}


def test_prefill_sends_nothing_without_the_consent(started, monkeypatch):
    server, _, _ = started
    monkeypatch.setattr(consent, "is_given", REAL_CONSENT_CHECK)
    messages = install_client(monkeypatch, prefill_reply())
    upload(server, name="cv.txt", data="Erika Beispiel, Entwicklerin bei Muster GmbH seit 2019".encode())

    status, answer = call(server, "/api/angaben/vorbefuellen", {"track": "job", "data": PREFILL_DATA})

    assert status == 400 and answer["fehler"] == consent.MISSING
    assert messages.calls == []


def test_prefill_without_the_consent_reads_no_documents(started, monkeypatch):
    """Large PDFs take seconds to read; the missing consent must be said before that, not after (#156)."""
    server, _, _ = started
    monkeypatch.setattr(consent, "is_given", REAL_CONSENT_CHECK)
    install_client(monkeypatch, prefill_reply())
    read = []
    monkeypatch.setattr(read_documents, "collect_texts", lambda *args: read.append(args))
    upload(server, name="cv.txt", data="Erika Beispiel, Entwicklerin bei Muster GmbH seit 2019".encode())

    status, answer = call(server, "/api/angaben/vorbefuellen", {"track": "job", "data": PREFILL_DATA})

    assert status == 400 and answer["fehler"] == consent.MISSING
    assert read == []


def test_prefill_suggests_without_writing_the_persons_files(started, monkeypatch):
    server, folder, _ = started
    messages = install_client(monkeypatch, prefill_reply())
    upload(server, name="cv.txt", data="Erika Beispiel, Entwicklerin bei Muster GmbH seit 2019".encode())

    status, answer = call(server, "/api/angaben/vorbefuellen", {"track": "job", "data": PREFILL_DATA})

    assert status == 200 and answer["suggestions"]["work"][0]["source"] == {"file": "cv.txt", "place": "Seite 1"}
    assert "Erika" not in json.dumps(messages.calls[0]["messages"], ensure_ascii=False)
    assert not (folder / "cv.yaml").exists()
    assert [d["name"] for d in call(server, "/api/angaben/stand")[1]["unterlagen"]] == ["cv.txt"]


def test_prefill_needs_the_name_first_and_sends_nothing_without_it(started, monkeypatch):
    server, _, _ = started
    messages = install_client(monkeypatch, prefill_reply())
    upload(server, name="cv.txt", data=b"Text")

    status, answer = call(server, "/api/angaben/vorbefuellen", {"track": "job", "data": {}})

    assert status == 400 and "Person und Kontakt" in answer["fehler"] and messages.calls == []


def test_prefill_refuses_a_second_run_at_the_same_time(started, monkeypatch):
    server, _, _ = started
    entered, leave = threading.Event(), threading.Event()
    messages = PrefillMessages(prefill_reply())
    original = messages.create

    def slow(**payload):
        entered.set()
        leave.wait(10)
        return original(**payload)

    monkeypatch.setattr(messages, "create", slow)
    monkeypatch.setattr(routes_ai, "new_client", lambda: types.SimpleNamespace(messages=messages))
    upload(server, name="cv.txt", data=b"Text")
    body = {"track": "job", "data": PREFILL_DATA}
    with concurrent.futures.ThreadPoolExecutor(1) as pool:
        first = pool.submit(call, server, "/api/angaben/vorbefuellen", body)
        assert entered.wait(10)
        status, answer = call(server, "/api/angaben/vorbefuellen", body)
        uploaded = upload(server, name="noch.txt", data=b"Text")  # the AI call does not hold up the page
        leave.set()
        assert first.result()[0] == 200
    assert status == 400 and "schon" in answer["fehler"] and uploaded[0] == 200


def test_after_taking_over_read_documents_are_done_but_stay_as_files(started, monkeypatch):
    server, folder, _ = started
    install_client(monkeypatch, prefill_reply())
    upload(server, name="cv.txt", data=b"Text")
    call(server, "/api/angaben/vorbefuellen", {"track": "job", "data": PREFILL_DATA})
    upload(server, name="neu.txt", category="zeugnisse", data=b"Neu")

    status, _ = call(server, "/api/angaben/uebernehmen", {"bundle": valid_bundle(), "ersetzen": False})

    assert status == 200
    assert [d["name"] for d in call(server, "/api/angaben/stand")[1]["unterlagen"]] == ["neu.txt"]
    assert (folder / "dokumente" / "lebenslauf-bisher" / "cv.txt").is_file()


def test_incomplete_answers_keep_read_documents_listed(started, monkeypatch):
    server, _, _ = started
    install_client(monkeypatch, prefill_reply())
    upload(server, name="cv.txt", data=b"Text")
    call(server, "/api/angaben/vorbefuellen", {"track": "job", "data": PREFILL_DATA})
    bundle = {**valid_bundle(), "data": {"person": {"name": "Erika Beispiel"}}}

    status, answer = call(server, "/api/angaben/uebernehmen", {"bundle": bundle, "ersetzen": False})

    assert status == 200 and answer["unvollstaendig"] is True
    assert [d["name"] for d in call(server, "/api/angaben/stand")[1]["unterlagen"]] == ["cv.txt"]


def test_prefill_with_unknown_form_of_answers_is_refused(started):
    server, _, _ = started
    status, answer = call(server, "/api/angaben/vorbefuellen", {"track": "job", "data": "nein"})
    assert status == 400 and answer["fehler"]


def test_replacing_names_what_stays_in_the_search(started):
    server, folder, _ = started
    call(server, "/api/angaben/uebernehmen", {"bundle": valid_bundle()})
    profile = folder / "suchprofil.md"
    profile.write_text(profile.read_text(encoding="utf-8").replace("## Suchrichtungen\n", "## Suchrichtungen\n1. Empfang\n", 1), encoding="utf-8")

    status, answer = call(server, "/api/angaben/uebernehmen", {"bundle": valid_bundle(), "ersetzen": True})

    assert status == 200 and answer["behalten"] == ["Empfang"]
    assert "Empfang" in profile.read_text(encoding="utf-8")


def test_changes_count_as_not_taken_over_until_the_page_says_otherwise(started):
    server, _, _ = started
    assert call(server, "/api/angaben/offen") == (200, {"offen": False})
    call(server, "/api/angaben/stand", {"stand": {"track": "job", "data": {}, "offen": True}})
    assert call(server, "/api/angaben/offen") == (200, {"offen": True})
    call(server, "/api/angaben/stand", {"stand": {"track": "job", "data": {}, "offen": False}})
    assert call(server, "/api/angaben/offen") == (200, {"offen": False})


def test_a_state_from_before_counts_as_taken_over(started):
    server, _, _ = started
    call(server, "/api/angaben/stand", {"stand": {"track": "job", "data": {}}})
    assert call(server, "/api/angaben/offen") == (200, {"offen": False})


def test_the_overview_reads_the_cv_for_the_form(started):
    server, folder, _ = started
    (folder / "cv.yaml").write_text("basics:\n  name: Erika Beispiel\n  x-image: {zoom: 1.2}\n"
                                    "work:\n  - position: Entwicklerin\n    name: Beispiel AG\n    tags: [daten]\n"
                                    "    highlights: [{text: Ein Punkt, tags: [daten]}]\n", encoding="utf-8")

    cv = call(server, "/api/angaben/stand")[1]["lebenslauf"]

    assert cv["person"] == {"name": "Erika Beispiel"}
    assert cv["work"] == [{"position": "Entwicklerin", "name": "Beispiel AG", "tags": ["daten"],
                           "highlights": [{"text": "Ein Punkt", "tags": ["daten"]}]}]


def test_the_overview_suggests_the_tags_of_the_data_folder(started):
    server, folder, _ = started
    (folder / "cv.yaml").write_text("work:\n  - position: Entwicklerin\n    tags: [web]\n", encoding="utf-8")
    (folder / "varianten.yaml").write_text("- id: daten\n  quelle: jobs/daten.yaml\n  tags: [fullstack]\n",
                                           encoding="utf-8")
    (folder / "jobs").mkdir()
    (folder / "jobs" / "daten.yaml").write_text("tags: [daten, web]\n", encoding="utf-8")

    assert call(server, "/api/angaben/stand")[1]["tags"] == ["daten", "fullstack", "web"]


def test_the_overview_suggests_no_tags_without_any(started):
    server, _, _ = started

    assert call(server, "/api/angaben/stand")[1]["tags"] == []


def test_replacing_merges_into_the_cv_and_keeps_what_the_form_cannot_show(started):
    server, folder, _ = started
    cv = folder / "cv.yaml"
    cv.write_text("basics:\n  name: Alt Beispiel\n  x-image: {zoom: 1.2}\n  url: https://beispiel.example\n"
                  "work:\n  - position: Software-Entwicklerin\n    name: Beispiel AG\n    tags: [daten]\n"
                  "    highlights: [{text: Plattform für Kundendaten, tags: [daten]}]\n"
                  "projects:\n  - name: Beispielprojekt\n    url: https://beispiel.example/projekt\n"
                  "references:\n  - name: Beispiel Referenz\n", encoding="utf-8")
    bundle = valid_bundle()
    bundle["data"]["projects"] = [{"name": "Beispielprojekt"}]

    status, answer = call(server, "/api/angaben/uebernehmen", {"bundle": bundle, "ersetzen": True})

    merged = yaml.safe_load(cv.read_text(encoding="utf-8"))
    assert status == 200 and answer["unveraendert"] == [] and answer["hinweis"] == ""
    assert "cv.yaml" in answer["geschrieben"] and merged["basics"]["name"] == "Erika Beispiel"
    assert merged["basics"]["x-image"] == {"zoom": 1.2} and merged["work"][0]["tags"] == ["daten"]
    assert merged["work"][0]["highlights"][0] == {"text": "Plattform für Kundendaten", "tags": ["daten"]}
    assert merged["projects"] == [{"name": "Beispielprojekt", "url": "https://beispiel.example/projekt"}]
    assert merged["references"] == [{"name": "Beispiel Referenz"}]


def test_replacing_keeps_a_cv_that_cannot_be_read_and_says_so(started):
    server, folder, _ = started
    cv = folder / "cv.yaml"
    cv.write_text("basics: [nicht: lesbar\n", encoding="utf-8")
    before = cv.read_bytes()

    status, answer = call(server, "/api/angaben/uebernehmen", {"bundle": valid_bundle(), "ersetzen": True})

    assert status == 200 and cv.read_bytes() == before
    assert answer["unveraendert"] == ["cv.yaml"]
    assert "cv.yaml" not in answer["geschrieben"] and "suchprofil.md" in answer["geschrieben"]
    assert "Inhalte" in answer["hinweis"] and "ß" not in answer["hinweis"]
