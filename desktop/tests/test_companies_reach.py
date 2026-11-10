"""The page Firmen stays with the person (G35, #188, #189): the extension only hands in what it read at kununu on the
person's click, and Claude reaches none of the routes."""
import inspect

import mcp_tools
import native_host


def test_the_extension_reaches_only_the_route_for_what_it_read():
    assert sorted(route for route in native_host.ALLOWED if "/api/firmen" in route[1]) == [("POST", "/api/firmen/kununu")]


def test_claude_has_no_tool_for_companies():
    assert "/api/firmen" not in inspect.getsource(mcp_tools)
