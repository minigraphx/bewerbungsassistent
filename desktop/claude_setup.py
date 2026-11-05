"""Claude with the person's own subscription (MIN-377): the entry in Claude Desktop and the skills to upload.

Only ever changes our own entry in the configuration of Claude Desktop, keeps the old file next to it, and leaves a file
it cannot read alone. Each skill is a ZIP with its folder at the top, as Claude expects it for an upload.
"""
import io
import json
import os
import pathlib
import zipfile

SERVER_NAME = "bewerbungsassistent"
CONFIG_NAME = "claude_desktop_config.json"
BACKUP_SUFFIX = ".vor-bewerbungsassistent"
SERVERS = "mcpServers"
SKILLS = ("einstieg", "jobsuche", "bewerbung")
FIXED_TIME = (1980, 1, 1, 0, 0, 0)  # the same files give the same bytes
UNREADABLE = "Die Einstellungen von Claude Desktop lassen sich nicht lesen. Bitte den Eintrag selbst vornehmen, wie darunter beschrieben."
UNKNOWN_SKILL = "Diesen Skill gibt es nicht."


def desktop_config(platform: str, environ: dict, home: pathlib.Path) -> pathlib.Path:
    if platform == "win32":
        return pathlib.Path(environ.get("APPDATA") or home / "AppData" / "Roaming") / "Claude" / CONFIG_NAME
    if platform == "darwin":
        return home / "Library" / "Application Support" / "Claude" / CONFIG_NAME
    return home / ".config" / "Claude" / CONFIG_NAME


def server_command(executable: pathlib.Path) -> list[str]:
    return [str(executable), "--mcp"]


def _entry(command: list[str]) -> dict:
    return {"command": command[0], "args": command[1:]}


def config_text(command: list[str]) -> str:
    return json.dumps({SERVERS: {SERVER_NAME: _entry(command)}}, indent=2, ensure_ascii=False)


def code_line(command: list[str]) -> str:
    parts = [f'"{part}"' if " " in part else part for part in command]
    return f"claude mcp add --scope user {SERVER_NAME} -- {' '.join(parts)}"


def _read(path: pathlib.Path) -> dict:
    try:
        content = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    except (OSError, ValueError) as error:
        raise ValueError(UNREADABLE) from error
    if not isinstance(content, dict) or not isinstance(content.get(SERVERS, {}), dict):
        raise ValueError(UNREADABLE)
    return content


def _write(path: pathlib.Path, content: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(content, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(temporary, path)


def is_entered(path: pathlib.Path) -> bool:
    try:
        return SERVER_NAME in _read(path).get(SERVERS, {})
    except ValueError:
        return False


def enter_in_desktop(path: pathlib.Path, command: list[str]) -> None:
    content = _read(path)
    if path.is_file():
        path.with_name(path.name + BACKUP_SUFFIX).write_bytes(path.read_bytes())
    _write(path, {**content, SERVERS: {**content.get(SERVERS, {}), SERVER_NAME: _entry(command)}})


def remove_from_desktop(path: pathlib.Path) -> None:
    content = _read(path)
    servers = content.get(SERVERS, {})
    if SERVER_NAME in servers:
        _write(path, {**content, SERVERS: {name: value for name, value in servers.items() if name != SERVER_NAME}})


def skills_folder(bundle: pathlib.Path) -> pathlib.Path:
    """In the package next to the code, in development in the repo."""
    inside = bundle / "skills"
    return inside if inside.is_dir() else bundle.parent / "skills"


def skill_zip(folder: pathlib.Path, name: str) -> bytes:
    if name not in SKILLS:
        raise ValueError(UNKNOWN_SKILL)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for path in sorted((folder / name).glob("*.md")):
            info = zipfile.ZipInfo(f"{name}/{path.name}", FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())
    return buffer.getvalue()
