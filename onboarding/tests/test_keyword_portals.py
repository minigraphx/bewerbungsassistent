"""G105, #376: Meine Angaben never merges or drops a line «- Nur <Portal>: <Begriff>» under Keywords.

The form knows only the core list; the line is the person's own and stays as written, whether the page merges its
answers into the file or replaces it. All data is invented.
"""
import datetime

import basics_read
import import_bundle
import markdown_files
import search_plan
from basics_slots import JOB, PROFILE
from form_cases import base_bundle

TODAY = datetime.date(2026, 11, 22)
LIMIT_LINE = "- Nur jobs.ch, job-room: Lernbegleiter, Kursleiter"


def written_with_limit(folder) -> str:
    data = base_bundle(JOB)["data"]
    text = markdown_files.search_profile({**data, "searchJob": {**data["searchJob"], "keywords": ["Kursplaner"]}}, JOB, "")
    limited = text.replace("- Kernliste: Kursplaner\n", f"- Kernliste: Kursplaner\n{LIMIT_LINE}\n", 1)
    assert limited != text
    folder.mkdir(parents=True, exist_ok=True)
    (folder / PROFILE).write_text(limited, encoding="utf-8")
    return limited


def bundle_with(keywords: list[str]) -> dict:
    bundle = base_bundle(JOB)
    return {**bundle, "data": {**bundle["data"], "searchJob": {**bundle["data"]["searchJob"], "keywords": keywords}}}


def test_the_form_shows_only_the_core_list_and_the_line_as_text_of_its_own(form, tmp_path):
    written_with_limit(tmp_path)

    answers = basics_read.read_back(form, tmp_path, JOB, None)

    assert answers["daten"]["searchJob"]["keywords"] == ["Kursplaner"]
    unknown = [group for group in answers["fremd"] if group["ueberschrift"] == "Keywords"]
    assert unknown and LIMIT_LINE in str(unknown)


def test_saving_meine_angaben_keeps_the_line_as_written(form, tmp_path):
    written_with_limit(tmp_path)
    base = basics_read.read_back(form, tmp_path, JOB, None)["daten"]

    import_bundle.import_answers(tmp_path, bundle_with(["Kursplaner", "Lerncoach"]), TODAY, force=True, base=base)

    text = (tmp_path / PROFILE).read_text(encoding="utf-8")
    assert f"- Kernliste: Kursplaner, Lerncoach\n{LIMIT_LINE}\n" in text
    assert search_plan.parse(text).as_dict()["nur_portale"] == {"Lernbegleiter": ["jobs.ch", "job-room"],
                                                                "Kursleiter": ["jobs.ch", "job-room"]}


def test_replacing_the_profile_keeps_the_line_and_merges_none_of_its_terms(tmp_path):
    written_with_limit(tmp_path)

    result = import_bundle.import_answers(tmp_path, bundle_with(["Kursplaner"]), TODAY, force=True)

    text = (tmp_path / PROFILE).read_text(encoding="utf-8")
    assert f"{LIMIT_LINE}\n" in text
    assert "- Kernliste: Kursplaner\n" in text
    assert result.kept_terms == ()
    assert search_plan.parse(text).as_dict()["nur_portale"] == {"Lernbegleiter": ["jobs.ch", "job-room"],
                                                                "Kursleiter": ["jobs.ch", "job-room"]}
