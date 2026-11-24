"""The refusals of lebenslauf/anschreiben.py as messages of the app (#453, G10).

lebenslauf builds on its own and never imports the app, so `anschreiben.LetterError` carries its German template and
values; here they become a T, which the routes say in the app language. In German the message stays byte for byte.
"""
import contextlib
from typing import Iterator

import pfade  # noqa: F401  (makes the module lebenslauf importable)
import anschreiben
from ui_message import T


@contextlib.contextmanager
def in_app_language() -> Iterator[None]:
    """Any LetterError raised inside comes out as a ValueError with its message as T; other errors pass unchanged."""
    try:
        yield
    except anschreiben.LetterError as error:
        raise ValueError(T(error.template, **error.values)) from error
