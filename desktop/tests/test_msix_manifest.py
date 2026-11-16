"""The package manifest of the MSIX trial (#255, #256): the variant without registry virtualization."""
import pathlib
import xml.etree.ElementTree as ET

import pytest

from msix import manifest

TEMPLATE = (pathlib.Path(__file__).resolve().parents[1] / "msix" / "AppxManifest.xml").read_text(encoding="utf-8")
FOUNDATION = "{http://schemas.microsoft.com/appx/manifest/foundation/windows10}"
RESCAP = "{http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities}"
DESKTOP6 = "{http://schemas.microsoft.com/appx/manifest/desktop/windows10/6}"


def capabilities(root: ET.Element) -> list[str]:
    return [element.get("Name") for element in root.find(f"{FOUNDATION}Capabilities")]


def test_the_standard_variant_keeps_virtualization_and_asks_only_for_full_trust():
    root = ET.fromstring(manifest.fill(TEMPLATE, "0.2.19", "standard"))

    assert root.find(f"{FOUNDATION}Identity").get("Version") == "0.2.19.0"
    assert capabilities(root) == ["runFullTrust"]
    assert root.find(f"{FOUNDATION}Properties/{DESKTOP6}RegistryWriteVirtualization") is None


def test_the_registry_variant_disables_only_registry_virtualization():
    root = ET.fromstring(manifest.fill(TEMPLATE, "0.2.19", "registry"))
    properties = root.find(f"{FOUNDATION}Properties")

    assert capabilities(root) == ["runFullTrust", "unvirtualizedResources"]
    assert properties.find(f"{DESKTOP6}RegistryWriteVirtualization").text == "disabled"
    assert properties.find(f"{DESKTOP6}FileSystemWriteVirtualization") is None
    assert "desktop6" in root.get("IgnorableNamespaces").split()


def test_the_files_variant_disables_file_virtualization_too():
    properties = ET.fromstring(manifest.fill(TEMPLATE, "0.2.19", "registry-und-dateien")).find(f"{FOUNDATION}Properties")

    assert properties.find(f"{DESKTOP6}RegistryWriteVirtualization").text == "disabled"
    assert properties.find(f"{DESKTOP6}FileSystemWriteVirtualization").text == "disabled"


def test_an_unknown_variant_is_refused():
    with pytest.raises(ValueError):
        manifest.fill(TEMPLATE, "0.2.19", "alles")


# The Store package (#343, G6): the variant #256 proved, with the real identity from the repo variables.
UAP3 = "{http://schemas.microsoft.com/appx/manifest/uap/windows10/3}"
DESKTOP = "{http://schemas.microsoft.com/appx/manifest/desktop/windows10}"
REAL = {"MSIX_IDENTITY_NAME": "12345Erfunden.Bewerbungsbegleiter",
        "MSIX_PUBLISHER": "CN=00000000-0000-0000-0000-000000000000",
        "MSIX_PUBLISHER_DISPLAY_NAME": "Erfundene Firma & Co"}
TAG = {"GITHUB_REF": "refs/tags/v0.3.0"}
MAIN = {"GITHUB_REF": "refs/heads/main"}


def store_root(environ: dict) -> ET.Element:
    return ET.fromstring(manifest.fill_store(TEMPLATE, "0.3.0", manifest.store_identity(environ)))


def test_the_store_package_carries_the_identity_from_the_variables():
    root = store_root({**REAL, **TAG})
    identity = root.find(f"{FOUNDATION}Identity")

    assert identity.get("Name") == "12345Erfunden.Bewerbungsbegleiter"
    assert identity.get("Publisher") == "CN=00000000-0000-0000-0000-000000000000"
    assert identity.get("Version") == "0.3.0.0"
    assert root.find(f"{FOUNDATION}Properties/{FOUNDATION}PublisherDisplayName").text == "Erfundene Firma & Co"
    assert "Versuch" not in root.find(f"{FOUNDATION}Properties/{FOUNDATION}DisplayName").text


def test_the_store_package_turns_off_both_virtualizations_with_the_restricted_capability():
    root = store_root({**REAL, **TAG})
    properties = root.find(f"{FOUNDATION}Properties")

    assert capabilities(root) == ["runFullTrust", "unvirtualizedResources"]
    assert properties.find(f"{DESKTOP6}RegistryWriteVirtualization").text == "disabled"
    assert properties.find(f"{DESKTOP6}FileSystemWriteVirtualization").text == "disabled"


def test_the_store_package_declares_the_link_and_the_alias():
    extensions = store_root({**REAL, **TAG}).find(f"{FOUNDATION}Applications/{FOUNDATION}Application/{FOUNDATION}Extensions")
    by_category = {extension.get("Category"): extension for extension in extensions}

    assert by_category["windows.protocol"].find(f"{UAP3}Protocol").get("Name") == "bewerbungsbegleiter"
    alias = by_category["windows.appExecutionAlias"].find(f"{UAP3}AppExecutionAlias/{DESKTOP}ExecutionAlias")
    assert alias.get("Alias") == "bewerbungsbegleiter.exe"


def test_a_tag_without_a_variable_names_the_missing_one():
    environ = {**REAL, **TAG, "MSIX_PUBLISHER": ""}

    with pytest.raises(manifest.MissingIdentity, match="MSIX_PUBLISHER") as refused:
        manifest.store_identity(environ)
    assert "MSIX_IDENTITY_NAME" not in str(refused.value)


def test_main_without_the_variables_falls_back_to_the_trial_identity():
    root = store_root(MAIN)
    identity = root.find(f"{FOUNDATION}Identity")

    assert (identity.get("Name"), identity.get("Publisher")) == ("BewerbungsbegleiterVersuch", "CN=Bewerbungsbegleiter Versuch")
    assert capabilities(root) == ["runFullTrust", "unvirtualizedResources"]


@pytest.mark.parametrize("variable, value", [("MSIX_IDENTITY_NAME", "mit Leerzeichen"),
                                             ("MSIX_PUBLISHER", "O=ohne CN")])
def test_a_malformed_identity_is_refused(variable, value):
    with pytest.raises(ValueError, match=variable):
        manifest.store_identity({**REAL, **TAG, variable: value})


def test_the_command_fails_on_a_tag_and_names_the_variable(tmp_path, capsys):
    template = tmp_path / "AppxManifest.xml"
    template.write_text(TEMPLATE, encoding="utf-8")
    output = tmp_path / "out.xml"

    code = manifest.main([str(template), "0.3.0", "store", str(output)], environ=TAG)

    assert code == 1
    assert not output.exists()
    out = capsys.readouterr().out
    assert out.startswith("::error::")
    assert all(name in out for name in manifest.IDENTITY_VARIABLES)


def test_the_command_writes_the_store_manifest(tmp_path):
    template = tmp_path / "AppxManifest.xml"
    template.write_text(TEMPLATE, encoding="utf-8")
    output = tmp_path / "out.xml"

    assert manifest.main([str(template), "0.3.0", "store", str(output)], environ={**REAL, **TAG}) == 0
    assert ET.fromstring(output.read_text(encoding="utf-8")).find(f"{FOUNDATION}Identity").get("Name") == REAL["MSIX_IDENTITY_NAME"]
