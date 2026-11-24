"""G125, #390: Meine Angaben keeps «- Nischen mit Remote ausserhalb der Region: aussortieren» under Region.

The switch lives on Suche einstellen; the form has no field for it, so neither merging the answers into the file nor
replacing the file may drop the line, also when Remote itself changes. All data is invented.
"""
import datetime

import basics_read
import import_bundle
import markdown_files
import search_plan
from basics_slots import JOB, PROFILE
from form_cases import base_bundle

TODAY = datetime.date(2026, 11, 24)
OFF_LINE = "- Nischen mit Remote ausserhalb der Region: aussortieren"


def bundle_with(remote: str) -> dict:
    bundle = base_bundle(JOB)
    data = bundle["data"]
    return {**bundle, "data": {**data, "searchJob": {**data["searchJob"], "keywords": ["Kursplaner"],
                                                       "cantons": ["BE"], "remote": remote}}}


def written_switched_off(folder) -> str:
    text = markdown_files.search_profile(bundle_with("ja")["data"], JOB, "")
    switched = text.replace("- Remote: ja\n", f"- Remote: ja\n{OFF_LINE}\n", 1)
    assert switched != text
    folder.mkdir(parents=True, exist_ok=True)
    (folder / PROFILE).write_text(switched, encoding="utf-8")
    return switched


def test_saving_meine_angaben_with_another_remote_keeps_the_line(form, tmp_path):
    written_switched_off(tmp_path)
    base = basics_read.read_back(form, tmp_path, JOB, None)["daten"]

    import_bundle.import_answers(tmp_path, bundle_with("nein"), TODAY, force=True, base=base)

    text = (tmp_path / PROFILE).read_text(encoding="utf-8")
    assert f"- Remote: nein\n{OFF_LINE}\n" in text
    assert search_plan.parse(text).niche_remote_kept is False


def test_replacing_the_profile_keeps_the_line_under_remote(tmp_path):
    written_switched_off(tmp_path)

    import_bundle.import_answers(tmp_path, bundle_with("teilweise"), TODAY, force=True)

    text = (tmp_path / PROFILE).read_text(encoding="utf-8")
    assert f"- Remote: teilweise\n{OFF_LINE}\n" in text
    assert search_plan.parse(text).niche_remote_kept is False
