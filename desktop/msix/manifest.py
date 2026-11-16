"""Fill the package manifest of the MSIX trial (#255) for one variant (#256), or of the Store package (#343).

  python desktop/msix/manifest.py <template> <version> <variant> <output>

`standard` keeps what Windows does for every packaged app. `registry` declares the restricted capability
unvirtualizedResources and turns off the virtualization of registry writes, so the keys of the native messaging host
land in the real HKCU; `registry-und-dateien` also turns off the virtualization of writes to AppData.
`store` is `registry-und-dateien` with the identity of Partner Center from the repo variables in the environment.
"""
import os
import pathlib
import re
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from xml.sax.saxutils import escape

VARIANTS = ("standard", "registry", "registry-und-dateien")
STORE = "store"
DESKTOP6 = 'xmlns:desktop6="http://schemas.microsoft.com/appx/manifest/desktop/windows10/6"'
RESCAP = 'xmlns:rescap="http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities"'
IGNORABLE = 'IgnorableNamespaces="uap uap3 desktop rescap"'
# The desktop6 virtualization switches need Windows 10 version 2004.
MIN_VERSION = ('MinVersion="10.0.17763.0"', 'MinVersion="10.0.19041.0"')
FULL_TRUST = '<rescap:Capability Name="runFullTrust" />'

IDENTITY_VARIABLES = ("MSIX_IDENTITY_NAME", "MSIX_PUBLISHER", "MSIX_PUBLISHER_DISPLAY_NAME")
# Only the Store package proven in #256 goes out: the native messaging host needs both switches.
STORE_VARIANT = "registry-und-dateien"
IDENTITY_NAME = re.compile(r"^[A-Za-z0-9.-]{3,50}$")
MAX_DISPLAY_NAME = 256
TRIAL_NAMES = {
    'Name="BewerbungsbegleiterVersuch"': 'Name="{name}"',
    'Publisher="CN=Bewerbungsbegleiter Versuch"': 'Publisher="{publisher}"',
    "<PublisherDisplayName>Bewerbungsbegleiter Versuch</PublisherDisplayName>":
        "<PublisherDisplayName>{publisher_display_name}</PublisherDisplayName>",
    "<DisplayName>Bewerbungsbegleiter (Versuch)</DisplayName>": "<DisplayName>Bewerbungsbegleiter</DisplayName>",
    'DisplayName="Bewerbungsbegleiter (Versuch)" Description="Bewerbungsbegleiter als MSIX, nur zum Versuch"':
        'DisplayName="Bewerbungsbegleiter" Description="Begleitet Bewerbungen von der Stellensuche bis zum Versand"',
}


@dataclass(frozen=True)
class Identity:
    name: str
    publisher: str
    publisher_display_name: str


# The placeholder of #255, for builds on main and manual runs before the variables exist.
PLACEHOLDER = Identity("BewerbungsbegleiterVersuch", "CN=Bewerbungsbegleiter Versuch", "Bewerbungsbegleiter Versuch")


class MissingIdentity(ValueError):
    """A release tag is built without the identity of Partner Center."""


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


def _checked(identity: Identity) -> Identity:
    if not IDENTITY_NAME.match(identity.name):
        raise ValueError("MSIX_IDENTITY_NAME passt nicht: 3 bis 50 Zeichen, nur Buchstaben, Ziffern, Punkt und Bindestrich")
    if not identity.publisher.startswith("CN="):
        raise ValueError("MSIX_PUBLISHER passt nicht: Er beginnt mit «CN=», wie in Partner Center angegeben")
    if len(identity.publisher_display_name) > MAX_DISPLAY_NAME:
        raise ValueError(f"MSIX_PUBLISHER_DISPLAY_NAME passt nicht: höchstens {MAX_DISPLAY_NAME} Zeichen")
    return identity


def store_identity(environ: Mapping[str, str]) -> Identity:
    """The identity from the repo variables; without them the placeholder, except on a release tag."""
    values = [environ.get(name, "").strip() for name in IDENTITY_VARIABLES]
    missing = [name for name, value in zip(IDENTITY_VARIABLES, values) if not value]
    if not missing:
        return _checked(Identity(*values))
    if environ.get("GITHUB_REF", "").startswith("refs/tags/v"):
        raise MissingIdentity(f"Variable fehlt für das Store-Paket: {', '.join(missing)}. In den Variablen des Repos "
                              "aus Partner Center eintragen (Produktidentität), dann den Job neu starten.")
    return PLACEHOLDER


def fill_store(template: str, version: str, identity: Identity) -> str:
    text = fill(template, version, STORE_VARIANT)
    values = {"name": identity.name, "publisher": escape(identity.publisher, {'"': "&quot;"}),
              "publisher_display_name": escape(identity.publisher_display_name)}
    for old, new in TRIAL_NAMES.items():
        text = _replace_once(text, old, new.format(**values))
    return text


def _store(template: str, version: str, environ: Mapping[str, str]) -> str | None:
    try:
        identity = store_identity(environ)
    except ValueError as error:
        print(f"::error::{error}")
        return None
    if identity == PLACEHOLDER:
        print("Platzhalter-Identität aus dem Versuch: Die Variablen für den Store fehlen, das Paket geht nicht in ein Release")
    return fill_store(template, version, identity)


def main(argv: list[str], environ: Mapping[str, str] = os.environ) -> int:
    template_path, version, variant, output = argv
    template = pathlib.Path(template_path).read_text(encoding="utf-8")
    text = _store(template, version, environ) if variant == STORE else fill(template, version, variant)
    if text is None:
        return 1
    pathlib.Path(output).write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
