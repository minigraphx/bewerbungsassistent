"""The extension carries the app version (#358).

The app copies the extension folder only when the manifest version changes (extension.py), a hand-loaded extension
reloads once per app version (erweiterung/lib/reload.js), and the stores take an update only with a higher version.
A manifest that stays behind ships none of the extension's changes, so every release bumps both together.
"""
import extension
import start
import version


def test_the_extension_manifest_carries_the_app_version():
    folder = extension.source(start.bundle_dir(), frozen=False)
    assert extension.version(folder) == version.VERSION, (
        "bump erweiterung/manifest.json together with desktop/version.py")
