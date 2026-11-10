"""Own stars per hit stay with the person (G22, #158): the extension cannot set them, Claude does not see them."""
import json

import pytest

import mcp_tools
import native_host


def test_the_extension_cannot_set_own_stars():
    assert ("POST", "/api/suche/sterne") not in native_host.ALLOWED


def test_claude_lists_hits_without_own_stars():
    answer = {"treffer": [{"id": "jobs-ch-1", "stelle": "Datenanalyst:in", "eigene_sterne": 4, "bewertung": {"note": 5}}], "art": "stelle"}

    listed = mcp_tools.BY_NAME["list_hits"].run(lambda method, path, body: answer, {})

    assert listed["treffer"] == [{"id": "jobs-ch-1", "stelle": "Datenanalyst:in", "bewertung": {"note": 5}}]
    assert answer["treffer"][0]["eigene_sterne"] == 4  # the answer of the app stays as it was


STORED_HIT = {"id": "jobs-ch-1", "stelle": "Datenanalyst:in", "firma": "Beispiel AG", "eigene_sterne": 4, "zustand": "neu"}


@pytest.mark.parametrize("tool, args", [
    ("rate_hit", {"id": "jobs-ch-1", "note": 2, "zusammenfassung": "Passt gut."}),
    ("take_over_hit", {"id": "jobs-ch-1"}),
    ("discard_hit", {"id": "jobs-ch-1"}),
])
def test_every_hit_returned_to_claude_leaves_out_own_stars(tool, args):
    answer = {**STORED_HIT, "bewertung": {"note": 2}}

    returned = mcp_tools.BY_NAME[tool].run(lambda method, path, body: answer, args)

    assert "eigene_sterne" not in returned
    assert returned["id"] == "jobs-ch-1" and returned["zustand"] == "neu"
    assert answer["eigene_sterne"] == 4  # the answer of the app stays as it was


def test_no_tool_that_returns_a_hit_is_left_unfiltered():
    """A new tool on a hit route must filter too; this list names every route whose answer is a stored hit."""
    hit_routes = {"/api/suche/liste": {"treffer": [STORED_HIT]}, "/api/suche/bewertung": STORED_HIT,
                  "/api/suche/uebernehmen": STORED_HIT, "/api/suche/verwerfen": STORED_HIT}
    covered = set()
    for tool in mcp_tools.TOOLS:
        for path in set(tool.paths) & set(hit_routes):
            returned = tool.run(lambda method, p, body, answer=hit_routes[path]: answer,
                                {"id": "jobs-ch-1", "note": 2, "zusammenfassung": "Passt."})
            assert "eigene_sterne" not in json.dumps(returned), tool.name
            covered.add(path)
    assert covered == set(hit_routes)
