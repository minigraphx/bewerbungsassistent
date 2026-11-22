"""A published full release uploads the extension to the Chrome Web Store and to Edge Add-ons (#365).

These tests read the workflow and run its bash steps here: the build and version check against the real extension,
the store steps against fake_curl.py with invented settings, so no store is ever reached.
"""
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

import pytest
import yaml

import store_upload
import version

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
WORKFLOWS = REPO / ".github" / "workflows"
WORKFLOW = "erweiterung-einreichen.yml"
PINNED_ACTION = re.compile(r"^[\w.-]+/[\w./-]+@[0-9a-f]{40}$")
READY = "${{ steps.einstellungen.outputs.ready == 'true' }}"
CHROME_API = "https://chromewebstore.googleapis.com"
CHROME_ITEM = "publishers/erfunden-publisher/items/erfundene-erweiterung"
EDGE_API = "https://api.addons.microsoftedge.microsoft.com/v1/products/erfundenes-produkt/submissions"
SECRET_VALUES = {"CHROME_CLIENT_ID": "erfunden-client.apps", "CHROME_CLIENT_SECRET": "erfunden-geheim&=",
                 "CHROME_REFRESH_TOKEN": "erfunden-refresh/1", "EDGE_CLIENT_ID": "erfunden-edge-client",
                 "EDGE_API_KEY": "erfunden-edge-key"}
VARIABLE_VALUES = {"CHROME_PUBLISHER_ID": "erfunden-publisher", "CHROME_EXTENSION_ID": "erfundene-erweiterung",
                   "EDGE_PRODUCT_ID": "erfundenes-produkt"}
INVENTED_ACCESS = "erfunden-zugriff"  # what the fake Google sign-in hands out


def load(name: str) -> dict:
    return yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def workflow():
    return load(WORKFLOW)


def step_named(job: dict, text: str) -> dict:
    found = [step for step in job["steps"] if text in step.get("name", "")]
    assert len(found) == 1, f"expected one step named {text!r}, found {len(found)}"
    return found[0]


def all_steps(workflow: dict) -> list[dict]:
    return [step for job in workflow["jobs"].values() for step in job["steps"]]


def bash() -> str:
    found = shutil.which("bash")
    if not found or not shutil.which("jq"):
        pytest.skip("needs bash and jq, as on the runner")
    return found


def run_step(step: dict, tmp_path: pathlib.Path, env: dict[str, str], stdin: str = ""):
    """Runs the step's script as GitHub does with `shell: bash`."""
    path = f"{tmp_path / 'bin'}{os.pathsep}{pathlib.Path(sys.executable).parent}{os.pathsep}{os.environ['PATH']}"
    full_env = {"PATH": path, "RUNNER_TEMP": str(tmp_path / "runner"), **env}
    (tmp_path / "runner").mkdir(exist_ok=True)
    return subprocess.run([bash(), "--noprofile", "--norc", "-eo", "pipefail", "-c", step["run"]], env=full_env,
                          input=stdin, capture_output=True, text=True, cwd=REPO)


# --- trigger, jobs and permissions ---------------------------------------------------------------------------------

def test_it_runs_only_when_a_full_release_is_published(workflow):
    assert workflow[True] == {"release": {"types": ["released"]}}  # YAML reads the key `on` as true
    for job in workflow["jobs"].values():
        assert job["if"] == "${{ !github.event.release.prerelease }}"
        assert job["env"]["TAG"] == "${{ github.event.release.tag_name }}"


def test_each_store_is_its_own_job_that_waits_for_nothing(workflow):
    assert set(workflow["jobs"]) == {"chrome", "edge"}
    for job in workflow["jobs"].values():
        assert "needs" not in job and "continue-on-error" not in job
        assert job["timeout-minutes"] <= 30
    for name in os.listdir(WORKFLOWS):
        if name != WORKFLOW:
            text = (WORKFLOWS / name).read_text(encoding="utf-8")
            assert WORKFLOW not in text and "workflow_run" not in text, name
    groups = {load(name).get("concurrency", {}).get("group") for name in ("update-ausrollen.yml", "store-einreichen.yml")}
    assert workflow["concurrency"]["group"] not in groups
    assert workflow["concurrency"]["cancel-in-progress"] is False


def test_each_job_only_reads_the_repo_and_never_nears_the_signing_key(workflow):
    assert workflow["permissions"] == {}
    for job in workflow["jobs"].values():
        assert job["permissions"] == {"contents": "read"}
        assert "environment" not in job  # never the environment that holds the update signing key
    text = yaml.safe_dump(workflow)
    assert "UPDATE_SIGNING_KEY" not in text and "gh release" not in text


def test_every_action_is_pinned_to_a_commit_and_checks_out_the_tag(workflow):
    for job in workflow["jobs"].values():
        uses = [step for step in job["steps"] if "uses" in step]
        assert len(uses) == 1 and job["steps"][0] is uses[0]
        assert uses[0]["uses"].startswith("actions/checkout@")
        assert uses[0]["with"] == {"ref": "${{ github.event.release.tag_name }}", "persist-credentials": False}
    for step in all_steps(workflow):
        if "uses" in step:
            assert PINNED_ACTION.match(step["uses"].split(" ")[0]), step["uses"]


# --- missing settings -----------------------------------------------------------------------------------------------

@pytest.mark.parametrize("store", store_upload.STORES)
def test_the_readiness_step_reads_the_store_settings_from_secrets_and_variables(workflow, store):
    step = step_named(workflow["jobs"][store], "Einstellungen")
    settings = store_upload.STORES[store]

    expected = {name: f"${{{{ secrets.{name} }}}}" for name in settings.secrets}
    expected |= {name: f"${{{{ vars.{name} }}}}" for name in settings.variables}
    assert step["env"] == expected
    assert step["id"] == "einstellungen"
    assert step["run"].strip() == f"python3 desktop/store_upload.py ready {store}"
    assert "if" not in step


@pytest.mark.parametrize("store", store_upload.STORES)
def test_without_settings_the_job_ends_green_and_skips_every_later_step(workflow, store, tmp_path):
    job = workflow["jobs"][store]
    step = step_named(job, "Einstellungen")
    output = tmp_path / "output.txt"

    done = run_step(step, tmp_path, {"GITHUB_OUTPUT": str(output)})

    assert done.returncode == 0, done.stderr
    assert output.read_text(encoding="utf-8") == "ready=false\n"
    assert store_upload.SETUP_DOC in done.stdout and done.stdout.startswith("::notice::")
    later = job["steps"][job["steps"].index(step) + 1:]
    assert later and all(later_step["if"] == READY for later_step in later)


def test_the_setup_doc_exists_and_names_every_setting():
    text = (REPO / store_upload.SETUP_DOC).read_text(encoding="utf-8")

    for store in store_upload.STORES.values():
        for name in store.settings:
            assert f"`{name}`" in text, name
    assert "ß" not in text


def test_the_release_steps_name_the_workflow_and_its_settings_instead_of_the_manual_upload():
    text = (REPO / "desktop" / "README.md").read_text(encoding="utf-8")
    steps = text[text.index("**Neue Version ausrollen:**"):text.index("Das Release bleibt auch auf GitHub stehen")]

    assert WORKFLOW in steps and store_upload.SETUP_DOC.removeprefix("docs/") in steps
    for store in store_upload.STORES.values():
        for name in store.settings:
            assert f"`{name}`" in steps, name
    assert "Gleich nach dem Tag die ZIP-Datei" not in steps
    assert "Zeit zwischen Tag und Veröffentlichen" in steps


# --- build from the tag and version check ---------------------------------------------------------------------------

@pytest.mark.parametrize("store", store_upload.STORES)
def test_the_zip_is_built_and_checked_against_the_tag_before_any_upload(workflow, store):
    job = workflow["jobs"][store]
    names = [step.get("name", "") for step in job["steps"]]
    build = step_named(job, "Version prüfen")
    upload = step_named(job, "Hochladen")

    assert names.index(build["name"]) < names.index(upload["name"]) == len(names) - 1
    assert "python3 desktop/store_package.py" in build["run"]
    assert 'python3 desktop/store_upload.py version "$TAG"' in build["run"]


def test_a_tag_that_matches_the_manifest_builds_the_zip(workflow, tmp_path):
    build = step_named(workflow["jobs"]["chrome"], "Version prüfen")
    github_env = tmp_path / "env.txt"

    done = run_step(build, tmp_path, {"TAG": f"v{version.VERSION}", "GITHUB_ENV": str(github_env)})

    assert done.returncode == 0, done.stderr
    values = dict(line.split("=", 1) for line in github_env.read_text(encoding="utf-8").splitlines())
    assert values["VERSION"] == version.VERSION
    assert pathlib.Path(values["ZIP"]).is_file()
    assert values["ZIP"].endswith(f"bewerbungsbegleiter-erweiterung-{version.VERSION}.zip")


def test_a_tag_that_differs_from_the_manifest_fails_the_job(workflow, tmp_path):
    build = step_named(workflow["jobs"]["edge"], "Version prüfen")
    github_env = tmp_path / "env.txt"

    done = run_step(build, tmp_path, {"TAG": "v0.0.1", "GITHUB_ENV": str(github_env)})

    assert done.returncode != 0
    assert "::error::" in done.stderr and "v0.0.1" in done.stderr
    assert not github_env.exists() or "ZIP=" not in github_env.read_text(encoding="utf-8")


# --- the store calls, against fake_curl.py --------------------------------------------------------------------------

@pytest.fixture
def fake_curl(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    curl = bin_dir / "curl"
    curl.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{HERE / "fake_curl.py"}" "$@"\n', encoding="utf-8")
    curl.chmod(0o755)
    log = tmp_path / "curl.log"

    def run(step: dict, responses: list[dict]):
        (tmp_path / "responses.json").write_text(json.dumps(responses), encoding="utf-8")
        package = tmp_path / "erweiterung.zip"
        package.write_bytes(b"PK erfunden")
        env = {**SECRET_VALUES, **VARIABLE_VALUES, "ZIP": str(package), "VERSION": "9.2.0", "POLL_SECONDS": "0",
               "POLL_TRIES": "3", "FAKE_CURL_LOG": str(log), "FAKE_CURL_RESPONSES": str(tmp_path / "responses.json")}
        done = run_step(step, tmp_path, env)
        calls = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()] if log.exists() else []
        return done, calls

    return run


def assert_no_secret_leaks(done, calls):
    for value in (*SECRET_VALUES.values(), INVENTED_ACCESS):
        assert value not in done.stdout.replace(f"::add-mask::{INVENTED_ACCESS}", "") + done.stderr
        for call in calls:
            assert not any(value in arg for arg in call["argv"]), call["url"]  # never on curl's command line


def test_every_store_step_gets_its_secrets_only_through_env(workflow):
    for step in all_steps(workflow):
        assert "${{" not in step.get("run", ""), step.get("name")  # no expression is pasted into a script
    for store, settings in store_upload.STORES.items():
        upload = step_named(workflow["jobs"][store], "Hochladen")
        expected = {name: f"${{{{ secrets.{name} }}}}" for name in settings.secrets}
        expected |= {name: f"${{{{ vars.{name} }}}}" for name in settings.variables}
        assert {key: value for key, value in upload["env"].items() if key in expected} == expected
    secret_steps = sorted(step["name"] for step in all_steps(workflow) if "secrets." in yaml.safe_dump(step))
    assert secret_steps == sorted(["Einstellungen vorhanden?", "Einstellungen vorhanden?",
                                   step_named(workflow["jobs"]["chrome"], "Hochladen")["name"],
                                   step_named(workflow["jobs"]["edge"], "Hochladen")["name"]])


def chrome_token():
    return {"match": "https://oauth2.googleapis.com/token", "code": 200,
            "body": {"access_token": INVENTED_ACCESS, "expires_in": 3599, "token_type": "Bearer"}}


def test_chrome_uploads_the_zip_waits_for_it_and_submits_it_for_review(workflow, fake_curl):
    step = step_named(workflow["jobs"]["chrome"], "Hochladen")

    done, calls = fake_curl(step, [
        chrome_token(),
        {"match": f"{CHROME_API}/upload/v2/{CHROME_ITEM}:upload", "code": 200, "body": {"uploadState": "IN_PROGRESS"}},
        {"match": f"{CHROME_API}/v2/{CHROME_ITEM}:fetchStatus", "code": 200,
         "body": {"lastAsyncUploadState": "SUCCEEDED"}},
        {"match": f"{CHROME_API}/v2/{CHROME_ITEM}:publish", "code": 200, "body": {"state": "PENDING_REVIEW"}},
    ])

    assert done.returncode == 0, done.stdout + done.stderr
    token, upload, status, publish = calls
    form = dict(pair.split("=", 1) for pair in token["data"].strip().split("&"))
    assert form == {"client_id": "erfunden-client.apps", "client_secret": "erfunden-geheim%26%3D",
                    "refresh_token": "erfunden-refresh%2F1", "grant_type": "refresh_token"}
    assert upload["method"] == "POST" and upload["upload_bytes"] == b"PK erfunden".hex()
    for call in (upload, status, publish):
        assert f"Authorization: Bearer {INVENTED_ACCESS}" in call["headers"]
    assert publish["method"] == "POST" and json.loads(publish["data"]) == {}
    assert "::notice::" in done.stdout and "PENDING_REVIEW" in done.stdout
    assert_no_secret_leaks(done, calls)


def test_chrome_stops_before_publishing_when_the_upload_fails(workflow, fake_curl):
    step = step_named(workflow["jobs"]["chrome"], "Hochladen")

    done, calls = fake_curl(step, [
        chrome_token(),
        {"match": ":upload", "code": 200, "body": {"uploadState": "FAILED"}},
    ])

    assert done.returncode == 1
    assert "::error::" in done.stdout and "FAILED" in done.stdout
    assert not [call for call in calls if call["url"].endswith(":publish")]
    assert_no_secret_leaks(done, calls)


def test_chrome_stops_when_google_refuses_the_sign_in(workflow, fake_curl):
    step = step_named(workflow["jobs"]["chrome"], "Hochladen")

    done, calls = fake_curl(step, [
        {"match": "oauth2.googleapis.com", "code": 400, "body": {"error": "invalid_grant"}},
    ])

    assert done.returncode == 1 and len(calls) == 1
    assert "::error::" in done.stdout and store_upload.SETUP_DOC in done.stdout
    assert_no_secret_leaks(done, calls)


def test_chrome_gives_up_when_the_upload_never_finishes(workflow, fake_curl):
    step = step_named(workflow["jobs"]["chrome"], "Hochladen")
    waiting = {"match": ":fetchStatus", "code": 200, "body": {"lastAsyncUploadState": "IN_PROGRESS"}}

    done, calls = fake_curl(step, [
        chrome_token(), {"match": ":upload", "code": 200, "body": {"uploadState": "IN_PROGRESS"}},
        waiting, waiting, waiting,
    ])

    assert done.returncode == 1 and "::error::" in done.stdout
    assert not [call for call in calls if call["url"].endswith(":publish")]


def edge_operation(path: str, status: str) -> dict:
    return {"match": f"{EDGE_API}/{path}", "code": 200, "body": {"id": "op", "status": status, "message": status,
                                                                  "errorCode": "", "errors": None}}


def test_edge_uploads_the_package_then_publishes_the_draft(workflow, fake_curl):
    step = step_named(workflow["jobs"]["edge"], "Hochladen")

    done, calls = fake_curl(step, [
        {"match": f"{EDGE_API}/draft/package", "code": 202, "headers": {"location": "upload-op-1"}},
        edge_operation("draft/package/operations/upload-op-1", "InProgress"),
        edge_operation("draft/package/operations/upload-op-1", "Succeeded"),
        {"match": EDGE_API, "code": 202, "headers": {"Location": "/v1/products/erfundenes-produkt/submissions/operations/publish-op-2"}},
        edge_operation("operations/publish-op-2", "Succeeded"),
    ])

    assert done.returncode == 0, done.stdout + done.stderr
    upload, _, _, publish, _ = calls
    assert upload["method"] == "POST" and upload["url"] == f"{EDGE_API}/draft/package"
    assert "Content-Type: application/zip" in upload["headers"] and upload["upload_bytes"] == b"PK erfunden".hex()
    assert publish["method"] == "POST" and publish["url"] == EDGE_API
    assert json.loads(publish["data"]) == {"notes": "Update to version 9.2.0."}
    for call in calls:
        assert "Authorization: ApiKey erfunden-edge-key" in call["headers"]
        assert "X-ClientID: erfunden-edge-client" in call["headers"]
    assert "::notice::" in done.stdout
    assert_no_secret_leaks(done, calls)


def test_edge_stops_before_publishing_when_the_upload_is_refused(workflow, fake_curl):
    step = step_named(workflow["jobs"]["edge"], "Hochladen")

    done, calls = fake_curl(step, [{"match": "draft/package", "code": 400, "body": "Bad Request"}])

    assert done.returncode == 1 and len(calls) == 1
    assert "::error::" in done.stdout and "400" in done.stdout


def test_edge_fails_the_job_when_the_store_rejects_the_submission(workflow, fake_curl):
    step = step_named(workflow["jobs"]["edge"], "Hochladen")
    rejected = {**edge_operation("operations/publish-op-2", "Failed")}
    rejected["body"] = {**rejected["body"], "errorCode": "InProgressSubmission"}

    done, calls = fake_curl(step, [
        {"match": "draft/package", "code": 202, "headers": {"Location": "upload-op-1"}},
        edge_operation("draft/package/operations/upload-op-1", "Succeeded"),
        {"match": EDGE_API, "code": 202, "headers": {"Location": "publish-op-2"}},
        rejected,
    ])

    assert done.returncode == 1
    assert "::error::" in done.stdout and "InProgressSubmission" in done.stdout
    assert_no_secret_leaks(done, calls)


def test_edge_refuses_an_operation_id_that_is_not_one(workflow, fake_curl):
    step = step_named(workflow["jobs"]["edge"], "Hochladen")

    done, calls = fake_curl(step, [{"match": "draft/package", "code": 202, "headers": {"Location": "a b;c"}}])

    assert done.returncode == 1 and len(calls) == 1 and "::error::" in done.stdout
