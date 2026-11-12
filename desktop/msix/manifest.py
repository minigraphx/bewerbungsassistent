"""Fill the package manifest of the MSIX trial (#255) for one variant (#256).

  python desktop/msix/manifest.py <template> <version> <variant> <output>

`standard` keeps what Windows does for every packaged app. `registry` declares the restricted capability
unvirtualizedResources and turns off the virtualization of registry writes, so the keys of the native messaging host
land in the real HKCU; `registry-und-dateien` also turns off the virtualization of writes to AppData.
"""
import pathlib
import sys

VARIANTS = ("standard", "registry", "registry-und-dateien")
DESKTOP6 = 'xmlns:desktop6="http://schemas.microsoft.com/appx/manifest/desktop/windows10/6"'
RESCAP = 'xmlns:rescap="http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities"'
IGNORABLE = 'IgnorableNamespaces="uap uap3 desktop rescap"'
# The desktop6 virtualization switches need Windows 10 version 2004.
MIN_VERSION = ('MinVersion="10.0.17763.0"', 'MinVersion="10.0.19041.0"')
FULL_TRUST = '<rescap:Capability Name="runFullTrust" />'


def _replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise ValueError(f"Vorlage passt nicht: {old!r} nicht genau einmal gefunden")
    return text.replace(old, new)


def fill(template: str, version: str, variant: str) -> str:
    if variant not in VARIANTS:
        raise ValueError(f"Unbekannte Variante {variant!r}, erlaubt: {', '.join(VARIANTS)}")
    text = _replace_once(template, "@VERSION@", f"{version}.0")
    if variant == "standard":
        return text
    switches = ["<desktop6:RegistryWriteVirtualization>disabled</desktop6:RegistryWriteVirtualization>"]
    if variant == "registry-und-dateien":
        switches.append("<desktop6:FileSystemWriteVirtualization>disabled</desktop6:FileSystemWriteVirtualization>")
    text = _replace_once(text, RESCAP, f"{DESKTOP6}\n         {RESCAP}")
    text = _replace_once(text, IGNORABLE, IGNORABLE.replace("rescap", "desktop6 rescap"))
    text = _replace_once(text, *MIN_VERSION)
    text = _replace_once(text, "  </Properties>", "".join(f"    {switch}\n" for switch in switches) + "  </Properties>")
    return _replace_once(text, FULL_TRUST, f'{FULL_TRUST}\n    <rescap:Capability Name="unvirtualizedResources" />')


def main(argv: list[str]) -> int:
    template, version, variant, output = argv
    pathlib.Path(output).write_text(fill(pathlib.Path(template).read_text(encoding="utf-8"), version, variant),
                                    encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
