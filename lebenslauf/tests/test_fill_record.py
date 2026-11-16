"""Each build says how it balanced its pages (G93, #324): the density chosen per part, returned by the build and kept
beside the PDF with its fingerprint, so the check can name it for exactly this file. All data is invented."""
import json
import shutil

import pytest

import anschreiben
import build
import dossier
import fill_record
import page_fill

DATA = build.ROOT / "data"
CHOSEN = 2


@pytest.fixture
def chosen_level(monkeypatch):
    """Every part gets the same level, so the test knows what the build should report."""
    monkeypatch.setattr(page_fill, "choose", lambda probe, limit=None: CHOSEN)


def test_the_cv_build_returns_its_level_and_keeps_it_beside_the_pdf(tmp_path, chosen_level):
    built = build.run([str(DATA / "beispiel.yaml"), "--build-dir", str(tmp_path / "b"), "-o", str(tmp_path / "cv.pdf")])

    assert built.pdf == tmp_path / "cv.pdf" and built.pdf.is_file()
    assert built.levels == {"cv": CHOSEN}
    assert fill_record.read(built.pdf) == {"cv": CHOSEN}


def test_the_letter_build_returns_its_level_and_keeps_it_beside_the_pdf(tmp_path, chosen_level):
    built = anschreiben.run([str(DATA / "anschreiben-beispiel.yaml"), "--build-dir", str(tmp_path / "b"),
                             "-o", str(tmp_path / "brief.pdf")])

    assert built.levels == {"letter": CHOSEN}
    assert fill_record.read(built.pdf) == {"letter": CHOSEN}


def test_main_still_returns_the_path_of_the_pdf(tmp_path):
    out = build.main([str(DATA / "beispiel.yaml"), "--build-dir", str(tmp_path / "b"), "-o", str(tmp_path / "cv.pdf")])

    assert out == tmp_path / "cv.pdf"
    assert set(fill_record.read(out)) == {"cv"}, "the level the design really got is kept too"


def test_the_dossier_names_the_levels_of_each_of_its_files(tmp_path, chosen_level):
    result = dossier.main([str(DATA / "dossier-beispiel.yaml"), "--build-dir", str(tmp_path / "b"),
                           "--out-dir", str(tmp_path / "out")])

    assert result.levels == {"dossier": {"letter": CHOSEN, "cv": CHOSEN}, "cv": {"cv": CHOSEN},
                             "letter": {"letter": CHOSEN}}
    assert fill_record.read(result.dossier) == {"letter": CHOSEN, "cv": CHOSEN}
    assert fill_record.read(result.cv) == {"cv": CHOSEN}
    assert fill_record.read(result.letter) == {"letter": CHOSEN}


def test_a_record_counts_only_for_the_pdf_it_was_written_for(tmp_path):
    pdf = tmp_path / "lebenslauf.pdf"
    pdf.write_bytes(b"%PDF-1.7 first build")
    fill_record.write(pdf, {"cv": 3})
    sent = tmp_path / "versendet" / "lebenslauf.pdf"
    sent.parent.mkdir()
    shutil.copyfile(pdf, sent)

    assert fill_record.read(pdf) == {"cv": 3}
    assert fill_record.read(sent) is None, "nothing lies beside the sent copy"
    assert fill_record.read(sent, built_as=pdf) == {"cv": 3}, "the record of the build it came from"
    pdf.write_bytes(b"%PDF-1.7 another build")
    assert fill_record.read(pdf) is None
    assert fill_record.read(sent, built_as=pdf) == {"cv": 3}, "the sent copy is still the file the record is about"


@pytest.mark.parametrize("content", [
    "not json",
    "[]",
    json.dumps({"levels": {"cv": 1}}),
    json.dumps({"pdf": "FINGERPRINT", "levels": {"cv": "2"}}),
    json.dumps({"pdf": "FINGERPRINT", "levels": {"cv": True}}),
    json.dumps({"pdf": "FINGERPRINT", "levels": {"cv": 9}}),
    json.dumps({"pdf": "FINGERPRINT", "levels": {"photo": 1}}),
    json.dumps({"pdf": "FINGERPRINT", "levels": []}),
])
def test_a_broken_or_strange_record_counts_as_none(tmp_path, content):
    pdf = tmp_path / "lebenslauf.pdf"
    pdf.write_bytes(b"%PDF-1.7")
    fill_record.path_for(pdf).write_text(content.replace("FINGERPRINT", fill_record.fingerprint(pdf)),
                                         encoding="utf-8")

    assert fill_record.read(pdf) is None


def test_each_level_says_how_the_page_fill_changed_the_setting():
    levels = (*page_fill.WIDER, 0, *page_fill.TIGHTER)

    assert {level: page_fill.change(level) for level in levels} == {
        -1: "wider", -2: "wider", -3: "wider", -4: "wider", -5: "wider", 0: None,
        1: "slightly-tighter", 2: "slightly-tighter", 3: "tighter", 4: "tighter", 5: "tightest"}
