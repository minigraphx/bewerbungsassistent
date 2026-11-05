"""What the person chose in the first step of the setup (MIN-369): a job or an apprenticeship, the form of address, RAV.

Stored in the data folder (`einrichtung.yaml`), so it moves with the person's files and Claude sees it too. Before
anything is chosen, the search profile says what is sought (an apprenticeship profile has „## Lehrbeginn“), the form
of address follows from it, and RAV stays as it was (on for jobs, off for apprenticeships): nothing changes for people
who set up the app earlier.

Three text sets follow from the choice: a job with Sie, a job with du, an apprenticeship with du.
"""
import dataclasses
import pathlib

import yaml

import search_plan
from dateien import schreibe_atomar

FILE = "einrichtung.yaml"
JOB = search_plan.KIND_JOB
APPRENTICESHIP = search_plan.KIND_APPRENTICESHIP
SIE = "sie"
DU = "du"
SOUGHT = (JOB, APPRENTICESHIP)
ADDRESSES = (SIE, DU)
HEADER = "# Einrichtung: was gesucht wird, Anrede, RAV. Geschrieben vom Bewerbungsassistenten.\n"
BAD_SOUGHT = "Bitte wählen: eine Stelle oder eine Lehrstelle."
BAD_ADDRESS = "Bitte wählen: mit Sie oder mit du."
BAD_RAV = "Bitte wählen, ob beim RAV gemeldet: Ja oder Nein."


@dataclasses.dataclass(frozen=True)
class Choice:
    sought: str
    address: str
    rav: bool
    chosen: bool = False  # False: derived from the search profile, nobody has chosen yet

    @property
    def text_set(self) -> str:
        return f"{self.sought}-{self.address}"

    def as_dict(self) -> dict:
        return {"gesucht": self.sought, "anrede": self.address, "rav": self.rav, "gewaehlt": self.chosen,
                "textsatz": self.text_set}


def _default(data_dir: pathlib.Path) -> Choice:
    sought = search_plan.kind_of_folder(data_dir)
    return Choice(sought, DU if sought == APPRENTICESHIP else SIE, sought != APPRENTICESHIP)


def parse(values) -> Choice:
    """A choice as the page sends it; ValueError with a German message. An apprenticeship is always du."""
    if not isinstance(values, dict):
        raise ValueError(BAD_SOUGHT)
    sought, address, rav = values.get("gesucht"), values.get("anrede"), values.get("rav")
    if sought not in SOUGHT:
        raise ValueError(BAD_SOUGHT)
    if sought == APPRENTICESHIP:
        address = DU
    elif address not in ADDRESSES:
        raise ValueError(BAD_ADDRESS)
    if not isinstance(rav, bool):
        raise ValueError(BAD_RAV)
    return Choice(sought, address, rav, chosen=True)


def load(data_dir: pathlib.Path) -> Choice:
    """The stored choice; without one (or with a broken file) what the search profile says."""
    path = data_dir / FILE
    try:
        stored = yaml.safe_load(path.read_text(encoding="utf-8")) if path.is_file() else None
        return parse(stored) if stored is not None else _default(data_dir)
    except (OSError, yaml.YAMLError, ValueError):
        return _default(data_dir)


def save(k, values) -> Choice:
    """Store a choice, with drafts before and after like every file in the data folder."""
    choice = parse(values)
    path = k.daten / FILE
    text = HEADER + yaml.safe_dump({"gesucht": choice.sought, "anrede": choice.address, "rav": choice.rav},
                                   allow_unicode=True, sort_keys=False)
    words = {JOB: "eine Stelle", APPRENTICESHIP: "eine Lehrstelle"}
    description = f"Einrichtung: {words[choice.sought]}, {'du' if choice.address == DU else 'Sie'}, RAV {'ja' if choice.rav else 'nein'}"
    k.mit_entwurf(path, description, lambda: schreibe_atomar(path, text.encode("utf-8")))
    return choice
