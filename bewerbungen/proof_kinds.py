"""Which kind a certificate or reference is (G63, #282): Arbeitszeugnis, Diplom or Zertifikat.

References keep their own folder, since they go along with every application. Diplomas share the folder of the
certificates: both are chosen per application and packed into its ZIP, so the choice and the ZIP stay as they were.
What tells a diploma from a certificate is recorded per file in `dokumente/arten.yaml`; a file without an entry keeps
the kind its folder gave it, so nothing filed before changes until the person changes it.
"""
import pathlib

import yaml

from dateien import schreibe_atomar

FILE = "dokumente/arten.yaml"
DIPLOMA = "diplom"
RECORDED = (DIPLOMA,)  # kinds that share a folder with another one and so need an entry
UNREADABLE = f"Die Liste der Dateiarten ({FILE}) lässt sich nicht lesen. Unter „Entwürfe und Versionen“ liegt der Stand davor."


def load(data_dir: pathlib.Path) -> dict[str, str]:
    """The recorded kind per file, relative to the data folder; entries of another form are left out."""
    path = data_dir / FILE
    if not path.is_file():
        return {}
    try:
        found = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as error:
        raise ValueError(UNREADABLE) from error
    if found is None:
        return {}
    if not isinstance(found, dict):
        raise ValueError(UNREADABLE)
    return {rel: kind for rel, kind in found.items() if isinstance(rel, str) and kind in RECORDED}


def with_kind(recorded: dict[str, str], rel: str, kind: str) -> dict[str, str]:
    """A new record in which this file has this kind; a kind its folder already says needs no entry."""
    others = {path: known for path, known in recorded.items() if path != rel}
    return {**others, rel: kind} if kind in RECORDED else others


def without(recorded: dict[str, str], rel: str) -> dict[str, str]:
    return {path: known for path, known in recorded.items() if path != rel}


def save(data_dir: pathlib.Path, recorded: dict[str, str]) -> None:
    text = yaml.safe_dump(dict(sorted(recorded.items())), allow_unicode=True, sort_keys=False)
    schreibe_atomar(data_dir / FILE, text.encode("utf-8"))
