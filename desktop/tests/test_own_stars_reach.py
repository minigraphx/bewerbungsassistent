"""Own stars per hit stay with the person (G22, #158): the extension cannot set them, Claude does not see them."""
import mcp_tools
import native_host


def test_the_extension_cannot_set_own_stars():
    assert ("POST", "/api/suche/sterne") not in native_host.ALLOWED


def test_claude_lists_hits_without_own_stars():
    answer = {"treffer": [{"id": "jobs-ch-1", "stelle": "Datenanalyst:in", "eigene_sterne": 4, "bewertung": {"note": 5}}], "art": "stelle"}

    listed = mcp_tools.BY_NAME["list_hits"].run(lambda method, path, body: answer, {})

    assert listed["treffer"] == [{"id": "jobs-ch-1", "stelle": "Datenanalyst:in", "bewertung": {"note": 5}}]
    assert answer["treffer"][0]["eigene_sterne"] == 4  # the answer of the app stays as it was
