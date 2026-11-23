"""The shared search logic in French and English (#421, G10, docs/design/sprachen.md).

The scripts that the pages Stellen, Suche einstellen, Suchbegriffe prüfen and Firmen share have every text in the
catalog in fr and en, so they are in FERTIG and the gate keeps them so. What the scripts say at run time is tested in
tests/search_logic_languages.test.cjs. The lines of the search profile are data the person finds in the profile under
these words, so the catalog never translates them.
"""
import sprachen_pruefen
import translation_catalog

SCRIPTS = ("seiten/treffer-logik.js", "seiten/suchbegriffe-logik.js", "seiten/verworfen-woerter-logik.js",
           "seiten/suche-anzeige.js", "seiten/firmen-logik.js", "seiten/kununu-pruefen.js", "seiten/firmen-ausschluss.js")
# Search profile grammar (vorlagen/suchprofil.md): the scripts show it as it stands in the profile.
PROFILE_LINES = ("Nischen (ohne Ort suchen)", "Nur {portale}", "(ganzes Wort)")


def test_the_shared_search_scripts_are_finished():
    finished = {str(path.relative_to(sprachen_pruefen.BASE)) for path in sprachen_pruefen.FERTIG
                if path.is_relative_to(sprachen_pruefen.BASE)}

    assert set(SCRIPTS) <= finished


def test_the_shared_search_scripts_have_no_gap():
    catalog = translation_catalog.load(translation_catalog.CATALOG_DIR)

    assert sprachen_pruefen.gaps([sprachen_pruefen.BASE / script for script in SCRIPTS], catalog) == ()


def test_the_lines_of_the_search_profile_are_never_translated():
    catalog = translation_catalog.load(translation_catalog.CATALOG_DIR)

    assert [line for line in PROFILE_LINES if catalog.text(line, "fr") or catalog.text(line, "en")] == []
