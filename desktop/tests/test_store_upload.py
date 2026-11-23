"""The checks before a published release uploads the extension to the browser stores (#365)."""
import json
import zipfile

import pytest

import store_upload

INVENTED = "erfunden-123"


def store_zip(tmp_path, version="9.2.0", name="erweiterung.zip"):
    path = tmp_path / name
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("manifest.json", json.dumps({"manifest_version": 3, "version": version}))
    return path


def all_settings(store):
    return {name: INVENTED for name in store_upload.STORES[store].settings}


def run_ready(store, environ, tmp_path, capsys):
    output = tmp_path / "output.txt"
    code = store_upload.main(["ready", store], {**environ, "GITHUB_OUTPUT": str(output)})
    printed = capsys.readouterr()
    return code, output.read_text(encoding="utf-8").splitlines(), printed.out + printed.err


@pytest.mark.parametrize("store, missing", [(store, name) for store, settings in store_upload.STORES.items()
                                            for name in settings.settings])
def test_a_missing_setting_skips_the_store_with_a_notice_naming_it(store, missing, tmp_path, capsys):
    environ = {name: value for name, value in all_settings(store).items() if name != missing}

    code, output, printed = run_ready(store, environ, tmp_path, capsys)

    assert code == 0  # the job ends green
    assert output == ["ready=false"]
    notices = [line for line in printed.splitlines() if line.startswith("::notice::")]
    assert len(notices) == 1
    assert missing in notices[0] and store_upload.SETUP_DOC in notices[0]
    assert INVENTED not in printed  # names only, never a value


def test_an_empty_value_counts_as_missing(tmp_path, capsys):
    environ = {**all_settings("edge"), "EDGE_API_KEY": ""}

    code, output, printed = run_ready("edge", environ, tmp_path, capsys)

    assert code == 0 and output == ["ready=false"] and "EDGE_API_KEY" in printed


@pytest.mark.parametrize("store", store_upload.STORES)
def test_without_any_setting_the_notice_names_all_of_them(store, tmp_path, capsys):
    code, output, printed = run_ready(store, {}, tmp_path, capsys)

    assert code == 0 and output == ["ready=false"]
    assert all(name in printed for name in store_upload.STORES[store].settings)


@pytest.mark.parametrize("store", store_upload.STORES)
def test_with_every_setting_the_upload_goes_ahead_silently(store, tmp_path, capsys):
    code, output, printed = run_ready(store, all_settings(store), tmp_path, capsys)

    assert code == 0 and output == ["ready=true"] and printed == ""


def test_the_stores_need_their_credentials_and_listing_ids():
    chrome, edge = store_upload.STORES["chrome"], store_upload.STORES["edge"]

    assert chrome.secrets == ("CHROME_CLIENT_ID", "CHROME_CLIENT_SECRET", "CHROME_REFRESH_TOKEN")
    assert chrome.variables == ("CHROME_PUBLISHER_ID", "CHROME_EXTENSION_ID")
    assert edge.secrets == ("EDGE_CLIENT_ID", "EDGE_API_KEY")
    assert edge.variables == ("EDGE_PRODUCT_ID",)


def test_an_unknown_store_is_a_usage_error(tmp_path, capsys):
    assert store_upload.main(["ready", "firefox"], {"GITHUB_OUTPUT": str(tmp_path / "out")}) == 2


def test_the_version_check_passes_when_the_manifest_matches_the_tag(tmp_path, capsys):
    code = store_upload.main(["version", "v9.2.0", str(store_zip(tmp_path))], {})

    assert code == 0
    assert capsys.readouterr().out == "9.2.0\n"


@pytest.mark.parametrize("tag, version", [("v9.2.1", "9.2.0"), ("v9.2.0", "9.2.0.1"), ("v10.0.0", "1.0.0")])
def test_the_version_check_fails_when_the_manifest_differs_from_the_tag(tag, version, tmp_path, capsys):
    code = store_upload.main(["version", tag, str(store_zip(tmp_path, version))], {})

    printed = capsys.readouterr()
    assert code == 1 and printed.out == ""
    assert printed.err.startswith("::error::") and version in printed.err and tag in printed.err


@pytest.mark.parametrize("tag", ["9.2.0", "v9.2", "v9.2.0-beta", "latest", ""])
def test_the_version_check_refuses_a_tag_that_is_no_version(tag, tmp_path, capsys):
    assert store_upload.main(["version", tag, str(store_zip(tmp_path))], {}) == 1
    assert capsys.readouterr().err.startswith("::error::")


def test_the_version_check_fails_without_a_manifest_in_the_zip(tmp_path, capsys):
    path = tmp_path / "leer.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("background.js", "")

    assert store_upload.main(["version", "v9.2.0", str(path)], {}) == 1
    assert "manifest.json" in capsys.readouterr().err


def test_the_version_check_fails_when_the_zip_is_missing(tmp_path, capsys):
    assert store_upload.main(["version", "v9.2.0", str(tmp_path / "fehlt.zip")], {}) == 1
    assert capsys.readouterr().err.startswith("::error::")
