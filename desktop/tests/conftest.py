"""Tests never touch the real keychain."""
import os
import pathlib

import pytest

os.environ["PYTHON_KEYRING_BACKEND"] = "keyring.backends.null.Keyring"

HERE = pathlib.Path(__file__).parent


@pytest.fixture(autouse=True)
def update_server(request, monkeypatch):
    """Every test talks to the fake update server of signed_update, signed with its test key (MIN-403).

    Only for tests in this folder: run together with other modules, pytest would apply it to theirs (#90).
    """
    if not request.path.is_relative_to(HERE):
        return
    import signed_update
    import updates
    monkeypatch.setenv(updates.URL_VARIABLE, signed_update.BASE)
    monkeypatch.setattr(updates.update_key, "PUBLIC_KEY", signed_update.PUBLIC_KEY)


TEST_CERTIFICATE_SHA1 = "0123456789ABCDEF0123456789ABCDEF01234567"  # invented: no app is signed with it


@pytest.fixture(autouse=True)
def signing_identity_registered(request, monkeypatch):
    """Every test sees a registered macOS signing identity, as a released app has (#213); some set their own."""
    if not request.path.is_relative_to(HERE):
        return
    import signing_identity
    monkeypatch.setattr(signing_identity, "CERTIFICATE_SHA1", TEST_CERTIFICATE_SHA1)
