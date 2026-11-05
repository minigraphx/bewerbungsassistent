"""Setup of the desktop app (MIN-342): data folder, native dialogs, import of the einstieg file."""
import json
import pathlib
import re
import subprocess
import threading
import urllib.request

import pytest

import app
import dialogs
import routes_setup
import settings
import setup

CASES = pathlib.Path(__file__).resolve().parents[2] / "onboarding" / "tests" / "cases.json"


# Data folder: which folders are allowed


def test_new_folder_is_created_later(tmp_path):
    check = setup.check_folder(str(tmp_path / "Bewerbungsbegleiter"))

    assert check.state == "neu" and not check.path.exists()


def test_empty_folder_is_used(tmp_path):
    (tmp_path / "leer").mkdir()

    assert setup.check_folder(str(tmp_path / "leer")).state == "leer"


def test_existing_data_folder_is_recognised(tmp_path):
    folder = tmp_path / "daten"
    folder.mkdir()
    (folder / "cv.yaml").write_text("basics: {}\n", encoding="utf-8")

    assert setup.check_folder(str(folder)).state == "datenordner"


@pytest.mark.parametrize("raw", ["", "   ", "relativ/ordner"])
def test_path_must_be_complete(raw):
    with pytest.raises(ValueError, match="vollständigen Pfad"):
        setup.check_folder(raw)


def test_folder_with_other_files_is_refused(tmp_path):
    (tmp_path / "Dokumente").mkdir()
    (tmp_path / "Dokumente" / "steuern.pdf").write_bytes(b"%PDF")

    with pytest.raises(ValueError, match="andere Dateien"):
        setup.check_folder(str(tmp_path / "Dokumente"))


def test_file_is_not_a_folder(tmp_path):
    (tmp_path / "datei.txt").write_text("x", encoding="utf-8")

    with pytest.raises(ValueError, match="Datei"):
        setup.check_folder(str(tmp_path / "datei.txt"))


def test_folders_of_the_app_are_refused(tmp_path):
    app_folder = tmp_path / "app"

    with pytest.raises(ValueError, match="App"):
        setup.check_folder(str(app_folder / "daten"), forbidden=[app_folder])


def test_settings_remember_the_chosen_folder(tmp_path):
    paths = settings.Paths(tmp_path / "app")

    assert settings.chosen_data_dir(paths) is None
    settings.remember_data_dir(paths, tmp_path / "daten")
    assert settings.chosen_data_dir(paths) == tmp_path / "daten"


# Native dialogs


class Runner:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.result = subprocess.CompletedProcess([], returncode, stdout, stderr)
        self.calls = []

    def __call__(self, command, **options):
        self.calls.append((command, options))
        return self.result


def test_windows_folder_dialog_returns_the_path(tmp_path):
    run = Runner(stdout="C:\\Users\\Erika\\Bewerbung\r\n")

    chosen = dialogs.choose("ordner", tmp_path, platform="win32", run=run)

    command, options = run.calls[0]
    assert chosen == pathlib.Path("C:\\Users\\Erika\\Bewerbung")
    assert command[0] == "powershell" and "FolderBrowserDialog" in command[-1]
    assert str(tmp_path) not in command[-1] and options["env"][dialogs.START_VARIABLE] == str(tmp_path)


def test_cancelled_dialog_returns_nothing(tmp_path):
    assert dialogs.choose("datei", tmp_path, platform="win32", run=Runner(stdout="")) is None
    assert dialogs.choose("ordner", tmp_path, platform="darwin",
                          run=Runner(1, stderr="execution error: User canceled. (-128)")) is None


def test_mac_file_dialog_uses_osascript(tmp_path):
    run = Runner(stdout="/Users/erika/Downloads/einstieg.zip\n")

    chosen = dialogs.choose("datei", tmp_path, platform="darwin", run=run)

    assert chosen == pathlib.Path("/Users/erika/Downloads/einstieg.zip")
    assert run.calls[0][0][0] == "osascript"


def test_failed_dialog_asks_for_the_path(tmp_path):
    with pytest.raises(ValueError, match="Pfad"):
        dialogs.choose("ordner", tmp_path, platform="darwin", run=Runner(1, stderr="boom"))
    with pytest.raises(ValueError, match="Pfad"):
        dialogs.choose("ordner", tmp_path, platform="linux", run=Runner())


def test_unknown_dialog_kind(tmp_path):
    with pytest.raises(ValueError):
        dialogs.choose("drucker", tmp_path, platform="win32", run=Runner())


# Routes: first start until the data folder is chosen and the einstieg file is imported


@pytest.fixture
def started(tmp_path):
    paths = settings.Paths(tmp_path / "app")
    placeholder = setup.placeholder_dir(paths)
    server = app.erstelle_server(placeholder)
    chosen = []

    def switch(folder):
        server.kontext = app.erstelle_kontext(folder)
        chosen.append(folder)

    state = routes_setup.Setup(paths=paths, switch=switch, suggestion=tmp_path / "Dokumente" / "Bewerbungsbegleiter",
                               choose=lambda kind, start: tmp_path / "gewaehlt")
    get_routes, post_routes = routes_setup.make_routes(state)
    server.routen_get.update(get_routes)
    server.routen_post.update(post_routes)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield server, paths, chosen
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
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def write_bundle(folder: pathlib.Path) -> pathlib.Path:
    bundle = json.loads(CASES.read_text(encoding="utf-8"))["bases"]["job"]
    path = folder / "einstieg.json"
    path.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
    return path


def test_first_start_is_not_set_up(started):
    server, _, _ = started

    status, answer = call(server, "/api/app/einrichtung")

    assert status == 200 and answer["eingerichtet"] is False
    assert answer["vorschlag"].endswith("Bewerbungsbegleiter") and answer["datenordner"] is None


def test_choosing_the_data_folder_switches_without_restart(started, tmp_path):
    server, paths, chosen = started
    folder = tmp_path / "Dokumente" / "Bewerbungsbegleiter"

    status, answer = call(server, "/api/app/datenordner", {"pfad": str(folder)})

    assert status == 200 and answer["eingerichtet"] is True and answer["datenordner"] == str(folder)
    assert folder.is_dir() and chosen == [folder] and server.kontext.daten == folder.resolve()
    assert settings.chosen_data_dir(paths) == folder
    status, register = call(server, "/api/bewerbungen")
    assert status == 200


def test_check_shows_what_happens_with_the_folder(started, tmp_path):
    server, _, _ = started

    status, answer = call(server, "/api/app/ordner-pruefen", {"pfad": str(tmp_path / "neu")})

    assert status == 200 and answer["zustand"] == "neu" and "angelegt" in answer["text"]
    assert not (tmp_path / "neu").exists()


def test_refused_folder_is_a_german_message(started, tmp_path):
    server, paths, _ = started
    (tmp_path / "voll").mkdir()
    (tmp_path / "voll" / "x.txt").write_text("x", encoding="utf-8")

    status, answer = call(server, "/api/app/datenordner", {"pfad": str(tmp_path / "voll")})

    assert status == 400 and "andere Dateien" in answer["fehler"]
    assert settings.chosen_data_dir(paths) is None


def test_dialog_route_returns_the_chosen_path(started, tmp_path):
    server, _, _ = started

    status, answer = call(server, "/api/app/waehlen", {"art": "ordner"})

    assert status == 200 and answer["pfad"] == str(tmp_path / "gewaehlt")


def test_import_needs_a_data_folder_first(started, tmp_path):
    server, _, _ = started

    status, answer = call(server, "/api/app/einstieg", {"pfad": str(write_bundle(tmp_path))})

    assert status == 400 and "Datenordner" in answer["fehler"]


def test_einstieg_file_is_imported_into_the_data_folder(started, tmp_path):
    server, _, _ = started
    folder = tmp_path / "daten"
    call(server, "/api/app/datenordner", {"pfad": str(folder)})

    status, answer = call(server, "/api/app/einstieg", {"pfad": str(write_bundle(tmp_path))})

    assert status == 200 and "cv.yaml" in answer["geschrieben"] and answer["unvollstaendig"] is False
    assert (folder / "cv.yaml").is_file()
    status, again = call(server, "/api/app/einstieg", {"pfad": str(write_bundle(tmp_path))})
    assert status == 409 and again["vorhanden"] and "gibt es schon" in again["fehler"]
    assert "„Vorhandene Dateien ersetzen“" in again["fehler"] and "--force" not in again["fehler"]
    status, replaced = call(server, "/api/app/einstieg", {"pfad": str(write_bundle(tmp_path)), "ersetzen": True})
    assert status == 200 and "cv.yaml" in replaced["geschrieben"]


def test_invalid_einstieg_file_lists_the_problems(started, tmp_path):
    server, _, _ = started
    call(server, "/api/app/datenordner", {"pfad": str(tmp_path / "daten")})
    broken = tmp_path / "kaputt.json"
    broken.write_text("{nicht json", encoding="utf-8")

    status, answer = call(server, "/api/app/einstieg", {"pfad": str(broken)})

    assert status == 400 and "Einstiegsvorlage" in answer["fehler"]


def test_missing_data_folder_leads_back_to_the_setup(started, tmp_path):
    server, paths, _ = started
    settings.remember_data_dir(paths, tmp_path / "usb-stick" / "daten")

    status, answer = call(server, "/api/app/einrichtung")

    assert status == 200 and answer["eingerichtet"] is True and answer["fehlt"] is True


def test_start_uses_the_placeholder_until_a_folder_is_chosen(tmp_path):
    import start
    paths = settings.Paths(tmp_path / "app")

    assert start.start_folder(paths) == setup.placeholder_dir(paths)
    settings.remember_data_dir(paths, tmp_path / "weg")
    assert start.start_folder(paths) == setup.placeholder_dir(paths)
    (tmp_path / "da").mkdir()
    settings.remember_data_dir(paths, tmp_path / "da")
    assert start.start_folder(paths) == tmp_path / "da"


def test_folder_that_comes_back_is_used_again(started, tmp_path):
    server, paths, chosen = started
    folder = tmp_path / "usb-stick" / "daten"
    settings.remember_data_dir(paths, folder)
    folder.mkdir(parents=True)

    status, answer = call(server, "/api/app/einrichtung")

    assert status == 200 and answer["fehlt"] is False and answer["gewechselt"] is True
    assert chosen == [folder] and server.kontext.daten == folder.resolve()


def test_import_never_writes_into_another_folder(started, tmp_path):
    server, paths, _ = started
    folder = tmp_path / "daten"
    folder.mkdir()
    settings.remember_data_dir(paths, folder)

    status, _ = call(server, "/api/app/einstieg", {"pfad": str(write_bundle(tmp_path))})

    assert status == 200 and (folder / "cv.yaml").is_file()
    assert not (setup.placeholder_dir(paths) / "cv.yaml").exists()


def test_windows_leftovers_count_as_empty(tmp_path):
    (tmp_path / "Thumbs.db").write_bytes(b"x")
    (tmp_path / "Desktop.ini").write_text("x", encoding="utf-8")

    assert setup.check_folder(str(tmp_path)).state == "leer"


def test_unreadable_folder_is_a_german_message(tmp_path, monkeypatch):
    def refuse(self):
        raise PermissionError(13, "Permission denied")

    (tmp_path / "gesperrt").mkdir()
    monkeypatch.setattr(pathlib.Path, "iterdir", refuse)

    with pytest.raises(ValueError, match="nicht lesen"):
        setup.check_folder(str(tmp_path / "gesperrt"))


def test_dialog_output_with_bom(tmp_path):
    chosen = dialogs.choose("ordner", tmp_path, platform="win32", run=Runner(stdout="\ufeffC:\\Daten\r\n"))

    assert chosen == pathlib.Path("C:\\Daten")


# Opening the extensions page of the browser from the app (MIN-366)

def recording(returncode=0):
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, returncode, "", "")
    run.calls = calls
    return run


@pytest.mark.parametrize("browser, platform, command", [
    ("chrome", "darwin", ["open", "-a", "Google Chrome", "chrome://extensions"]),
    ("edge", "darwin", ["open", "-a", "Microsoft Edge", "edge://extensions"]),
    ("chrome", "win32", ["cmd", "/c", "start", "", "chrome", "chrome://extensions"]),
    ("edge", "win32", ["cmd", "/c", "start", "", "msedge", "edge://extensions"]),
])
def test_extensions_page_opens_in_the_chosen_browser(browser, platform, command):
    run = recording()

    dialogs.open_extensions_page(browser, platform, run)

    assert run.calls == [command]


def test_missing_browser_is_explained():
    with pytest.raises(ValueError, match="Microsoft Edge"):
        dialogs.open_extensions_page("edge", "darwin", recording(returncode=1))


def test_unknown_browser_is_refused():
    with pytest.raises(ValueError, match="Unbekannter Browser"):
        dialogs.open_extensions_page("firefox", "darwin", recording())


def test_route_opens_the_page_and_shows_the_folder(tmp_path):
    opened, shown = [], []
    state = routes_setup.Setup(paths=settings.Paths(tmp_path / "app"), switch=lambda folder: None,
                               suggestion=tmp_path / "x", extension_dir=tmp_path / "erweiterung",
                               open_page=opened.append, reveal=shown.append)
    _, post_routes = routes_setup.make_routes(state)

    answer = post_routes["/api/app/erweiterungsseite"](None, {}, {"browser": "edge"})

    assert answer.status == 200 and opened == ["edge"] and shown == [tmp_path / "erweiterung"]


def test_the_setup_page_links_to_the_guide_and_its_pictures_exist():
    root = pathlib.Path(__file__).resolve().parents[2]
    page = (root / "bewerbungen" / "seiten" / "einrichtung.html").read_text(encoding="utf-8")
    guide = root / "docs" / "installation.md"
    assert "docs/installation.md" in page
    pictures = re.findall(r"\]\((bilder/[^)]+)\)", guide.read_text(encoding="utf-8"))
    assert pictures and all((guide.parent / picture).exists() for picture in pictures)
