"""Presets of Meine Angaben and the setup (#218): fewer fields block taking over, nothing typed is overwritten."""
import datetime
import json
import re
import shutil
import subprocess

import pytest

import build_template
import import_bundle
import validation
from form_cases import ROOT, base_bundle

TODAY = datetime.date(2026, 11, 2)
REPO = ROOT.parent
PRESETS_JS = ROOT / "src" / "presets.js"
SETUP_PAGE = REPO / "bewerbungen" / "seiten" / "einrichtung.html"
SETUP_SCRIPT = REPO / "bewerbungen" / "seiten" / "einrichtung.js"
pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node is needed for the page logic")


def run_presets(state: dict, section_ids: list[str] | None = None) -> dict:
    """The state after withPresets in presets.js, as the page computes it."""
    script = (
        "const fs = require('node:fs');"
        f"const {{ withPresets }} = require({json.dumps(str(PRESETS_JS))});"
        f"const form = JSON.parse(fs.readFileSync({json.dumps(str(ROOT / 'form.json'))}, 'utf8'));"
        "const [state, ids] = JSON.parse(process.argv[1]);"
        "const result = withPresets(form, state, ids);"
        "process.stdout.write(JSON.stringify({ same: result === state, state: result }));"
    )
    done = subprocess.run(["node", "-e", script, json.dumps([state, section_ids])],
                          capture_output=True, text=True, check=True, timeout=30)
    return json.loads(done.stdout)


def empty_job(city: str = "Bern") -> dict:
    return {"track": "job", "data": {"person": {"name": "Erika Beispiel", "city": city, "email": "erika@example.ch"}}}


def required_errors(form: dict, state: dict) -> set[str]:
    bundle = {"format": form["format"], "version": form["version"], "track": state["track"], "data": state["data"]}
    return {e.path for e in validation.validate_bundle(form, bundle) if e.code == "required"}


def test_an_empty_job_form_blocks_on_far_fewer_fields_with_presets(form):
    before = required_errors(form, empty_job())

    after = required_errors(form, run_presets(empty_job())["state"])

    for path in ("searchJob.home", "searchJob.workload", "searchJob.start", "style.address", "style.tone",
                 "style.opening", "style.closing"):
        assert path in before and path not in after


def test_presets_take_the_ort_and_the_first_options_of_the_track(form):
    job = run_presets(empty_job("Thun"))["state"]["data"]
    apprenticeship = run_presets({**empty_job("Thun"), "track": "apprenticeship"})["state"]["data"]

    assert job["searchJob"] == {"home": "Thun", "workload": "80–100 %", "start": "nach Vereinbarung"}
    assert job["style"] == {
        "address": "Sie-Form; Du-Form, wenn das Inserat duzt",
        "tone": "Sachlich und freundlich",
        "opening": "Mit grossem Interesse habe ich Ihr Inserat für … gelesen.",
        "closing": "Über ein persönliches Gespräch freue ich mich.",
        "place": "Thun",
    }
    assert apprenticeship["searchApprenticeship"] == {"home": "Thun"}
    assert apprenticeship["style"]["tone"] == "Freundlich und offen"
    assert "address" not in apprenticeship["style"]


def test_what_the_person_typed_or_emptied_stays():
    state = empty_job()
    state["data"]["searchJob"] = {"workload": "60 %", "start": ""}
    state["data"]["style"] = {"tone": "Eigener Ton", "place": "Biel"}

    data = run_presets(state)["state"]["data"]

    assert data["searchJob"] == {"workload": "60 %", "start": "", "home": "Bern"}
    assert data["style"]["tone"] == "Eigener Ton" and data["style"]["place"] == "Biel"


def test_without_an_ort_the_place_waits_and_only_named_sections_are_filled():
    no_city = run_presets({"track": "job", "data": {}})["state"]["data"]
    only_search = run_presets(empty_job(), ["searchJob", "frame"])["state"]["data"]

    assert "home" not in no_city["searchJob"] and "place" not in no_city["style"]
    assert "searchJob" in only_search and "style" not in only_search


def test_a_complete_state_comes_back_unchanged():
    done = run_presets(empty_job())["state"]

    assert run_presets(done)["same"] is True
    assert run_presets({"track": None, "data": {}})["same"] is True


def test_the_page_fills_presets_on_the_step_it_shows():
    app = (ROOT / "src" / "app.js").read_text(encoding="utf-8")
    page = build_template.build(app=True)

    assert "fillPresets(all[step]);" in app
    assert "function withPresets(" in page


def test_verfuegbar_ab_is_no_longer_asked_for_jobs(form):
    frame = next(s for s in form["sections"] if s["id"] == "frame")
    availability = next(f for f in frame["fields"] if f["id"] == "availability")

    assert availability["hiddenFor"] == ["job"]
    shown = subprocess.run(
        ["node", "-e", "const m = require(process.argv[1]); const f = JSON.parse(require('node:fs').readFileSync("
         "process.argv[2], 'utf8')); const s = f.sections.find((x) => x.id === 'frame');"
         "process.stdout.write(JSON.stringify([m.shownFields(s, 'job').map((x) => x.id),"
         " m.shownFields(s, 'apprenticeship').map((x) => x.id), m.fieldsFor(s, 'job').map((x) => x.id)]));",
         str(ROOT / "src" / "model.js"), str(ROOT / "form.json")],
        capture_output=True, text=True, check=True, timeout=30)
    job_shown, apprenticeship_shown, job_kept = json.loads(shown.stdout)
    assert "availability" not in job_shown
    assert "availability" in apprenticeship_shown and "availability" in job_kept


def test_an_old_verfuegbar_ab_is_kept_in_the_import(tmp_path):
    bundle = base_bundle("job")
    bundle["data"]["frame"]["availability"] = "1. April"
    bundle["data"]["searchJob"]["start"] = "nach Vereinbarung"

    import_bundle.import_answers(tmp_path / "alt", bundle, TODAY)
    del bundle["data"]["frame"]["availability"]
    import_bundle.import_answers(tmp_path / "neu", bundle, TODAY)

    old = (tmp_path / "alt" / "anschreiben" / "bausteine.md").read_text(encoding="utf-8")
    new = (tmp_path / "neu" / "anschreiben" / "bausteine.md").read_text(encoding="utf-8")
    assert "- Verfügbar ab: 1. April" in old
    assert "- Verfügbar ab: nach Vereinbarung" in new


def test_an_emptied_ort_im_datum_is_taken_over_as_none(form, tmp_path):
    """The page now sends an emptied preset field as "" (#230); the import takes that as no place, not as an error."""
    bundle = base_bundle("job")
    bundle["data"].setdefault("style", {})["place"] = ""
    assert not [e for e in validation.validate_bundle(form, bundle) if e.path.startswith("style.place")]

    import_bundle.import_answers(tmp_path, bundle, TODAY)

    written = "".join(p.read_text(encoding="utf-8") for p in tmp_path.rglob("*.md"))
    assert "Gruss:" in written and "Ort im Datum" not in written


def test_rav_is_preset_to_nein_in_the_setup_and_keeps_its_explanation():
    page = SETUP_PAGE.read_text(encoding="utf-8")
    script = SETUP_SCRIPT.read_text(encoding="utf-8")

    assert re.search(r'name="rav" value="nein" checked', page)
    assert not re.search(r'name="rav" value="ja" checked', page)
    assert "Mit Ja hilft die App beim Eintragen der Arbeitsbemühungen im Job-Room." in page
    assert 'gesucht === "lehrstelle" ? "nein" : "ja"' not in script
    assert 'rav: true, gewaehlt: false' not in script


def test_built_pages_are_current():
    assert build_template.main(["--check"]) == 0
