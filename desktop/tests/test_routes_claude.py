"""The section „Mit dem eigenen Claude-Abo arbeiten“ (MIN-377)."""
import json
import pathlib

import pytest

import app
import claude_setup
import routes_claude
import settings

REPO = pathlib.Path(__file__).resolve().parents[2]


@pytest.fixture
def running(tmp_path):
    data = tmp_path / "daten"
    data.mkdir()
    paths = settings.Paths(tmp_path / "app")
    setup = routes_claude.ClaudeRoutes(paths=paths, config=tmp_path / "Claude" / "claude_desktop_config.json",
                                       command=("/app/Bewerbungsbegleiter", "--mcp"), skills=REPO / "skills")
    get_routes, post_routes = routes_claude.make_routes(setup)
    server = app.erstelle_server(data, extra_routes=(get_routes, post_routes))
    import threading
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server, setup
    server.shutdown()
    server.server_close()


def request(server, path, body=None):
    import urllib.error
    import urllib.request
    if body is None:
        call = urllib.request.Request(f"{server.url.rstrip('/')}{path}{'&' if '?' in path else '?'}t={server.token}")
    else:
        call = urllib.request.Request(f"{server.url.rstrip('/')}{path}", method="POST", data=json.dumps(body).encode(),
                                      headers={"Content-Type": "application/json", "X-Token": server.token})
    try:
        with urllib.request.urlopen(call) as answer:  # noqa: S310 (local)
            return answer.status, answer.read(), answer.headers
    except urllib.error.HTTPError as error:
        return error.code, error.read(), error.headers


def state(server):
    return json.loads(request(server, "/api/claude/stand")[1])


def test_starts_switched_off_and_names_what_to_enter(running):
    found = state(running[0])
    assert found["zugang"] is False and found["desktop_eingetragen"] is False
    assert found["skills"] == ["einstieg", "jobsuche", "bewerbung"]
    assert "claude mcp add" in found["code_befehl"] and "mcpServers" in found["desktop_text"]


def test_switching_on_needs_the_confirmation(running):
    server, setup = running
    status, content, _ = request(server, "/api/claude/zugang", {"an": True})
    assert status == 400 and "bestätigen" in json.loads(content)["fehler"]
    assert settings.claude_access(setup.paths) is False
    assert request(server, "/api/claude/zugang", {"an": True, "bestaetigt": True})[0] == 200
    assert settings.claude_access(setup.paths) is True


def test_switching_off_needs_no_confirmation(running):
    server, setup = running
    settings.set_claude_access(setup.paths, True)
    assert request(server, "/api/claude/zugang", {"an": False})[0] == 200
    assert settings.claude_access(setup.paths) is False


def test_claude_desktop_only_gets_the_entry_after_switching_on(running):
    server, setup = running
    assert request(server, "/api/claude/desktop", {"eintragen": True})[0] == 400
    assert not setup.config.exists()
    settings.set_claude_access(setup.paths, True)
    assert request(server, "/api/claude/desktop", {"eintragen": True})[0] == 200
    assert state(server)["desktop_eingetragen"] is True
    assert request(server, "/api/claude/desktop", {"eintragen": False})[0] == 200
    assert state(server)["desktop_eingetragen"] is False


def test_a_skill_comes_as_a_download(running):
    status, content, headers = request(running[0], "/api/claude/skill?name=jobsuche")
    assert status == 200 and content[:2] == b"PK" and "jobsuche.zip" in headers["Content-Disposition"]
    assert request(running[0], "/api/claude/skill?name=andere")[0] == 400


def test_the_state_says_when_the_entry_points_to_an_old_place(running):
    server, setup = running
    assert state(server)["desktop_veraltet"] is False
    claude_setup.enter_in_desktop(setup.config, ["/alt/Bewerbungsbegleiter", "--mcp"])
    assert state(server)["desktop_veraltet"] is True
