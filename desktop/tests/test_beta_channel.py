"""Pre-releases as updates for whoever switches them on (#212, G47); everyone else only gets published releases.

Announcements here are invented and signed with the test key of signed_update.
"""
import json
import os
import pathlib
import shutil
import subprocess
import threading

import pytest
import yaml
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

import release_manifest
import routes_app
import settings
import updates
from signed_update import BASE, PACKAGE_NAMES, announcement, envelope

WORKFLOW = pathlib.Path(__file__).resolve().parents[2] / ".github" / "workflows" / "update-ausrollen.yml"
INSTALLER = b"MZ" + b"x" * 500


def channels(stable: str | None = "9.2.0", beta: str | None = "9.3.0", beta_raw: bytes | None = None, asked=None):
    """A fetch with a stable and a beta announcement; `asked` collects the addresses the app asked for."""
    files = {}
    for name, version in (("latest.json", stable), ("beta.json", beta)):
        if version:
            files[f"{BASE}/{name}"] = envelope(announcement(version, {"win32": INSTALLER}))
            files[f"{BASE}/{version}/{PACKAGE_NAMES['win32'].format(version)}"] = INSTALLER
    if beta_raw is not None:
        files[f"{BASE}/beta.json"] = beta_raw

    def fetch(url: str, limit: int) -> bytes:
        if asked is not None:
            asked.append(url)
        if url not in files:
            raise OSError("not found")
        return files[url]
    return fetch


# The app


def test_without_the_switch_only_published_releases_are_offered():
    asked = []

    found = updates.latest(channels(asked=asked), "win32")

    assert found.version == "9.2.0"
    assert f"{BASE}/beta.json" not in asked


def test_with_the_switch_the_newer_pre_release_is_offered():
    found = updates.latest(channels(), "win32", beta=True)

    assert found.version == "9.3.0"
    assert found.installer_url == f"{BASE}/9.3.0/{PACKAGE_NAMES['win32'].format('9.3.0')}"


def test_with_the_switch_a_newer_published_release_still_wins():
    assert updates.latest(channels(stable="9.4.0", beta="9.3.0"), "win32", beta=True).version == "9.4.0"


def test_with_the_switch_a_missing_beta_announcement_leaves_the_release():
    assert updates.latest(channels(beta=None), "win32", beta=True).version == "9.2.0"


def test_a_beta_announcement_needs_the_same_update_key():
    foreign = envelope(announcement("9.9.0", {"win32": INSTALLER}), Ed25519PrivateKey.generate())

    assert updates.latest(channels(beta_raw=foreign), "win32", beta=True).version == "9.2.0"


def test_only_a_pre_release_and_no_release_is_offered_with_the_switch():
    assert updates.latest(channels(stable=None), "win32") is None
    assert updates.latest(channels(stable=None), "win32", beta=True).version == "9.3.0"


# The setting


def test_the_switch_is_off_until_the_person_turns_it_on(tmp_path):
    paths = settings.Paths(tmp_path)

    assert settings.beta_updates(paths) is False
    settings.set_beta_updates(paths, True)
    assert settings.beta_updates(paths) is True
    assert settings.load(paths)[settings.BETA_UPDATES] is True


def controls(tmp_path, fetch=None):
    return routes_app.Controls(stop=threading.Event().set, automatic=True, platform="win32", fetch=fetch or channels(),
                               run_installer=lambda path: None, paths=settings.Paths(tmp_path))


def answer(route_result) -> dict:
    return json.loads(route_result.inhalt)


def test_the_route_switches_and_the_offer_follows_at_once(tmp_path):
    get, post = routes_app.make_routes(controls(tmp_path))
    assert answer(get["/api/app/vorabversionen"](None, {}, None)) == {"an": False}
    assert answer(get["/api/app/version"](None, {}, None))["update"]["version"] == "9.2.0"

    assert answer(post["/api/app/vorabversionen"](None, {}, {"an": True})) == {"an": True}

    assert answer(get["/api/app/version"](None, {}, None))["update"]["version"] == "9.3.0"
    assert settings.beta_updates(settings.Paths(tmp_path)) is True


@pytest.mark.parametrize("body", [None, {}, {"an": "ja"}, {"an": 1}])
def test_the_route_wants_yes_or_no(tmp_path, body):
    _, post = routes_app.make_routes(controls(tmp_path))

    with pytest.raises(ValueError, match="an erwartet"):
        post["/api/app/vorabversionen"](None, {}, body)


def test_the_page_has_the_switch_under_the_advanced_settings():
    pages = pathlib.Path(__file__).resolve().parents[2] / "bewerbungen" / "seiten"
    html = (pages / "einstellungen.html").read_text(encoding="utf-8")
    script = (pages / "vorabversionen.js").read_text(encoding="utf-8")

    assert 'id="vorabversionen"' in html and 'id="beta-an"' in html and '<script src="/vorabversionen.js">' in html
    assert "/api/app/vorabversionen" in script


# The rollout


@pytest.mark.parametrize("prerelease, current, expected", [
    (True, None, ["beta.json"]),
    (False, None, ["beta.json", "latest.json"]),
    (False, "9.1.0", ["beta.json", "latest.json"]),
    (False, "9.2.0", ["beta.json", "latest.json"]),
    (False, "9.3.0", ["latest.json"]),  # the newer pre-release stays offered to whoever has the switch on
    (True, "9.3.0", ["beta.json"]),
], ids=["pre", "release", "release-after-older-beta", "pre-made-release", "release-under-newer-beta", "pre-under-beta"])
def test_where_an_announcement_goes(prerelease, current, expected):
    raw = envelope(announcement(current, {})) if current else None

    assert release_manifest.announcements("v9.2.0", prerelease, raw) == expected


@pytest.mark.parametrize("raw", [b"", b"kaputt", b'{"payload": "!!"}', json.dumps({"payload": "e30=", "signature": ""}).encode()])
def test_an_unreadable_beta_announcement_is_replaced(raw):
    assert release_manifest.announcements("v9.2.0", False, raw) == ["beta.json", "latest.json"]


def test_the_command_line_names_the_announcements(tmp_path, capsys):
    current = tmp_path / "beta-aktuell.json"
    current.write_bytes(envelope(announcement("9.3.0", {})))

    assert release_manifest.main(["channels", "v9.2.0", "false", str(current)]) == 0
    assert capsys.readouterr().out.split() == ["latest.json"]
    assert release_manifest.main(["channels", "v9.2.0", "true", str(tmp_path / "fehlt.json")]) == 0
    assert capsys.readouterr().out.split() == ["beta.json"]


@pytest.fixture(scope="module")
def workflow():
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def test_pre_releases_and_releases_both_roll_out(workflow):
    triggers = workflow[True]  # YAML reads the key `on` as true
    assert triggers["release"]["types"] == ["prereleased", "released"]
    assert "if" not in workflow["jobs"]["ausrollen"]


def test_the_website_follows_only_a_release(workflow):
    job = workflow["jobs"]["webseite"]

    assert job["if"] == "${{ needs.ausrollen.outputs.prerelease == 'false' }}"
    assert workflow["jobs"]["ausrollen"]["outputs"]["prerelease"]


def run_upload(workflow, tmp_path, prerelease: str, served_beta: bytes | None):
    """The upload step with a fake curl: it records every call and serves the current beta announcement."""
    bash = shutil.which("bash")
    if not bash:
        pytest.skip("needs bash")
    step = next(s for s in workflow["jobs"]["ausrollen"]["steps"] if s.get("name", "").startswith("Hochladen"))
    calls, beta = tmp_path / "calls.txt", tmp_path / "served-beta.json"
    if served_beta is not None:
        beta.write_bytes(served_beta)
    fake = tmp_path / "bin" / "curl"
    fake.parent.mkdir()
    fake.write_text(f"""#!/bin/sh
printf '%s ' "$@" >> "{calls}"; printf '\\n' >> "{calls}"
case "$*" in
  *-o\\ *) [ -f "{beta}" ] || exit 22; out=""; prev=""
    for arg in "$@"; do [ "$prev" = "-o" ] && out="$arg"; prev="$arg"; done
    cp "{beta}" "$out" ;;
esac
""", encoding="utf-8")
    fake.chmod(0o755)
    work = tmp_path / "work"
    (work / "pakete").mkdir(parents=True)
    (work / "announcement.json").write_bytes(envelope(announcement("9.2.0", {})))
    repo = WORKFLOW.parents[2]
    (work / "desktop").symlink_to(repo / "desktop")
    env = {"PATH": f"{fake.parent}{os.pathsep}{os.environ['PATH']}", "TAG": "v9.2.0", "PRERELEASE": prerelease,
           "FTP_PASSWORD": "erfunden", "FTP_HOST": "ftp.example.ch", "FTP_USER": "erfunden", "FTP_FOLDER": "app",
           "UPDATE_URL": "https://updates.example.ch/app", "RUNNER_TEMP": str(tmp_path)}
    done = subprocess.run([bash, "-e", "-c", step["run"]], env=env, cwd=work, capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    lines = calls.read_text(encoding="utf-8").splitlines()
    return [line for line in lines if "-T announcement.json" in line], (work / "angekuendigt.txt").read_text().split()


def test_a_pre_release_is_announced_only_as_beta(workflow, tmp_path):
    uploads, announced = run_upload(workflow, tmp_path, "true", None)

    assert announced == ["beta.json"]
    assert len(uploads) == 1 and "/beta.json.part" in uploads[0]


def test_a_release_is_announced_in_both(workflow, tmp_path):
    uploads, announced = run_upload(workflow, tmp_path, "false", envelope(announcement("9.1.0", {})))

    assert announced == ["beta.json", "latest.json"]
    assert [u for u in uploads if "/latest.json.part" in u] and [u for u in uploads if "/beta.json.part" in u]
