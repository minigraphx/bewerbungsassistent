"""The page Firmen stays with the person (G35, #188): neither the extension nor Claude reach its routes."""
import inspect

import mcp_tools
import native_host


def test_the_extension_reaches_no_company_route():
    assert not [route for route in native_host.ALLOWED if "/api/firmen" in route[1]]


def test_claude_has_no_tool_for_companies():
    assert "/api/firmen" not in inspect.getsource(mcp_tools)
