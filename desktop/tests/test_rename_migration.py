"""The move from the old technical name, up to version 0.2.10 (MIN-395)."""
import json
import pathlib

import claude_setup
import instance
import native_messaging
import rename_migration
import settings
import start


def _old_and_new(tmp_path: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path]:
    old = tmp_path / "Bewerbungsassistent"
    old.mkdir()
    (old / settings.SETTINGS_FILE).write_text('{"datenordner": "/irgendwo"}', encoding="utf-8")
    return old, tmp_path / "Bewerbungsbegleiter"


def _not_running(_folder: pathlib.Path) -> None:
    return None


def test_old_folder_moves_to_the_new_name(tmp_path):
    old, new = _old_and_new(tmp_path)
    assert rename_migration.adopt_app_folder(new, stop_old=_not_running) is True
    assert not old.exists()
    assert json.loads((new / settings.SETTINGS_FILE).read_text(encoding="utf-8")) == {"datenordner": "/irgendwo"}


def test_linux_folder_is_lower_case(tmp_path):
    old = tmp_path / "bewerbungsassistent"
    old.mkdir()
    new = tmp_path / "bewerbungsbegleiter"
    assert rename_migration.adopt_app_folder(new, stop_old=_not_running) is True
    assert new.is_dir() and not old.exists()


def test_new_installation_has_nothing_to_adopt(tmp_path):
    new = tmp_path / "Bewerbungsbegleiter"
    assert rename_migration.adopt_app_folder(new, stop_old=_not_running) is False
    assert not new.exists()


def test_existing_new_folder_is_never_overwritten(tmp_path):
    old, new = _old_and_new(tmp_path)
    new.mkdir()
    (new / settings.SETTINGS_FILE).write_text("{}", encoding="utf-8")
    assert rename_migration.adopt_app_folder(new, stop_old=_not_running) is False
    assert (new / settings.SETTINGS_FILE).read_text(encoding="utf-8") == "{}"
    assert old.is_dir()


def test_old_app_is_stopped_before_the_move(tmp_path):
    old, new = _old_and_new(tmp_path)
    seen = []
    rename_migration.adopt_app_folder(new, stop_old=lambda folder: seen.append((folder, folder.exists())))
    assert seen == [(old, True)]


def test_address_of_the_old_app_does_not_move_along(tmp_path):
    old, new = _old_and_new(tmp_path)
    (old / settings.INSTANCE_FILE).write_text('{"port": 1, "token": "x"}', encoding="utf-8")
    rename_migration.adopt_app_folder(new, stop_old=_not_running)
    assert not (new / settings.INSTANCE_FILE).exists()


def test_locked_folder_is_copied_instead(tmp_path, monkeypatch):
    old, new = _old_and_new(tmp_path)

    def locked(_source, _target):
        raise PermissionError("in use")

    monkeypatch.setattr(rename_migration.os, "rename", locked)
    assert rename_migration.adopt_app_folder(new, stop_old=_not_running) is True
    assert (new / settings.SETTINGS_FILE).is_file() and old.is_dir()


def test_failed_copy_leaves_no_half_folder(tmp_path, monkeypatch):
    _old, new = _old_and_new(tmp_path)

    def locked(_source, _target):
        raise PermissionError("in use")

    def half_copy(_source, target, **_options):
        pathlib.Path(target).mkdir()
        raise OSError("disk full")

    monkeypatch.setattr(rename_migration.os, "rename", locked)
    monkeypatch.setattr(rename_migration.shutil, "copytree", half_copy)
    assert rename_migration.adopt_app_folder(new, stop_old=_not_running) is False
    assert not new.exists()


def test_running_old_app_is_asked_to_quit_and_awaited(tmp_path, monkeypatch):
    running = instance.Running(1, "token")
    answers = [running, running, None]
    asked = []
    monkeypatch.setattr(rename_migration.instance, "find", lambda _paths: answers.pop(0))
    monkeypatch.setattr(rename_migration.instance, "ask_to_quit", asked.append)
    monkeypatch.setattr(rename_migration.time, "sleep", lambda _seconds: None)
    rename_migration.stop_old_app(tmp_path)
    assert asked == [running] and answers == []


def test_old_app_that_keeps_running_does_not_block_the_start(tmp_path, monkeypatch):
    running = instance.Running(1, "token")
    monkeypatch.setattr(rename_migration.instance, "find", lambda _paths: running)
    monkeypatch.setattr(rename_migration.instance, "ask_to_quit", lambda _running: None)
    monkeypatch.setattr(rename_migration.time, "sleep", lambda _seconds: None)
    rename_migration.stop_old_app(tmp_path)  # returns after the wait


def test_no_running_old_app_means_nothing_to_stop(tmp_path, monkeypatch):
    monkeypatch.setattr(rename_migration.instance, "find", lambda _paths: None)
    monkeypatch.setattr(rename_migration.instance, "ask_to_quit", lambda _running: (_ for _ in ()).throw(AssertionError))
    rename_migration.stop_old_app(tmp_path)


def test_start_adopts_folder_and_keychain_before_it_logs(tmp_path, monkeypatch):
    _old, new = _old_and_new(tmp_path)
    adopted = []
    monkeypatch.setattr(start.settings, "app_dir", lambda: new)
    monkeypatch.setattr(rename_migration, "stop_old_app", _not_running)
    monkeypatch.setattr("ai.connection.adopt_old_keychain", lambda: adopted.append(True))
    monkeypatch.setattr(start, "serve", lambda paths, code, open_browser=True: 7)
    assert start.main(["--kein-browser"]) == 7
    assert (new / settings.SETTINGS_FILE).is_file() and adopted == [True]


def test_later_starts_leave_the_keychain_alone(tmp_path, monkeypatch):
    new = tmp_path / "Bewerbungsbegleiter"
    new.mkdir()
    adopted = []
    monkeypatch.setattr(start.settings, "app_dir", lambda: new)
    monkeypatch.setattr("ai.connection.adopt_old_keychain", lambda: adopted.append(True))
    monkeypatch.setattr(start, "serve", lambda paths, code, open_browser=True: 7)
    assert start.main(["--kein-browser"]) == 7
    assert adopted == []


def test_old_host_files_go_on_macos(tmp_path):
    folder = tmp_path / "Library" / "Application Support" / "Google" / "Chrome" / "NativeMessagingHosts"
    folder.mkdir(parents=True)
    (folder / "bewerbungsassistent.json").write_text("{}", encoding="utf-8")
    (folder / "fremd.json").write_text("{}", encoding="utf-8")
    native_messaging.forget_old_host("darwin", tmp_path)
    assert [path.name for path in folder.iterdir()] == ["fremd.json"]


def test_old_host_missing_is_fine(tmp_path):
    (tmp_path / "Library" / "Application Support" / "Google" / "Chrome").mkdir(parents=True)
    native_messaging.forget_old_host("darwin", tmp_path)


def test_old_host_keys_go_on_windows(tmp_path):
    deleted = []
    native_messaging.forget_old_host("win32", tmp_path, delete_registry=deleted.append)
    assert deleted == list(native_messaging.WINDOWS_KEYS)


def test_old_host_that_cannot_be_removed_does_not_stop_the_start(tmp_path):
    def refused(_key):
        raise PermissionError("nein")

    native_messaging.forget_old_host("win32", tmp_path, delete_registry=refused)


def test_old_entry_in_claude_becomes_the_new_one(tmp_path):
    config = tmp_path / claude_setup.CONFIG_NAME
    others = {"fremd": {"command": "x"}}
    config.write_text(json.dumps({"theme": "dark", "mcpServers": {**others, "bewerbungsassistent": {"command": "/alt"}}}), encoding="utf-8")
    assert claude_setup.adopt_old_entry(config, ["/neu", "--mcp"]) is True
    content = json.loads(config.read_text(encoding="utf-8"))
    assert content["theme"] == "dark"
    assert content["mcpServers"] == {**others, claude_setup.SERVER_NAME: {"command": "/neu", "args": ["--mcp"]}}
    assert "/alt" in config.with_name(config.name + claude_setup.BACKUP_SUFFIX).read_text(encoding="utf-8")


def test_no_old_entry_changes_nothing_in_claude(tmp_path):
    config = tmp_path / claude_setup.CONFIG_NAME
    text = json.dumps({"mcpServers": {"fremd": {"command": "x"}}})
    config.write_text(text, encoding="utf-8")
    assert claude_setup.adopt_old_entry(config, ["/neu", "--mcp"]) is False
    assert config.read_text(encoding="utf-8") == text
    assert not config.with_name(config.name + claude_setup.BACKUP_SUFFIX).exists()


def test_no_claude_config_is_fine(tmp_path):
    assert claude_setup.adopt_old_entry(tmp_path / claude_setup.CONFIG_NAME, ["/neu", "--mcp"]) is False


def test_unreadable_claude_config_does_not_stop_the_start(tmp_path, monkeypatch):
    config = tmp_path / claude_setup.CONFIG_NAME
    config.write_text("{kaputt", encoding="utf-8")
    start.adopt_claude_entry(config, ["/neu", "--mcp"])
    assert config.read_text(encoding="utf-8") == "{kaputt"
