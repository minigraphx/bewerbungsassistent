"""The label of every date field names each form the hint accepts (#298, G30).

Since #181 a date may be a year, a year and month or a full date; the format hint gives an example of each.
A label that names fewer forms tells the person a full date is not allowed.
"""
import json
import re
from collections.abc import Iterator

import pytest

from form_cases import ROOT

FORM = json.loads((ROOT / "form.json").read_text(encoding="utf-8"))
APP_PAGE = ROOT.parent / "bewerbungen" / "seiten" / "angaben.html"

# how a label names the form of each example in the hint, by the shape of the example
FORM_NAMES = {
    r"[0-9]{4}": "Jahr",
    r"[0-9]{4}-[0-9]{2}": "Jahr-Monat",
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}": "ganzes Datum",
}


def names_in_hint(form: dict) -> list[str]:
    examples = re.findall(r"[0-9]{4}(?:-[0-9]{2}){0,2}", form["formats"]["date"]["example"])
    return [name for example in examples for shape, name in FORM_NAMES.items() if re.fullmatch(shape, example)]


def date_labels(form: dict) -> Iterator[tuple[str, str]]:
    for section in form["sections"]:
        for field in section.get("fields", []):
            if field.get("format") != "date":
                continue
            label = field["label"]
            for text in label.values() if isinstance(label, dict) else [label]:
                yield f"{section['id']}.{field['id']}", text


def embedded_form(page: str) -> dict:
    match = re.search(r'<script type="application/json" id="form-definition">(.*?)</script>', page, re.S)
    return json.loads(match.group(1))


def test_the_hint_gives_a_year_a_month_and_a_full_date() -> None:
    assert names_in_hint(FORM) == ["Jahr", "Jahr-Monat", "ganzes Datum"]


@pytest.mark.parametrize("path,label", list(date_labels(FORM)))
def test_each_date_label_names_every_form_of_the_hint(path: str, label: str) -> None:
    missing = [name for name in names_in_hint(FORM) if name not in label]

    assert not missing, f"{path}: „{label}“ nennt {missing} nicht"


def test_the_stations_show_the_full_labels_on_meine_angaben() -> None:
    shown = dict(date_labels(embedded_form(APP_PAGE.read_text(encoding="utf-8"))))

    for path in ("work.startDate", "work.endDate", "teaching.startDate", "teaching.endDate"):
        assert "ganzes Datum" in shown[path], path
