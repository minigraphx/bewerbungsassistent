"""The language the app speaks to the person (#414, G10, docs/design/sprachen.md).

`sprache(k)` is the one source for pages, scripts and, with #415, the server's messages. Until every page is translated
(#95, step 15) the switch stays off and the app speaks German whatever the person chose. For development and for
verifying an item, `BEWERBUNGSBEGLEITER_SPRACHE_VORSCHAU=1` turns it on: the app then speaks the stored app language.
"""
import functools
import os
import pathlib
from typing import Any

import language_settings

# Turned on once, with the last item of #95 (Andy, 23.11.2026).
SWITCH_ON = False
PREVIEW_ENV = "BEWERBUNGSBEGLEITER_SPRACHE_VORSCHAU"
GERMAN = language_settings.DEFAULT_APP


def is_on() -> bool:
    return SWITCH_ON or os.environ.get(PREVIEW_ENV) == "1"


def _stamp(path: pathlib.Path) -> int | None:
    try:
        return path.stat().st_mtime_ns
    except OSError:
        return None


@functools.lru_cache(maxsize=8)
def _stored(data_dir: pathlib.Path, stamp: int | None) -> str:
    return language_settings.app_language(data_dir)


def sprache(k: Any) -> str:
    """The app language for the data folder of `k`: de while the switch is off, else what `sprachen.yaml` says."""
    data_dir = getattr(k, "daten", None)
    if not is_on() or data_dir is None:
        return GERMAN
    folder = pathlib.Path(data_dir)
    return _stored(folder, _stamp(folder / language_settings.FILE))
