"""Does the built package speak MCP? python desktop/mcp_smoke.py <program>; run in the CI on Windows and macOS (MIN-377).

A windowed program gets its pipes differently on each system, so only the package itself can show it.
"""
import json
import pathlib
import subprocess
import sys

TIMEOUT_SECONDS = 60
MESSAGES = ({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "smoke", "version": "1"}}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})


def check(output: str) -> str:
    """What is wrong with the answers, or an empty text."""
    try:
        replies = {reply.get("id"): reply for reply in map(json.loads, output.splitlines())}
    except ValueError as error:
        return f"Keine JSON-Antwort: {error}"
    if set(replies) != {1, 2}:
        return f"Unerwartete Antworten: {sorted(map(str, replies))}"
    if replies[1].get("result", {}).get("serverInfo", {}).get("name") != "bewerbungsassistent":
        return "Der Server meldet sich nicht richtig."
    if not replies[2].get("result", {}).get("tools"):
        return "Keine Werkzeuge."
    return ""


def main(argv: list[str]) -> int:
    source = "".join(json.dumps(message) + "\n" for message in MESSAGES)
    done = subprocess.run([str(pathlib.Path(argv[1])), "--mcp"], input=source, capture_output=True, text=True, encoding="utf-8", timeout=TIMEOUT_SECONDS, check=False)  # noqa: S603
    problem = f"Ende mit {done.returncode}: {done.stderr[-500:]}" if done.returncode else check(done.stdout)
    print(problem or "MCP antwortet.")
    return 1 if problem else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
