"""Updates of the macOS app inside the app (MIN-368): the package, its place, the swap with a way back."""
import hashlib
import http.client
import json
import os
import pathlib
import shutil
import stat
import subprocess
import sys
import time

import pytest

import routes_app
import updates
import updates_macos

ZIP = b"PK" + b"z" * 4000
BASE = updates.DOWNLOAD_PREFIX + "v9.2.0/"
ZIP_NAME = "Bewerbungsassistent-9.2.0-macOS.zip"
needs_shell = pytest.mark.skipif(sys.platform == "win32", reason="the swap is a shell script for macOS")
needs_mac = pytest.mark.skipif(sys.platform != "darwin", reason="ditto and codesign exist on macOS only")


def release(package=ZIP):
    files = {
        updates.LATEST_URL: json.dumps({"tag_name": "v9.2.0", "html_url": "https://github.com/x/releases/v", "assets": [
            {"name": "Bewerbungsassistent-Setup-9.2.0.exe", "browser_download_url": BASE + "Bewerbungsassistent-Setup-9.2.0.exe"},
            {"name": "SHA256SUMS.txt", "browser_download_url": BASE + "SHA256SUMS.txt"},
            {"name": ZIP_NAME, "browser_download_url": BASE + ZIP_NAME},
            {"name": updates.MAC_CHECKSUMS, "browser_download_url": BASE + updates.MAC_CHECKSUMS}]}).encode(),
        BASE + ZIP_NAME: package,
        BASE + updates.MAC_CHECKSUMS: f"{hashlib.sha256(ZIP).hexdigest()}  {ZIP_NAME}\n".encode(),
    }

    def fetch(url, limit):
        if url not in files:
            raise OSError("not found")
        return files[url]
    return fetch


def fake_app(folder: pathlib.Path, name="Bewerbungsassistent.app", mark="alt") -> pathlib.Path:
    app = folder / name
    (app / "Contents" / "MacOS").mkdir(parents=True)
    (app / "Contents" / "MacOS" / "Bewerbungsassistent").write_text(mark)
    return app


class Tools:
    """ditto and codesign without macOS: extracting makes a package, the signature is good unless told otherwise."""

    def __init__(self, signed=True, extracts=True):
        self.signed, self.extracts, self.calls = signed, extracts, []

    def __call__(self, args, **kwargs):
        self.calls.append(args)
        if args[0] == updates_macos.DITTO and self.extracts:
            fake_app(pathlib.Path(args[-1]), mark="neu")
        code = 1 if args[0] == updates_macos.CODESIGN and not self.signed else 0
        return subprocess.CompletedProcess(args, code, "", "kaputt")


def test_the_mac_finds_its_zip_and_its_checksums():
    found = updates.latest(release(), "darwin")

    assert found.installer_url == BASE + ZIP_NAME and found.checksums_url == BASE + updates.MAC_CHECKSUMS


def test_windows_still_finds_the_installer():
    found = updates.latest(release(), "win32")

    assert found.installer_url.endswith(".exe") and found.checksums_url.endswith("/SHA256SUMS.txt")


def test_other_systems_get_no_package():
    assert updates.latest(release(), "linux").installer_url is None


def test_running_app_is_read_from_the_executable():
    inside = "/Applications/Bewerbungsassistent 2.app/Contents/MacOS/Bewerbungsassistent"

    assert updates_macos.running_app(inside) == pathlib.Path("/Applications/Bewerbungsassistent 2.app")
    assert updates_macos.running_app("/usr/local/bin/python3") is None
    assert updates_macos.running_app("python") is None


def test_writable_place_is_fine(tmp_path):
    assert updates_macos.place_problem(fake_app(tmp_path)) is None


def test_translocated_app_must_be_moved_first():
    app = pathlib.Path("/private/var/folders/x/AppTranslocation/ABC/d/Bewerbungsassistent.app")

    assert "Ordner Programme" in updates_macos.place_problem(app)


def test_no_app_cannot_update():
    assert updates_macos.place_problem(None)


@pytest.mark.skipif(sys.platform == "win32" or (hasattr(os, "geteuid") and os.geteuid() == 0),
                    reason="needs a folder without write access")
def test_folder_without_write_access_must_be_moved_first(tmp_path):
    app = fake_app(tmp_path)
    tmp_path.chmod(stat.S_IRUSR | stat.S_IXUSR)
    try:
        assert "Ordner Programme" in updates_macos.place_problem(app)
    finally:
        tmp_path.chmod(stat.S_IRWXU)


def test_prepare_unpacks_next_to_the_app_and_verifies(tmp_path):
    app, tools = fake_app(tmp_path), Tools()

    staging = updates_macos.prepare(updates.latest(release(), "darwin"), app, release(), tools)

    assert staging.parent == tmp_path and (staging / updates_macos.NEW_APP).is_dir()
    assert not list(staging.glob("*.zip")), "the archive is not needed any more"
    assert tools.calls[0][:3] == [updates_macos.DITTO, "-x", "-k"]
    assert tools.calls[1] == [updates_macos.CODESIGN, "--verify", "--deep", "--strict", str(staging / updates_macos.NEW_APP)]


def test_a_wrong_checksum_leaves_nothing_behind(tmp_path):
    app, tools = fake_app(tmp_path), Tools()

    with pytest.raises(updates.UpdateError, match="Prüfsumme"):
        updates_macos.prepare(updates.latest(release(), "darwin"), app, release(b"PK anders"), tools)

    assert tools.calls == [] and not (tmp_path / updates_macos.STAGING).exists()


def test_a_bad_signature_is_refused_and_cleaned_up(tmp_path):
    app = fake_app(tmp_path)

    with pytest.raises(updates.UpdateError, match="Signatur"):
        updates_macos.prepare(updates.latest(release(), "darwin"), app, release(), Tools(signed=False))

    assert not (tmp_path / updates_macos.STAGING).exists()


def test_a_zip_without_the_app_is_refused(tmp_path):
    app = fake_app(tmp_path)

    with pytest.raises(updates.UpdateError, match="unvollständig"):
        updates_macos.prepare(updates.latest(release(), "darwin"), app, release(), Tools(extracts=False))

    assert not (tmp_path / updates_macos.STAGING).exists()


def test_a_missing_tool_is_a_clear_message(tmp_path):
    def missing(args, **kwargs):
        raise FileNotFoundError(args[0])

    with pytest.raises(updates.UpdateError, match="entpacken"):
        updates_macos.prepare(updates.latest(release(), "darwin"), fake_app(tmp_path), release(), missing)


def test_leftovers_of_an_earlier_try_are_replaced(tmp_path):
    app = fake_app(tmp_path)
    old_try = tmp_path / updates_macos.STAGING
    old_try.mkdir()
    (old_try / "rest").write_text("alt")

    staging = updates_macos.prepare(updates.latest(release(), "darwin"), app, release(), Tools())

    assert not (staging / "rest").exists()


def opener(folder: pathlib.Path, confirms=True, works=True) -> pathlib.Path:
    """Stands in for `open`: logs what it starts; the new version confirms its start like the real app."""
    path = folder / "open.sh"
    confirm = f'[ "$(cat "$1/Contents/MacOS/Bewerbungsassistent")" = neu ] && : > "{folder}/.Bewerbungsassistent-update/gestartet"' if confirms else ":"
    path.write_text(f'#!/bin/sh\nprintf "%s\\n" "$(cat "$1/Contents/MacOS/Bewerbungsassistent")" >> "{folder}/gestartet.log"\n'
                    f'{confirm}\nexit {0 if works else 1}\n')
    path.chmod(0o755)
    return path


def swap(tmp_path, pid, command, exit_wait=2, start_wait=1):
    app = fake_app(tmp_path)
    staging = tmp_path / updates_macos.STAGING
    fake_app(staging, updates_macos.NEW_APP, mark="neu")
    note = tmp_path / "fehlgeschlagen.txt"
    updates_macos.start_swap(app, staging, note, "9.2.0", pid=pid, open_command=str(command),
                             exit_wait=exit_wait, start_wait=start_wait)
    return app, staging, note


def wait_until_gone(path: pathlib.Path, seconds=8.0):
    end = time.monotonic() + seconds
    while path.exists() and time.monotonic() < end:
        time.sleep(0.05)
    assert not path.exists(), "the swap did not finish"


def content(app: pathlib.Path) -> str:
    return (app / "Contents" / "MacOS" / "Bewerbungsassistent").read_text()


def gone_process() -> int:
    process = subprocess.Popen([sys.executable, "-c", ""])
    process.wait()
    return process.pid


@needs_shell
def test_swap_starts_the_new_version_and_cleans_up(tmp_path):
    app, staging, note = swap(tmp_path, gone_process(), opener(tmp_path))

    wait_until_gone(staging)

    assert content(app) == "neu" and not note.exists()
    assert (tmp_path / "gestartet.log").read_text() == "neu\n"


@needs_shell
def test_swap_keeps_the_name_of_the_installed_app(tmp_path):
    app = fake_app(tmp_path, "Bewerbungsassistent 2.app")
    staging = tmp_path / updates_macos.STAGING
    fake_app(staging, updates_macos.NEW_APP, mark="neu")

    updates_macos.start_swap(app, staging, tmp_path / "n.txt", "9.2.0", pid=gone_process(),
                             open_command=str(opener(tmp_path)), exit_wait=2, start_wait=1)
    wait_until_gone(staging)

    assert content(app) == "neu"


@needs_shell
def test_swap_goes_back_when_the_new_version_does_not_confirm(tmp_path):
    app, staging, note = swap(tmp_path, gone_process(), opener(tmp_path, confirms=False))

    wait_until_gone(staging)

    assert content(app) == "alt" and note.read_text().strip() == "9.2.0"
    log = tmp_path / "gestartet.log"
    end = time.monotonic() + 3  # the old version starts after the clean-up
    while log.read_text() != "neu\nalt\n" and time.monotonic() < end:
        time.sleep(0.05)
    assert log.read_text() == "neu\nalt\n"


@needs_shell
def test_swap_goes_back_when_the_new_version_cannot_be_opened(tmp_path):
    app, staging, note = swap(tmp_path, gone_process(), opener(tmp_path, confirms=False, works=False))

    wait_until_gone(staging)

    assert content(app) == "alt" and note.read_text().strip() == "9.2.0"


@needs_shell
def test_swap_gives_up_when_the_app_does_not_quit(tmp_path):
    running = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    try:
        app, staging, note = swap(tmp_path, running.pid, opener(tmp_path), exit_wait=1)
        wait_until_gone(staging)
    finally:
        running.kill()
        running.wait()

    assert content(app) == "alt" and not note.exists(), "the new version was never tried, so it did not fail"
    assert not (tmp_path / "gestartet.log").exists(), "the old app is still running"


def test_the_new_version_confirms_its_start(tmp_path):
    app = fake_app(tmp_path)
    staging = tmp_path / updates_macos.STAGING
    staging.mkdir()

    updates_macos.confirm_started(app)

    assert (staging / updates_macos.STARTED).exists()


def test_confirming_without_an_update_writes_nothing(tmp_path):
    updates_macos.confirm_started(fake_app(tmp_path))
    updates_macos.confirm_started(None)

    assert not (tmp_path / updates_macos.STAGING).exists()


def routes(tmp_path, app=None, tools=None, fetch=None):
    stopped, started = [], []
    controls = routes_app.Controls(
        stop=lambda: stopped.append(True), automatic=True, platform="darwin", fetch=fetch or release(), app=app,
        failed_note=tmp_path / "note.txt", run_tool=tools or Tools(),
        start_swap=lambda *args, **kwargs: started.append(args))
    get, post = routes_app.make_routes(controls)
    return get, post, started, controls


def body(answer):
    return json.loads(answer.inhalt)


def test_route_offers_the_update_in_a_good_place(tmp_path):
    get, _, _, _ = routes(tmp_path, app=fake_app(tmp_path))

    update = body(get["/api/app/version"](None, {}, None))["update"]

    assert update["automatisch"] is True and update["hinweis"] == ""


def test_route_names_the_problem_of_the_place(tmp_path):
    app = pathlib.Path("/private/var/folders/x/AppTranslocation/ABC/d/Bewerbungsassistent.app")
    get, post, started, _ = routes(tmp_path, app=app)

    update = body(get["/api/app/version"](None, {}, None))["update"]

    assert update["automatisch"] is False and "Ordner Programme" in update["hinweis"]
    with pytest.raises(ValueError, match="Ordner Programme"):
        post["/api/app/aktualisieren"](None, {}, {})
    assert started == []


def test_route_does_not_offer_a_version_that_failed_again(tmp_path):
    get, _, _, controls = routes(tmp_path, app=fake_app(tmp_path))
    controls.failed_note.write_text("9.2.0\n")

    update = body(get["/api/app/version"](None, {}, None))["update"]

    assert update["automatisch"] is False and "liess sich nicht starten" in update["hinweis"]


def test_route_offers_a_newer_version_after_a_failed_one(tmp_path):
    get, _, _, controls = routes(tmp_path, app=fake_app(tmp_path))
    controls.failed_note.write_text("0.1.9\n")

    assert body(get["/api/app/version"](None, {}, None))["update"]["automatisch"] is True


def test_route_prepares_swaps_and_quits(tmp_path):
    app = fake_app(tmp_path)
    _, post, started, controls = routes(tmp_path, app=app)
    stopping = []
    controls.stop_soon = lambda: stopping.append(True)

    assert body(post["/api/app/aktualisieren"](None, {}, {}))["version"] == "9.2.0"

    assert started[0][0] == app and started[0][1] == tmp_path / updates_macos.STAGING and stopping == [True]


def test_route_reports_a_failed_preparation_and_can_try_again(tmp_path):
    app = fake_app(tmp_path)
    _, post, started, controls = routes(tmp_path, app=app, tools=Tools(signed=False))

    with pytest.raises(ValueError, match="Signatur"):
        post["/api/app/aktualisieren"](None, {}, {})

    controls.run_tool = Tools()
    controls.stop_soon = lambda: None
    assert body(post["/api/app/aktualisieren"](None, {}, {}))["ok"] and started


def test_route_refuses_a_second_update_at_the_same_time(tmp_path):
    _, post, _, controls = routes(tmp_path, app=fake_app(tmp_path))
    controls.installing.acquire()

    with pytest.raises(ValueError, match="läuft schon"):
        post["/api/app/aktualisieren"](None, {}, {})


@needs_mac
def test_real_tools_accept_an_ad_hoc_signed_package(tmp_path):
    """The real ditto and codesign, on a package signed like the app itself."""
    build = tmp_path / "build"
    package = fake_app(build)
    executable = package / "Contents" / "MacOS" / "Bewerbungsassistent"
    shutil.copy("/bin/ls", executable)
    subprocess.run(["codesign", "--force", "--deep", "--sign", "-", str(package)], check=True, capture_output=True)
    subprocess.run(["ditto", "-c", "-k", "--keepParent", str(package), str(tmp_path / ZIP_NAME)], check=True)
    archive = (tmp_path / ZIP_NAME).read_bytes()
    base = updates.DOWNLOAD_PREFIX + "v9.2.0/"
    update = updates.Update("9.2.0", "https://x", base + ZIP_NAME, base + updates.MAC_CHECKSUMS)
    files = {base + ZIP_NAME: archive,
             base + updates.MAC_CHECKSUMS: f"{hashlib.sha256(archive).hexdigest()}  {ZIP_NAME}\n".encode()}
    installed = tmp_path / "Programme"
    installed.mkdir()

    staging = updates_macos.prepare(update, fake_app(installed), lambda url, limit: files[url])

    assert (staging / updates_macos.NEW_APP / "Contents" / "MacOS" / "Bewerbungsassistent").is_file()


def failing_mv(folder: pathlib.Path, source_part: str) -> str:
    """A `mv` that refuses the source named, so the script's way back can be tried; returns a PATH with it first."""
    bin_dir = folder / "fake-bin"
    bin_dir.mkdir()
    path = bin_dir / "mv"
    path.write_text(f'#!/bin/sh\ncase "$1" in *{source_part}*) exit 1;; esac\nexec /bin/mv "$@"\n')
    path.chmod(0o755)
    return f"{bin_dir}{os.pathsep}{os.environ['PATH']}"


def wait_for(path: pathlib.Path, seconds=8.0):
    end = time.monotonic() + seconds
    while not path.exists() and time.monotonic() < end:
        time.sleep(0.05)
    assert path.exists(), f"{path.name} did not appear"
    time.sleep(0.2)  # the script finishes its last steps


@needs_shell
def test_the_old_version_is_kept_when_it_cannot_be_put_back(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", failing_mv(tmp_path, "Bewerbungsassistent-alt.app"))

    _, staging, note = swap(tmp_path, gone_process(), opener(tmp_path, confirms=False))
    wait_for(note)

    assert (staging / "Bewerbungsassistent-alt.app" / "Contents" / "MacOS" / "Bewerbungsassistent").read_text() == "alt"


@needs_shell
def test_the_old_version_is_kept_when_the_new_one_cannot_be_moved_away(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", failing_mv(tmp_path, "Programme-x"))
    programme = tmp_path / "Programme-x"
    programme.mkdir()
    staging = programme / updates_macos.STAGING
    fake_app(staging, updates_macos.NEW_APP, mark="neu")
    app = fake_app(programme)
    # moving the old app aside must work here, so only a move out of the program folder itself is refused later
    (tmp_path / "fake-bin" / "mv").write_text(
        '#!/bin/sh\ncase "$2" in *fehlgeschlagen.app) exit 1;; esac\nexec /bin/mv "$@"\n')
    note = tmp_path / "note.txt"

    updates_macos.start_swap(app, staging, note, "9.2.0", pid=gone_process(), open_command=str(opener(tmp_path, confirms=False)),
                             exit_wait=2, start_wait=1)
    wait_for(note)

    assert (staging / "Bewerbungsassistent-alt.app" / "Contents" / "MacOS" / "Bewerbungsassistent").read_text() == "alt"
    assert not (app / "Bewerbungsassistent-alt.app").exists(), "moving onto a folder would bury the old version in it"


@needs_shell
def test_old_version_comes_back_when_the_new_one_cannot_be_moved_in(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", failing_mv(tmp_path, updates_macos.STAGING + "/" + updates_macos.NEW_APP))

    app, staging, note = swap(tmp_path, gone_process(), opener(tmp_path, confirms=False))
    wait_until_gone(staging)

    assert content(app) == "alt" and note.read_text().strip() == "9.2.0"


def test_a_symlink_instead_of_the_app_is_refused(tmp_path):
    outside = fake_app(tmp_path / "anderswo")

    def links(args, **kwargs):
        if args[0] == updates_macos.DITTO:
            (pathlib.Path(args[-1]) / updates_macos.NEW_APP).symlink_to(outside)
        return subprocess.CompletedProcess(args, 0, "", "")

    with pytest.raises(updates.UpdateError, match="unvollständig"):
        updates_macos.prepare(updates.latest(release(), "darwin"), fake_app(tmp_path), release(), links)


def test_a_dropped_download_is_a_clear_message_and_leaves_nothing(tmp_path):
    good = release()

    def dropped(url, limit):
        if url.endswith(".zip"):
            raise http.client.IncompleteRead(b"")
        return good(url, limit)

    with pytest.raises(updates.UpdateError, match="nicht laden"):
        updates_macos.prepare(updates.latest(good, "darwin"), fake_app(tmp_path), dropped, Tools())

    assert not (tmp_path / updates_macos.STAGING).exists()


def test_an_unexpected_error_cleans_up_and_frees_the_route(tmp_path):
    app = fake_app(tmp_path)

    def broken(args, **kwargs):
        raise RuntimeError("unerwartet")

    _, post, _, controls = routes(tmp_path, app=app, tools=broken)

    with pytest.raises(RuntimeError):
        post["/api/app/aktualisieren"](None, {}, {})

    assert not (tmp_path / updates_macos.STAGING).exists() and not controls.installing.locked()


def test_a_failed_start_of_the_swap_leaves_nothing(tmp_path):
    def cannot_start(*args, **kwargs):
        raise OSError("kein Prozess")

    _, post, _, controls = routes(tmp_path, app=fake_app(tmp_path))
    controls.start_swap = cannot_start

    with pytest.raises(ValueError, match="nicht starten"):
        post["/api/app/aktualisieren"](None, {}, {})

    assert not (tmp_path / updates_macos.STAGING).exists() and not controls.installing.locked()
