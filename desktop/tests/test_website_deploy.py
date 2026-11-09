"""Publishing an app release also deploys the website, so its guide matches the released version (#153)."""
import os
import pathlib
import shutil
import subprocess

import pytest
import yaml

WORKFLOW = pathlib.Path(__file__).resolve().parents[2] / ".github" / "workflows" / "update-ausrollen.yml"
EXPECTED_CALL = ["workflow", "run", "ausrollen.yml", "--repo", "minigraphx/bewerbungsbegleiter-webseite", "--ref", "main",
                 "-f", "tag=v9.2.0"]


@pytest.fixture(scope="module")
def workflow():
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def job(workflow):
    return workflow["jobs"]["webseite"]


def test_the_website_job_runs_only_after_the_update_went_out(job):
    assert job["needs"] == "ausrollen"
    assert "always()" not in str(job.get("if", "")) and "failure()" not in str(job.get("if", ""))


def test_the_website_job_gets_no_permission_of_this_repo(workflow, job):
    assert job["permissions"] == {}
    assert workflow["permissions"] == {"contents": "read"}
    assert "environment" not in job  # the signing key stays with the job 'ausrollen'


def test_the_token_comes_from_the_secret_and_the_tag_from_the_release(job):
    step = job["steps"][-1]

    assert step["env"]["GH_TOKEN"] == "${{ secrets.WEBSITE_DISPATCH_TOKEN }}"
    assert job["env"]["TAG"] == "${{ github.event.release.tag_name || inputs.tag }}"


def run_step(job, tmp_path, token):
    bash = shutil.which("bash")
    if not bash:
        pytest.skip("needs bash")
    calls = tmp_path / "calls.txt"
    fake = tmp_path / "bin" / "gh"
    fake.parent.mkdir()
    fake.write_text(f'#!/bin/sh\nprintf "%s\\n" "$@" > "{calls}"\n', encoding="utf-8")
    fake.chmod(0o755)
    env = {"PATH": f"{fake.parent}{os.pathsep}{os.environ['PATH']}", "TAG": "v9.2.0", "GH_TOKEN": token}
    done = subprocess.run([bash, "-e", "-c", job["steps"][-1]["run"]], env=env, capture_output=True, text=True)
    return done, calls.read_text(encoding="utf-8").splitlines() if calls.exists() else None


def test_the_step_starts_the_website_workflow_with_the_tag(job, tmp_path):
    done, call = run_step(job, tmp_path, token="github_pat_erfunden")

    assert done.returncode == 0, done.stderr
    assert call == EXPECTED_CALL


def test_without_the_secret_the_step_fails_clearly(job, tmp_path):
    done, call = run_step(job, tmp_path, token="")

    assert done.returncode != 0 and call is None
    assert "::error::" in done.stdout and "WEBSITE_DISPATCH_TOKEN" in done.stdout
