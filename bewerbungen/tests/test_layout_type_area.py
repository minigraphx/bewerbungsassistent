"""Text in a design's own margin (G51, G52, #304): the build passes each page's margins beside the PDF, and the check
before sending flags text that reaches into them, not only text within 20 pt of the page edge.

The constructed documents are small Typst sources with the marker every design sets; all text is invented.
"""
import pytest
import typst

import anschreiben
import build
import dossier
import layout_check
import pruefung
import type_area

FONTS = [str(build.ROOT / "fonts")]
THEMES = build.ROOT / "themes"
MARGIN = 80.0  # pt, wider than the 20 pt edge rule, so a margin breach can stay far from the edge
PAGE = ('#import "type-area.typ": type-area\n'
        f'#set page(paper: "a4", margin: {MARGIN}pt, foreground: type-area())\n'
        '#set text(font: "Liberation Sans", size: 10pt, lang: "de")\n')
BODY = "Aufbau und Betrieb einer Auswertung für den Bereich Finanzen, mit Berichten fürs Team.\n\n"

LETTER = {"left": 70.87, "right": 56.69, "top": 42.52, "bottom": 42.52}  # themes/brief.typ, for both CV designs
DESIGNS = {  # the margins each design draws, from its Typst source
    "zweispaltig": {"left": 50.5, "right": 50.5, "top": 62.36, "bottom": 45.35},
    "einspaltig": {"left": 56.69, "right": 56.69, "top": 56.69, "bottom": 56.69},
    "dossier-siegel": {"left": 48.0, "right": 48.0, "top": 48.0, "bottom": 60.0},
    "dossier-raster": {"left": 48.0, "right": 48.0, "top": 60.0, "bottom": 60.0},
    "dossier-register": {"left": 48.0, "right": 64.0, "top": 48.0, "bottom": 60.0},
}


def built(tmp_path, body: str, name: str = "doc", preamble: str = PAGE):
    """A PDF with the type area beside it, written the way the builds write it, from the designs' own marker."""
    for helper in ("type-area.typ", "page-fill.typ"):
        (tmp_path / helper).write_bytes((THEMES / helper).read_bytes())
    source = tmp_path / f"{name}.typ"
    source.write_text(preamble + body, encoding="utf-8")
    pdf = tmp_path / f"{name}.pdf"
    typst.compile(str(source), output=str(pdf), root=str(tmp_path), font_paths=FONTS, ignore_system_fonts=True)
    type_area.record(pdf, str(source), str(tmp_path), FONTS, {})
    return pdf


def margin_breaches(pdf) -> list[layout_check.Breach]:
    return [b for b in layout_check.check(pdf, "anschreiben") if b.rule == "rand"]


def margins_of(pdf) -> list[dict]:
    areas = type_area.read(pdf)
    assert areas, f"{pdf.name}: der Bau legt keinen Satzspiegel daneben"
    return [{side: round(area[side], 2) for side in ("left", "right", "top", "bottom")} for area in areas.values()]


# The designs pass their own margins, and their examples keep them


@pytest.mark.parametrize("design", ["zweispaltig", "einspaltig"])
def test_the_cv_designs_pass_their_margins_and_their_examples_keep_them(tmp_path, design):
    data = build.ROOT / "data"
    cv = build.main([str(data / "beispiel.yaml"), "--theme", design, "--build-dir", str(tmp_path / "build"),
                     "-o", str(tmp_path / "cv.pdf")])
    letter = anschreiben.main([str(data / "anschreiben-beispiel.yaml"), "--theme", design, "--build-dir",
                               str(tmp_path / "build"), "-o", str(tmp_path / "brief.pdf")])

    assert all(m == DESIGNS[design] for m in margins_of(cv))
    assert margins_of(letter) == [LETTER]
    assert layout_check.check(cv, "lebenslauf") == []
    assert layout_check.check(letter, "anschreiben") == []


@pytest.mark.parametrize("design", ["dossier-siegel", "dossier-raster", "dossier-register"])
def test_the_dossier_designs_pass_their_margins_and_their_examples_keep_them(tmp_path, design):
    result = dossier.main([str(build.ROOT / "data" / "dossier-beispiel.yaml"), "--theme", design, "--build-dir",
                           str(tmp_path / "build"), "--out-dir", str(tmp_path / "out")])

    for pdf, part in ((result.dossier, "dossier"), (result.cv, "lebenslauf"), (result.letter, "anschreiben")):
        assert all(m == DESIGNS[design] for m in margins_of(pdf)), pdf.name
        assert layout_check.check(pdf, part) == [], pdf.name


# Text in the margin


def test_text_in_the_margin_far_from_the_edge_is_named(tmp_path):
    pdf = built(tmp_path, BODY + "#place(dx: -40pt, dy: 100pt)[Weit links gesetzt]")

    [found] = margin_breaches(pdf)

    assert found.page == 1 and "«Weit links gesetzt»" in found.reason and "Rand des Designs" in found.reason


@pytest.mark.parametrize("placed", ['#place(top + left, dy: -30pt)[Oben im Rand]',
                                    '#place(bottom + left, dy: 30pt)[Unten im Rand]',
                                    '#place(top + right, dx: 30pt, dy: 200pt)[Rechts im Rand]'])
def test_text_in_any_margin_is_named(tmp_path, placed):
    assert len(margin_breaches(built(tmp_path, BODY + placed))) == 1


def test_text_in_the_type_area_passes(tmp_path):
    pdf = built(tmp_path, BODY * 5 + "#place(top + right)[Bündig rechts]")

    assert margin_breaches(pdf) == []


def test_the_footer_sits_in_the_bottom_margin_on_purpose(tmp_path):
    preamble = PAGE.replace("foreground: type-area()", "foreground: type-area(), footer: align(right)[Erika Muster]")

    assert margin_breaches(built(tmp_path, BODY, preamble=preamble)) == []


def test_a_band_at_the_foot_the_design_declares_may_carry_text(tmp_path):
    band = '#place(bottom + left, dy: 50pt)[Kontakt im Band]'
    declared = '#page(foreground: type-area(foot: 70pt))[' + BODY + band + ']'

    assert margin_breaches(built(tmp_path, declared)) == []
    assert len(margin_breaches(built(tmp_path, BODY + band, "ohne"))) == 1


def test_full_bleed_shapes_and_images_in_the_margin_are_left_alone(tmp_path):
    bleed = ('#place(top + left, dx: -80pt, dy: -80pt, rect(width: 595pt, height: 60pt, fill: gray))\n'
             '#place(top + left, dx: -80pt, dy: 300pt, image("bild.png", width: 40pt, height: 300pt))\n')
    (tmp_path / "bild.png").write_bytes((build.ROOT / "tests" / "halbe.png").read_bytes())

    assert margin_breaches(built(tmp_path, BODY + bleed)) == []


def test_a_type_area_of_another_build_does_not_count(tmp_path):
    pdf = built(tmp_path, BODY + "#place(dx: -40pt, dy: 100pt)[Weit links gesetzt]")
    pdf.write_bytes(pdf.read_bytes() + b"\n% neu gebaut\n")

    assert type_area.read(pdf) is None
    assert margin_breaches(pdf) == []  # without the design's margins, only the page edge counts


def test_the_check_before_sending_names_the_margin_breach(tmp_path):
    pdf = built(tmp_path, BODY + "#place(dx: -40pt, dy: 100pt)[Weit links gesetzt]")

    found = [f for f in pruefung.layout_findings(pdf, "anschreiben") if "Rand des Designs" in f.text]

    assert [(f.stufe, bool(f.schluessel)) for f in found] == [("hinweis", True)]
    assert found[0].text.startswith("Anschreiben, Seite 1: ")
