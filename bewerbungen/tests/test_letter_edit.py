"""Editing the letter paragraph by paragraph on the application page (G94, #332): the route merges into anschreiben.yaml,
keeps drafts before and after, refuses a changed, sent or own letter, and estimates lines like the built PDF."""
import json
import math

import pytest
import yaml

import anschreiben
import build
import letter_approval
import letter_edit
import pdf_boxes
import unterlagen
from register import Register
from sample_folder import BRIEF_ID
from test_app import get, post, server  # noqa: F401  (server is a fixture)

ROUTE = "/api/bewerbung/anschreiben"
PARAGRAPHS = ["Erster Absatz, frei erfunden.", "Zweiter Absatz mit etwas mehr Text, ebenfalls frei erfunden."]


def details(s) -> dict:
    _, _, body = get(s, "/api/bewerbung", id=BRIEF_ID)
    return json.loads(body)


def source(s):
    return unterlagen.letter_source(s.kontext.daten, BRIEF_ID)


def body_for(s, **changes) -> dict:
    letter = details(s)["anschreiben_text"]
    return {"betreff": letter["betreff"], "anrede": letter["anrede"], "absaetze": letter["absaetze"],
            "gruss": letter["gruss"], "fingerabdruck": letter["fingerabdruck"], **changes}


def drafts(s) -> list[str]:
    return [d.beschreibung for d in s.kontext.ablage.liste(source(s))]


def test_the_page_data_carries_the_fingerprint_and_the_characters_per_line(server):  # noqa: F811
    letter = details(server)["anschreiben_text"]
    assert letter["fingerabdruck"] == letter_approval.fingerprint(source(server))
    assert letter["zeichen_pro_zeile"] == letter_edit.CHARS_PER_LINE


def test_saving_merges_the_fields_and_keeps_every_other_key_in_its_order(server):  # noqa: F811
    before = yaml.safe_load(source(server).read_text(encoding="utf-8"))
    status, answer = post(server, ROUTE, body_for(server, betreff="Neuer Betreff", absaetze=PARAGRAPHS,
                                                  gruss="Beste Grüsse"), id=BRIEF_ID)
    assert status == 200 and answer["geaendert"] is True
    after = yaml.safe_load(source(server).read_text(encoding="utf-8"))
    assert list(after) == list(before), "no key added, dropped or moved"
    assert {k: v for k, v in after.items() if k not in ("betreff", "text", "gruss")} == \
        {k: v for k, v in before.items() if k not in ("betreff", "text", "gruss")}
    assert after["betreff"] == "Neuer Betreff" and after["gruss"] == "Beste Grüsse"
    assert after["text"] == "\n\n".join(PARAGRAPHS)


def test_the_text_is_written_as_a_literal_block(server):  # noqa: F811
    post(server, ROUTE, body_for(server, absaetze=PARAGRAPHS), id=BRIEF_ID)
    written = source(server).read_text(encoding="utf-8")
    assert f"text: |-\n  {PARAGRAPHS[0]}\n\n  {PARAGRAPHS[1]}\n" in written


def test_fields_are_trimmed_and_empty_paragraphs_dropped(server):  # noqa: F811
    post(server, ROUTE, body_for(server, betreff="  Betreff  ", absaetze=["  Eins. ", "", "   ", "Zwei."]), id=BRIEF_ID)
    after = yaml.safe_load(source(server).read_text(encoding="utf-8"))
    assert after["betreff"] == "Betreff"
    assert anschreiben.absaetze(after["text"]) == ["Eins.", "Zwei."]


def test_a_blank_line_typed_inside_a_field_splits_it_on_the_next_load(server):  # noqa: F811
    post(server, ROUTE, body_for(server, absaetze=["Eins.\n\nZwei.", "Drei."]), id=BRIEF_ID)
    assert details(server)["anschreiben_text"]["absaetze"] == ["Eins.", "Zwei.", "Drei."]


def test_saving_keeps_a_draft_before_and_after(server):  # noqa: F811
    old = source(server).read_bytes()
    post(server, ROUTE, body_for(server, absaetze=PARAGRAPHS), id=BRIEF_ID)
    kept = server.kontext.ablage.liste(source(server))
    assert [d.beschreibung for d in kept] == ["Anschreiben geändert", "Stand vor: Anschreiben geändert"]
    assert server.kontext.ablage.inhalt(kept[1].id) == old
    assert server.kontext.ablage.inhalt(kept[0].id) == source(server).read_bytes()


def test_nothing_changed_writes_nothing_and_keeps_no_draft(server):  # noqa: F811
    old = source(server).read_bytes()
    status, answer = post(server, ROUTE, body_for(server), id=BRIEF_ID)
    assert status == 200 and answer["geaendert"] is False
    assert source(server).read_bytes() == old
    assert drafts(server) == []


def test_saving_voids_the_approval(server):  # noqa: F811
    post(server, "/api/anschreiben/freigeben", {"id": BRIEF_ID})
    assert details(server)["anschreiben_freigabe"]["freigegeben"] is True
    post(server, ROUTE, body_for(server, absaetze=PARAGRAPHS), id=BRIEF_ID)
    assert details(server)["anschreiben_freigabe"]["freigegeben"] is False


def test_a_letter_changed_since_loading_is_refused_with_409(server):  # noqa: F811
    stale = body_for(server, absaetze=PARAGRAPHS)
    source(server).write_text(source(server).read_text(encoding="utf-8") + "\n# neuer Entwurf\n", encoding="utf-8")
    changed = source(server).read_bytes()
    status, answer = post(server, ROUTE, stale, id=BRIEF_ID)
    assert status == 409 and answer["fehler"] == letter_edit.CHANGED
    assert source(server).read_bytes() == changed
    assert drafts(server) == []


def test_a_sent_application_is_refused(server):  # noqa: F811
    register = Register(server.kontext.daten)
    entry = register.hole(BRIEF_ID)
    register.speichere({**entry, "versand": {"datum": "2026-10-26", "art": "elektronisch", "dateien": {}}})
    old = source(server).read_bytes()
    status, answer = post(server, ROUTE, body_for(server, absaetze=PARAGRAPHS), id=BRIEF_ID)
    assert status == 400 and answer["fehler"] == letter_approval.ALREADY_SENT
    assert source(server).read_bytes() == old


def test_an_own_letter_is_refused(server):  # noqa: F811
    unterlagen.own_letter_path(server.kontext.daten, BRIEF_ID).write_bytes(b"%PDF-1.4\n%eigenes Anschreiben\n")
    old = source(server).read_bytes()
    status, answer = post(server, ROUTE, body_for(server, absaetze=PARAGRAPHS), id=BRIEF_ID)
    assert status == 400 and answer["fehler"] == letter_approval.OWN_LETTER
    assert source(server).read_bytes() == old


def test_a_letter_without_text_is_refused(server):  # noqa: F811
    status, answer = post(server, ROUTE, body_for(server, absaetze=["", "  "]), id=BRIEF_ID)
    assert status == 400 and answer["fehler"] == letter_edit.NO_PARAGRAPH


def test_a_letter_the_build_refuses_is_not_written(server):  # noqa: F811
    old = source(server).read_bytes()
    status, answer = post(server, ROUTE, body_for(server, betreff="", absaetze=PARAGRAPHS), id=BRIEF_ID)
    assert status == 400 and "betreff" in answer["fehler"]
    assert source(server).read_bytes() == old and drafts(server) == []


@pytest.mark.parametrize("changes", [
    {"absaetze": ["Absatz."] * (letter_edit.MAX_PARAGRAPHS + 1)},
    {"absaetze": ["x" * (letter_edit.MAX_PARAGRAPH_CHARS + 1)]},
    {"betreff": "x" * (letter_edit.MAX_FIELD_CHARS + 1)},
    {"anrede": "x" * (letter_edit.MAX_FIELD_CHARS + 1)},
    {"gruss": "x" * (letter_edit.MAX_FIELD_CHARS + 1)},
    {"absaetze": "Ein Text statt einer Liste"},
    {"absaetze": ["Eins.", 2]},
    {"betreff": None},
    {"fingerabdruck": 5},
])
def test_types_and_limits_are_checked_at_the_boundary(server, changes):  # noqa: F811
    old = source(server).read_bytes()
    status, answer = post(server, ROUTE, body_for(server, **changes), id=BRIEF_ID)
    assert status == 400 and answer["fehler"]
    assert source(server).read_bytes() == old


def test_the_limits_themselves_are_allowed():
    edit = letter_edit.request_of({"betreff": "x" * letter_edit.MAX_FIELD_CHARS, "anrede": "Guten Tag",
                                   "absaetze": ["y" * letter_edit.MAX_PARAGRAPH_CHARS] * letter_edit.MAX_PARAGRAPHS,
                                   "gruss": "Gruss", "fingerabdruck": "abc"})
    assert len(edit.paragraphs) == letter_edit.MAX_PARAGRAPHS


def test_a_body_that_is_no_object_is_refused():
    with pytest.raises(ValueError):
        letter_edit.request_of(["betreff"])


# The line estimate against the built letter (±1 line per paragraph)

def _lines_per_paragraph(pdf, paragraphs: list[str]) -> list[int]:
    """How many lines each paragraph takes in the PDF, found by its text from the first to the last line."""
    rows = {}
    for page in pdf_boxes.read(pdf):
        for box in page.text:
            rows.setdefault((page.number, round(box.baseline)), []).append(box)
    lines = ["".join("".join(b.text for b in sorted(rows[key], key=lambda b: b.left)).split()) for key in sorted(rows)]
    counts, at = [], 0
    for paragraph in paragraphs:
        wanted = "".join(paragraph.split())
        at = next(i for i in range(at, len(lines)) if lines[i] and wanted.startswith(lines[i]))
        taken, count = "", 0
        while taken != wanted:
            taken += lines[at + count]
            count += 1
            assert wanted.startswith(taken), f"lines of «{paragraph[:30]}…» not found in order"
        counts.append(count)
        at += count
    return counts


def _estimate(paragraph: str) -> int:
    return math.ceil(len(paragraph) / letter_edit.CHARS_PER_LINE)


def _built_letter(tmp_path, letter: dict):
    path = tmp_path / "anschreiben.yaml"
    path.write_text(yaml.safe_dump({**letter, "lebenslauf": str(build.ROOT / "data" / "beispiel.yaml")},
                                   allow_unicode=True), encoding="utf-8")
    return anschreiben.main([str(path), "--build-dir", str(tmp_path / "build"), "-o", str(tmp_path / "brief.pdf")])


def test_the_estimate_is_within_one_line_of_the_example_letter(tmp_path):
    letter = yaml.safe_load((build.ROOT / "data" / "anschreiben-beispiel.yaml").read_text(encoding="utf-8"))
    paragraphs = anschreiben.absaetze(letter["text"])
    built = _lines_per_paragraph(_built_letter(tmp_path, letter), paragraphs)
    assert all(abs(_estimate(p) - n) <= 1 for p, n in zip(paragraphs, built, strict=True)), built


def test_the_estimate_holds_for_a_long_paragraph_too(tmp_path):
    letter = yaml.safe_load((build.ROOT / "data" / "anschreiben-beispiel.yaml").read_text(encoding="utf-8"))
    paragraphs = anschreiben.absaetze(letter["text"])
    paragraphs = [*paragraphs[:3], " ".join(paragraphs[:3]), paragraphs[3]]
    built = _lines_per_paragraph(_built_letter(tmp_path, {**letter, "text": "\n\n".join(paragraphs)}), paragraphs)
    assert built[3] >= 5, "the joined paragraph runs over several lines"
    assert all(abs(_estimate(p) - n) <= 1 for p, n in zip(paragraphs, built, strict=True)), built
