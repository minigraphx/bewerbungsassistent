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
