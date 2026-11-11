"""How the build chooses the density of a part (G49, #236): measured markers, then the smaller of two fixes."""
import pytest
import typst

import page_fill
from page_fill import Fill


def _probe(fills: dict[int, Fill], otherwise: Fill):
    asked = []

    def probe(level: int) -> Fill:
        asked.append(level)
        return fills.get(level, otherwise)

    return probe, asked


def _end(page: int, y: float) -> dict:
    return {"part": "cv", "edge": "end", "page": page, "y": y, "top": 100.0, "bottom": 100.0, "height": 1000.0}


def test_measure_reads_pages_and_the_fill_of_the_last_page():
    markers = [{"part": "cv", "edge": "start", "page": 2}, _end(3, 400.0), _end(3, 250.0), _end(2, 880.0),
               {"part": "letter", "edge": "start", "page": 1}]
    assert page_fill.measure(markers, "cv") == Fill(pages=2, last=pytest.approx(300 / 800))


def test_measure_refuses_a_design_without_markers():
    with pytest.raises(ValueError, match="Seitenfüllung"):
        page_fill.measure([], "cv")


def test_a_part_that_fills_its_last_page_stays_as_drawn():
    probe, asked = _probe({0: Fill(2, 0.6)}, Fill(2, 0.0))
    assert page_fill.choose(probe) == 0
    assert asked == [0]


def test_a_single_page_stays_as_drawn():
    assert page_fill.choose(lambda level: Fill(1, 0.05)) == 0


def test_tightening_wins_when_it_saves_a_page_with_the_smaller_change():
    probe, _ = _probe({0: Fill(3, 0.1), 1: Fill(2, 0.95), -1: Fill(3, 0.2), -2: Fill(3, 0.5)}, Fill(3, 0.1))
    assert page_fill.choose(probe) == 1


def test_widening_wins_when_it_fills_the_last_page_with_the_smaller_change():
    probe, _ = _probe({0: Fill(3, 0.1), -1: Fill(3, 0.45), 2: Fill(2, 0.9)}, Fill(3, 0.05))
    assert page_fill.choose(probe) == -1


def test_at_the_same_step_tightening_goes_first():
    probe, _ = _probe({0: Fill(3, 0.1), 2: Fill(2, 0.9), -2: Fill(3, 0.6)}, Fill(3, 0.1))
    assert page_fill.choose(probe) == 2


def test_tightening_must_save_a_page_and_widening_must_keep_the_pages():
    # Tighter but still three pages, wider but spilling onto a fourth: neither is a fix
    probe, _ = _probe({0: Fill(3, 0.1)}, Fill(3, 0.2))
    assert page_fill.choose(lambda level: Fill(4, 0.5) if level < 0 else probe(level)) == 0


def test_a_fix_that_reaches_the_aim_goes_before_one_that_barely_meets_the_rule():
    probe, _ = _probe({0: Fill(3, 0.2), -1: Fill(3, 0.34), -2: Fill(3, 0.5)}, Fill(3, 0.2))
    assert page_fill.choose(probe) == -2


def test_a_fix_that_only_meets_the_rule_is_taken_when_nothing_reaches_the_aim():
    probe, _ = _probe({0: Fill(3, 0.2), -3: Fill(3, 0.35)}, Fill(3, 0.2))
    assert page_fill.choose(probe) == -3


def test_a_design_that_meets_the_rule_stays_when_no_fix_reaches_the_aim():
    probe, _ = _probe({0: Fill(3, 0.35)}, Fill(3, 0.36))
    assert page_fill.choose(probe) == 0


def test_when_nothing_works_the_part_stays_as_drawn():
    assert page_fill.choose(lambda level: Fill(3, 0.1)) == 0


def test_each_level_is_measured_once():
    probe, asked = _probe({0: Fill(3, 0.1)}, Fill(3, 0.1))
    page_fill.choose(probe)
    assert sorted(asked) == sorted(set(asked))


def test_levels_choose_each_part_after_the_one_before():
    seen = []

    def query(inputs: dict) -> list[dict]:
        seen.append(dict(inputs))
        cv_fill = 900.0 if inputs.get("density-cv") == "-1" else 150.0
        return [{"part": "letter", "edge": "start", "page": 1}, {**_end(1, 500.0), "part": "letter"},
                {"part": "cv", "edge": "start", "page": 2}, _end(3, cv_fill)]

    chosen = page_fill.levels(query, {"data": "x.json"}, ("letter", "cv"))
    assert chosen == {"data": "x.json", "density-letter": "0", "density-cv": "-1"}
    assert all(s.get("density-letter") == "0" for s in seen if "density-cv" in s)


def test_a_document_that_does_not_compile_raises_the_error_typst_compile_raises(tmp_path):
    # Callers such as the trial build of Inhalte catch typst.TypstError; the query alone raises a bare RuntimeError
    broken = tmp_path / "broken.typ"
    broken.write_text("#(5).map(x => x)\n", encoding="utf-8")
    with pytest.raises(typst.TypstError, match="map"):
        page_fill.markers(str(broken), str(tmp_path), [], {})
