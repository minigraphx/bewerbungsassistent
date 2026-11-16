"""Colour and mark of one CV (G77, #295): chosen in „Lebenslauf erstellen“, passed to build.py as --akzent and --zeichen.

The CV designs Zweispaltig and Einspaltig draw the colour on their lines and headings and the mark small in the footer
of every page. Without the options a CV keeps its design's colours and has no mark, even when cv.yaml holds a mark
and colour for the dossier (G18). All data is invented.
"""
import json
import pathlib
import shutil

import pytest
import typst
import yaml
from pypdf import PdfReader

import build
import fill_record
from dossier_samples import example_cv
from typst_root import typst_root

HERE = pathlib.Path(__file__).parent
DESIGNS = ("zweispaltig", "einspaltig")
OWN_ACCENTS = {"zweispaltig": "#38495d", "einspaltig": "#2f5d4a"}
WINE = "#7a2e3a"


def built(folder: pathlib.Path, design: str, *options: str, basics: dict | None = None,
          files: dict | None = None) -> dict:
    """Builds the example CV (with extra basics and files beside it) and reads back marks, accent and pages."""
    folder.mkdir(parents=True)
    cv = example_cv()
    cv["basics"] = {**cv["basics"], **(basics or {})}
    cv["basics"].pop("image", None)
    for name, source in (files or {}).items():
        shutil.copy(source, folder / name)
    (folder / "cv.yaml").write_text(yaml.safe_dump(cv, allow_unicode=True), encoding="utf-8")
    build_dir = folder / "build"
    pdf = build.main([str(folder / "cv.yaml"), "--theme", design, *options, "--build-dir", str(build_dir),
                      "-o", str(folder / "cv.pdf")])
    data = json.loads((build_dir / "cv.json").read_text(encoding="utf-8"))
    extra = [folder / name for name in (files or {})]
    root = typst_root(build_dir, [build.ROOT / "themes", *extra])
    # laid out like the PDF: with the density the build chose
    density = {f"density-{part}": str(level) for part, level in (fill_record.read(pdf) or {}).items()}

    def query(selector: str) -> list:
        return json.loads(typst.query(str(root.locate(build.ROOT / "themes" / design / "main.typ")), selector,
                                      field="value", root=str(root.path), font_paths=[str(build.ROOT / "fonts")],
                                      sys_inputs={"data": root.typst_path(build_dir / "cv.json"), "lang": "de",
                                                  **density}))

    return {"data": data, "marks": query("<dossier-mark>"), "accent": query("<cv-accent>"),
            "pages": len(PdfReader(pdf).pages)}


@pytest.fixture
def make(tmp_path):
    counter = iter(range(100))
    return lambda *args, **kwargs: built(tmp_path / f"run{next(counter)}", *args, **kwargs)


@pytest.mark.parametrize("design", DESIGNS)
def test_without_a_choice_the_cv_keeps_its_colours_and_has_no_mark(make, design):
    found = make(design)

    assert "x-aussehen" not in found["data"]
    assert found["marks"] == []
    assert found["accent"] == [OWN_ACCENTS[design]]


@pytest.mark.parametrize("design", DESIGNS)
def test_the_dossier_choice_in_cv_yaml_does_not_change_other_cvs(make, design):
    found = make(design, basics={"x-zeichen": "block", "x-akzent": WINE})

    assert found["marks"] == [] and found["accent"] == [OWN_ACCENTS[design]]


@pytest.mark.parametrize("design", DESIGNS)
def test_a_chosen_colour_is_the_accent_of_the_cv(make, design):
    found = make(design, "--akzent", WINE.upper())

    assert found["accent"] == [WINE]
    assert found["data"]["x-aussehen"] == {"akzent": WINE}


@pytest.mark.parametrize("design", DESIGNS)
def test_a_chosen_mark_stands_small_in_the_footer_of_every_page(make, design):
    found = make(design, "--zeichen", "ring")

    assert found["marks"] == [{"variant": "ring", "at": "cv-footer"}] * found["pages"]
    assert found["data"]["x-aussehen"]["zeichen"]["monogram"] == "EB"


def test_passend_for_mark_and_colour_is_the_cv_as_it_was(make):
    found = make("zweispaltig", "--zeichen", "passend", "--akzent", "passend")

    assert "x-aussehen" not in found["data"] and found["marks"] == []


def test_the_own_logo_of_cv_yaml_can_be_the_mark(make):
    found = make("einspaltig", "--zeichen", "logo", basics={"x-logo": "logo.png"}, files={"logo.png": HERE / "halbe.png"})

    assert found["marks"] == [{"variant": "logo", "at": "cv-footer"}] * found["pages"]


def test_without_its_logo_file_the_logo_mark_is_left_out(make):
    found = make("zweispaltig", "--zeichen", "logo", basics={"x-logo": "fehlt.png"})

    assert found["marks"] == [] and "x-aussehen" not in found["data"]


def test_a_colour_that_does_not_read_well_is_refused(tmp_path):
    with pytest.raises(ValueError, match="Zu hell"):
        built(tmp_path / "run", "zweispaltig", "--akzent", "#f0f0f0")
