"""Tests never touch the real keychain."""
import os

os.environ["PYTHON_KEYRING_BACKEND"] = "keyring.backends.null.Keyring"
