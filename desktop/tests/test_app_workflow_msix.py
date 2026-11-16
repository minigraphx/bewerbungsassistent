"""The release builds the Store package next to the Windows installer (#343, G6), only as an artifact (#353).

The Windows job itself cannot run here; these tests read the workflow and check how the MSIX job is wired.
"""
import pathlib

import pytest
import yaml

WORKFLOWS = pathlib.Path(__file__).resolve().parents[2] / ".github" / "workflows"
ON_TAG = "startsWith(github.ref, 'refs/tags/v')"
IDENTITY_VARIABLES = ("MSIX_IDENTITY_NAME", "MSIX_PUBLISHER", "MSIX_PUBLISHER_DISPLAY_NAME")


@pytest.fixture(scope="module")
def workflow():
    return yaml.safe_load((WORKFLOWS / "app.yml").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def job(workflow):
    return workflow["jobs"]["msix"]


def step_named(steps: list[dict], text: str) -> dict:
    found = [step for step in steps if text in step.get("name", "") or text in step.get("uses", "")]
    assert len(found) == 1, f"expected one step with {text!r}, found {len(found)}"
    return found[0]


def scripts(job: dict) -> str:
    return "\n".join(step.get("run", "") for step in job["steps"])


def test_the_msix_job_packs_the_pyinstaller_output_of_the_windows_job(workflow, job):
    upload = step_named(workflow["jobs"]["windows"]["steps"], "PyInstaller")
    download = step_named(job["steps"], "download-artifact")

    assert job["needs"] == "windows"
    assert job["runs-on"] == "windows-latest"
    assert upload["with"]["path"] == "dist/Bewerbungsbegleiter/"
    assert download["with"]["name"] == upload["with"]["name"]
    assert "pyinstaller --" not in scripts(job).lower()  # packs the output above, never builds its own


def test_no_other_job_waits_for_the_msix_job(workflow, job):
    assert "continue-on-error" not in job
    for name, other in workflow["jobs"].items():
        assert "msix" not in str(other.get("needs", "")), name


def test_the_identity_comes_from_the_repo_variables_never_from_secrets(job):
    manifest = step_named(job["steps"], "Manifest")

    assert manifest["env"] == {name: f"${{{{ vars.{name} }}}}" for name in IDENTITY_VARIABLES}
    assert "desktop/msix/manifest.py" in manifest["run"] and " store " in manifest["run"]
    assert "secrets." not in yaml.safe_dump(job)


def test_the_package_is_packed_but_not_signed(job):
    assert "makeappx.exe" in scripts(job) and " pack /o /d $env:STAGE " in scripts(job)
    assert "Bewerbungsbegleiter-$env:VERSION.msix" in scripts(job)
    assert "signtool" not in scripts(job).lower()


def test_every_run_keeps_the_package_as_an_artifact(job):
    upload = step_named(job["steps"], "upload-artifact")

    assert "if" not in upload
    assert upload["with"]["path"] == "dist-msix/"


def test_the_package_never_goes_into_the_release(job):
    """Unsigned, it does not install outside the Store; Partner Center takes it from the artifact (#353)."""
    assert not [step for step in job["steps"] if "gh release" in step.get("run", "")]
    assert not [step for step in job["steps"] if "Release" in step.get("name", "")]
    assert "GH_TOKEN" not in yaml.safe_dump(job)


def test_the_msix_job_may_only_read_the_repo(job):
    assert job["permissions"] == {"contents": "read"}


@pytest.mark.parametrize(("name", "folder"), [("windows", "dist-installer"), ("macos", "dist-mac"), ("linux", "dist-linux")])
def test_a_tag_still_attaches_the_other_assets_to_the_draft_release(workflow, name, folder):
    release = step_named(workflow["jobs"][name]["steps"], "Release-Entwurf")

    assert release["if"] == ON_TAG
    assert "gh release upload" in release["run"] and folder in release["run"]
