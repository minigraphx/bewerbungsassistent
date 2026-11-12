"""Mark and accent colour of the dossier (G18, docs/design/monogramm.md, option B decided on 10.11.2026).

Five marks from the initials or an own logo, drawn by all three designs on the cover and small on following pages
(Raster also in the footer); each design its own main colour; own colours only when they read well. All data is
invented: the example CV, letter and dossier file, and logos drawn here.
"""
import json
import pathlib
import shutil

import pytest
import yaml

import dossier
import dossier_data
import mark
import svg_check
from dossier_samples import EXAMPLE, example_cv, example_letter, flat, page_texts

HERE = pathlib.Path(__file__).parent
CASES = json.loads((HERE / "accent_cases.json").read_text(encoding="utf-8"))
PNG_LOGO = HERE / "halbe.png"
DESIGNS = ("dossier-siegel", "dossier-raster", "dossier-register")
NS = 'xmlns="http://www.w3.org/2000/svg"'
SVG_LOGO = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 110"><rect width="110" height="110" rx="20" '
            'fill="#a35a2b"/></svg>')


def build(folder: pathlib.Path, *options: str, basics: dict | None = None, files: dict | None = None,
          cv_text=lambda text: text) -> dossier.Result:
    """Writes CV (with extra basics, its text passed through cv_text), letter, dossier file and further files to
    folder and builds all three PDFs."""
    folder.mkdir(parents=True)
    cv = example_cv()
    cv["basics"] = {**cv["basics"], **(basics or {})}
    for name, content in (files or {}).items():
        target = folder / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, pathlib.Path):
            shutil.copy(content, target)
        else:
            target.write_text(content, encoding="utf-8")
    (folder / "cv.yaml").write_text(cv_text(yaml.safe_dump(cv, allow_unicode=True)), encoding="utf-8")
    (folder / "brief.yaml").write_text(yaml.safe_dump({**example_letter(), "lebenslauf": "cv.yaml"}, allow_unicode=True),
                                       encoding="utf-8")
    file_data = {**yaml.safe_load(EXAMPLE.read_text(encoding="utf-8")), "lebenslauf": "cv.yaml", "anschreiben": "brief.yaml"}
    (folder / "dossier.yaml").write_text(yaml.safe_dump(file_data, allow_unicode=True), encoding="utf-8")
    return dossier.main([str(folder / "dossier.yaml"), "--build-dir", str(folder / "build"),
                         "--out-dir", str(folder / "out"), *options])


@pytest.fixture
def make(tmp_path):
    counter = iter(range(100))
    return lambda *options, **kwargs: build(tmp_path / f"run{next(counter)}", *options, **kwargs)


def marks(result: dossier.Result, part: str = "dossier") -> list[tuple[str, str]]:
    return [(m["variant"], m["at"]) for m in dossier.query(result, "<dossier-mark>", part)]


def accent(result: dossier.Result) -> str:
    return json.loads(result.data.read_text(encoding="utf-8"))["style"]["farbe-akzent"]


# Accent colour


@pytest.mark.parametrize("case", CASES["cases"], ids=lambda c: c["farbe"])
def test_an_own_colour_is_kept_only_when_text_on_it_and_lines_on_paper_read_well(case):
    found = mark.accent_check(case["farbe"])

    assert found["ok"] is case["ok"]
    if case["ok"]:
        assert found["schrift"] == case["schrift"] and found["vorschlag"] is None
        assert mark.contrast(found["farbe"], mark.text_on(found["farbe"])) >= 4.5
        assert mark.contrast(found["farbe"], mark.PAPER) >= 3
    else:
        assert (found["problem"], found["vorschlag"]) == (case["problem"], case["vorschlag"])
        assert mark.readable(found["vorschlag"])
        with pytest.raises(ValueError, match="Gespeichert wird"):
            mark.stored_accent(case["farbe"])


@pytest.mark.parametrize("value", CASES["invalid"])
def test_a_colour_must_look_like_a_colour(value):
    with pytest.raises(ValueError, match="#38495d"):
        mark.accent_check(value)


def test_every_offered_colour_and_every_main_colour_reads_well():
    for _, value in mark.SWATCHES:
        assert mark.accent_check(value)["ok"], value
    assert mark.MAIN_COLOURS == {"dossier-siegel": "#38495d", "dossier-raster": "#7a2e3a", "dossier-register": "#2f5d50"}


@pytest.mark.parametrize("design", DESIGNS)
def test_without_a_choice_each_design_shows_its_own_main_colour(make, design):
    assert accent(make("--theme", design)) == mark.MAIN_COLOURS[design]


def test_a_chosen_colour_stays_whatever_the_design_and_a_mix_takes_the_cover_colour(make):
    assert accent(make("--theme", "dossier-raster", basics={"x-akzent": "#1d5c6b"})) == "#1d5c6b"
    assert accent(make("--theme", "dossier-siegel", "--design-deckblatt", "dossier-register")) == "#2f5d50"
    assert accent(make("--theme", "dossier-siegel", "--akzent", "#5b3f6b", basics={"x-akzent": "#1d5c6b"})) == "#5b3f6b"


def test_a_stored_colour_that_reads_badly_is_refused_when_building(make):
    with pytest.raises(ValueError, match="Vorschlag #927119"):
        make(basics={"x-akzent": "#e0b84a"})


# The five marks in the three designs


def test_without_a_choice_the_designs_draw_their_own_marks(make):
    siegel = marks(make("--theme", "dossier-siegel"))
    assert {v for v, _ in siegel} == {"passend"}
    assert {"cover", "footer", "thanks"} == {at for _, at in siegel}
    assert ("passend", "cover") in marks(make("--theme", "dossier-register"))
    raster = make("--theme", "dossier-raster")
    assert marks(raster) == [("passend", "cover")]  # no mark in the footer: Raster looks as before


@pytest.mark.parametrize("design", DESIGNS)
@pytest.mark.parametrize("variant", ["ring", "block", "verschraenkt", "linie", "punkt"])
def test_a_chosen_variant_shows_on_the_cover_and_small_on_following_pages(make, design, variant):
    result = make("--theme", design, "--zeichen", variant)

    drawn = marks(result)
    assert (variant, "cover") in drawn
    assert (variant, "footer") in drawn
    assert {v for v, _ in drawn} == {variant}
    assert "EB" in flat(page_texts(result.dossier)[0]).replace(" ", "")  # the initials stay real text


def test_raster_repeats_a_chosen_mark_in_the_footer_of_following_pages(make):
    result = make("--theme", "dossier-raster", basics={"x-zeichen": "ring"})

    assert marks(result).count(("ring", "footer")) >= 2
    assert ("ring", "footer") in marks(result, "cv")


def test_interlaced_needs_exactly_two_letters_otherwise_the_design_mark_shows(make):
    assert mark.settings({"x-zeichen": "verschraenkt"}, HERE, "EB")["variant"] == "verschraenkt"
    for letters in ("E", "EKB"):
        assert mark.settings({"x-zeichen": "verschraenkt"}, HERE, letters)["variant"] == "passend"
    result = make("--theme", "dossier-siegel", basics={"x-zeichen": "verschraenkt", "x-monogramm": "EKB"})
    assert {v for v, _ in marks(result)} == {"passend"}


def test_initials_of_three_letters_and_an_unknown_mark_are_checked(make):
    result = make("--theme", "dossier-siegel", basics={"x-zeichen": "ring", "x-monogramm": "EKB"})
    assert "EKB" in flat(page_texts(result.dossier)[0])
    with pytest.raises(ValueError, match="Unbekanntes Zeichen"):
        make(basics={"x-zeichen": "stern"})
    assert dossier_data.monogram({"name": "Erika Beispiel", "x-monogramm": "EKB"}) == "EKB"


@pytest.mark.parametrize("initials", ("NO", "ON", "OFF", "YES"))
def test_initials_written_unquoted_before_248_are_drawn_as_written(make, initials):
    """#250: YAML 1.1 (PyYAML) reads an unquoted NO as False; the dossier takes the letters from the field text."""
    unquoted = lambda text: text.replace(f"x-monogramm: '{initials}'", f"x-monogramm: {initials}")  # noqa: E731
    result = make("--theme", "dossier-siegel", basics={"x-zeichen": "ring", "x-monogramm": initials}, cv_text=unquoted)

    assert json.loads(result.data.read_text(encoding="utf-8"))["person"]["monogram"] == initials
    assert initials in flat(page_texts(result.dossier)[0])


# Own logo


@pytest.mark.parametrize("design", DESIGNS)
def test_an_own_logo_replaces_the_initials_on_the_cover_and_following_pages(make, design):
    result = make("--theme", design, basics={"x-zeichen": "logo", "x-logo": "logos/logo.png"},
                  files={"logos/logo.png": PNG_LOGO})

    drawn = marks(result)
    assert ("logo", "cover") in drawn and ("logo", "footer") in drawn
    assert not result.logo_missing
    assert json.loads(result.data.read_text(encoding="utf-8"))["person"]["mark"]["logo"].endswith("logo.png")


def test_a_logo_from_the_command_line_and_as_svg(make):
    result = make("--theme", "dossier-raster", "--logo", str(PNG_LOGO))
    assert ("logo", "cover") in marks(result)
    svg = make("--theme", "dossier-siegel", basics={"x-zeichen": "logo", "x-logo": "logo.svg"}, files={"logo.svg": SVG_LOGO})
    assert ("logo", "cover") in marks(svg)


def test_a_missing_logo_falls_back_to_the_design_mark_and_says_so(make):
    result = make("--theme", "dossier-register", basics={"x-zeichen": "logo", "x-logo": "logos/weg.png"})

    assert result.logo_missing
    assert {v for v, _ in marks(result)} == {"passend"}


@pytest.mark.parametrize("svg", [
    '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
    '<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"><rect width="9" height="9"/></svg>',
    '<svg xmlns="http://www.w3.org/2000/svg"><image href="https://example.com/a.png" width="9" height="9"/></svg>',
    '<svg xmlns="http://www.w3.org/2000/svg"><foreignObject><p>x</p></foreignObject></svg>',
    '<svg xmlns="http://www.w3.org/2000/svg"><style>@import url(https://example.com/x.css);</style></svg>',
    '<!DOCTYPE svg [<!ENTITY x SYSTEM "file:///etc/passwd">]><svg xmlns="http://www.w3.org/2000/svg">&x;</svg>',
    f'<svg {NS} xmlns:s="http://www.w3.org/2000/svg"><s:script>alert(1)</s:script><rect width="9" height="9"/></svg>',
    f'<svg {NS} xmlns:h="http://www.w3.org/2000/svg"><h:foreignObject><p>x</p></h:foreignObject></svg>',
])
def test_an_svg_with_script_or_outside_links_is_refused_and_never_drawn(make, svg):
    assert mark.svg_problem(svg)
    result = make("--theme", "dossier-siegel", basics={"x-zeichen": "logo", "x-logo": "logo.svg"}, files={"logo.svg": svg})
    assert result.logo_missing and {v for v, _ in marks(result)} == {"passend"}


def test_a_plain_svg_with_inner_references_is_fine():
    assert mark.svg_problem('<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">'
                            '<defs><linearGradient id="g"/></defs><rect fill="url(#g)"/><use xlink:href="#g"/></svg>') is None


INKSCAPE = ('<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n<!-- Created with an editor -->\n'
            f'<svg {NS} xmlns:xlink="http://www.w3.org/1999/xlink" '
            'xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:cc="http://creativecommons.org/ns#" '
            'xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd" viewBox="0 0 40 40">'
            '<metadata><rdf:RDF><cc:Work rdf:about=""><cc:license rdf:resource="http://creativecommons.org/licenses/by/4.0/"/>'
            '</cc:Work></rdf:RDF></metadata><sodipodi:namedview pagecolor="#ffffff"/>'
            '<style>.a{fill:url(#g)}</style><defs><linearGradient id="g"/></defs>'
            '<rect class="a" style="fill:url(\'#g\');stroke:#000" width="40" height="40"/>'
            '<image xlink:href="data:image/png;base64,iVBORw0KGgo=" width="1" height="1"/></svg>')


def test_an_svg_from_an_editor_with_metadata_and_inner_links_is_fine():
    assert mark.svg_problem(INKSCAPE) is None


@pytest.mark.parametrize(("svg", "message"), [
    (f'<svg {NS} xmlns:s="http://www.w3.org/2000/svg"><s:script>alert(1)</s:script></svg>', "SVG_SCRIPT"),
    (f'<svg {NS} xmlns:h="http://www.w3.org/2000/svg"><h:foreignObject><p>x</p></h:foreignObject></svg>', "SVG_SCRIPT"),
    (f'<svg {NS} xmlns:s="http://www.w3.org/2000/svg" s:onload="alert(1)"><rect width="9" height="9"/></svg>',
     "SVG_SCRIPT"),
    (f'<svg {NS} onload="alert(1)"/>', "SVG_SCRIPT"),
    (f'<svg {NS} xmlns:x="http://www.w3.org/1999/xlink"><a x:href=" jav&#x61;script:alert(1)"><rect/></a></svg>',
     "SVG_SCRIPT"),
    (f'<svg {NS}><rect style="fill:url(javascript:alert(1))"/></svg>', "SVG_SCRIPT"),
    ('<!DOCTYPE svg [<!ENTITY x "y">]>' f'<svg {NS}><text>&x;</text></svg>', "SVG_UNCHECKABLE"),
    ('<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">'
     f'<svg {NS}/>', "SVG_UNCHECKABLE"),
    ('<?xml-stylesheet href="https://example.com/x.css"?>' f'<svg {NS}/>', "SVG_UNCHECKABLE"),
    (f'<svg {NS}><rect></svg>', "SVG_UNCHECKABLE"),
    (f'<svg {NS}><image href="data:image/svg+xml;base64,PHN2Zy8+" width="9" height="9"/></svg>', "SVG_UNCHECKABLE"),
    (f'<svg {NS} xmlns:x="http://www.w3.org/1999/xlink"><image x:href="https://example.com/a.png"/></svg>', "SVG_REMOTE"),
    (f'<svg {NS}><image src="//example.com/a.png"/></svg>', "SVG_REMOTE"),
    (f'<svg {NS}><g xml:base="https://example.com/"><use href="a.svg#x"/></g></svg>', "SVG_REMOTE"),
    (f'<svg {NS}><a><set attributeName="xlink:href" to="https://example.com/a.png"/></a></svg>', "SVG_REMOTE"),
    (f'<svg {NS}><rect style="fill: URL( \'https://example.com/p.svg#a\' )"/></svg>', "SVG_REMOTE"),
    (f'<svg {NS}><rect fill="url(https://example.com/p.svg#a)"/></svg>', "SVG_REMOTE"),
    (f'<svg {NS} xmlns:s="http://www.w3.org/2000/svg"><s:style>@import "x.css";</s:style></svg>', "SVG_REMOTE"),
    (f'<svg {NS}><style><![CDATA[rect{{fill:url(http://example.com/a#b)}}]]></style></svg>', "SVG_REMOTE"),
])
def test_each_way_to_hide_a_script_or_an_outside_link_is_refused(svg, message):
    """Names count without their prefix; nothing is expanded or fetched while checking (review of #124)."""
    assert mark.svg_problem(svg) == getattr(mark, message, message)


def test_a_logo_outside_the_folder_or_of_another_kind_is_not_used(tmp_path):
    (tmp_path / "daten").mkdir()
    shutil.copy(PNG_LOGO, tmp_path / "logo.png")
    (tmp_path / "daten" / "logo.gif").write_bytes(b"GIF89a")
    assert mark.logo_file({"x-logo": "../logo.png"}, tmp_path / "daten") is None
    assert mark.logo_file({"x-logo": "logo.gif"}, tmp_path / "daten") is None


def test_the_logo_is_fitted_never_stretched():
    zeichen = (dossier.THEMES / "zeichen.typ").read_text(encoding="utf-8")
    assert 'fit: "contain"' in zeichen


# A plain SVG DOCTYPE from an editor's export is taken off; anything more stays refused (#243, G18)

SVG11 = '<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">'
EXPORT = ('<?xml version="1.0" encoding="utf-8"?>\n<!-- Generator: an editor -->\n' + SVG11 + '\n'
          f'<svg {NS} viewBox="0 0 40 40"><rect width="40" height="40" fill="#a35a2b"/></svg>')


@pytest.mark.parametrize("doctype", [
    SVG11,
    '<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.0//EN" "http://www.w3.org/TR/2001/REC-SVG-20010904/DTD/svg10.dtd">',
    "<!DOCTYPE svg PUBLIC '-//W3C//DTD SVG 1.1 Basic//EN' 'https://www.w3.org/Graphics/SVG/1.1/DTD/svg11-basic.dtd'>",
    '<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1 Tiny//EN"\n  "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11-tiny.dtd" >',
    '<!DOCTYPE svg SYSTEM "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">',
    "<!DOCTYPE svg>",
])
def test_a_plain_svg_doctype_is_taken_off_and_the_rest_checked(doctype):
    svg = f'<?xml version="1.0"?>{doctype}<svg {NS}><rect width="9" height="9"/></svg>'
    assert mark.svg_problem(svg) == mark.SVG_UNCHECKABLE  # the check itself still refuses every DOCTYPE
    stripped = svg_check.without_doctype(svg)
    assert "DOCTYPE" not in stripped and mark.svg_problem(stripped) is None
    assert stripped == f'<?xml version="1.0"?><svg {NS}><rect width="9" height="9"/></svg>'


def test_an_editor_export_with_a_comment_before_its_doctype_is_taken_off():
    stripped = svg_check.without_doctype(EXPORT)
    assert "DOCTYPE" not in stripped and mark.svg_problem(stripped) is None


@pytest.mark.parametrize("svg", [
    SVG11[:-1] + ' [<!ENTITY x "y">]>' f'<svg {NS}><text>&x;</text></svg>',
    SVG11[:-1] + ' []>' f'<svg {NS}/>',
    '<!DOCTYPE svg PUBLIC "-//Evil//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">' f'<svg {NS}/>',
    '<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "https://example.com/svg11.dtd">' f'<svg {NS}/>',
    '<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "file:///etc/passwd">' f'<svg {NS}/>',
    '<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.0//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">' f'<svg {NS}/>',
    '<!DOCTYPE svg SYSTEM "https://example.com/svg11.dtd">' f'<svg {NS}/>',
    '<!DOCTYPE html PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">' f'<svg {NS}/>',
    '<!DOCTYPE svg [<!ENTITY x SYSTEM "file:///etc/passwd">]>' f'<svg {NS}>&x;</svg>',
    f'<svg {NS}/>' + SVG11,
])
def test_any_other_doctype_stays_and_is_refused(svg):
    assert mark.svg_problem(svg_check.without_doctype(svg)) == mark.SVG_UNCHECKABLE


def test_an_svg_without_doctype_is_left_as_it_is():
    assert svg_check.without_doctype(INKSCAPE) == INKSCAPE
