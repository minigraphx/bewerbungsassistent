"""Tests never touch the real keychain."""
import os

import pytest

os.environ["PYTHON_KEYRING_BACKEND"] = "keyring.backends.null.Keyring"


@pytest.fixture(autouse=True)
def update_server(monkeypatch):
    """Every test talks to the fake update server of signed_update, signed with its test key (MIN-403)."""
    import signed_update
    import updates
    monkeypatch.setenv(updates.URL_VARIABLE, signed_update.BASE)
    monkeypatch.setattr(updates.update_key, "PUBLIC_KEY", signed_update.PUBLIC_KEY)
