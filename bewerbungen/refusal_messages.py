"""The refusals of lebenslauf as messages of the app: the letter (#453), the photo crop and the headings (#455), G10.

lebenslauf builds on its own and never imports the app, so `refusal.Refusal` carries its German template and values;
here they become a T, which the routes say in the app language. In German the message stays byte for byte.
"""
import contextlib
from typing import Iterator

import pfade  # noqa: F401  (makes the module lebenslauf importable)
import refusal
from ui_message import T


@contextlib.contextmanager
def in_app_language() -> Iterator[None]:
    """Any Refusal raised inside comes out as a ValueError with its message as T; other errors pass unchanged."""
    try:
        yield
    except refusal.Refusal as error:
        raise ValueError(T(error.template, **error.values)) from error
