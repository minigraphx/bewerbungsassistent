"""Tests für die Themes: Fortsetzung auf Folgeseiten, englische Fassung, Foto-Optionen."""
import re

import pytest
import yaml

import build
import page_fill
from cv_samples import beispiel, lang
from page_fill_samples import CONTINUED, HEADINGS, Line, content_lines

A4_MIDDLE = 595.28 / 2  # pt: on both pages the gap between the columns spans the middle of the page
OVERFLOWING_SKILLS = 24  # invented one-line skills: more than fit on page 1 beside the header, less than a page
PAGE_OF_SKILLS = 60  # more than a whole page holds
SKILL = "Werkzeug"
SKILL_LINE = re.compile(rf"\b{SKILL} \d\d:")  # not the project "Werkzeuge für Online-Kurse"
SKILLS_HEADING = "FÄHIGKEITEN"
BULLET = "•"


def with_skills(cv: dict, count: int) -> dict:
    """The CV with `count` invented one-line skills instead of its own."""
    return {**cv, "skills": [{"name": f"{SKILL} {n:02d}", "keywords": ["Aufbau", "Betrieb"]} for n in range(count)]}


def column(line: Line) -> tuple[int, str]:
    return line.page, "left" if line.left < A4_MIDDLE else "right"


@pytest.fixture
def drawn_lines(tmp_path, monkeypatch):
    """Builds a CV as drawn, without page fill, and returns its content lines with their place on the page."""
    monkeypatch.setattr(page_fill, "choose", lambda probe, limit=None, tight_over_limit=False: 0)

    def _drawn_lines(name: str, cv: dict) -> list[Line]:
        folder = tmp_path / name
        folder.mkdir()
        data = folder / "cv.yaml"
        data.write_text(yaml.safe_dump(cv, allow_unicode=True), encoding="utf-8")
        return content_lines(build.main([str(data), "--build-dir", str(folder / "build"), "-o", str(folder / "cv.pdf")]))

    return _drawn_lines


def test_left_section_that_does_not_fit_moves_whole_to_page_2_right(drawn_lines):
    """#372: a split skills list was read only after the experience on page 2 left; whole it is read in one go."""
    long_cv = lang(beispiel(), 2)
    lines = drawn_lines("overflowing", with_skills(long_cv, OVERFLOWING_SKILLS))

    skills = [line for line in lines if SKILL_LINE.search(line.text)]
    assert len(skills) == OVERFLOWING_SKILLS
    assert {column(line) for line in skills} == {(2, "right")}
    assert not [line for line in lines if line.text.startswith(SKILLS_HEADING + " (")]
    heading = next(line for line in lines if line.text == SKILLS_HEADING)
    assert column(heading) == (2, "right")
    assert heading.top < min(line.top for line in skills)

    # Read p1 left, p1 right, p2 left, p2 right: the right column flows on to p2 left, the left one to p2 right
    assert headings_by_column(lines) == {
        (1, "left"): ["PROFIL", "PROJEKTE"],
        (1, "right"): ["BERUFSERFAHRUNG"],
        (2, "left"): ["BERUFSERFAHRUNG (FORTSETZUNG)", "BILDUNG & WEITERBILDUNG"],
        (2, "right"): [SKILLS_HEADING, "LEHRE & TRAINING", "SPRACHEN", "WEITERE PROJEKTE", "INTERESSEN"],
    }


def test_only_the_left_column_continuing_keeps_the_page_1_layout(drawn_lines):
    """With the right column done on p1, page 2 keeps its columns: a wide empty column left would read as a fault."""
    lines = drawn_lines("left-only", with_skills(beispiel(), OVERFLOWING_SKILLS))

    skills = [line for line in lines if SKILL_LINE.search(line.text)]
    assert len(skills) == OVERFLOWING_SKILLS
    assert {column(line) for line in skills} == {(2, "left")}
    assert not [line for line in lines if column(line) == (2, "right")]
    assert headings_by_column(lines) == {
        (1, "left"): ["PROFIL", "PROJEKTE"],
        (1, "right"): ["BERUFSERFAHRUNG", "BILDUNG & WEITERBILDUNG"],
        (2, "left"): [SKILLS_HEADING, "LEHRE & TRAINING", "SPRACHEN", "WEITERE PROJEKTE", "INTERESSEN"],
    }


def headings_by_column(lines: list[Line]) -> dict[tuple[int, str], list[str]]:
    found = {}
    for line in lines:
        if line.text.casefold().removesuffix(f" ({CONTINUED.casefold()})") in HEADINGS:
            found.setdefault(column(line), []).append(line.text)
    return found


def right_column_rows(lines: list[Line]) -> dict[tuple[int, int], str]:
    """The right column's text per printed row, p1 right and p2 left. pdftotext cuts a row into lines differently
    from one document to the next, and may give a list bullet to the line beside it, so the pieces of a row are
    joined from left to right without bullets."""
    rows = {}
    for line in sorted(lines, key=lambda line: line.left):
        if column(line) in ((1, "right"), (2, "left")):
            rows.setdefault((line.page, round(line.top)), []).extend(w for w in line.text.split() if w != BULLET)
    return {row: " ".join(words) for row, words in rows.items() if words}


def test_moving_a_left_section_leaves_the_right_column_as_it_was(drawn_lines):
    long_cv = lang(beispiel(), 2)
    fitting = right_column_rows(drawn_lines("fitting", with_skills(long_cv, 3)))
    overflowing = right_column_rows(drawn_lines("overflowing", with_skills(long_cv, OVERFLOWING_SKILLS)))

    assert any(page == 2 for page, _ in fitting)
    assert overflowing == fitting


def test_left_section_taller_than_a_page_is_still_split(drawn_lines):
    """Whole it would fit on no page, so it starts on page 1 as before instead of leaving the column empty."""
    lines = drawn_lines("tall", with_skills(lang(beispiel(), 2), PAGE_OF_SKILLS))

    skills = [line for line in lines if SKILL_LINE.search(line.text)]
    assert len(skills) == PAGE_OF_SKILLS
    assert (1, "left") in {column(line) for line in skills}
    assert SKILLS_HEADING + " (FORTSETZUNG)" in headings_by_column(lines)[(2, "right")]


def test_fortsetzung_auf_seite_2(baue):
    seiten = baue(lang(beispiel()))

    assert len(seiten) >= 2
    assert "FORTSETZUNG" not in seiten[0]
    assert "BERUFSERFAHRUNG (FORTSETZUNG)" in seiten[1]


@pytest.mark.parametrize("faktor", [2, 3, 8])
def test_fortsetzung_der_hauptspalte_beginnt_links(baue, faktor):
    """Gedruckt liest man nach Seite 1 unten rechts oben links weiter: dort steht die Berufserfahrung."""
    cv = lang(beispiel(), faktor)
    seiten = baue(cv)

    assert seiten[1].lstrip().startswith("BERUFSERFAHRUNG (FORTSETZUNG)")
    alles = "".join(seiten)
    for station in cv["work"]:
        assert alles.count(station["position"] + "\n") == 1, station["position"]


def test_keine_fortsetzung_bei_einer_seite(baue):
    kurz = {k: v for k, v in beispiel().items() if k not in ("teaching", "interests", "projects")}
    seiten = baue(kurz)

    assert len(seiten) == 1
    assert "FORTSETZUNG" not in seiten[0]


def test_ganzer_abschnitt_auf_neuer_seite_ohne_fortsetzung(baue, monkeypatch):
    # The design as drawn: the page fill (G49) would pull these short last sections back onto page 1.
    # At 10 pt body text (G53) the last two sections of the left column move over whole.
    monkeypatch.setattr(page_fill, "choose", lambda probe, limit=None, tight_over_limit=False: 0)
    seiten = baue(beispiel())

    assert len(seiten) == 2
    assert seiten[1].lstrip().startswith("WEITERE PROJEKTE")
    assert "FORTSETZUNG" not in "".join(seiten)


@pytest.mark.parametrize(
    "label, zeile1, zeile2",
    [
        ("Senior-Entwickler – Qualitätssicherung und KI-Systeme", "SENIOR-ENTWICKLER –", "QUALITÄTSSICHERUNG UND KI-SYSTEME"),
        ("Software-Entwickler – KI-Anwendungen und Qualitätssicherung", "SOFTWARE-ENTWICKLER –", "KI-ANWENDUNGEN UND QUALITÄTSSICHERUNG"),
    ],
)
def test_label_umbruch_nach_gedankenstrich(baue, label, zeile1, zeile2):
    cv = beispiel()
    cv["basics"]["label"] = label

    zeilen = [z.strip() for z in baue(cv)[0].splitlines()]

    assert zeilen[zeilen.index(zeile1) + 1] == zeile2


def test_englische_beschriftungen(baue):
    seiten = baue(lang(beispiel()), "--lang", "en")

    assert "EXPERIENCE" in seiten[0]
    assert "March 2019 – present" in seiten[0]
    assert "EXPERIENCE (CONTINUED)" in seiten[1]
    assert "BERUFSERFAHRUNG" not in "".join(seiten)


@pytest.mark.parametrize("theme", ["zweispaltig", "einspaltig"])
def test_englisch_in_beiden_themes(baue, theme):
    text = "".join(baue(beispiel(), "--lang", "en", "--theme", theme))

    assert "present" in text
    assert "heute" not in text


def test_foto_optionen(baue, mit_foto):
    seiten = baue(mit_foto(beispiel(), mirror=True, zoom=1.5, x=0.3, y=0.2))

    assert "Erika" in seiten[0]


def test_foto_ohne_optionen(baue, mit_foto):
    seiten = baue(mit_foto(beispiel()))

    assert "Erika" in seiten[0]


@pytest.mark.parametrize(
    "optionen, meldung",
    [
        ({"mirror": "ja"}, "mirror"),
        ({"zoom": 0.5}, "zoom"),
        ({"zoom": 5}, "zoom"),
        ({"x": 1.5}, "x"),
        ({"y": -0.1}, "y"),
        ({"spiegeln": True}, "spiegeln"),
    ],
)
def test_ungueltige_foto_optionen(optionen, meldung):
    with pytest.raises(ValueError, match=meldung):
        build.pruefe_foto_optionen(optionen)


def test_gueltige_foto_optionen():
    assert build.pruefe_foto_optionen({"mirror": True, "zoom": 1, "x": 0, "y": 1}) == {
        "mirror": True,
        "zoom": 1,
        "x": 0,
        "y": 1,
    }
