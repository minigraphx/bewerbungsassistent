"""The tags already in a data folder, as suggestions on the page „Meine Angaben“ (#161, G24).

Tags choose per job what goes into the CV (lebenslauf/README.md, „Zuschnitt pro Stelle“). They stand on entries and
highlights of cv.yaml, on the variants in varianten.yaml and on the tailorings under jobs/. Only what passes the rules
of the form comes back, each tag once; a file that cannot be read adds nothing and keeps the page from nothing.
"""
import logging
import pathlib
import re

import yaml

log = logging.getLogger(__name__)

FILES = ("cv.yaml", "varianten.yaml")
JOBS = "jobs"
JOB_FILES = "*.yaml"
TAGS = "tags"
MAX_TAGS = 500
MAX_DEPTH = 20


def known_tags(folder: pathlib.Path, form: dict) -> list[str]:
    """Every tag of the data folder once, sorted without regard to case; at most MAX_TAGS."""
    pattern = re.compile(form["formats"]["tag"]["pattern"])
    limit = form["limits"]["tag"]
    jobs = sorted((folder / JOBS).glob(JOB_FILES)) if (folder / JOBS).is_dir() else []
    found = {tag.strip() for path in [*(folder / name for name in FILES), *jobs] for tag in _tags_in(_read(path))}
    valid = [tag for tag in found if len(tag) <= limit and pattern.fullmatch(tag)]
    return sorted(valid, key=lambda tag: (tag.casefold(), tag))[:MAX_TAGS]


def _read(path: pathlib.Path) -> object:
    if not path.is_file():
        return None
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as error:
        log.warning("Tags aus %s nicht lesbar: %s", path.name, error)
        return None


def _tags_in(value: object, depth: int = 0) -> list[str]:
    """The text tags under every key "tags", at any depth."""
    if depth > MAX_DEPTH:
        return []
    if isinstance(value, list):
        return [tag for item in value for tag in _tags_in(item, depth + 1)]
    if not isinstance(value, dict):
        return []
    own = value.get(TAGS)
    tags = [tag for tag in own if isinstance(tag, str)] if isinstance(own, list) else []
    return tags + [tag for key, item in value.items() if key != TAGS for tag in _tags_in(item, depth + 1)]
