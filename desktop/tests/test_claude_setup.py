"""Setting Claude up with the person's own subscription (MIN-377): the configuration of Claude Desktop and the skills."""
import io
import json
import pathlib
import zipfile

import pytest
import yaml

import claude_setup

REPO = pathlib.Path(__file__).resolve().parents[2]
COMMAND = ["/Programme/Bewerbungsassistent", "--mcp"]


@pytest.fixture
def config(tmp_path):
    return tmp_path / "Claude" / "claude_desktop_config.json"


def test_where_claude_desktop_keeps_its_configuration():
    home = pathlib.Path("/home/x")
    assert claude_setup.desktop_config("darwin", {}, home) == home / "Library/Application Support/Claude/claude_desktop_config.json"
    assert claude_setup.desktop_config("win32", {"APPDATA": "C:/Roaming"}, home) == pathlib.Path("C:/Roaming/Claude/claude_desktop_config.json")
    assert claude_setup.desktop_config("linux", {}, home) == home / ".config/Claude/claude_desktop_config.json"


def test_entering_creates_the_file_if_there_is_none(config):
    claude_setup.enter_in_desktop(config, COMMAND)
    assert json.loads(config.read_text(encoding="utf-8")) == {"mcpServers": {"bewerbungsassistent": {"command": COMMAND[0], "args": ["--mcp"]}}}
    assert claude_setup.is_entered(config)


def test_entering_keeps_everything_else_and_saves_the_old_file(config):
    config.parent.mkdir(parents=True)
    old = {"mcpServers": {"anderer": {"command": "x"}}, "preferences": {"a": 1}}
    config.write_text(json.dumps(old), encoding="utf-8")
    claude_setup.enter_in_desktop(config, COMMAND)
    new = json.loads(config.read_text(encoding="utf-8"))
    assert new["mcpServers"]["anderer"] == {"command": "x"} and new["preferences"] == {"a": 1}
    assert json.loads(config.with_name(config.name + claude_setup.BACKUP_SUFFIX).read_text(encoding="utf-8")) == old


@pytest.mark.parametrize("content", ["{kaputt", "[1]", '{"mcpServers": 3}'])
def test_a_file_it_cannot_read_stays_untouched(config, content):
    config.parent.mkdir(parents=True)
    config.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError, match="selbst"):
        claude_setup.enter_in_desktop(config, COMMAND)
    assert config.read_text(encoding="utf-8") == content
    assert not claude_setup.is_entered(config)


def test_removing_takes_only_our_entry(config):
    config.parent.mkdir(parents=True)
    config.write_text(json.dumps({"mcpServers": {"anderer": {"command": "x"}}}), encoding="utf-8")
    claude_setup.enter_in_desktop(config, COMMAND)
    claude_setup.remove_from_desktop(config)
    assert json.loads(config.read_text(encoding="utf-8")) == {"mcpServers": {"anderer": {"command": "x"}}}
    assert not claude_setup.is_entered(config)


def test_removing_without_a_file_writes_nothing(config):
    claude_setup.remove_from_desktop(config)
    assert not config.exists()


def test_claude_starts_the_same_program_as_the_browser_with_a_flag():
    assert claude_setup.server_command(pathlib.Path("/app/Bewerbungsassistent")) == ["/app/Bewerbungsassistent", "--mcp"]


def test_the_line_for_claude_code_is_quoted_for_paths_with_spaces():
    line = claude_setup.code_line(["/Applications/Bewerbungs Assistent.app/x", "--mcp"])
    assert line == 'claude mcp add --scope user bewerbungsassistent -- "/Applications/Bewerbungs Assistent.app/x" --mcp'


def test_the_text_to_enter_by_hand_is_valid_json():
    assert json.loads(claude_setup.config_text(COMMAND))["mcpServers"]["bewerbungsassistent"]["args"] == ["--mcp"]


@pytest.mark.parametrize("name", claude_setup.SKILLS)
def test_each_skill_is_a_zip_as_claude_expects_it(name):
    content = claude_setup.skill_zip(REPO / "skills", name)
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        names = archive.namelist()
        assert f"{name}/SKILL.md" in names and all(n.startswith(f"{name}/") and n.endswith(".md") for n in names)
        head = archive.read(f"{name}/SKILL.md").decode("utf-8").split("---")[1]
    meta = yaml.safe_load(head)
    assert meta["name"] == name and len(meta["description"]) <= 1024


def test_the_same_skill_gives_the_same_bytes():
    assert claude_setup.skill_zip(REPO / "skills", "jobsuche") == claude_setup.skill_zip(REPO / "skills", "jobsuche")


@pytest.mark.parametrize("name", ["../secret", "andere", ""])
def test_only_known_skills(name):
    with pytest.raises(ValueError):
        claude_setup.skill_zip(REPO / "skills", name)


def test_skills_are_found_in_the_package_and_in_the_repo(tmp_path):
    (tmp_path / "skills").mkdir()
    assert claude_setup.skills_folder(tmp_path) == tmp_path / "skills"
    assert claude_setup.skills_folder(REPO / "desktop") == REPO / "skills"


@pytest.mark.parametrize("name", claude_setup.SKILLS)
def test_each_skill_says_how_it_works_with_the_app(name):
    text = (REPO / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
    assert "Mit der App" in text and "bewerbungsassistent" in text


def test_an_entry_with_another_path_is_stale(config):
    claude_setup.enter_in_desktop(config, ["/alt/Bewerbungsassistent", "--mcp"])
    assert claude_setup.is_entered(config) is True and claude_setup.is_stale(config, COMMAND) is True
    claude_setup.enter_in_desktop(config, COMMAND)
    assert claude_setup.is_stale(config, COMMAND) is False


def test_no_entry_is_not_stale(config):
    assert claude_setup.is_stale(config, COMMAND) is False


def test_a_broken_entry_of_ours_is_stale_and_an_unreadable_file_is_not(config):
    config.parent.mkdir(parents=True)
    config.write_text(json.dumps({"mcpServers": {"bewerbungsassistent": "alt"}}), encoding="utf-8")
    assert claude_setup.is_stale(config, COMMAND) is True
    config.write_text("{kein json", encoding="utf-8")
    assert claude_setup.is_stale(config, COMMAND) is False


@pytest.mark.parametrize("content", [b"\xef\xbb\xbf{\"mcpServers\": {\"anderer\": {\"command\": \"x\"}}}", b"", b"  \n"])
def test_a_file_from_notepad_or_an_empty_one_can_be_read(config, content):
    config.parent.mkdir(parents=True)
    config.write_bytes(content)
    claude_setup.enter_in_desktop(config, COMMAND)
    assert claude_setup.is_entered(config) is True
