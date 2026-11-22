"""G110, #386: a keyword with required words, «Berufsbildner (nur mit Informatik, ICT)», is one line of «Stichworte
für die Suche» in Meine Angaben, and saving keeps its remark. All data is invented.
"""
import datetime

import basics_read
import import_bundle
import markdown_files
import search_plan
from basics_slots import JOB, PROFILE
from form_cases import base_bundle

TODAY = datetime.date(2026, 11, 22)
BROAD = "Berufsbildner (nur mit Informatik, ICT)"


def bundle_with(keywords: list[str]) -> dict:
    bundle = base_bundle(JOB)
    return {**bundle, "data": {**bundle["data"], "searchJob": {**bundle["data"]["searchJob"], "keywords": keywords}}}


def written(folder, keywords: list[str]) -> str:
    text = markdown_files.search_profile(bundle_with(keywords)["data"], JOB, "")
    folder.mkdir(parents=True, exist_ok=True)
    (folder / PROFILE).write_text(text, encoding="utf-8")
    return text


def test_the_form_writes_the_remark_with_its_term(tmp_path):
    text = written(tmp_path, ["Kursplaner", BROAD])
    assert f"- Kernliste: Kursplaner, {BROAD}\n" in text
    assert search_plan.parse(text).keywords == ("Kursplaner", "Berufsbildner")


def test_the_form_reads_a_term_with_its_remark_as_one_line(form, tmp_path):
    written(tmp_path, ["Kursplaner", BROAD, "Lerncoach"])

    answers = basics_read.read_back(form, tmp_path, JOB, None)

    assert answers["daten"]["searchJob"]["keywords"] == ["Kursplaner", BROAD, "Lerncoach"]


def test_saving_meine_angaben_keeps_the_remark(form, tmp_path):
    written(tmp_path, ["Kursplaner", BROAD])
    base = basics_read.read_back(form, tmp_path, JOB, None)["daten"]

    import_bundle.import_answers(tmp_path, bundle_with(["Kursplaner", BROAD, "Lerncoach"]), TODAY, force=True, base=base)

    assert f"- Kernliste: Kursplaner, {BROAD}, Lerncoach\n" in (tmp_path / PROFILE).read_text(encoding="utf-8")
