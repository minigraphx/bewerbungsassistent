"""Suggestions for professions (MIN-375): what the AI sees, what may come back, and how a choice reaches the search."""
import json
import pathlib
import re
import shutil
import threading

import pytest

import routes_ai
import search_plan
import search_terms
from ai import career, errors, tasks
from ai.connection import ACCESS_VARIABLE, KEY_VARIABLE, URL_VARIABLE
from test_ai_tasks import FakeMessages, VORLAGEN, gateway_for  # noqa: F401
from test_app import get, post, server  # noqa: F401  (server is a fixture)

ANSWERS = {"interests": "Ich arbeite gern mit den Händen.", "strengths": "geduldig", "avoid": "Büro"}
FIRST = {"profession": "Polymechaniker/in EFZ", "why": "Du arbeitest gern mit den Händen.", "daily": "Du fertigst Teile.",
         "check": "Prüfe in der Schnupperlehre, ob dir die Genauigkeit liegt."}
SECOND = {"profession": "Fachfrau/Fachmann Gesundheit EFZ", "why": "Du bist geduldig.", "daily": "Du pflegst Menschen.",
          "check": "Prüfe, ob dir die Nähe liegt."}


class Client:
    def __init__(self, reply):
        self.messages = FakeMessages(reply=reply)


@pytest.fixture
def folder(tmp_path):
    shutil.copy(VORLAGEN / "suchprofil-lehrstelle.md", tmp_path / "suchprofil.md")
    shutil.copytree(VORLAGEN / "anschreiben", tmp_path / "anschreiben")
    shutil.copy(VORLAGEN.parent / "lebenslauf" / "data" / "beispiel.yaml", tmp_path / "cv.yaml")
    return tmp_path


def recommend(folder, reply):
    client = Client(reply)
    gateway, material = gateway_for(folder, client)
    return career.recommend(gateway, material, ANSWERS), client


def test_task_has_its_model_and_limit():
    assert tasks.MODELS["career"] and tasks.MAX_TOKENS["career"]


def test_suggestions_come_back_clean(folder):
    result, _ = recommend(folder, {"recommendations": [FIRST, SECOND]})
    assert [r["profession"] for r in result["recommendations"]] == [FIRST["profession"], SECOND["profession"]]
    assert result["recommendations"][0]["why"] == FIRST["why"]
    assert "cost_usd" in result and result["model"]


def test_what_the_person_wrote_is_sent_as_data_and_their_name_is_not(folder):
    _, client = recommend(folder, {"recommendations": [FIRST]})
    sent = json.dumps(client.messages.calls, ensure_ascii=False)
    assert "Ich arbeite gern mit den Händen." in sent and "<angaben>" in sent
    assert "Lea Beispiel" not in sent


@pytest.mark.parametrize("name", ["Polymechaniker", "Studium Informatik", "x" * 120 + " EFZ", "A\nB EFZ", "## Region EFZ", "", None, 5])
def test_something_that_is_no_basic_training_is_dropped(folder, name):
    result, _ = recommend(folder, {"recommendations": [{**FIRST, "profession": name}, SECOND]})
    assert [r["profession"] for r in result["recommendations"]] == [SECOND["profession"]]


def test_the_same_profession_twice_counts_once_and_the_list_is_bounded(folder):
    many = [{**FIRST, "profession": f"Beruf {n} EFZ"} for n in range(career.MAX_RECOMMENDATIONS + 3)]
    result, _ = recommend(folder, {"recommendations": [FIRST, FIRST, *many]})
    names = [r["profession"] for r in result["recommendations"]]
    assert len(names) == career.MAX_RECOMMENDATIONS and len(set(names)) == len(names)


@pytest.mark.parametrize("reply", [{"recommendations": []}, {"recommendations": [{"profession": "Nichts"}]}, {"recommendations": "x"}, {}])
def test_an_answer_without_usable_suggestions_is_an_error_for_the_person(folder, reply):
    with pytest.raises(errors.AiError):
        recommend(folder, reply)


def test_a_suggestion_with_missing_text_is_dropped(folder):
    result, _ = recommend(folder, {"recommendations": [{"profession": "Koch/Köchin EFZ", "why": "", "daily": "x", "check": "y"}, SECOND]})
    assert [r["profession"] for r in result["recommendations"]] == [SECOND["profession"]]


def test_answers_are_checked():
    assert career.clean_answers({"interessen": " gern ", "staerken": "", "vermeiden": None}) == {"interests": "gern", "strengths": "", "avoid": ""}
    for bad in (None, "x", {"interessen": 5}, {"interessen": "x" * (career.MAX_TEXT + 1)}):
        with pytest.raises(ValueError):
            career.clean_answers(bad)


# The profile


def profile() -> str:
    return (VORLAGEN / "suchprofil-lehrstelle.md").read_text(encoding="utf-8")


def test_a_profession_is_added_at_the_end_of_the_list():
    changed = search_plan.with_profession(profile(), "Polymechaniker/in EFZ")
    plan = search_plan.parse(changed)
    assert plan.keywords[-1] == "Polymechaniker/in EFZ"
    assert len(plan.keywords) == len(search_plan.parse(profile()).keywords) + 1
    assert changed.count("## Region") == 1


def test_a_profession_that_is_there_is_not_added_twice():
    first = search_plan.parse(profile()).keywords[0]
    assert search_plan.with_profession(profile(), first) == profile()
    assert search_plan.with_profession(profile(), first.upper()) == profile()


def test_a_profile_without_the_list_gets_one():
    text = "# Suchprofil\n\n## Lehrbeginn\n- 2027\n\n## Region\n- Wohnort: Bern\n"
    plan = search_plan.parse(search_plan.with_profession(text, "Koch/Köchin EFZ"))
    assert plan.keywords == ("Koch/Köchin EFZ",)


def test_an_empty_list_gets_its_first_entry():
    text = "# Suchprofil\n\n## Berufe (mit Priorität)\n\n## Lehrbeginn\n- 2027\n\n## Region\n- Wohnort: Bern\n"
    assert search_plan.parse(search_plan.with_profession(text, "Koch/Köchin EFZ")).keywords == ("Koch/Köchin EFZ",)


def test_only_for_an_apprenticeship_profile():
    with pytest.raises(ValueError):
        search_plan.with_profession((VORLAGEN / "suchprofil.md").read_text(encoding="utf-8"), "Koch/Köchin EFZ")


# Routes


@pytest.fixture
def apprentice(server, monkeypatch):  # noqa: F811
    daten = server.kontext.daten
    shutil.copy(VORLAGEN / "suchprofil-lehrstelle.md", daten / "suchprofil.md")
    shutil.copytree(VORLAGEN / "anschreiben", daten / "anschreiben", dirs_exist_ok=True)
    for name in (URL_VARIABLE, ACCESS_VARIABLE):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(KEY_VARIABLE, "sk-test")
    return server


def known_profession() -> str:
    return search_plan.parse(profile()).keywords[0]


def test_route_marks_what_is_already_searched(apprentice, monkeypatch):
    reply = {"recommendations": [FIRST, {**SECOND, "profession": known_profession()}]}
    monkeypatch.setattr(routes_ai, "new_client", lambda: Client(reply))
    status, answer = post(apprentice, "/api/beruf/vorschlag", {"interessen": "Hände", "staerken": "geduldig"})
    assert status == 200
    assert [(r["beruf"], r["schon_gesucht"]) for r in answer["vorschlaege"]] == [(FIRST["profession"], False), (known_profession(), True)]
    assert set(answer["vorschlaege"][0]) == {"beruf", "warum", "alltag", "pruefen", "schon_gesucht", "schluessel"}


def test_route_needs_something_to_go_on(apprentice):
    for body in ({"interessen": "  ", "staerken": ""}, {"interessen": "Hände"}, {"staerken": "geduldig"}):
        status, answer = post(apprentice, "/api/beruf/vorschlag", body)
        assert status == 400 and "beidem" in answer["fehler"]


JOB_REPLY = {"recommendations": [
    {"profession": "Sachbearbeitung Administration", "why": "Sie organisieren gern.", "daily": "Sie bearbeiten Anfragen.", "check": "Achten Sie auf verlangte Abschlüsse."},
    {"profession": "Polymechaniker/in (EFZ), Bern", "why": "x", "daily": "x", "check": "x"},
]}


@pytest.fixture
def job_seeker(apprentice):
    shutil.copy(VORLAGEN / "suchprofil.md", apprentice.kontext.daten / "suchprofil.md")
    return apprentice


def test_a_job_seeker_gets_search_terms_and_can_add_and_remove_them(job_seeker, monkeypatch):
    path = job_seeker.kontext.daten / "suchprofil.md"
    client = Client(JOB_REPLY)
    monkeypatch.setattr(routes_ai, "new_client", lambda: client)
    status, answer = post(job_seeker, "/api/beruf/vorschlag", {"interessen": "etwas Administratives", "staerken": "ordentlich"})
    assert status == 200
    assert [entry["beruf"] for entry in answer["vorschlaege"]] == ["Sachbearbeitung Administration"]
    assert "Sie-Form" in json.dumps(client.messages.calls[-1], ensure_ascii=False, default=str)
    name = answer["vorschlaege"][0]["beruf"]
    status, answer = post(job_seeker, "/api/beruf/aufnehmen", {"beruf": name})
    assert status == 200 and name in answer["berufe"]
    assert name in search_plan.for_folder(job_seeker.kontext.daten).keywords
    status, answer = post(job_seeker, "/api/beruf/entfernen", {"beruf": name})
    assert status == 200 and name not in answer["berufe"]
    assert name not in path.read_text(encoding="utf-8")


def test_job_messages_address_the_person_formally(job_seeker):
    _, answer = post(job_seeker, "/api/beruf/vorschlag", {"interessen": "x"})
    assert "Schreiben Sie" in answer["fehler"]


def test_a_job_term_is_short_and_fits_a_list():
    assert career.is_job_term("Sachbearbeitung Administration")
    for bad in ("a, b", "x" * 200, "Zeile\nzwei", "## Region", "x", "Sachbearbeiter (m/w)", "`Code`", "Kauffrau/Kaufmann", "", None, 5):
        assert not career.is_job_term(bad)


def test_removing_a_profession_through_the_route(apprentice):
    name = known_profession()
    status, answer = post(apprentice, "/api/beruf/entfernen", {"beruf": name})
    assert status == 200 and name not in answer["berufe"]
    assert any(apprentice.kontext.ablage.liste()), "drafts before and after"


@pytest.mark.parametrize("name", [None, 5, "", "x" * 200])
def test_removing_refuses_what_is_no_name(apprentice, name):
    assert post(apprentice, "/api/beruf/entfernen", {"beruf": name})[0] == 400


def test_without_a_profile_the_routes_say_so(server):  # noqa: F811
    for route, body in (("/api/beruf/vorschlag", {"interessen": "x", "staerken": "y"}), ("/api/beruf/aufnehmen", {"beruf": "Empfang"}), ("/api/beruf/entfernen", {"beruf": "Empfang"})):
        status, answer = post(server, route, body)
        assert status == 400 and "Suchprofil" in answer["fehler"]


def test_adding_goes_into_the_profile_with_a_draft(apprentice):
    status, answer = post(apprentice, "/api/beruf/aufnehmen", {"beruf": "Koch/Köchin EFZ"})
    assert status == 200 and "Koch/Köchin EFZ" in answer["berufe"]
    daten = apprentice.kontext.daten
    assert "Koch/Köchin EFZ" in (daten / "suchprofil.md").read_text(encoding="utf-8")
    assert search_plan.for_folder(daten).keywords[-1] == "Koch/Köchin EFZ"
    assert any(apprentice.kontext.ablage.liste()), "drafts before and after"


@pytest.mark.parametrize("name", ["Nur Text", "A\n## Region EFZ", "", None, 5, "x" * 200 + " EFZ"])
def test_adding_refuses_what_is_no_profession(apprentice, name):
    before = (apprentice.kontext.daten / "suchprofil.md").read_bytes()
    assert post(apprentice, "/api/beruf/aufnehmen", {"beruf": name})[0] == 400
    assert (apprentice.kontext.daten / "suchprofil.md").read_bytes() == before


def test_overview_says_what_is_searched(apprentice):
    _, _, content = get(apprentice, "/api/suche/liste")
    assert json.loads(content)["gesuchte_berufe"][0] == known_profession()


def test_with_profession_keeps_the_order_over_blank_lines():
    text = "## Berufe (mit Priorität)\n1. Koch EFZ\n\n2. Maler EFZ\n\n## Lehrbeginn\n- 2027\n"
    changed = search_plan.with_profession(text, "Gärtner EFZ")
    assert search_plan.professions_in(changed) == ("Koch EFZ", "Maler EFZ", "Gärtner EFZ")
    assert changed.endswith("## Lehrbeginn\n- 2027\n")


def test_with_profession_at_the_end_of_a_file_without_newline():
    text = "## Lehrbeginn\n- 2027\n## Berufe (mit Priorität)\n1. Koch EFZ"
    changed = search_plan.with_profession(text, "Maler EFZ")
    assert search_plan.professions_in(changed) == ("Koch EFZ", "Maler EFZ")


def test_with_profession_finds_the_section_in_any_case():
    text = "## Berufe (mit priorität)\n1. Koch EFZ\n\n## Lehrbeginn\n- 2027\n"
    changed = search_plan.with_profession(text, "Maler EFZ")
    assert changed.count("## Berufe") == 1
    assert search_plan.professions_in(changed) == ("Koch EFZ", "Maler EFZ")


def test_with_profession_refuses_more_than_the_search_uses():
    names = "".join(f"{i}. Beruf{i} EFZ\n" for i in range(1, search_plan.MAX_PROFESSIONS + 1))
    text = f"## Berufe (mit Priorität)\n{names}\n## Lehrbeginn\n- 2027\n"
    with pytest.raises(ValueError, match="Berufe"):
        search_plan.with_profession(text, "Maler EFZ")


@pytest.mark.parametrize("name", ["A\nEFZ", "A\u2028B EFZ", "A\tB\r EFZ", "<b> EFZ", " EFZ", "EFZ"])
def test_a_name_on_more_than_one_line_is_no_profession(name):
    assert not career.is_profession(name)


def test_every_accepted_name_reads_back_from_the_profile():
    name = "Fachfrau/Fachmann Betreuung (Kinder) EFZ"
    assert career.is_profession(name)
    text = "## Berufe (mit Priorität)\n\n## Lehrbeginn\n- 2027\n"
    assert search_plan.professions_in(search_plan.with_profession(text, name)) == (name,)


WORD_CASES = json.loads((pathlib.Path(__file__).parents[2] / "erweiterung" / "tests" / "profession_words.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("name, words", WORD_CASES)
def test_profession_words_follow_the_rules_of_the_extension(name, words):
    assert search_plan.profession_words(name) == frozenset(words)


def test_the_same_profession_in_another_form_is_not_added_again():
    assert search_plan.with_profession(profile(), "Fachfrau/Fachmann Gesundheit EFZ") == profile()


def test_a_name_is_written_as_it_reads_back_and_counts_once():
    text = "## Berufe (mit Priorität)\n\n## Lehrbeginn\n- 2027\n"
    once = search_plan.with_profession(text, "Koch  Spezial EFZ")
    assert search_plan.professions_in(once) == ("Koch Spezial EFZ",)
    assert search_plan.with_profession(once, "Koch  Spezial EFZ") == once


def test_the_profile_form_with_a_specialisation_is_a_profession():
    assert career.is_profession("Fachfrau Betreuung EFZ, Fachrichtung Kinder")
    assert not career.is_profession("Fachfrau Betreuung EFZ, Fachrichtung\nKinder")


def test_the_first_of_two_names_for_a_profession_stays_in_its_place():
    def item(name):
        return {**FIRST, "profession": name}

    found = career._suggestions({"recommendations": [item("Koch/Köchin EFZ"), item("Maler/in EFZ"), item("Koch EFZ")]})
    assert [entry["profession"] for entry in found] == ["Koch/Köchin EFZ", "Maler/in EFZ"]


def test_adding_at_the_same_time_loses_nothing(apprentice):
    names = ["Maler/in EFZ", "Gärtner/in EFZ", "Bäcker/in EFZ", "Dachdecker/in EFZ", "Elektroinstallateur/in EFZ"]
    answers = []
    threads = [threading.Thread(target=lambda n=name: answers.append(post(apprentice, "/api/beruf/aufnehmen", {"beruf": n})[0])) for name in names]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert answers == [200] * len(names)
    assert set(names) <= set(search_plan.professions_in((apprentice.kontext.daten / search_plan.PROFILE).read_text(encoding="utf-8")))


def test_a_person_without_a_profession_gets_suggestions_and_then_can_search(apprentice, monkeypatch):
    path = apprentice.kontext.daten / search_plan.PROFILE
    text = re.sub(r"## Berufe \(mit Priorität\)\n(?:.+\n)*\n", "", profile())
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="Welcher Beruf passt zu dir"):
        search_plan.parse(text)
    monkeypatch.setattr(routes_ai, "new_client", lambda: Client({"recommendations": [FIRST]}))
    status, answer = post(apprentice, "/api/beruf/vorschlag", {"interessen": "Hände", "staerken": "geduldig"})
    assert status == 200 and answer["vorschlaege"][0]["schon_gesucht"] is False
    assert post(apprentice, "/api/beruf/aufnehmen", {"beruf": FIRST["profession"]})[0] == 200
    assert search_plan.parse(path.read_text(encoding="utf-8")).keywords == (FIRST["profession"],)


def test_overview_lists_professions_also_when_the_plan_cannot_search_yet(apprentice):
    path = apprentice.kontext.daten / "suchprofil.md"
    path.write_text("## Lehrbeginn\n- 2027\n\n## Berufe (mit Priorität)\n1. Koch/Köchin EFZ\n", encoding="utf-8")
    _, _, content = get(apprentice, "/api/suche/liste")
    answer = json.loads(content)
    assert answer["gesuchte_berufe"] == ["Koch/Köchin EFZ"]
    assert answer["gesuchte_schluessel"] == [search_terms.key("Koch/Köchin EFZ")]


def test_a_change_tells_the_page_what_is_searched_now(apprentice):
    _, answer = post(apprentice, "/api/beruf/aufnehmen", {"beruf": "Maler/in EFZ"})
    assert search_terms.key("Maler/in EFZ") in answer["schluessel"]
    _, answer = post(apprentice, "/api/beruf/entfernen", {"beruf": "Maler/in EFZ"})
    assert search_terms.key("Maler/in EFZ") not in answer["schluessel"]


def test_removing_what_cannot_be_found_changes_nothing_and_says_nothing_wrong(apprentice):
    before = (apprentice.kontext.daten / "suchprofil.md").read_bytes()
    status, answer = post(apprentice, "/api/beruf/entfernen", {"beruf": "Astronaut EFZ"})
    assert status == 200 and known_profession() in answer["berufe"]
    assert (apprentice.kontext.daten / "suchprofil.md").read_bytes() == before


def test_job_terms_are_cleaned_of_gender_forms_and_stay_short(folder):
    def item(name):
        return {"profession": name, "why": "w", "daily": "d", "check": "c"}

    found = career._suggestions({"recommendations": [item("Sachbearbeiter/in"), item("Kauffrau/Kaufmann"), item("Mitarbeiter im Kundendienst mit viel Erfahrung in Administration")]}, search_plan.KIND_JOB)
    assert [entry["profession"] for entry in found] == ["Sachbearbeiter"]
    for good in ("HR", "C# Entwicklung", "Empfang"):
        assert career.is_job_term(good), good


def test_what_the_person_does_not_want_never_comes_back(folder):
    reply = {"recommendations": [{**FIRST, "profession": "Büroassistent/in EFZ"}, SECOND]}
    gateway, material = gateway_for(folder, Client(reply))
    answers = {**ANSWERS, "avoid": "Ich möchte nicht ins Büro."}
    result = career.recommend(gateway, material, answers)
    assert [item["profession"] for item in result["recommendations"]] == [SECOND["profession"]]


def test_only_avoided_suggestions_end_in_a_clear_message(folder):
    gateway, material = gateway_for(folder, Client({"recommendations": [{**FIRST, "profession": "Büroassistent/in EFZ"}]}))
    with pytest.raises(errors.AiError, match="ausgeschlossen"):
        career.recommend(gateway, material, {**ANSWERS, "avoid": "Büro"})
