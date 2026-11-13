"""Region, Pensum, exclusions and the title filter, changed on Suche einstellen (#286, G64)."""
import json
import pathlib

import pytest

import search_frame
import search_plan
from test_ai_tasks import VORLAGEN
from test_app import get, post, server  # noqa: F401  (server is a fixture)

SEITEN = pathlib.Path(__file__).resolve().parents[1] / "seiten"
JOB = (VORLAGEN / "suchprofil.md").read_text(encoding="utf-8")
APPRENTICESHIP = (VORLAGEN / "suchprofil-lehrstelle.md").read_text(encoding="utf-8")


def changed_lines(before: str, after: str) -> list[tuple[str, str]]:
    return [(old, new) for old, new in zip(before.split("\n"), after.split("\n")) if old != new]


def test_the_values_are_read_as_written_for_editing():
    values = search_frame.values(JOB)
    assert values["kantone"] == ["BE", "SO"]
    assert values["pensum"] == "80–100%"
    assert values["ausschluss"] == ["Bildung ohne IT-Bezug", "Recruiting"]
    assert "Entwickler/Developer/Engineer" in values["titel_positiv"]  # one entry, as the person wrote it
    assert values["titel_ausschluss"][:2] == ["Praktikum", "Lehrstelle"]
    apprenticeship = search_frame.values(APPRENTICESHIP)
    assert (apprenticeship["wohnort"], apprenticeship["kantone"], apprenticeship["umkreis_km"]) == ("Bern", ["BE"], 25)


def test_a_change_replaces_only_its_line_and_keeps_the_label():
    changed = search_frame.with_values(JOB, {"kantone": ["ZH", "AG"], "pensum": "60–80 %"})
    assert changed_lines(JOB, changed) == [("- Kantone (job-room): BE, SO", "- Kantone (job-room): ZH, AG"),
                                           ("- Pensum: 80–100%", "- Pensum: 60–80 %")]


def test_an_indented_exclusion_keeps_its_place_and_indentation():
    changed = search_frame.with_values(JOB, {"ausschluss": ["Schichtarbeit", "Pikettdienst"]})
    assert changed_lines(JOB, changed) == [("   - Ausschluss: Bildung ohne IT-Bezug, Recruiting",
                                            "   - Ausschluss: Schichtarbeit, Pikettdienst")]


def test_the_title_filter_is_written_where_the_search_reads_it():
    changed = search_frame.with_values(JOB, {"titel_positiv": ["Python", "Entwickler/Developer"],
                                             "titel_ausschluss": ["Praktikum"]})
    plan = search_plan.parse(changed)
    assert plan.title_positive == ("Python", "Entwickler", "Developer")
    assert plan.title_exclude == ("Praktikum",)


def test_an_empty_list_removes_its_line():
    changed = search_frame.with_values(JOB, {"titel_ausschluss": []})
    assert "- Ausschluss: Praktikum" not in changed
    assert search_plan.parse(changed).title_exclude == ()
    assert len(changed.split("\n")) == len(JOB.split("\n")) - 1


def test_a_missing_line_and_section_are_added():
    profile = "# Suchprofil\n\n## Region\n- Wohnort: Bern\n\n## Keywords\n- Kernliste: Python\n"
    changed = search_frame.with_values(profile, {"kantone": ["BE"], "pensum": "100 %", "titel_ausschluss": ["Praktikum"]})
    assert search_plan.section_lines(changed, "## Region") == ["- Wohnort: Bern", "- Kantone (job-room): BE"]
    assert search_plan.section_lines(changed, "## Rahmen") == ["- Pensum: 100 %"]
    assert search_plan.section_lines(changed, "## Titelfilter") == ["- Ausschluss: Praktikum"]
    plan = search_plan.parse(changed)
    assert (plan.cantons, plan.title_exclude) == (("BE",), ("Praktikum",))


def test_the_apprenticeship_region_changes_home_radius_and_cantons():
    changed = search_frame.with_values(APPRENTICESHIP, {"wohnort": "Thun", "umkreis_km": 50, "kantone": ["BE", "FR"]})
    plan = search_plan.parse(changed)
    assert (plan.places, plan.radius_km, plan.cantons) == (("Thun",), 50, ("BE", "FR"))
    assert "- Umkreis: 50 km" in changed and "- Kantone: BE, FR" in changed


def test_whitespace_and_line_breaks_cannot_reach_another_line():
    changed = search_frame.with_values(JOB, {"pensum": "80 %\n## Titelfilter\n- Positiv: Koch"})
    assert "- Pensum: 80 % ## Titelfilter - Positiv: Koch" in changed
    assert search_plan.parse(changed).title_positive == search_plan.parse(JOB).title_positive


@pytest.mark.parametrize("change, message", [
    ({"kantone": ["XY"]}, "Kanton"),
    ({"kantone": "BE"}, "Kantone"),
    ({"pensum": ""}, "Pensum"),
    ({"wohnort": "  "}, "Wohnort"),
    ({"pensum": "x" * 81}, "80 Zeichen"),
    ({"titel_positiv": [f"Wort{n}" for n in range(31)]}, "30"),
    ({"ausschluss": ["ok", 3]}, "Ausschl"),
    ({"umkreis_km": 2}, "km"),
    ({"unbekannt": "x"}, "Unbekannt"),
    ({}, "Nichts"),
])
def test_a_change_the_search_cannot_take_is_refused(change, message):
    with pytest.raises(ValueError, match=message):
        search_frame.with_values(JOB if not {"umkreis_km", "wohnort"} & set(change) else APPRENTICESHIP, change)


@pytest.mark.parametrize("change", [{"pensum": "80 %"}, {"ausschluss": ["Schicht"]}, {"titel_positiv": ["Koch"]}])
def test_an_apprenticeship_has_no_workload_exclusions_or_title_filter(change):
    with pytest.raises(ValueError, match="Stellensuche"):
        search_frame.with_values(APPRENTICESHIP, change)


def test_a_job_search_needs_no_home():
    changed = search_frame.with_values(JOB.replace("- Orte", "- Wohnort: Bern\n- Orte"), {"wohnort": ""})
    assert changed == JOB


def test_a_job_profile_has_no_radius():
    with pytest.raises(ValueError, match="Lehrstellen"):
        search_frame.with_values(JOB, {"umkreis_km": 25})


def test_the_page_saves_to_the_profile_with_drafts_and_the_next_plan_uses_it(server):  # noqa: F811
    path = server.kontext.daten / "suchprofil.md"
    path.write_text(JOB, encoding="utf-8")
    status, answer = post(server, "/api/suche/rahmen", {"kantone": ["ZH"], "titel_ausschluss": ["Praktikum", "Sales"]})
    assert status == 200
    assert answer["werte"]["kantone"] == ["ZH"] and answer["titel_ausschluss"] == ["Praktikum", "Sales"]
    text = path.read_text(encoding="utf-8")
    assert "- Kantone (job-room): ZH" in text and "- Ausschluss: Praktikum, Sales" in text
    drafts = server.kontext.ablage.liste(path)
    assert len(drafts) >= 2  # before and after
    plan = json.loads(get(server, "/api/suche/plan")[2])["plan"]
    assert plan["kantone"] == ["ZH"] and plan["titel_ausschluss"] == ["Praktikum", "Sales"]


def test_the_earlier_state_stays_as_a_draft(server):  # noqa: F811
    path = server.kontext.daten / "suchprofil.md"
    path.write_text(JOB, encoding="utf-8")
    assert post(server, "/api/suche/rahmen", {"pensum": "50 %"})[0] == 200
    contents = [server.kontext.ablage.inhalt(eintrag.id) for eintrag in server.kontext.ablage.liste(path)]
    assert JOB.encode("utf-8") in contents and path.read_bytes() in contents


def test_a_refused_change_leaves_the_profile_alone(server):  # noqa: F811
    path = server.kontext.daten / "suchprofil.md"
    path.write_text(JOB, encoding="utf-8")
    status, answer = post(server, "/api/suche/rahmen", {"kantone": ["XY"]})
    assert status == 400 and "Kanton" in answer["fehler"]
    assert path.read_text(encoding="utf-8") == JOB


def test_without_a_profile_nothing_is_written(server):  # noqa: F811
    status, answer = post(server, "/api/suche/rahmen", {"pensum": "80 %"})
    assert status == 400 and "Meine Angaben" in answer["fehler"]
    assert not (server.kontext.daten / "suchprofil.md").exists()


def test_the_frame_says_the_kind_and_the_values_to_edit(server):  # noqa: F811
    (server.kontext.daten / "suchprofil.md").write_text(APPRENTICESHIP, encoding="utf-8")
    frame = json.loads(get(server, "/api/suche/rahmen")[2])
    assert frame["art"] == search_plan.KIND_APPRENTICESHIP and frame["werte"]["wohnort"] == "Bern"


def test_neither_the_extension_nor_claude_can_change_the_frame():
    desktop = pathlib.Path(__file__).resolve().parents[2] / "desktop"
    for name in ("native_host.py", "mcp_tools.py"):
        assert "/api/suche/rahmen" not in (desktop / name).read_text(encoding="utf-8"), name


def test_the_cards_are_edited_on_the_page_instead_of_in_meine_angaben():
    html = (SEITEN / "suche-einstellen.html").read_text(encoding="utf-8")
    for gone in ("/angaben#feld=searchJob.cantons", "/angaben#feld=searchJob.exclusions", "/angaben#feld=searchJob.titleExclude"):
        assert gone not in html, gone
    for form in ("region-form", "nicht-form", "titelfilter-form"):
        assert f'id="{form}"' in html, form
    assert '<script src="/suche-rahmen.js"></script>' in html
    assert '<script src="/suche-rahmen-logik.js"></script>' in html


def test_every_field_the_script_reads_is_one_element_of_the_page():
    import re
    html = (SEITEN / "suche-einstellen.html").read_text(encoding="utf-8")
    script = (SEITEN / "suche-rahmen.js").read_text(encoding="utf-8")
    ids = re.findall(r'id="([^"]+)"', html)
    assert sorted({i for i in ids if ids.count(i) > 1}) == []
    named = set(re.findall(r'\$\("([^"$]+)"\)', script))
    for karte in ("region", "nicht", "titelfilter"):
        named |= {f"{karte}-{teil}" for teil in ("form", "aendern", "abbrechen", "meldung")}
    assert named - set(ids) == set()
