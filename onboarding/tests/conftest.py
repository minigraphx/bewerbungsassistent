"""Shared fixtures for onboarding tests; the cases of cases.json are in form_cases.py."""
import json
import os

import pytest

from form_cases import ROOT

os.environ["PYTHON_KEYRING_BACKEND"] = "keyring.backends.null.Keyring"  # tests never touch the real keychain


@pytest.fixture
def form():
    return json.loads((ROOT / "form.json").read_text(encoding="utf-8"))
