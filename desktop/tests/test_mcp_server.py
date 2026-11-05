"""The local MCP server (MIN-377): protocol, access switch, and what Claude can never reach."""
import io
import json

import pytest

import mcp_server
import mcp_tools
import native_host
import settings


class FakeHost:
    """Stands in for the running app: answers from a table and records what was asked."""

    def __init__(self, answers=None):
        self.answers, self.calls = answers or {}, []

    def __call__(self, method, path, data):
        self.calls.append((method, path, data))
        answer = self.answers.get((method, path.split("?")[0]), {"ok": True})
        if isinstance(answer, Exception):
            raise answer
        return answer


@pytest.fixture
def paths(tmp_path):
    found = settings.Paths(tmp_path)
    settings.set_claude_access(found, True)
    return found


def server(paths, answers=None):
    host = FakeHost(answers)
    return mcp_server.McpServer(paths, host), host


def call(mcp, tool, /, **arguments):
    return mcp.answer({"jsonrpc": "2.0", "id": 7, "method": "tools/call", "params": {"name": tool, "arguments": arguments}})["result"]


def payload(result):
    assert not result.get("isError"), result
    return json.loads(result["content"][0]["text"])


# Protocol

def test_initialize_answers_with_the_version_of_the_client_if_known(paths):
    mcp, _ = server(paths)
    reply = mcp.answer({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}})
    assert reply["id"] == 1 and reply["result"]["protocolVersion"] == "2025-06-18"
    assert reply["result"]["capabilities"] == {"tools": {}}
    assert reply["result"]["serverInfo"]["name"] == "bewerbungsassistent"
    assert "Daten" in reply["result"]["instructions"] or "data" in reply["result"]["instructions"]


def test_initialize_offers_its_own_version_for_an_unknown_one(paths):
    mcp, _ = server(paths)
    reply = mcp.answer({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2099-01-01"}})
    assert reply["result"]["protocolVersion"] == mcp_server.PROTOCOLS[0]


def test_notifications_get_no_answer(paths):
    mcp, _ = server(paths)
    assert mcp.answer({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None


def test_ping_and_unknown_method(paths):
    mcp, _ = server(paths)
    assert mcp.answer({"jsonrpc": "2.0", "id": 2, "method": "ping"})["result"] == {}
    assert mcp.answer({"jsonrpc": "2.0", "id": 3, "method": "server/discover"})["error"]["code"] == -32601


def test_serve_speaks_one_json_message_per_line(paths):
    mcp, _ = server(paths)
    incoming = io.BytesIO(b'{"jsonrpc":"2.0","id":1,"method":"ping"}\nkein json\n[1]\n{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
    outgoing = io.BytesIO()
    assert mcp.serve(incoming, outgoing) == 0
    lines = [json.loads(line) for line in outgoing.getvalue().decode("utf-8").splitlines()]
    assert lines[0] == {"jsonrpc": "2.0", "id": 1, "result": {}}
    assert lines[1]["error"]["code"] == -32700 and lines[1]["id"] is None
    assert lines[2]["error"]["code"] == -32600
    assert len(lines) == 3


def test_a_too_long_line_is_refused_and_the_next_one_still_works(paths, monkeypatch):
    monkeypatch.setattr(mcp_server, "MAX_LINE", 50)
    mcp, _ = server(paths)
    incoming = io.BytesIO(b"x" * 500 + b'\n{"jsonrpc":"2.0","id":1,"method":"ping"}\n')
    outgoing = io.BytesIO()
    mcp.serve(incoming, outgoing)
    lines = [json.loads(line) for line in outgoing.getvalue().decode("utf-8").splitlines()]
    assert lines[0]["error"]["code"] == -32600 and lines[1]["result"] == {}


def test_tool_list_has_schemas_and_says_what_only_reads(paths):
    mcp, _ = server(paths)
    tools = {tool["name"]: tool for tool in mcp.answer({"jsonrpc": "2.0", "id": 4, "method": "tools/list"})["result"]["tools"]}
    assert tools["read_file"]["annotations"]["readOnlyHint"] is True
    assert tools["write_file"]["annotations"]["readOnlyHint"] is False
    for tool in tools.values():
        assert tool["inputSchema"]["type"] == "object" and tool["description"]


def test_an_unknown_tool_is_a_protocol_error(paths):
    mcp, _ = server(paths)
    reply = mcp.answer({"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "send_application", "arguments": {}}})
    assert reply["error"]["code"] == -32602


def test_arguments_must_be_an_object(paths):
    mcp, _ = server(paths)
    reply = mcp.answer({"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "read_file", "arguments": [1]}})
    assert reply["error"]["code"] == -32602


def test_a_name_in_another_form_is_a_protocol_error_and_the_server_goes_on(paths):
    mcp, _ = server(paths)
    for name in (["read_file"], {"a": 1}, None, 3):
        reply = mcp.answer({"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": name, "arguments": {}}})
        assert reply["error"]["code"] == -32602


def test_arguments_may_be_null_for_a_tool_without_arguments(paths):
    mcp, host = server(paths, {("GET", "/api/suche/plan"): {"portale": []}})
    reply = mcp.answer({"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "get_search_plan", "arguments": None}})
    assert "error" not in reply and host.calls


def test_json_nested_too_deeply_is_a_parse_error_and_the_server_goes_on(paths):
    mcp, _ = server(paths)
    incoming = io.BytesIO(b"[" * 200_000 + b"\n" + b'{"jsonrpc":"2.0","id":2,"method":"ping"}\n')
    outgoing = io.BytesIO()
    assert mcp.serve(incoming, outgoing) == 0
    replies = [json.loads(line) for line in outgoing.getvalue().splitlines()]
    assert replies[0]["error"]["code"] == -32700 and replies[1]["id"] == 2


def test_a_partial_write_of_the_pipe_still_sends_the_whole_answer(paths):
    class Slow(io.BytesIO):
        def write(self, data):
            return super().write(bytes(data)[:3])
    mcp, _ = server(paths)
    outgoing = Slow()
    mcp.serve(io.BytesIO(b'{"jsonrpc":"2.0","id":2,"method":"ping"}\n'), outgoing)
    assert json.loads(outgoing.getvalue())["id"] == 2


def test_tools_that_replace_something_say_so(paths):
    mcp, _ = server(paths)
    tools = {tool["name"]: tool for tool in mcp.answer({"jsonrpc": "2.0", "id": 4, "method": "tools/list"})["result"]["tools"]}
    for name in ("write_file", "update_application", "save_ad_text", "rate_hit", "build_documents", "discard_hit"):
        assert tools[name]["annotations"]["destructiveHint"] is True, name
    for name in ("read_file", "list_hits", "save_hits", "new_application", "take_over_hit"):
        assert tools[name]["annotations"]["destructiveHint"] is False, name


# Access

def test_without_the_switch_in_the_app_no_tool_runs(tmp_path):
    mcp, host = server(settings.Paths(tmp_path))
    result = call(mcp, "get_search_plan")
    assert result["isError"] is True and "Erweiterte Einstellungen" in result["content"][0]["text"]
    assert host.calls == []


def test_switching_off_counts_at_once(paths):
    mcp, host = server(paths)
    assert not call(mcp, "get_search_plan").get("isError")
    settings.set_claude_access(paths, False)
    assert call(mcp, "get_search_plan")["isError"] is True
    assert len(host.calls) == 1


def test_error_of_the_app_comes_back_as_tool_error_in_its_words(paths):
    mcp, _ = server(paths, {("GET", "/api/suche/plan"): ValueError("Es gibt noch kein Suchprofil.")})
    result = call(mcp, "get_search_plan")
    assert result["isError"] is True and result["content"][0]["text"] == "Es gibt noch kein Suchprofil."


def test_unexpected_error_says_nothing_about_details(paths):
    mcp, _ = server(paths, {("GET", "/api/suche/plan"): RuntimeError("geheimer Pfad /x/y")})
    result = call(mcp, "get_search_plan")
    assert result["isError"] is True and "geheimer" not in result["content"][0]["text"]


# What Claude can reach

SENSITIVE_PREFIXES = ("/api/versand", "/api/rav", "/api/bewerben", "/api/schluessel", "/api/ki", "/api/sicherung", "/api/entwurf",
                      "/api/foto", "/api/claude", "/api/suche/bewerten", "/api/suche/einstellungen")


def test_no_tool_reaches_sending_rav_keys_or_deleting():
    assert not [path for path in mcp_tools.ALL_PATHS if path.startswith(SENSITIVE_PREFIXES) and path != "/api/suche/bewertung"]


def test_the_whole_register_is_no_file_for_claude(paths):
    mcp, host = server(paths, {("GET", "/api/inhalte"): {"dateien": [{"datei": "bewerbungen.yaml"}, {"datei": "cv.yaml"}]}})
    assert [f["datei"] for f in payload(call(mcp, "list_files"))["dateien"]] == ["cv.yaml"]
    assert call(mcp, "read_file", datei="bewerbungen.yaml")["isError"] is True
    assert call(mcp, "write_file", datei="bewerbungen.yaml", text="x")["isError"] is True
    assert [c for c in host.calls if "bewerbungen.yaml" in c[1] or (c[2] or {}).get("datei") == "bewerbungen.yaml"] == []


FULL_ENTRY = {"id": "a-1", "firma": "Muster AG", "stelle": "Koch", "status": "Beworben", "rav_zuweisung": True, "rav_eingetragen_am": "2026-11-01",
              "versand": [{"datei": "x"}], "ausfuellen": "abgeschickt", "zertifikate": ["z.pdf"], "notiz": "gut"}


def test_lists_of_applications_carry_nothing_about_the_rav_or_sending(paths):
    mcp, _ = server(paths, {("GET", "/api/bewerbungen"): {"bewerbungen": [FULL_ENTRY], "status": ["Gemerkt"]}})
    entry = payload(call(mcp, "list_applications"))["bewerbungen"][0]
    assert entry == {"id": "a-1", "firma": "Muster AG", "stelle": "Koch", "status": "Beworben", "notiz": "gut"}


def test_one_application_comes_without_the_job_room_part(paths):
    answer = {"bewerbung": FULL_ENTRY, "jobroom": {"art": "elektronisch"}, "stellentext": "Inserat", "pdfs": {}, "hat_anschreiben": False,
              "varianten": [], "status": []}
    mcp, _ = server(paths, {("GET", "/api/bewerbung"): answer})
    got = payload(call(mcp, "get_application", id="a-1"))
    assert "jobroom" not in got and "rav_zuweisung" not in got["bewerbung"] and got["stellentext"] == "Inserat"


def test_updating_sends_only_the_named_fields_so_it_overwrites_nothing_the_person_changed(paths):
    entry = {**FULL_ENTRY, "status": "Gemerkt", "versand": []}
    mcp, host = server(paths, {("GET", "/api/bewerbung"): {"bewerbung": entry}, ("POST", "/api/bewerbung"): {**entry, "notiz": "neu"}})
    got = payload(call(mcp, "update_application", id="a-1", felder={"notiz": "neu", "status": "Bewerben"}))
    assert host.calls[-1][2] == {"id": "a-1", "notiz": "neu", "status": "Bewerben"}
    assert "rav_zuweisung" not in got


@pytest.mark.parametrize("fields", [{"link": "https://andere.example/"}, {"formular_link": "https://andere.example/"},
                                    {"rav_zuweisung": False}, {"beworben_am": "2026-11-01"}, {"firma": "Neu"}])
def test_updating_refuses_fields_that_are_not_for_claude(paths, fields):
    mcp, host = server(paths, {("GET", "/api/bewerbung"): {"bewerbung": {**FULL_ENTRY, "status": "Gemerkt"}}})
    assert call(mcp, "update_application", id="a-1", felder=fields)["isError"] is True
    assert [c for c in host.calls if c[0] == "POST"] == []


@pytest.mark.parametrize("now, wanted", [("Gemerkt", "Beworben"), ("Gemerkt", "Zusage"), ("Beworben", "Verworfen"), ("Gespräch", "Gemerkt")])
def test_only_the_person_records_what_was_sent(paths, now, wanted):
    mcp, host = server(paths, {("GET", "/api/bewerbung"): {"bewerbung": {**FULL_ENTRY, "status": now}}})
    assert call(mcp, "update_application", id="a-1", felder={"status": wanted})["isError"] is True
    assert [c for c in host.calls if c[0] == "POST"] == []


@pytest.mark.parametrize("status", ["Beworben", "Gespräch", "Absage", "Zusage", "Zurückgezogen"])
@pytest.mark.parametrize("fields", [{"adresse": "Falsch 1"}, {"kontakt": "falsch@example.org"}, {"kontaktperson": "Falsch"}, {"pensum": "10%"}, {"passung": 1}])
def test_what_the_rav_proof_is_filled_from_stays_as_it_was_sent(paths, status, fields):
    mcp, host = server(paths, {("GET", "/api/bewerbung"): {"bewerbung": {**FULL_ENTRY, "status": status}}})
    assert call(mcp, "update_application", id="a-1", felder=fields)["isError"] is True
    assert [c for c in host.calls if c[0] == "POST"] == []


def test_a_sent_application_only_takes_a_note(paths):
    entry = {**FULL_ENTRY, "status": "Beworben"}
    mcp, host = server(paths, {("GET", "/api/bewerbung"): {"bewerbung": entry}, ("POST", "/api/bewerbung"): entry})
    assert not call(mcp, "update_application", id="a-1", felder={"notiz": "Gespräch vorbereiten"}).get("isError")
    assert host.calls[-1][2]["notiz"] == "Gespräch vorbereiten"


def test_an_entry_with_a_recorded_sending_counts_as_sent_whatever_its_status(paths):
    mcp, host = server(paths, {("GET", "/api/bewerbung"): {"bewerbung": {**FULL_ENTRY, "status": "Gemerkt", "versand": [{"datum": "2026-11-01"}]}}})
    assert call(mcp, "update_application", id="a-1", felder={"adresse": "Falsch 1"})["isError"] is True


@pytest.mark.parametrize("wanted", ["Bewerben", "Gemerkt"])
def test_what_the_person_discarded_stays_discarded_for_claude(paths, wanted):
    mcp, host = server(paths, {("GET", "/api/bewerbung"): {"bewerbung": {**FULL_ENTRY, "status": "Verworfen"}}})
    assert call(mcp, "update_application", id="a-1", felder={"status": wanted})["isError"] is True
    assert [c for c in host.calls if c[0] == "POST"] == []


def test_saving_a_job_goes_through_the_route_that_keeps_only_known_links(paths):
    mcp, host = server(paths)
    call(mcp, "save_job", stelle="Koch", firma="Muster AG", link="https://evil.example/", text="Inserat")
    assert host.calls[-1][:2] == ("POST", "/api/seite/von-claude")
    assert "/api/seite/speichern" not in mcp_tools.ALL_PATHS


def test_the_questions_to_the_ai_are_only_for_the_page_of_the_app():
    assert not any(path.startswith("/api/fragen") for path in mcp_tools.ALL_PATHS)
    assert not any(path.startswith("/api/fragen") for _, path in native_host.ALLOWED)


def test_a_rating_asks_for_half_steps_in_the_schema(paths):
    assert mcp_tools.BY_NAME["rate_hit"].properties["note"]["multipleOf"] == 0.5


def test_requests_keep_the_id_in_the_address(paths):
    mcp, host = server(paths)
    call(mcp, "build_documents", id="a b")
    assert host.calls[-1][:2] == ("POST", "/api/unterlagen?id=a+b")
    call(mcp, "write_file", datei="cv.yaml", text="basics: {}")
    assert host.calls[-1] == ("POST", "/api/inhalt?datei=cv.yaml", {"text": "basics: {}"})
    call(mcp, "take_over_hit", id="jobs-1")
    assert host.calls[-1][1] == "/api/suche/uebernehmen?id=jobs-1"


def test_a_missing_required_value_is_a_tool_error(paths):
    mcp, host = server(paths)
    assert call(mcp, "read_file")["isError"] is True
    assert host.calls == []


def test_saving_hits_and_rating_pass_their_values_on(paths):
    mcp, host = server(paths)
    call(mcp, "save_hits", treffer=[{"portal": "jobs.ch"}])
    assert host.calls[-1] == ("POST", "/api/suche/treffer", {"treffer": [{"portal": "jobs.ch"}]})
    call(mcp, "rate_hit", id="x", note=2, zusammenfassung="passt")
    assert host.calls[-1] == ("POST", "/api/suche/bewertung?id=x", {"note": 2, "zusammenfassung": "passt"})


@pytest.mark.parametrize("name", mcp_tools.TEMPLATES)
def test_templates_are_there(paths, name):
    mcp, host = server(paths)
    assert payload(call(mcp, "read_template", name=name))["text"].strip()
    assert host.calls == []


@pytest.mark.parametrize("name", ["../../etc/passwd", "andere"])
def test_only_known_templates(paths, name):
    mcp, _ = server(paths)
    assert call(mcp, "read_template", name=name)["isError"] is True


def test_list_of_hits_leaves_the_settings_out(paths):
    mcp, _ = server(paths, {("GET", "/api/suche/liste"): {"treffer": [{"id": "x"}], "hinweise": [], "art": "stelle", "portale": ["jobs.ch"],
                                                          "einstellungen": {"weitere_seiten": ["https://a.example"]}, "letzte_suche": None}})
    got = payload(call(mcp, "list_hits"))
    assert got["treffer"] == [{"id": "x"}] and "einstellungen" not in got


def test_the_check_of_the_package_sees_good_and_bad_answers(paths):
    import mcp_smoke
    mcp, _ = server(paths)
    good = "\n".join(json.dumps(mcp.answer(message)) for message in mcp_smoke.MESSAGES if "id" in message)
    assert mcp_smoke.check(good) == ""
    assert mcp_smoke.check("kein json")
    assert mcp_smoke.check(json.dumps({"id": 1, "result": {}}))
