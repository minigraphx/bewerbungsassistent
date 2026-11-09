"""The app quits a minute after its last page closed, like the quit button (#193, G36)."""
import json
import threading
import urllib.parse
import urllib.request

import pytest

import app
import presence
import routes_app
import server
import settings
import start
from signed_update import server as update_server

INSTALLER = b"MZ" + b"x" * 5000


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def at(self, seconds: float) -> "Clock":
        self.now = seconds
        return self


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def watch(clock):
    return presence.Presence(clock=clock)


def test_the_app_quits_a_minute_after_the_last_page_said_goodbye(watch, clock):
    watch.page_seen("seite-1")
    clock.at(5)
    watch.page_left("seite-1")

    assert not watch.due(clock.at(5 + presence.GRACE_SECONDS - 1)())
    assert watch.due(clock.at(5 + presence.GRACE_SECONDS)())


def test_a_reload_within_the_minute_keeps_it_running(watch, clock):
    watch.page_seen("seite-1")
    clock.at(5)
    watch.page_left("seite-1")
    clock.at(6)
    watch.page_seen("seite-2")

    for second in range(20, 400, 20):
        clock.at(second)
        watch.page_seen("seite-2")
        assert not watch.due(clock())


def test_a_tab_reopened_within_the_minute_keeps_it_running(watch, clock):
    watch.page_seen("seite-1")
    watch.page_left("seite-1")
    clock.at(50)
    watch.page_seen("seite-3")

    assert not watch.due(clock.at(50 + presence.GRACE_SECONDS + 1)())


def test_a_hidden_tab_whose_timers_run_once_a_minute_keeps_it_running(watch, clock):
    every = 65  # browsers run the timers of a background tab about once a minute, sometimes a little later
    for second in range(0, 1200, every):
        clock.at(second)
        watch.page_seen("seite-1")
        assert not watch.due(clock.at(second + every - 0.1)())


def test_a_page_that_falls_silent_without_goodbye_counts_as_closed(watch, clock):
    watch.page_seen("seite-1")
    silent = presence.PAGE_SILENT_SECONDS

    assert not watch.due(clock.at(silent + presence.GRACE_SECONDS - 1)())
    assert watch.due(clock.at(silent + presence.GRACE_SECONDS)())


def test_without_any_page_the_app_quits_a_minute_after_the_start(watch, clock):
    assert not watch.due(clock.at(presence.GRACE_SECONDS - 1)())
    assert watch.due(clock.at(presence.GRACE_SECONDS)())


def test_it_waits_while_an_ai_task_runs(watch, clock):
    watch.page_left("seite-1")
    with watch.request("/api/ki/entwurf"):
        assert not watch.due(clock.at(600)())
    assert not watch.due(clock.at(600 + presence.GRACE_SECONDS - 1)())
    assert watch.due(clock.at(600 + presence.GRACE_SECONDS)())


def test_it_waits_until_a_search_run_ends(watch, clock):
    with watch.request("/api/suche/plan"):
        pass
    assert not watch.due(clock.at(300)())
    clock.at(400)
    with watch.request("/api/suche/treffer"):
        pass
    assert not watch.due(clock.at(400 + presence.SEARCH_SILENT_SECONDS - 1)())
    finished = 400 + presence.SEARCH_SILENT_SECONDS - 1
    with watch.request("/api/suche/abschluss"):
        pass
    assert not watch.due(clock.at(finished + presence.GRACE_SECONDS - 1)())
    assert watch.due(clock.at(finished + presence.GRACE_SECONDS)())


def test_a_search_run_that_never_ends_stops_holding_the_app(watch, clock):
    with watch.request("/api/suche/plan"):
        pass

    assert watch.due(clock.at(presence.SEARCH_SILENT_SECONDS + 1)())


def test_a_page_keeps_the_app_open_while_others_close(watch, clock):
    watch.page_seen("seite-1")
    watch.page_seen("seite-2")
    clock.at(10)
    watch.page_left("seite-1")
    for second in range(30, 300, 30):
        clock.at(second)
        watch.page_seen("seite-2")
        assert not watch.due(clock())


def quitting_controls(version="9.2.0"):
    stopped, installed = threading.Event(), []
    controls = routes_app.Controls(stop=stopped.set, automatic=True, platform="win32",
                                   fetch=update_server(version, {"win32": INSTALLER}),
                                   run_installer_after_quit=installed.append, background=lambda work: work())
    return controls, stopped, installed


def test_the_watchdog_quits_once_like_the_quit_button_with_the_waiting_update(watch, clock, monkeypatch):
    monkeypatch.setattr(routes_app, "QUIT_DELAY_SECONDS", 0.01)
    controls, stopped, installed = quitting_controls()
    dog = presence.Watchdog(watch, lambda: routes_app.quit_app_now(controls))

    assert dog.check() is False
    clock.at(presence.GRACE_SECONDS)
    assert dog.check() is True

    assert installed and installed[0].name.endswith("9.2.0.exe")
    assert stopped.wait(3)
    assert dog.check() is False


def test_the_watchdog_leaves_an_open_app_alone(watch, clock):
    quits = []
    dog = presence.Watchdog(watch, lambda: quits.append(1))
    for second in range(0, 600, 20):
        clock.at(second)
        watch.page_seen("seite-1")
        dog.check()

    assert quits == []


def test_the_quit_button_still_answers_with_the_update(monkeypatch):
    monkeypatch.setattr(routes_app, "QUIT_DELAY_SECONDS", 0.01)
    controls, stopped, _ = quitting_controls()

    answer = routes_app.make_routes(controls)[1]["/api/app/beenden"](None, {}, {})

    assert json.loads(answer.inhalt) == {"ok": True, "aktualisiert": "9.2.0"}
    assert stopped.wait(3)


def test_the_routes_take_a_heartbeat_and_a_goodbye(watch, clock):
    post = presence.make_routes(watch)[1]

    post["/api/app/da"](None, {}, {"seite": "a1b2-c3"})
    assert not watch.due(clock.at(presence.GRACE_SECONDS + 10)())
    post["/api/app/weg"](None, {}, {"seite": "a1b2-c3"})
    assert not watch.due(clock())
    assert watch.due(clock.at(presence.GRACE_SECONDS * 2 + 10)())


@pytest.mark.parametrize("body", [{}, {"seite": ""}, {"seite": 7}, {"seite": "x" * 65}, {"seite": "<b>"}, []])
def test_the_routes_refuse_a_bad_page_id(watch, body):
    post = presence.make_routes(watch)[1]

    with pytest.raises(ValueError):
        post["/api/app/da"](None, {}, body)


def test_the_server_tells_the_presence_about_each_request(tmp_path):
    seen = []
    watch = presence.Presence()

    def recording(path):
        seen.append(path)
        return watch.request(path)

    server = app.erstelle_server(tmp_path, activity=recording)
    threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True).start()
    try:
        url = f"{server.url}api/bewerbungen?" + urllib.parse.urlencode({"t": server.token})
        with urllib.request.urlopen(url, timeout=10) as response:
            assert response.status == 200
    finally:
        server.shutdown()
        server.server_close()

    assert seen == ["/api/bewerbungen"]


class NoWatchdog:
    def __init__(self, *args, **kwargs):
        pytest.fail("no watchdog outside the app with pages")


def test_the_mcp_mode_and_the_native_host_start_no_watchdog(monkeypatch, tmp_path):
    import mcp_server
    import native_host
    monkeypatch.setattr(settings, "app_dir", lambda: tmp_path)
    monkeypatch.setattr(presence, "Watchdog", NoWatchdog)
    monkeypatch.setattr(mcp_server, "main", lambda paths: 42)
    monkeypatch.setattr(native_host, "main", lambda paths: 43)

    assert start.main(["--mcp"]) == 42
    assert start.main(["chrome-extension://abcdefghijklmnopabcdefghijklmnop/"]) == 43


def test_a_new_start_opens_the_overview_and_watches_the_pages(monkeypatch, tmp_path):
    opened, watchdogs = [], []

    class RecordingWatchdog(presence.Watchdog):
        def start(self):
            watchdogs.append("gestartet")

        def stop(self):
            watchdogs.append("gestoppt")

    def interrupted(self, poll_interval=0.5):
        raise KeyboardInterrupt

    monkeypatch.setattr(presence, "Watchdog", RecordingWatchdog)
    monkeypatch.setattr(start.webbrowser, "open", opened.append)
    monkeypatch.setattr(start, "prepare_extension", lambda paths: None)
    monkeypatch.setattr(start, "adopt_claude_entry", lambda config, command: None)
    monkeypatch.setattr(start, "_apply_build_defaults", lambda defaults: None)
    monkeypatch.setattr(server.Server, "serve_forever", interrupted)

    assert start.serve(settings.Paths(tmp_path / "app"), None) == 0

    assert len(opened) == 1 and urllib.parse.urlsplit(opened[0]).path == "/"
    assert app.SEITEN["/"] == "uebersicht.html"
    assert watchdogs == ["gestartet", "gestoppt"]
