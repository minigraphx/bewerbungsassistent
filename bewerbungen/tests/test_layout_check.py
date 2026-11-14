"""The check before sending measures every generated PDF (G52, #237): page count, fill of the last page, lone
headings, text outside the type area, overlapping text. A breach names document, page and reason, and a form opens
only once the person has confirmed it.

The failing documents are small Typst sources with exactly one fault each, all text invented.
"""
import datetime
import hashlib
import json

import pytest
import typst
import yaml

import anschreiben
import build
import dossier
import layout_check
import layout_confirmed
import letter_approval
import pdf_boxes
import pruefung
import unterlagen
from register import Register
from sample_folder import BRIEF_ID
from test_app import get, post, server  # noqa: F401  (server is a fixture)

TODAY = datetime.date(2026, 10, 25)
FONTS = [str(build.ROOT / "fonts")]
PAGE = '#set page(paper: "a4", margin: 2.5cm)\n#set text(font: "Liberation Sans", size: 10pt, lang: "de")\n'


def lines(count: int) -> str:
    """Paragraphs of one line each, all different: the same text at the same height on two pages is a footer."""
    def code(i: int) -> str:
        return chr(65 + i % 26) + chr(65 + i // 26 % 26)
    return "".join(f"Aufbau und Betrieb einer Auswertung für den Bereich {code(i)}, mit Berichten fürs Team.\n\n"
                   for i in range(count))


def pdf_of(tmp_path, body: str, name: str = "doc"):
    path = tmp_path / f"{name}.pdf"
    path.write_bytes(typst.compile((PAGE + body).encode("utf-8"), font_paths=FONTS, ignore_system_fonts=True))
    return path


def rules(breaches) -> set[str]:
    return {b.rule for b in breaches}


def heading(text: str) -> str:
    return f"#block(sticky: false)[#text(size: 13pt, weight: \"bold\")[{text}]]\n"


# Reading the PDF


def test_the_boxes_sit_where_typst_placed_the_text(tmp_path):
    pdf = pdf_of(tmp_path, '#place(dx: 100pt, dy: 200pt)[Muster]')

    [page] = pdf_boxes.read(pdf)
    [box] = page.text

    assert box.text == "Muster"
    assert abs(box.left - (100 + 70.87)) < 0.5  # the page margin of 2.5 cm comes first
    assert 70.87 + 200 < box.baseline < 70.87 + 215
    assert 0 < box.right - box.left < 50 and page.width == pytest.approx(595.28, abs=0.1)


# Rule: fill of the last page


def test_a_last_page_filled_well_passes(tmp_path):
    pdf = pdf_of(tmp_path, lines(55))

    assert "fuellung" not in rules(layout_check.check(pdf, "lebenslauf"))


def test_a_nearly_empty_last_page_is_named_with_its_page(tmp_path):
    pdf = pdf_of(tmp_path, lines(40))

    found = [b for b in layout_check.check(pdf, "lebenslauf") if b.rule == "fuellung"]

    assert len(found) == 1 and found[0].page == 2
    assert "gefüllt" in found[0].reason and "Drittel" in found[0].reason


def test_a_single_page_is_never_too_empty(tmp_path):
    pdf = pdf_of(tmp_path, lines(1))

    assert "fuellung" not in rules(layout_check.check(pdf, "anschreiben"))


# Rule: lone headings


def test_a_heading_with_its_first_entry_passes(tmp_path):
    pdf = pdf_of(tmp_path, lines(20) + heading("Sprachen") + "Deutsch, Muttersprache\n\n" + lines(3))

    assert "ueberschrift" not in rules(layout_check.check(pdf, "lebenslauf"))


def test_a_heading_at_the_foot_of_a_page_is_named(tmp_path):
    pdf = pdf_of(tmp_path, lines(30) + "#v(1fr)\n" + heading("Sprachen") + "#pagebreak()\nDeutsch, Muttersprache\n\n"
                 + lines(30))

    found = [b for b in layout_check.check(pdf, "lebenslauf") if b.rule == "ueberschrift"]

    assert len(found) == 1 and found[0].page == 1
    assert "«Sprachen»" in found[0].reason


def test_a_custom_heading_of_the_cv_counts_too(tmp_path):
    pdf = pdf_of(tmp_path, lines(30) + "#v(1fr)\n" + heading("Schnupperlehren") + "#pagebreak()\n" + lines(30))

    assert "ueberschrift" not in rules(layout_check.check(pdf, "lebenslauf"))
    assert "ueberschrift" in rules(layout_check.check(pdf, "lebenslauf", headings=["Schnupperlehren"]))


# Rule: text outside the type area


def test_text_inside_the_page_passes(tmp_path):
    pdf = pdf_of(tmp_path, lines(5))

    assert "rand" not in rules(layout_check.check(pdf, "anschreiben"))


def test_text_running_off_the_page_is_named(tmp_path):
    pdf = pdf_of(tmp_path, lines(5) + '#place(dx: 420pt, dy: 100pt)[Ein Wort, das über den Rand hinausläuft]')

    found = [b for b in layout_check.check(pdf, "anschreiben") if b.rule == "rand"]

    assert len(found) == 1 and found[0].page == 1
    assert "«Ein Wort, das über den Rand hinausläuft»" in found[0].reason


# Rule: overlapping elements


def test_lines_one_below_the_other_pass(tmp_path):
    pdf = pdf_of(tmp_path, '#text(size: 30pt)[Erika Muster]\n\n' + lines(10))

    assert "ueberlappung" not in rules(layout_check.check(pdf, "lebenslauf"))


def test_text_printed_over_text_is_named(tmp_path):
    pdf = pdf_of(tmp_path, '#place(dx: 40pt, dy: 0pt)[Überlagerter Text]\n' + lines(3))

    found = [b for b in layout_check.check(pdf, "lebenslauf") if b.rule == "ueberlappung"]

    assert len(found) == 1 and found[0].page == 1
    assert "«Überlagerter Text»" in found[0].reason


def test_text_crossing_an_image_is_named_but_text_on_an_image_is_not(tmp_path):
    png = (build.ROOT / "tests" / "halbe.png").read_bytes()
    (tmp_path / "bild.png").write_bytes(png)
    inside = '#place(dx: 0pt, dy: 0pt, image("bild.png", width: 80pt, height: 80pt))\n#place(dx: 10pt, dy: 30pt)[Muster]\n'
    across = '#place(dx: 0pt, dy: 0pt, image("bild.png", width: 80pt, height: 80pt))\n#place(dx: 60pt, dy: 30pt)[Musterwort]\n'

    def check(body: str, name: str):
        path = tmp_path / f"{name}.pdf"
        path.write_bytes(typst.compile((PAGE + body).encode("utf-8"), root=str(tmp_path), font_paths=FONTS,
                                       ignore_system_fonts=True))
        return rules(layout_check.check(path, "lebenslauf"))

    assert "ueberlappung" not in check(inside, "innen")
    assert "ueberlappung" in check(across, "quer")


# Rule: page count, in the check before sending


def test_a_letter_on_one_page_passes_and_one_on_two_pages_is_an_error(tmp_path):
    one = pruefung.pruefe_pdf(pdf_of(tmp_path, lines(20), "eins"), "anschreiben")
    two = pruefung.pruefe_pdf(pdf_of(tmp_path, lines(50), "zwei"), "anschreiben")

    assert not [f for f in one if "Seiten," in f.text]
    assert [f.stufe for f in two if f.text.startswith("Anschreiben: 2 Seiten")] == ["fehler"]


def test_a_cv_over_its_pages_waits_for_the_person(tmp_path):
    found = pruefung.pruefe_pdf(pdf_of(tmp_path, lines(90)), "lebenslauf")

    [over] = [f for f in found if f.text.startswith("Lebenslauf: 3 Seiten")]

    assert over.stufe == "hinweis" and over.schluessel and not over.bestaetigt


# The designs themselves pass


@pytest.mark.parametrize("design", ["zweispaltig", "einspaltig"])
def test_the_example_cv_and_letter_pass_every_rule(tmp_path, design):
    data = build.ROOT / "data"
    cv = build.main([str(data / "beispiel.yaml"), "--theme", design, "--build-dir", str(tmp_path / "build"),
                     "-o", str(tmp_path / "cv.pdf")])
    letter = anschreiben.main([str(data / "anschreiben-beispiel.yaml"), "--theme", design, "--build-dir",
                               str(tmp_path / "build"), "-o", str(tmp_path / "brief.pdf")])

    assert layout_check.check(cv, "lebenslauf") == []
    assert layout_check.check(letter, "anschreiben") == []


@pytest.mark.parametrize("design", ["dossier-siegel", "dossier-raster", "dossier-register"])
def test_the_example_dossier_passes_every_rule(tmp_path, design):
    result = dossier.main([str(build.ROOT / "data" / "dossier-beispiel.yaml"), "--theme", design, "--build-dir",
                           str(tmp_path / "build"), "--out-dir", str(tmp_path / "out")])

    assert layout_check.check(result.dossier, "dossier") == []
    assert layout_check.check(result.cv, "lebenslauf") == []
    assert layout_check.check(result.letter, "anschreiben") == []


# In the check of an application


def _built(datenordner, tmp_path) -> dict:
    entry = Register(datenordner).hole(BRIEF_ID)
    unterlagen.baue(datenordner, entry, tmp_path / "build")
    return entry


def _breach(monkeypatch, art: str = "lebenslauf"):
    fake = layout_check.Breach(2, "fuellung", "nur zu 12 % gefüllt, verlangt ist mindestens ein Drittel.")
    monkeypatch.setattr(pruefung.layout_check, "check", lambda pdf, part, headings=(): [fake] if part == art else [])


@pytest.mark.parametrize("documents", ["einzeln", "dossier"])
def test_the_sample_application_with_a_photo_has_no_breach(server, tmp_path, documents):  # noqa: F811
    data = server.kontext.daten
    register = Register(data)
    register.speichere({**register.hole(BRIEF_ID), "unterlagen": documents})
    entry = _built(data, tmp_path)

    assert [f.text for f in pruefung.pruefe(data, entry, TODAY) if f.schluessel] == []


def test_a_breach_names_document_page_and_reason(datenordner, tmp_path, monkeypatch):
    entry = _built(datenordner, tmp_path)
    _breach(monkeypatch)

    [found] = [f for f in pruefung.pruefe(datenordner, entry, TODAY) if f.schluessel]

    assert found.text == "Lebenslauf, Seite 2: nur zu 12 % gefüllt, verlangt ist mindestens ein Drittel."
    assert found.stufe == "hinweis" and not found.bestaetigt
    pdf = unterlagen.wirksame_pdfs(datenordner, entry)["lebenslauf"]
    assert found.schluessel.startswith(hashlib.sha256(pdf.read_bytes()).hexdigest()[:16])


def test_an_own_pdf_is_not_measured(datenordner, tmp_path, monkeypatch):
    entry = _built(datenordner, tmp_path)
    measured = []
    monkeypatch.setattr(pruefung.layout_check, "check", lambda pdf, part, headings=(): measured.append(part) or [])
    monkeypatch.setattr(pruefung.unterlagen, "eigener_lebenslauf", lambda daten, b: daten / "eigen.pdf")

    pruefung.pruefe(datenordner, entry, TODAY)

    assert "lebenslauf" not in measured and "anschreiben" in measured


def test_the_headings_of_the_cv_reach_the_check(datenordner, tmp_path, monkeypatch):
    cv = yaml.safe_load((datenordner / "cv.yaml").read_text(encoding="utf-8"))
    cv["x-beschriftungen"] = {"lehre": "Schnupperlehren"}
    (datenordner / "cv.yaml").write_text(yaml.safe_dump(cv, allow_unicode=True), encoding="utf-8")
    entry = _built(datenordner, tmp_path)
    asked = {}
    monkeypatch.setattr(pruefung.layout_check, "check",
                        lambda pdf, part, headings=(): asked.setdefault(part, list(headings)) and [])

    pruefung.pruefe(datenordner, entry, TODAY)

    assert "Schnupperlehren" in asked["lebenslauf"]


def test_a_form_opens_only_after_the_person_confirmed_the_breach(server, tmp_path, monkeypatch):  # noqa: F811
    data = server.kontext.daten
    entry = _built(data, tmp_path)
    register = Register(data)
    register.speichere({**register.hole(entry["id"]), "status": "Bewerben", "link": "https://example.ch/stelle"})
    letter_approval.approve(data, register.hole(entry["id"]), TODAY)
    _breach(monkeypatch)
    monkeypatch.setattr(pruefung, "pruefe_anschreiben_text", lambda *a, **k: [])
    monkeypatch.setattr(pruefung, "contact_person_findings", lambda *a: [])

    _, refused = post(server, "/api/bewerben/start", {"ids": [entry["id"]]})
    key = next(f["schluessel"] for f in _findings(server, entry["id"]) if f["schluessel"])
    status, confirmed = post(server, "/api/pruefung/bestaetigen", {"id": entry["id"], "schluessel": key})
    _, opened = post(server, "/api/bewerben/start", {"ids": [entry["id"]]})

    assert refused["bereit"] == [] and "Lebenslauf, Seite 2" in refused["abgelehnt"][0]["grund"]
    assert "bestätigen" in refused["abgelehnt"][0]["grund"]
    assert status == 200 and any(f["schluessel"] == key and f["bestaetigt"] for f in confirmed["befunde"])
    assert opened["abgelehnt"] == [] and [r["id"] for r in opened["bereit"]] == [entry["id"]]


def _findings(server, entry_id: str) -> list[dict]:  # noqa: F811  (server is the fixture's value)
    status, _, content = get(server, "/api/pruefung", id=entry_id)
    assert status == 200
    return json.loads(content)["befunde"]


def test_a_confirmation_holds_only_for_that_pdf(datenordner, tmp_path, monkeypatch):
    entry = _built(datenordner, tmp_path)
    _breach(monkeypatch)
    [found] = [f for f in pruefung.pruefe(datenordner, entry, TODAY) if f.schluessel]

    layout_confirmed.confirm(datenordner, entry, found.schluessel, [found.schluessel])
    confirmed = [f for f in pruefung.pruefe(datenordner, entry, TODAY) if f.schluessel]
    pdf = unterlagen.wirksame_pdfs(datenordner, entry)["lebenslauf"]
    pdf.write_bytes(pdf.read_bytes() + b"\n% neu gebaut\n")
    rebuilt = [f for f in pruefung.pruefe(datenordner, entry, TODAY) if f.schluessel]

    assert confirmed[0].bestaetigt
    assert not rebuilt[0].bestaetigt


def test_only_a_current_breach_can_be_confirmed(datenordner, tmp_path):
    entry = _built(datenordner, tmp_path)

    with pytest.raises(ValueError, match=layout_confirmed.UNKNOWN):
        layout_confirmed.confirm(datenordner, entry, "abc:fuellung:2", [])


def test_nothing_is_confirmed_after_sending(datenordner, tmp_path):
    entry = {**_built(datenordner, tmp_path), "versand": {"datum": "2026-10-20"}}

    with pytest.raises(ValueError, match=layout_confirmed.ALREADY_SENT):
        layout_confirmed.confirm(datenordner, entry, "abc:fuellung:2", ["abc:fuellung:2"])


def test_a_pdf_that_cannot_be_measured_still_waits_for_the_person(tmp_path, monkeypatch):
    def broken(pdf, part, headings=()):
        raise ValueError("kaputte Schrift")
    monkeypatch.setattr(pruefung.layout_check, "check", broken)

    found = pruefung.layout_findings(pdf_of(tmp_path, lines(5)), "anschreiben")

    assert [(f.stufe, bool(f.schluessel)) for f in found] == [("hinweis", True)]
    assert found[0].text.startswith("Anschreiben: Der Satz der Seiten liess sich nicht messen (kaputte Schrift).")
