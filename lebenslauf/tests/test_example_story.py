"""The invented example tells one consistent story (#437).

The picture docs/bilder/beispiel-unterlagen.jpg is built from these files, and the website shows it: the
letter must go to a firm outside the CV, name only firms and years the CV holds, name no real institution
and open without a stock phrase.
"""
import re

import yaml

import build

DATA = build.ROOT / "data"
BUILDING_BLOCKS = build.ROOT.parent / "vorlagen" / "anschreiben" / "bausteine.md"
EXAMPLE_FILES = (DATA / "beispiel.yaml", DATA / "anschreiben-beispiel.yaml", DATA / "dossier-beispiel.yaml",
                 BUILDING_BLOCKS)

# Openers the app's tone advises against; compared case-insensitively with the start of the letter
STOCK_OPENERS = ("mit grossem interesse", "mit großem interesse", "mit interesse", "hiermit bewerbe ich mich",
                 "hiermit sende ich", "mit freude habe ich", "aufgrund ihrer stellenausschreibung",
                 "auf ihre stellenausschreibung", "bezugnehmend auf", "ich bewerbe mich", "gerne bewerbe ich mich",
                 "mit diesem schreiben", "ihre stellenanzeige hat")
# A word that marks a stock opening wherever it stands in the first sentence
STOCK_WORDS = ("hiermit",)
REAL_INSTITUTIONS = ("Volkshochschule",)

# A firm: capitalised words ending in a legal form; a school: one word ending in -schule
FIRM = re.compile(r"(?:[A-ZÄÖÜ][\w.&-]*\s)+(?:AG|GmbH|SA|Sàrl|KG)\b")
SCHOOL = re.compile(r"\b[A-ZÄÖÜ][\w-]*schule\b")
YEAR = re.compile(r"\b(?:19|20)\d\d\b")
BLOCK_FIRM = re.compile(r"^- \*\*([^,*(]+)")


def load(name: str) -> dict:
    return yaml.safe_load((DATA / name).read_text(encoding="utf-8"))


def cv_organisations(cv: dict) -> set[str]:
    stations = cv.get("work", []) + cv.get("teaching", []) + cv.get("volunteer", [])
    names = {s["name"] for s in stations if s.get("name")}
    names |= {e["institution"] for e in cv.get("education", []) if e.get("institution")}
    return names


def cv_years(cv: dict) -> set[str]:
    return set(YEAR.findall(yaml.safe_dump(cv, allow_unicode=True)))


def named_in(text: str) -> list[str]:
    return [m.strip() for m in FIRM.findall(text)] + SCHOOL.findall(text)


def known(name: str, organisations: set[str]) -> bool:
    """A name counts as known when it ends in one from the CV, so «Bei der Beispiel AG» reads as «Beispiel AG»."""
    return any(name == org or name.endswith(" " + org) for org in organisations)


def first_sentence(text: str) -> str:
    return re.split(r"(?<=[.!?:])\s", " ".join(text.split()), maxsplit=1)[0]


def test_the_letter_goes_to_a_firm_outside_the_cv():
    target = load("anschreiben-beispiel.yaml")["empfaenger"][0]
    assert target not in cv_organisations(load("beispiel.yaml"))


def test_every_firm_and_school_the_letter_names_is_in_the_cv():
    organisations = cv_organisations(load("beispiel.yaml"))
    named = named_in(load("anschreiben-beispiel.yaml")["text"])
    assert named, "the letter names no firm from the CV"
    assert [name for name in named if not known(name, organisations)] == []


def test_every_year_the_letter_names_is_in_the_cv():
    years = YEAR.findall(load("anschreiben-beispiel.yaml")["text"])
    assert set(years) <= cv_years(load("beispiel.yaml"))


def test_the_building_blocks_name_only_stations_of_the_cv():
    cv = load("beispiel.yaml")
    organisations = cv_organisations(cv)
    lines = BUILDING_BLOCKS.read_text(encoding="utf-8").splitlines()
    firms = [m.group(1).strip() for line in lines if (m := BLOCK_FIRM.match(line))]
    assert firms, "the building blocks name no station"
    assert [firm for firm in firms if firm not in organisations] == []
    assert set(YEAR.findall("\n".join(lines))) <= cv_years(cv)


def test_the_example_names_no_real_institution():
    found = [(path.name, word) for path in EXAMPLE_FILES for word in REAL_INSTITUTIONS
             if word in path.read_text(encoding="utf-8")]
    assert found == []


def test_the_letter_opens_without_a_stock_phrase():
    opening = first_sentence(load("anschreiben-beispiel.yaml")["text"]).lower()
    assert not opening.startswith(STOCK_OPENERS), opening
    assert not any(re.search(rf"\b{word}\b", opening) for word in STOCK_WORDS), opening


def test_the_stock_phrase_check_can_fail():
    assert first_sentence("Mit grossem Interesse habe ich Ihr Inserat gelesen. Weiter.").lower().startswith(
        STOCK_OPENERS)
    assert not known("Beispiel GmbH", {"Beispiel AG"})
    assert named_in("Bei der Beispiel GmbH und an der Muster-Abendschule.") == ["Beispiel GmbH", "Muster-Abendschule"]
