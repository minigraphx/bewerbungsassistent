"""The browser the app opens in (G99, #369): default browser, Chrome or Edge, with a fallback that always opens a window.

No test starts a real browser: launching and the default browser are stand-ins that record what they were given.
"""
import pathlib
import subprocess

import pytest

import app_browser
import routes_browser
import settings

ADDRESS = "http://127.0.0.1:8765/?t=token"
INVITED = f"{ADDRESS}&ki=einrichten"


class Recorder:
    """Stands in for launching a browser and for the default browser."""

    def __init__(self, exit_code=0, error=None, default_works=True):
        self.exit_code = exit_code
        self.error = error
        self.default_works = default_works
        self.launched = []
        self.defaults = []

    def launch(self, command):
        self.launched.append(command)
        if self.error:
            raise self.error
        return self.exit_code

    def open_default(self, address):
        self.defaults.append(address)
        return self.default_works


def system(platform, recorder=None, programs=(), apps=(), app_paths=None, home=pathlib.Path("/Users/muster")):
    recorder = recorder or Recorder()
    found_apps = {pathlib.Path(app) for app in apps}
    return app_browser.System(
        platform=platform, home=home,
        which=lambda name: f"/usr/bin/{name}" if name in programs else None,
        exists=lambda path: path in found_apps,
        app_path=lambda exe: (app_paths or {}).get(exe),
        launch=recorder.launch, open_default=recorder.open_default)


@pytest.fixture
def paths(tmp_path):
    return settings.Paths(tmp_path / "app")


# ---------- the command per platform ----------

def test_on_macos_the_app_opens_with_open_dash_a_when_the_app_bundle_is_there():
    mac = system("darwin", apps=["/Applications/Google Chrome.app", "/Users/muster/Applications/Microsoft Edge.app"])

    assert app_browser.command("chrome", INVITED, mac) == ["open", "-a", "Google Chrome", INVITED]
    assert app_browser.command("edge", INVITED, mac) == ["open", "-a", "Microsoft Edge", INVITED]


def test_on_macos_a_browser_without_its_app_bundle_is_not_found():
    assert app_browser.command("chrome", ADDRESS, system("darwin")) is None


def test_on_windows_the_program_from_app_paths_gets_the_address_without_a_shell():
    """No cmd /c start: cmd would cut the address at its "&"."""
    chrome = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    edge = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    windows = system("win32", app_paths={"chrome.exe": chrome, "msedge.exe": edge})

    assert app_browser.command("chrome", INVITED, windows) == [chrome, INVITED]
    assert app_browser.command("edge", INVITED, windows) == [edge, INVITED]
    assert app_browser.command("chrome", ADDRESS, system("win32")) is None


def test_on_linux_chromium_counts_for_chrome_and_the_first_program_found_is_used():
    linux = system("linux", programs=["chromium", "microsoft-edge-stable"])

    assert app_browser.command("chrome", ADDRESS, linux) == ["/usr/bin/chromium", ADDRESS]
    assert app_browser.command("edge", ADDRESS, linux) == ["/usr/bin/microsoft-edge-stable", ADDRESS]
    assert app_browser.command("chrome", ADDRESS, system("linux")) is None


def test_other_systems_find_no_named_browser():
    assert app_browser.command("chrome", ADDRESS, system("freebsd13", programs=["chromium"])) is None


def test_installed_names_what_this_computer_has():
    linux = system("linux", programs=["google-chrome"])

    assert app_browser.installed(linux) == {"standard": True, "chrome": True, "edge": False}


def test_windows_app_paths_are_read_from_the_user_then_the_machine():
    class Registry:
        HKEY_CURRENT_USER, HKEY_LOCAL_MACHINE = "HKCU", "HKLM"
        values = {("HKLM", rf"{app_browser.APP_PATHS}\msedge.exe"): r"C:\Edge\msedge.exe"}

        def QueryValue(self, root, key):
            if (root, key) not in self.values:
                raise FileNotFoundError(key)
            return self.values[(root, key)]

    registry = Registry()
    assert app_browser.windows_app_path("msedge.exe", registry) == r"C:\Edge\msedge.exe"
    assert app_browser.windows_app_path("chrome.exe", registry) is None
    assert app_browser.windows_app_path("chrome.exe", None) is None


# ---------- launching ----------

class FakeProcess:
    def __init__(self, result):
        self.result = result

    def wait(self, timeout):
        if self.result is None:
            raise subprocess.TimeoutExpired("browser", timeout)
        return self.result


def test_a_browser_still_running_after_the_grace_counts_as_started():
    started = []

    def popen(command, **options):
        started.append((command, options))
        return FakeProcess(None)

    assert app_browser.launch(["/usr/bin/chromium", ADDRESS], popen=popen) is None
    assert started[0][0] == ["/usr/bin/chromium", ADDRESS]
    assert started[0][1]["stdin"] is subprocess.DEVNULL


def test_a_browser_that_ends_reports_its_exit_code():
    assert app_browser.launch(["open", "-a", "Google Chrome", ADDRESS], popen=lambda command, **options: FakeProcess(1)) == 1


# ---------- opening the app, with the fallback ----------

def test_the_default_choice_opens_the_default_browser_and_launches_nothing():
    recorder = Recorder()

    assert app_browser.open_app("standard", INVITED, system("linux", recorder, programs=["chromium"])) is None
    assert recorder.defaults == [INVITED] and recorder.launched == []


def test_the_chosen_browser_opens_the_address_with_its_code():
    recorder = Recorder()

    assert app_browser.open_app("chrome", INVITED, system("linux", recorder, programs=["google-chrome"])) is None
    assert recorder.launched == [["/usr/bin/google-chrome", INVITED]] and recorder.defaults == []


def test_a_browser_still_running_is_no_failure():
    recorder = Recorder(exit_code=None)

    assert app_browser.open_app("edge", ADDRESS, system("linux", recorder, programs=["microsoft-edge"])) is None
    assert recorder.defaults == []


@pytest.mark.parametrize("recorder", [Recorder(exit_code=1), Recorder(error=OSError("kaputt")),
                                      Recorder(error=subprocess.SubprocessError("kaputt"))],
                         ids=["non-zero exit", "OSError", "SubprocessError"])
def test_a_failed_launch_falls_back_to_the_default_browser_with_the_notice(recorder):
    mac = system("darwin", recorder, apps=["/Applications/Google Chrome.app"])

    assert app_browser.open_app("chrome", INVITED, mac) == "chrome"
    assert recorder.defaults == [f"{INVITED}&{app_browser.FALLBACK_PARAMETER}=chrome"]


def test_a_chosen_browser_that_is_gone_falls_back_without_trying_it():
    recorder = Recorder()

    assert app_browser.open_app("edge", ADDRESS, system("win32", recorder)) == "edge"
    assert recorder.launched == []
    assert recorder.defaults == [f"{ADDRESS}&browser-fehlt=edge"]


def test_an_unknown_choice_counts_as_the_default_browser():
    recorder = Recorder()

    assert app_browser.open_app("firefox", ADDRESS, system("linux", recorder)) is None
    assert recorder.defaults == [ADDRESS]


def test_an_address_without_a_query_gets_the_notice_as_its_first_parameter():
    assert app_browser.with_notice("http://127.0.0.1:1/", "chrome") == "http://127.0.0.1:1/?browser-fehlt=chrome"


def test_the_entry_link_with_the_notice_works_in_a_browser_that_never_opened_the_app(tmp_path, monkeypatch):
    """The fallback browser has no session yet: the code in the link starts one and the notice parameter stays."""
    import http.client
    import threading
    import urllib.parse

    import app
    monkeypatch.delenv("BEWERBUNGSBEGLEITER_KI_URL", raising=False)
    data = tmp_path / "daten"
    data.mkdir()
    server = app.erstelle_server(data)
    threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True).start()
    try:
        address = urllib.parse.urlsplit(app_browser.with_notice(f"{server.entry_url}&ki=einrichten", "chrome"))
        connection = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=5)
        connection.request("GET", f"{address.path}?{address.query}")
        response = connection.getresponse()

        assert response.status == 303
        assert response.getheader("Location") == "/?ki=einrichten&browser-fehlt=chrome"
        assert response.getheader("Set-Cookie")
        connection.close()
    finally:
        server.shutdown()
        server.server_close()


# ---------- the setting ----------

def test_without_a_choice_the_default_browser_is_used(paths):
    assert settings.app_browser(paths) == "standard"


def test_the_choice_is_kept_with_the_other_settings(paths):
    settings.set_beta_updates(paths, True)
    settings.set_app_browser(paths, "edge")

    assert settings.app_browser(paths) == "edge"
    assert settings.beta_updates(paths) is True


def test_a_broken_choice_in_the_file_counts_as_the_default_browser(paths):
    settings.save(paths, {"browser": "netscape"})

    assert settings.app_browser(paths) == "standard"


def test_a_choice_outside_the_list_is_refused(paths):
    with pytest.raises(ValueError):
        settings.set_app_browser(paths, "netscape")


# ---------- the routes of the settings page ----------

def routes(paths, current):
    get, post = routes_browser.make_routes(routes_browser.BrowserRoutes(paths=paths, system=lambda: current))
    return get["/api/app/browser"], post["/api/app/browser"]


def answer(response):
    import json
    return json.loads(response.inhalt)


def test_the_page_learns_the_choice_and_what_this_computer_has(paths):
    settings.set_app_browser(paths, "chrome")
    show, _ = routes(paths, system("linux", programs=["chromium"]))

    assert answer(show(None, {}, None)) == {
        "gewaehlt": "chrome", "plattform": "linux",
        "browser": [{"wert": "standard", "gefunden": True}, {"wert": "chrome", "gefunden": True},
                    {"wert": "edge", "gefunden": False}]}


def test_a_saved_choice_that_is_gone_stays_chosen_and_says_not_found(paths):
    settings.set_app_browser(paths, "edge")
    show, _ = routes(paths, system("darwin"))

    shown = answer(show(None, {}, None))
    assert shown["gewaehlt"] == "edge" and shown["plattform"] == "macos"
    assert {"wert": "edge", "gefunden": False} in shown["browser"]


def test_saving_a_found_browser_or_the_default_works(paths):
    _, save = routes(paths, system("win32", app_paths={"msedge.exe": r"C:\Edge\msedge.exe"}))

    assert answer(save(None, {}, {"wahl": "edge"}))["gewaehlt"] == "edge"
    assert settings.app_browser(paths) == "edge"
    assert answer(save(None, {}, {"wahl": "standard"}))["gewaehlt"] == "standard"


@pytest.mark.parametrize("body", [{"wahl": "chrome"}, {"wahl": "netscape"}, {}, None, {"wahl": 3}])
def test_saving_a_browser_that_is_not_there_or_unknown_is_refused(paths, body):
    _, save = routes(paths, system("win32"))

    with pytest.raises(ValueError):
        save(None, {}, body)
    assert settings.app_browser(paths) == "standard"


# ---------- start and second start ----------

def test_the_start_opens_the_chosen_browser(paths, monkeypatch):
    import start
    recorder = Recorder()
    monkeypatch.setattr(app_browser, "current_system", lambda: system("linux", recorder, programs=["google-chrome"]))
    settings.set_app_browser(paths, "chrome")

    start.open_app(paths, INVITED)

    assert recorder.launched == [["/usr/bin/google-chrome", INVITED]]


def test_the_second_start_opens_the_running_app_in_the_chosen_browser(paths, tmp_path, monkeypatch):
    import threading

    import app
    import instance
    import start
    monkeypatch.delenv("BEWERBUNGSBEGLEITER_KI_URL", raising=False)
    data = tmp_path / "daten"
    data.mkdir()
    server = app.erstelle_server(data)
    threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True).start()
    try:
        instance.write(paths, server.server_address[1], server.token)
        recorder = Recorder(exit_code=1)
        monkeypatch.setattr(app_browser, "current_system", lambda: system("linux", recorder, programs=["microsoft-edge"]))
        monkeypatch.setattr(start.settings, "app_dir", lambda: paths.app_dir)
        settings.set_app_browser(paths, "edge")

        assert start.main(["bewerbungsbegleiter://einladung?code=ABCD-EFGH"]) == 0

        entry = instance.find(paths).entry_url
        assert recorder.launched == [["/usr/bin/microsoft-edge", f"{entry}&ki=einrichten"]]
        assert recorder.defaults == [f"{entry}&ki=einrichten&browser-fehlt=edge"]
    finally:
        server.shutdown()
        server.server_close()
