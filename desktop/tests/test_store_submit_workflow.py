"""A published full release submits its Store package to the Microsoft Store (#354, G6).

The Windows job cannot run here; these tests read the workflow, and run its bash check with made-up settings.
"""
import os
import pathlib
import re
import shutil
import subprocess

import pytest
import yaml

WORKFLOWS = pathlib.Path(__file__).resolve().parents[2] / ".github" / "workflows"
STORE_WORKFLOW = "store-einreichen.yml"
SECRET_NAMES = ("MSSTORE_TENANT_ID", "MSSTORE_SELLER_ID", "MSSTORE_CLIENT_ID", "MSSTORE_CLIENT_SECRET")
VARIABLE_NAME = "MSSTORE_PRODUCT_ID"
SETTING_NAMES = (*SECRET_NAMES, VARIABLE_NAME)
PINNED_ACTION = re.compile(r"^[\w.-]+/[\w./-]+@[0-9a-f]{40}$")


def load(name: str) -> dict:
    return yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def workflow():
    return load(STORE_WORKFLOW)


@pytest.fixture(scope="module")
def check(workflow):
    return workflow["jobs"]["bereit"]


@pytest.fixture(scope="module")
def submit(workflow):
    return workflow["jobs"]["einreichen"]


def step_named(job: dict, text: str) -> dict:
    found = [step for step in job["steps"] if text in step.get("name", "")]
    assert len(found) == 1, f"expected one step named {text!r}, found {len(found)}"
    return found[0]


def all_steps(workflow: dict) -> list[dict]:
    return [step for job in workflow["jobs"].values() for step in job["steps"]]


def test_it_runs_only_when_a_full_release_is_published(workflow, check, submit):
    assert workflow[True] == {"release": {"types": ["released"]}}  # YAML reads the key `on` as true
    assert check["if"] == "${{ !github.event.release.prerelease }}"
    assert submit["needs"] == "bereit"
    assert submit["if"] == "${{ needs.bereit.outputs.ready == 'true' }}"
    assert submit["env"]["TAG"] == "${{ github.event.release.tag_name }}"


def run_check(check: dict, tmp_path: pathlib.Path, settings: dict[str, str]):
    bash = shutil.which("bash")
    if not bash:
        pytest.skip("needs bash")
    step = step_named(check, "Einstellungen")
    output = tmp_path / "output.txt"
    env = {"PATH": os.environ["PATH"], "GITHUB_OUTPUT": str(output), **settings}
    done = subprocess.run([bash, "-e", "-c", step["run"]], env=env, capture_output=True, text=True, cwd=tmp_path)
    return done, output.read_text(encoding="utf-8").splitlines() if output.exists() else []


@pytest.mark.parametrize("missing", SETTING_NAMES)
def test_a_missing_setting_skips_the_submission_with_a_notice_naming_it(check, tmp_path, missing):
    settings = {name: "erfunden" for name in SETTING_NAMES if name != missing}

    done, output = run_check(check, tmp_path, settings)

    assert done.returncode == 0, done.stderr
    assert output == ["ready=false"]
    notice = [line for line in done.stdout.splitlines() if line.startswith("::notice::")]
    assert len(notice) == 1 and missing in notice[0]
    assert "erfunden" not in done.stdout + done.stderr  # names only, never a value


def test_without_any_setting_the_notice_names_all_of_them(check, tmp_path):
    done, output = run_check(check, tmp_path, {})

    assert done.returncode == 0 and output == ["ready=false"]
    assert all(name in done.stdout for name in SETTING_NAMES)


def test_with_every_setting_the_submission_goes_ahead_silently(check, tmp_path):
    done, output = run_check(check, tmp_path, {name: "erfunden" for name in SETTING_NAMES})

    assert done.returncode == 0, done.stderr
    assert output == ["ready=true"]
    assert done.stdout == ""


def test_the_check_reads_the_settings_from_secrets_and_the_variable(check):
    step = step_named(check, "Einstellungen")

    expected = {name: f"${{{{ secrets.{name} }}}}" for name in SECRET_NAMES}
    expected[VARIABLE_NAME] = f"${{{{ vars.{VARIABLE_NAME} }}}}"
    assert step["env"] == expected
    assert check["outputs"] == {"ready": "${{ steps.einstellungen.outputs.ready }}"}
    assert step["id"] == "einstellungen"


def test_the_cli_is_a_pinned_release_checked_against_its_checksum(submit):
    url = submit["env"]["MSSTORE_CLI_URL"]
    install = step_named(submit, "Developer CLI")

    assert re.fullmatch(r"https://github\.com/microsoft/msstore-cli/releases/download/v\d+\.\d+\.\d+/MSStoreCLI-win-x64\.zip", url)
    assert re.fullmatch(r"[0-9a-f]{64}", submit["env"]["MSSTORE_CLI_SHA256"])
    assert "Get-FileHash -Algorithm SHA256" in install["run"] and "$env:MSSTORE_CLI_SHA256" in install["run"]
    assert "winget" not in install["run"] and "latest" not in install["run"]


def test_every_action_is_pinned_to_a_commit(workflow):
    for step in all_steps(workflow):
        if "uses" in step:
            assert PINNED_ACTION.match(step["uses"]), step["uses"]


def test_secrets_reach_the_scripts_only_through_env(workflow, submit):
    for step in all_steps(workflow):
        assert "secrets." not in step.get("run", ""), step.get("name")
        assert "${{" not in step.get("run", ""), step.get("name")  # no expression is pasted into a script
    sign_in = step_named(submit, "Anmelden")
    assert sign_in["env"] == {name: f"${{{{ secrets.{name} }}}}" for name in SECRET_NAMES}
    for option, name in (("--tenantId", "MSSTORE_TENANT_ID"), ("--sellerId", "MSSTORE_SELLER_ID"),
                         ("--clientId", "MSSTORE_CLIENT_ID"), ("--clientSecret", "MSSTORE_CLIENT_SECRET")):
        assert f"{option} $env:{name}" in sign_in["run"]
    secret_steps = [step.get("name") for step in all_steps(workflow) if "secrets." in yaml.safe_dump(step)]
    assert secret_steps == ["Einstellungen vorhanden?", "Anmelden in Partner Center"]


def test_the_package_comes_from_the_app_run_of_the_tag(submit):
    fetch = step_named(submit, "Paket des Tags")
    app_upload = [step for step in load("app.yml")["jobs"]["msix"]["steps"] if "upload-artifact" in step.get("uses", "")]

    assert "gh run list --workflow app.yml --branch $env:TAG --event push --status success" in fetch["run"]
    assert f"gh run download $run --name {app_upload[0]['with']['name']}" in fetch["run"]
    assert "Bewerbungsbegleiter-$version.msix" in fetch["run"]
    assert fetch["env"] == {"GH_TOKEN": "${{ github.token }}", "GH_REPO": "${{ github.repository }}"}


def test_publish_submits_the_package_under_the_product_id_from_the_variable(submit):
    publish = step_named(submit, "Einreichen")

    assert publish["env"] == {VARIABLE_NAME: f"${{{{ vars.{VARIABLE_NAME} }}}}"}
    assert "msstore publish $env:PACKAGE -id $env:MSSTORE_PRODUCT_ID" in publish["run"]
    assert "--noCommit" not in publish["run"] and "-nc" not in publish["run"]


def test_each_job_gets_only_the_permission_it_needs(workflow, check, submit):
    assert workflow["permissions"] == {}
    assert check["permissions"] == {}
    assert submit["permissions"] == {"actions": "read"}
    assert "environment" not in submit  # never the environment that holds the update signing key
    assert "gh release" not in yaml.safe_dump(workflow)


def test_a_failed_submission_fails_its_job_and_nothing_else(workflow, submit):
    assert "continue-on-error" not in submit
    for name in os.listdir(WORKFLOWS):
        if name == STORE_WORKFLOW:
            continue
        text = (WORKFLOWS / name).read_text(encoding="utf-8")
        assert "msstore" not in text.lower() and STORE_WORKFLOW not in text, name
        assert "workflow_run" not in text, name
    assert workflow.get("concurrency", {}).get("group") != load("update-ausrollen.yml")["concurrency"]["group"]
