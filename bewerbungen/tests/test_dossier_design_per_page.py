"""The design of the dossier (G39, G41): one for all pages as the preset, under „Erweitert“ one per page."""
import io
import json
import pathlib
import re
import subprocess

import pytest
from pypdf import PdfReader

import dossier as dossier_modul
import unterlagen
from register import Register
from sample_folder import BRIEF_ID
from test_app import get, post, server  # noqa: F401  (server is a fixture)

TESTS = pathlib.Path(__file__).parent
THEMES = dossier_modul.THEMES
COLOUR = re.compile(rb"([\d.]+) ([\d.]+) ([\d.]+) (?:scn|SCN|rg|RG)\b")


@pytest.fixture
def built(monkeypatch):
    """Keeps what lebenslauf/dossier.py built, so a test can ask which design drew which page."""
    results = []
    original = unterlagen.dossier_modul.main

    def keep(argv):
        results.append(original(argv))
        return results[-1]

    monkeypatch.setattr(unterlagen.dossier_modul, "main", keep)
    return results


def save(s, **fields):
    return post(s, "/api/bewerbung", {"id": BRIEF_ID, **fields})


def build(s, built, **fields):
    status, saved = save(s, unterlagen="dossier", **fields)
    assert status == 200, saved
    status, answer = post(s, "/api/unterlagen", {}, id=BRIEF_ID)
    assert status == 200, answer
    return built[-1]


def drawn(result) -> dict[str, str]:
    return {m["part"]: m["design"] for m in dossier_modul.query(result, "<dossier-design>", part="dossier")}


def fonts(pdf: pathlib.Path) -> set[str]:
    names = set()
    for page in PdfReader(pdf).pages:
        for font in (page.get("/Resources", {}).get("/Font") or {}).values():
            names.add(str(font.get_object()["/BaseFont"]))
    return names


def colours(pdf: pathlib.Path) -> set[str]:
    found = set()
    for page in PdfReader(pdf).pages:
        for match in COLOUR.finditer(page.get_contents().get_data()):
            found.add("#" + "".join(f"{round(float(v) * 255):02x}" for v in match.groups()))
    return found


# Stored with the application


def test_one_design_and_designs_per_page_are_stored(server):
    status, saved = save(server, dossier_design="raster", dossier_seiten={"anschreiben": "siegel", "weitere": "register"})

    assert status == 200
    stored = Register(server.kontext.daten).hole(BRIEF_ID)
    assert (stored["dossier_design"], stored["dossier_seiten"]) == ("raster", {"anschreiben": "siegel", "weitere": "register"})
    assert "dossier_seiten" not in save(server, dossier_seiten={})[1]


@pytest.mark.parametrize("fields", [{"dossier_design": "bunt"}, {"dossier_seiten": {"rueckseite": "raster"}},
                                    {"dossier_seiten": {"lebenslauf": "bunt"}}, {"dossier_seiten": "raster"}])
def test_unknown_designs_and_pages_are_refused(server, fields):
    status, answer = save(server, **fields)

    assert status == 400 and "fehler" in answer
    assert "dossier_design" not in Register(server.kontext.daten).hole(BRIEF_ID)


def test_without_a_choice_every_page_is_siegel():
    assert unterlagen.dossier_designs({"id": "a"}) == {"deckblatt": "siegel", "anschreiben": "siegel",
                                                       "lebenslauf": "siegel", "weitere": "siegel"}


# Built with the chosen designs


def test_one_design_for_all_pages_builds_that_design(server, built):
    result = build(server, built, dossier_design="raster")

    assert result.entries == {"dossier": THEMES / "dossier-raster" / "dossier-main.typ",
                              "cv": THEMES / "dossier-raster" / "main.typ",
                              "letter": THEMES / "dossier-raster" / "anschreiben-main.typ"}


def test_each_page_gets_its_own_design_and_the_single_files_follow_their_pages(server, built):
    result = build(server, built, dossier_design="register",
                   dossier_seiten={"anschreiben": "siegel", "lebenslauf": "raster", "weitere": "siegel"})

    assert drawn(result) == {"cover": "dossier-register", "letter": "dossier-siegel", "cv": "dossier-raster",
                             "pages": "dossier-siegel"}
    assert result.entries["letter"] == THEMES / "dossier-siegel" / "anschreiben-main.typ"
    assert result.entries["cv"] == THEMES / "dossier-raster" / "main.typ"
    folder = unterlagen.bewerbungsordner(server.kontext.daten, BRIEF_ID)
    assert (folder / "lebenslauf.pdf").read_bytes() == result.cv.read_bytes()


def test_the_contents_of_another_design_find_letter_and_cv(server, built):
    result = build(server, built, dossier_design="register", dossier_seiten={"anschreiben": "siegel", "lebenslauf": "raster"})

    starts = {m["part"] for m in dossier_modul.query(result, "<dossier-part>", part="dossier")}
    text = PdfReader(result.dossier).pages[0].extract_text()

    assert {"anschreiben", "lebenslauf"} <= starts
    assert re.search(r"Anschreiben.*\d", text) and re.search(r"Lebenslauf.*\d", text)


def test_a_mixed_dossier_keeps_one_accent_colour_and_the_shared_fonts(server, built):
    mixed = build(server, built, dossier_design="register", dossier_seiten={"anschreiben": "siegel", "lebenslauf": "raster"})
    mixed_fonts, mixed_colours = fonts(mixed.dossier), colours(mixed.dossier)
    accent = json.loads(mixed.data.read_text(encoding="utf-8"))["style"].get("farbe-akzent", "#38495d")
    designs = {name: colours(build(server, built, dossier_design=name, dossier_seiten={}).dossier)
               for name in ("siegel", "raster", "register")}

    assert mixed_fonts and all("DMSans" in name.replace(" ", "") for name in mixed_fonts), mixed_fonts
    assert accent in mixed_colours
    assert mixed_colours <= set().union(*designs.values())


# The page


def test_the_page_offers_the_designs_with_the_pages_under_erweitert(server):
    _, _, page = get(server, "/bewerbung", id=BRIEF_ID)
    html = page.decode("utf-8")

    assert '<div id="dossier-design" hidden>' in html
    assert re.search(r'<details id="d-erweitert">\s*<summary>Erweitert</summary>', html)
    for name in ("Siegel", "Raster", "Register"):
        assert f">{name}</option>" in html
    for seite in ("deckblatt", "anschreiben", "lebenslauf", "weitere"):
        assert f'data-seite="{seite}"' in html


def test_the_page_logic():
    result = subprocess.run(["node", "--test", "tests/unterlagen_wahl.test.cjs"], cwd=TESTS.parent,
                            capture_output=True, text=True, timeout=120)

    assert result.returncode == 0, result.stdout + result.stderr
