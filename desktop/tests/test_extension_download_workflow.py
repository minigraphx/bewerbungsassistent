"""The release builds the extension download, attaches it and rolls it out next to the app packages (#403, G126).

These tests read the workflows and run their bash steps here: the build against the real extension, the rollout
against a fake curl that plays an invented update server, so no server is ever reached.
"""
import fnmatch
import json
import os
import pathlib
import shutil
import subprocess
import sys

import pytest
import yaml

import extension_download
import version

REPO = pathlib.Path(__file__).resolve().parents[2]
WORKFLOWS = REPO / ".github" / "workflows"
ON_TAG = "startsWith(github.ref, 'refs/tags/v')"
UPDATE_URL = "https://updates.example.ch/app"
FTP_FOLDER = "app"
ZIP_NAME = "Bewerbungsbegleiter-Erweiterung-9.2.0.zip"
PACKAGES = ["Bewerbungsbegleiter-Setup-9.2.0.exe", "Bewerbungsbegleiter-9.2.0-macOS.zip",
            "Bewerbungsbegleiter-9.2.0-x86_64.AppImage", ZIP_NAME]


def load(name: str) -> dict:
    return yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))


def step_named(steps: list[dict], text: str) -> dict:
    found = [step for step in steps if text in step.get("name", "") or text in step.get("uses", "")]
    assert len(found) == 1, f"expected one step with {text!r}, found {len(found)}"
    return found[0]


def bash() -> str:
    found = shutil.which("bash")
    if not found:
        pytest.skip("needs bash, as on the runner")
    return found


def run_script(script: str, cwd: pathlib.Path, env: dict[str, str], bin_dir: pathlib.Path | None = None):
    """Runs a step's script as GitHub does with `shell: bash`."""
    path = os.pathsep.join(str(part) for part in (bin_dir, pathlib.Path(sys.executable).parent) if part)
    full_env = {"PATH": f"{path}{os.pathsep}{os.environ['PATH']}", **env}
    return subprocess.run([bash(), "--noprofile", "--norc", "-eo", "pipefail", "-c", script], env=full_env, cwd=cwd,
                          capture_output=True, text=True)


# --- app.yml: build and attach to the release draft ----------------------------------------------------------------

@pytest.fixture(scope="module")
def app_job():
    return load("app.yml")["jobs"]["erweiterung"]


def test_the_app_workflow_builds_the_download_in_its_own_job(app_job):
    build = step_named(app_job["steps"], "ZIP bauen")

    assert "python desktop/extension_download.py dist-erweiterung" in build["run"]
    assert "needs" not in app_job and "secrets." not in yaml.safe_dump(app_job)
    artifact = step_named(app_job["steps"], "upload-artifact")
    assert artifact["with"]["path"] == "dist-erweiterung/"


def test_on_a_tag_the_zip_and_its_checksum_file_go_into_the_release_draft(app_job):
    release = step_named(app_job["steps"], "Release-Entwurf")

    assert release["if"] == ON_TAG
    assert 'gh release upload "v$VERSION" dist-erweiterung/* --clobber' in release["run"]
    assert "gh release create" in release["run"] and "--draft" in release["run"]


def build_step_in(tmp_path: pathlib.Path, app_job: dict, ref: str):
    work = tmp_path / "work"
    work.mkdir()
    (work / "desktop").symlink_to(REPO / "desktop")
    github_env = tmp_path / "env.txt"
    done = run_script(step_named(app_job["steps"], "ZIP bauen")["run"], work,
                      {"GITHUB_REF": ref, "GITHUB_ENV": str(github_env)})
    return done, work / "dist-erweiterung", github_env


def test_the_build_step_writes_the_zip_with_key_and_its_checksum_file(app_job, tmp_path):
    done, out, github_env = build_step_in(tmp_path, app_job, f"refs/tags/v{version.VERSION}")

    assert done.returncode == 0, done.stderr
    package = out / extension_download.NAME.format(version.VERSION)
    extension_download.check_package(package, version.VERSION)
    assert package.name in (out / extension_download.SUMS).read_text(encoding="ascii")
    assert f"VERSION={version.VERSION}" in github_env.read_text(encoding="utf-8")


def test_the_build_step_refuses_a_tag_of_another_version(app_job, tmp_path):
    done, out, _ = build_step_in(tmp_path, app_job, "refs/tags/v0.0.1")

    assert done.returncode != 0 and "::error::" in done.stdout + done.stderr
    assert not out.exists()


# --- update-ausrollen.yml: upload and the served-file check --------------------------------------------------------

FAKE_CURL = """#!{python}
import pathlib, shutil, sys
args = sys.argv[1:]
with open({log!r}, "a", encoding="utf-8") as log:
    log.write(" ".join(args) + "\\n")
served = pathlib.Path({served!r})
if "-T" in args:
    source = pathlib.Path(args[args.index("-T") + 1])
    url = next(arg for arg in args if arg.startswith("ftp://"))
    path = url.split("/", 3)[3].removeprefix({folder!r} + "/")
    path = path + source.name if path.endswith("/") else path.removesuffix(".part")
    (served / path).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(source, served / path)
else:
    url = next(arg for arg in args if arg.startswith("https://"))
    found = served / url.removeprefix({base!r} + "/")
    if not found.is_file():
        sys.exit(22)
    if "-o" in args:
        shutil.copy(found, args[args.index("-o") + 1])
    else:
        sys.stdout.buffer.write(found.read_bytes())
"""


@pytest.fixture(scope="module")
def rollout():
    return load("update-ausrollen.yml")["jobs"]["ausrollen"]


@pytest.fixture
def server(tmp_path):
    """A work folder with the release files, and a fake curl that stores uploads and serves them back."""
    bin_dir, served, work = tmp_path / "bin", tmp_path / "served", tmp_path / "work"
    for folder in (bin_dir, served, work / "pakete"):
        folder.mkdir(parents=True)
    log = tmp_path / "curl.log"
    curl = bin_dir / "curl"
    curl.write_text(FAKE_CURL.format(python=sys.executable, log=str(log), served=str(served), folder=FTP_FOLDER,
                                     base=UPDATE_URL), encoding="utf-8")
    curl.chmod(0o755)
    for index, name in enumerate(PACKAGES):
        (work / "pakete" / name).write_bytes(f"erfunden {index}".encode())
    (work / "announcement.json").write_text(json.dumps({"payload": "erfunden", "signature": "erfunden"}))
    (work / "desktop").symlink_to(REPO / "desktop")
    env = {"TAG": "v9.2.0", "PRERELEASE": "false", "FTP_PASSWORD": "erfunden", "FTP_HOST": "ftp.example.ch",
           "FTP_USER": "erfunden", "FTP_FOLDER": FTP_FOLDER, "UPDATE_URL": UPDATE_URL, "RUNNER_TEMP": str(tmp_path)}

    def run(step: dict):
        return run_script(step["run"], work, env, bin_dir)
    return run, served, log


def test_the_release_download_takes_the_zip_and_its_checksum_file(rollout):
    fetch = step_named(rollout["steps"], "Release holen")
    patterns = [fetch["run"].split("--pattern ")[i].split()[0].strip("'") for i in (1, 2)]

    for name in (ZIP_NAME, extension_download.SUMS):
        assert any(fnmatch.fnmatch(name, pattern) for pattern in patterns), name


def test_the_zip_goes_into_the_version_folder_before_any_announcement(rollout, server):
    run, served, log = server

    done = run(step_named(rollout["steps"], "Hochladen"))

    assert done.returncode == 0, done.stderr
    calls = log.read_text(encoding="utf-8").splitlines()
    upload = [n for n, call in enumerate(calls) if f"-T pakete/{ZIP_NAME} ftp://ftp.example.ch/app/9.2.0/" in call]
    announcements = [n for n, call in enumerate(calls) if "-T announcement.json" in call]
    assert len(upload) == 1 and announcements and upload[0] < min(announcements)
    assert (served / "9.2.0" / ZIP_NAME).is_file()


def test_the_served_file_check_passes_when_the_server_serves_the_built_zip(rollout, server):
    run, _, _ = server
    assert run(step_named(rollout["steps"], "Hochladen")).returncode == 0

    done = run(step_named(rollout["steps"], "Prüfen"))

    assert done.returncode == 0, done.stderr


def test_the_served_file_check_fails_when_the_served_zip_differs(rollout, server):
    run, served, log = server
    assert run(step_named(rollout["steps"], "Hochladen")).returncode == 0
    (served / "9.2.0" / ZIP_NAME).write_bytes(b"PK anders")

    done = run(step_named(rollout["steps"], "Prüfen"))

    assert done.returncode != 0
    assert f"{UPDATE_URL}/9.2.0/{ZIP_NAME}" in log.read_text(encoding="utf-8")


def test_the_served_file_check_fails_when_the_zip_is_not_served(rollout, server):
    run, served, _ = server
    assert run(step_named(rollout["steps"], "Hochladen")).returncode == 0
    (served / "9.2.0" / ZIP_NAME).unlink()

    assert run(step_named(rollout["steps"], "Prüfen")).returncode != 0
