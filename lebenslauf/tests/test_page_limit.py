"""Page limits (G51): the cover letter has one page, the CV at most two, or three where the person allows it.

Over a limit the build first tightens; when tightening is not enough, it keeps all content and `cuts` names what
could go, for the person to decide. All CVs and letters are invented (page_fill_samples).
"""
import pytest
import yaml

import anschreiben
import build
import cuts
import dossier
import page_fill
from page_fill import Fill
from page_fill_samples import cv_of_length, example_cv, example_letter, letter_of_length, page_count

# Drawn, this CV has three pages with a full enough last page, so the page fill alone would keep them (G49)
THREE_PAGES = 26
THREE_PAGE_DESIGN = "dossier-siegel"


def _probe(fills: dict[int, Fill], otherwise: Fill):
    return lambda level: fills.get(level, otherwise)


# The choice of the density


def test_a_cv_over_the_limit_is_tightened_even_when_its_last_page_is_full_enough():
    probe = _probe({0: Fill(3, 0.45), -1: Fill(3, 0.6), 1: Fill(3, 0.3), 2: Fill(2, 0.9)}, Fill(3, 0.2))
    assert page_fill.choose(probe) == 0, "without a limit the page fill keeps the three pages"
    assert page_fill.choose(probe, limit=2) == 2


def test_within_the_limit_the_page_fill_chooses_as_before():
    probe = _probe({0: Fill(3, 0.45), -1: Fill(3, 0.6), 1: Fill(3, 0.3), 2: Fill(2, 0.9)}, Fill(3, 0.2))
    assert page_fill.choose(probe, limit=3) == page_fill.choose(probe) == 0


def test_tightening_to_the_limit_goes_on_while_the_last_page_is_nearly_empty():
    probe = _probe({0: Fill(3, 0.5), 2: Fill(2, 0.1), 3: Fill(2, 0.2), 4: Fill(2, 0.45)}, Fill(3, 0.5))
    assert page_fill.choose(probe, limit=2) == 4


def test_the_first_level_within_the_limit_counts_when_none_fills_its_last_page():
    probe = _probe({0: Fill(3, 0.5), 3: Fill(2, 0.1), 4: Fill(2, 0.2), 5: Fill(2, 0.25)}, Fill(3, 0.5))
    assert page_fill.choose(probe, limit=2) == 3


def test_a_part_that_tightening_cannot_bring_to_the_limit_falls_back_to_the_page_fill():
    probe = _probe({0: Fill(3, 0.2), -1: Fill(3, 0.5)}, Fill(3, 0.1))
    assert page_fill.choose(probe, limit=2) == page_fill.choose(probe) == -1


def test_a_letter_over_one_page_is_tightened_onto_one():
    probe = _probe({0: Fill(2, 0.2), -1: Fill(2, 0.5), 4: Fill(1, 0.95)}, Fill(2, 0.1))
    assert page_fill.choose(probe) == -1, "the page fill alone would widen the second page"
    assert page_fill.choose(probe, limit=page_fill.LIMITS["letter"]) == 4


def test_the_limits_allow_a_three_page_cv_only_when_asked():
    assert page_fill.LIMITS == {"cv": 2, "letter": 1}
    assert page_fill.limits(3) == {"cv": 3, "letter": 1}
    assert page_fill.limits() == page_fill.LIMITS
    with pytest.raises(ValueError, match="zwei oder drei"):
        page_fill.limits(4)


def test_levels_apply_each_part_its_own_limit():
    def query(inputs: dict) -> list[dict]:
        level = int(inputs.get("density-cv", "0"))
        pages = 2 if level >= 2 else 3
        return [{"part": "cv", "edge": "start", "page": 1},
                {"part": "cv", "edge": "end", "page": pages, "y": 600.0, "top": 100.0, "bottom": 100.0,
                 "height": 1000.0}]

    assert page_fill.levels(query, {}, ("cv",))["density-cv"] == "2"
    assert page_fill.levels(query, {}, ("cv",), page_fill.limits(3))["density-cv"] == "0"


# The builds


@pytest.fixture(scope="module")
def three_pages(tmp_path_factory):
    folder = tmp_path_factory.mktemp("three-pages")
    (folder / "cv.yaml").write_text(yaml.safe_dump(cv_of_length(THREE_PAGES), allow_unicode=True), encoding="utf-8")
    (folder / "brief.yaml").write_text(yaml.safe_dump(example_letter(), allow_unicode=True), encoding="utf-8")
    (folder / "dossier.yaml").write_text(yaml.safe_dump({"lebenslauf": "cv.yaml", "anschreiben": "brief.yaml"}),
                                         encoding="utf-8")
    return folder


def _dossier(folder, name: str, *options: str):
    return dossier.main([str(folder / "dossier.yaml"), "--theme", THREE_PAGE_DESIGN, *options,
                         "--build-dir", str(folder / f"build-{name}"), "--out-dir", str(folder / name)])


def test_a_three_page_cv_is_brought_to_two_pages_by_default(three_pages):
    result = _dossier(three_pages, "default")
    assert page_count(result.cv) == 2
    assert int(result.inputs["cv"]["density-cv"]) > 0


def test_with_three_pages_allowed_the_cv_keeps_its_three_pages(three_pages):
    result = _dossier(three_pages, "three", "--lebenslauf-seiten", "3")
    assert page_count(result.cv) == 3


def test_the_cv_build_takes_the_allowed_pages(monkeypatch, tmp_path):
    asked = []
    monkeypatch.setattr(page_fill, "levels", lambda query, inputs, parts, limits=page_fill.LIMITS:
                        asked.append(limits) or inputs)
    (tmp_path / "cv.yaml").write_text(yaml.safe_dump(example_cv(), allow_unicode=True), encoding="utf-8")
    build.main([str(tmp_path / "cv.yaml"), "--build-dir", str(tmp_path / "b"), "-o", str(tmp_path / "a.pdf")])
    build.main([str(tmp_path / "cv.yaml"), "--lebenslauf-seiten", "3", "--build-dir", str(tmp_path / "b"),
                "-o", str(tmp_path / "b.pdf")])
    assert [limits["cv"] for limits in asked] == [2, 3]


def test_the_letter_build_holds_the_letter_to_one_page(monkeypatch, tmp_path):
    asked = []
    monkeypatch.setattr(page_fill, "levels", lambda query, inputs, parts, limits=page_fill.LIMITS:
                        asked.append(limits) or inputs)
    (tmp_path / "cv.yaml").write_text(yaml.safe_dump(example_cv(), allow_unicode=True), encoding="utf-8")
    (tmp_path / "brief.yaml").write_text(yaml.safe_dump({**letter_of_length(0), "lebenslauf": "cv.yaml"},
                                                        allow_unicode=True), encoding="utf-8")
    anschreiben.main([str(tmp_path / "brief.yaml"), "--build-dir", str(tmp_path / "b"), "-o", str(tmp_path / "a.pdf")])
    assert [limits["letter"] for limits in asked] == [1]


def test_only_two_or_three_cv_pages_can_be_asked_for(tmp_path):
    with pytest.raises(SystemExit):
        build.main([str(tmp_path / "cv.yaml"), "--lebenslauf-seiten", "4"])


# What could be cut, when tightening is not enough


def test_the_cuts_of_a_cv_name_the_stations_with_the_most_points_first():
    cv = cv_of_length(9)  # two stations of three points and one of one point
    named = cuts.for_cv(cv)
    assert named[0] == "Stichpunkte bei «Projektleiterin Daten 0, Muster Informatik 0 AG» (3)"
    assert named[1] == "Stichpunkte bei «Projektleiterin Daten 1, Muster Informatik 1 AG» (3)"
    assert all("Daten 99" not in entry for entry in named), "a single point is no cut worth naming"


def test_the_cuts_of_a_cv_name_optional_sections_it_has():
    cv = example_cv()
    named = cuts.for_cv(cv)
    assert "Abschnitt «Weitere Projekte»" in named
    assert len(named) <= cuts.MAX_NAMED
    assert cuts.for_cv({"basics": {"name": "Erika Beispiel"}}) == []


def test_the_cut_of_a_letter_names_its_longest_paragraph():
    text = "Kurz und klar.\n\nDieser Absatz ist deutlich länger als der erste und erzählt sehr viel.\n\nAuch kurz."
    assert cuts.for_letter(text) == ["der längste Absatz («Dieser Absatz ist deutlich länger …»)"]
    assert cuts.for_letter("") == []
