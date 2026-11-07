"""The smoke test of the AppImage starts it as on a fresh desktop (#89)."""
import pathlib

import linux_smoke


def test_the_app_runs_without_the_library_path_of_the_ci(monkeypatch, tmp_path):
    monkeypatch.setenv("LD_LIBRARY_PATH", "/opt/hostedtoolcache/Python/lib")

    env = linux_smoke.environment(pathlib.Path(tmp_path))

    assert "LD_LIBRARY_PATH" not in env


def test_the_app_gets_its_own_home_without_the_runner_folders(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", "/home/runner/.config")
    monkeypatch.setenv("PATH", "/usr/bin")

    env = linux_smoke.environment(pathlib.Path(tmp_path))

    assert env["HOME"] == str(tmp_path) and "XDG_CONFIG_HOME" not in env and env["PATH"] == "/usr/bin"
