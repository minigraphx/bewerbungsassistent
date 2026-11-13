"""No nearly empty last page and no lone headings, in every design and part (G49, G50, #236).

All CVs and letters are invented (page_fill_samples). The pages are measured in the PDF with pdftotext -bbox-layout,
not with the build's own markers, so the test sees what a reader sees.
"""
import pytest
import yaml

import anschreiben
import build
import dossier
from page_fill_samples import (CV_BODY, LETTER_BODY, MIN_BODY_SIZE, MIN_FILL_RULE, content_lines, cv_of_length,
                               example_cv, last_page_fill, letter_of_length, lone_headings, page_count,
                               section_pages, text_sizes, thin_continuations)
from dossier_samples import flat, pdftotext

SINGLE = ("zweispaltig", "einspaltig")
DOSSIER = ("dossier-siegel", "dossier-raster", "dossier-register")
DESIGNS = SINGLE + DOSSIER
ONE_COLUMN = ("einspaltig",) + DOSSIER  # sections follow each other, so a section's pages can be read in order
CV_LENGTHS = (0, 12, 20, 24, 32)  # extra lines of experience over the example CV; 0 has none of CV_BODY
LETTER_LENGTHS = (5, 7, 9)  # extra paragraphs over the example letter
# The lengths at which the designs as drawn put only their last section or two on a new page
SPILL = {"zweispaltig": 0, "einspaltig": 24, "dossier-siegel": 24, "dossier-raster": 24, "dossier-register": 20}


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    """Builds each design and length once: the documents with the page range of the part that was asked for."""
    cache = {}

    def _built(kind: str, design: str, length: int) -> dict:
        key = (kind, design, length)
        if key not in cache:
            folder = tmp_path_factory.mktemp(f"{kind}-{design}-{length}")
            cache[key] = _build(folder, kind, design, length)
        return cache[key]

    return _built


def _build(folder, kind: str, design: str, length: int) -> dict:
    cv = cv_of_length(length) if kind == "cv" else example_cv()
    letter = letter_of_length(length if kind == "letter" else 0)
    (folder / "cv.yaml").write_text(yaml.safe_dump(cv, allow_unicode=True), encoding="utf-8")
    (folder / "brief.yaml").write_text(yaml.safe_dump({**letter, "lebenslauf": "cv.yaml"}, allow_unicode=True),
                                       encoding="utf-8")
    if design in SINGLE:
        if kind == "cv":
            pdf = build.main([str(folder / "cv.yaml"), "--theme", design, "--build-dir", str(folder / "build"),
                              "-o", str(folder / "cv.pdf")])
        else:
            pdf = anschreiben.main([str(folder / "brief.yaml"), "--theme", design, "--build-dir",
                                    str(folder / "build"), "-o", str(folder / "brief.pdf")])
        return {"documents": {kind: (pdf, 1, None)}, "result": None}
    (folder / "dossier.yaml").write_text(yaml.safe_dump({"lebenslauf": "cv.yaml", "anschreiben": "brief.yaml"}),
                                         encoding="utf-8")
    result = dossier.main([str(folder / "dossier.yaml"), "--theme", design, "--build-dir", str(folder / "build"),
                           "--out-dir", str(folder / "out")])
    letter_pages = page_count(result.letter)
    # The dossier: cover, the letter, then the CV
    in_dossier = (result.dossier, letter_pages + 2, None) if kind == "cv" else (result.dossier, 2, letter_pages + 1)
    own = result.cv if kind == "cv" else result.letter
    return {"documents": {kind: (own, 1, None), f"dossier-{kind}": in_dossier}, "result": result}


def _documents(built, kind: str, design: str, length: int):
    return built(kind, design, length)["documents"].items()


# G49: the last page is at least a third full


@pytest.mark.parametrize("design", DESIGNS)
def test_a_cv_whose_last_section_spills_over_still_fills_its_last_page(built, design):
    for name, (pdf, first, last) in _documents(built, "cv", design, SPILL[design]):
        fill = last_page_fill(pdf, first, last)
        assert fill is None or fill >= MIN_FILL_RULE, f"{design} {name}: last page {fill:.0%} full"


@pytest.mark.parametrize("design", DESIGNS)
def test_no_content_is_removed_to_fill_the_pages(built, design):
    cv = cv_of_length(SPILL[design])
    for name, (pdf, first, last) in _documents(built, "cv", design, SPILL[design]):
        text = flat(pdftotext(pdf))
        for station in cv["work"]:
            assert station["position"] in text, f"{design} {name}: {station['position']} missing"
        for project in cv["projects"]:
            assert project["name"] in text, f"{design} {name}: {project['name']} missing"


@pytest.mark.parametrize("design", DESIGNS)
@pytest.mark.parametrize("length", CV_LENGTHS)
def test_the_last_page_of_a_cv_is_at_least_a_third_full(built, design, length):
    for name, (pdf, first, last) in _documents(built, "cv", design, length):
        fill = last_page_fill(pdf, first, last)
        assert fill is None or fill >= MIN_FILL_RULE, f"{design} {name}: last page {fill:.0%} full"


@pytest.mark.parametrize("design", DESIGNS)
@pytest.mark.parametrize("length", LETTER_LENGTHS)
def test_the_last_page_of_a_letter_is_at_least_a_third_full(built, design, length):
    for name, (pdf, first, last) in _documents(built, "letter", design, length):
        fill = last_page_fill(pdf, first, last)
        assert fill is None or fill >= MIN_FILL_RULE, f"{design} {name}: last page {fill:.0%} full"


# G49: the smaller of the two fixes


def _fill_at(result, file: str, part: str, level: int):
    import page_fill
    inputs = {**result.inputs[file], f"density-{part}": str(level)}
    markers = page_fill.markers(str(result.root.locate(result.entries[file])), str(result.root.path),
                                [str(build.ROOT / "fonts")], inputs)
    return page_fill.measure(markers, part)


def _assert_smallest_fix(result, file: str, part: str) -> int:
    """The chosen level works, and no smaller change of either kind would have reached as far."""
    import page_fill
    level = int(result.inputs[file][f"density-{part}"])
    drawn = _fill_at(result, file, part, 0)
    chosen = _fill_at(result, file, part, level)
    assert chosen.enough
    bar = page_fill.AIM if chosen.fills(page_fill.AIM) else page_fill.MIN_FILL
    if level > 0:
        assert chosen.pages < drawn.pages
    if level < 0:
        assert chosen.pages == drawn.pages
    for smaller in range(1, abs(level)):
        tighter, wider = _fill_at(result, file, part, smaller), _fill_at(result, file, part, -smaller)
        assert not (tighter.pages < drawn.pages and tighter.fills(bar)), f"level {smaller} would have done"
        assert not (wider.pages == drawn.pages and wider.fills(bar)), f"level {-smaller} would have done"
    return level


def test_a_letter_that_just_spills_is_tightened_onto_one_page(built):
    result = built("letter", "dossier-raster", 5)["result"]
    assert page_count(result.letter) == 1
    assert _assert_smallest_fix(result, "letter", "letter") > 0


def test_a_letter_with_a_nearly_empty_second_page_gets_more_space(built):
    result = built("letter", "dossier-raster", 7)["result"]
    assert page_count(result.letter) == 2
    assert _assert_smallest_fix(result, "letter", "letter") < 0


def _assert_smallest_fit(result, file: str, part: str) -> int:
    """Over its page limit (G51), the part takes the smallest tightening that fits, unless that leaves the last page
    nearly empty and a tighter one does not."""
    import page_fill
    level = int(result.inputs[file][f"density-{part}"])
    limit = page_fill.LIMITS[part]
    chosen = _fill_at(result, file, part, level)
    assert level > 0 and chosen.pages <= limit, f"level {level}: {chosen.pages} pages"
    for smaller in range(1, level):
        fill = _fill_at(result, file, part, smaller)
        assert not (fill.pages <= limit and fill.fills(page_fill.AIM)), f"level {smaller} would have done"
    return level


@pytest.mark.parametrize("design", DOSSIER)
def test_the_spilling_cv_takes_the_smaller_fix(built, design):
    """Within the page limit the smaller fix of G49; over it the smallest tightening that fits (G51)."""
    import page_fill
    result = built("cv", design, SPILL[design])["result"]
    if _fill_at(result, "cv", "cv", 0).pages > page_fill.LIMITS["cv"]:
        _assert_smallest_fit(result, "cv", "cv")
    else:
        _assert_smallest_fix(result, "cv", "cv")



# G53: body text stays at 10 pt or more, also where page fill tightens


@pytest.mark.parametrize("design", DESIGNS)
@pytest.mark.parametrize("kind, lengths, marker", [("cv", CV_LENGTHS[1:], CV_BODY), ("letter", LETTER_LENGTHS, LETTER_BODY)])
def test_body_text_is_never_smaller_than_ten_points(built, design, kind, lengths, marker):
    for length in lengths:
        for name, (pdf, first, last) in _documents(built, kind, design, length):
            sizes = text_sizes(pdf, marker, first, last)
            assert sizes, f"{design} {name} {length}: no body text found"
            assert min(sizes) >= MIN_BODY_SIZE, f"{design} {name} {length}: body text at {min(sizes)} pt"


# G50: headings with their content, short sections together


@pytest.mark.parametrize("design", DESIGNS)
@pytest.mark.parametrize("length", CV_LENGTHS)
def test_no_heading_ends_a_page_and_no_continuation_is_a_single_line(built, design, length):
    for name, (pdf, first, last) in _documents(built, "cv", design, length):
        content = content_lines(pdf, first, last)
        assert not lone_headings(content), f"{design} {name}: {lone_headings(content)}"
        assert not thin_continuations(content), f"{design} {name}: {thin_continuations(content)}"


@pytest.mark.parametrize("design", ONE_COLUMN)
@pytest.mark.parametrize("length", CV_LENGTHS)
def test_languages_and_interests_stay_on_one_page(built, design, length):
    for name, (pdf, first, last) in _documents(built, "cv", design, length):
        content = content_lines(pdf, first, last)
        for heading in ("Sprachen", "Interessen"):
            assert len(section_pages(content, heading)) <= 1, f"{design} {name}: {heading} split"
