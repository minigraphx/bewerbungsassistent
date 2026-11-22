"""Each term of a term proposal is a switch of its own (#371, G102): the page sends the terms that are on, the app
takes only current terms and proposed ones, works the result out itself and writes exactly that. All data is invented.
"""
import pytest

import search_plan
import term_changes
from test_app import post, server  # noqa: F401  (server is a fixture)
from test_optimize_terms import ai, job_search, profile, profile_of, propose, taken  # noqa: F401  (fixtures)

KERNLISTE = "Python, TypeScript, Softwareentwickler, Data Engineer, E-Learning, Kursleiter (nur mit Informatik, ICT)"
OVER_BEFORE = 31
NEW_KEYWORDS = ["Datenanalyst", "Fullstack Entwickler", "Cloud Architekt"]
GROWING_REPLY = {"summary": "Drei Begriffe fehlen.", "changed": "", "changes": [
    {"area": "keywords", "remove": [], "add": NEW_KEYWORDS, "reason": "Steht so im Lebenslauf."},
    {"area": "exclude", "remove": [], "add": ["Verkauf"], "reason": "Verkaufsstellen passen nicht."},
]}


def outcome_of(s, proposal: dict, on: dict) -> dict:
    status, answer = post(s, "/api/suchbegriffe/endstand", {"vorschlag": proposal["vorschlag"], "danach": on})
    assert status == 200, answer
    return answer


def adopt(s, proposal: dict, on: dict) -> tuple[int, dict]:
    return post(s, "/api/suchbegriffe/uebernehmen", {"vorschlag": proposal["vorschlag"], "danach": on})


def without(on: dict, area: str, *terms: str) -> dict:
    return {**on, area: [t for t in on[area] if t not in terms]}


def with_terms(on: dict, area: str, *terms: str) -> dict:
    return {**on, area: [*on[area], *terms]}


def test_a_current_term_no_change_touches_can_be_switched_off(job_search, ai):
    proposal = propose(job_search)
    on = without(taken(proposal), "suchbegriffe", "TypeScript")

    answer = outcome_of(job_search, proposal, on)

    assert "TypeScript" not in answer["endstand"]["suchbegriffe"] and "TypeScript" in answer["entfaellt"]
    status, done = adopt(job_search, proposal, on)
    assert status == 200, done
    assert "TypeScript" not in search_plan.job_terms(profile_of(job_search))
    assert (done["neu"], done["entfallen"]) == (4, 2)


def test_a_term_a_change_would_remove_can_stay(job_search, ai):
    proposal = propose(job_search)
    on = with_terms(taken(proposal), "positiv", "Engineer")

    status, done = adopt(job_search, proposal, on)

    assert status == 200, done
    positive = search_plan.title_terms(profile_of(job_search), "positiv")
    assert "Engineer" in positive and {"Backend", "Frontend"} <= set(positive)


def test_a_proposed_term_can_be_left_out(job_search, ai):
    proposal = propose(job_search)
    on = without(taken(proposal), "positiv", "Frontend")

    answer = outcome_of(job_search, proposal, on)

    assert "Backend" in answer["endstand"]["positiv"] and "Frontend" not in answer["endstand"]["positiv"]
    assert adopt(job_search, proposal, on)[0] == 200
    positive = search_plan.title_terms(profile_of(job_search), "positiv")
    assert "Backend" in positive and "Frontend" not in positive and "Engineer" not in positive


def test_the_proposal_names_the_current_terms_no_change_touches(job_search, ai):
    proposal = propose(job_search)

    assert "Engineer" not in proposal["bisherige"]["positiv"], "a term in a card is never also below"
    assert proposal["bisherige"]["positiv"] == [t for t in proposal["jetzt"]["positiv"] if t != "Engineer"]
    assert proposal["bisherige"]["suchbegriffe"] == proposal["jetzt"]["suchbegriffe"]


@pytest.fixture
def over_the_limit(job_search, ai):
    """A profile from before the limit: 31 search terms where 15 may be added."""
    path = job_search.kontext.daten / "suchprofil.md"
    many = ", ".join(f"Begriff{n}" for n in range(OVER_BEFORE))
    path.write_text(profile().replace(KERNLISTE, many), encoding="utf-8")
    ai.messages.reply = GROWING_REPLY
    return job_search


def test_a_profile_over_the_limit_can_switch_off_enough_to_take_the_proposal_over(over_the_limit):
    proposal = propose(over_the_limit)
    blocked = proposal["grenzen"]
    assert blocked["gesperrt"] == ("Mit dieser Auswahl wären es 34 Suchbegriffe. Höchstens 15 gehen; da es schon 31 sind, "
                                   "dürfen es nicht mehr werden. Bitte noch 3 ausschalten, unter «Bisherige Begriffe» "
                                   "oder bei den Vorschlägen.")
    assert blocked["teile"][0] == "Danach: 34 Suchbegriffe, erlaubt sind 31"
    assert blocked["zu_viel"] == {"suchbegriffe": 3, "positiv": 0, "ausschluss": 0}
    assert blocked["erlaubt"]["suchbegriffe"] == OVER_BEFORE
    on = without(taken(proposal), "suchbegriffe", "Begriff0", "Begriff1", "Begriff2")

    answer = outcome_of(over_the_limit, proposal, on)

    assert answer["grenzen"]["gesperrt"] is None and answer["grenzen"]["zu_viel"]["suchbegriffe"] == 0
    status, done = adopt(over_the_limit, proposal, on)
    assert status == 200, done
    after = search_plan.job_terms(profile_of(over_the_limit))
    assert len(after) == OVER_BEFORE and set(NEW_KEYWORDS) <= set(after) and "Begriff0" not in after


def test_over_the_limit_the_profile_stays_while_too_many_are_on(over_the_limit):
    proposal = propose(over_the_limit)
    before = profile_of(over_the_limit)
    on = without(taken(proposal), "suchbegriffe", "Begriff0")

    status, answer = adopt(over_the_limit, proposal, on)

    assert status == 400 and "Bitte noch 2 ausschalten" in answer["fehler"]
    assert profile_of(over_the_limit) == before


def sections(text: str) -> dict[str, list[str]]:
    found, title = {}, ""
    for line in text.split("\n"):
        title = line if line.startswith("## ") else title
        found = {**found, title: [*found.get(title, []), line]}
    return found


def test_only_the_three_term_areas_change_in_the_profile(job_search, ai):
    before = profile_of(job_search)
    proposal = propose(job_search)
    on = without(without(taken(proposal), "suchbegriffe", "TypeScript"), "ausschluss", "PhD")

    assert adopt(job_search, proposal, on)[0] == 200

    after = profile_of(job_search)
    changed = {title for title, lines in sections(after).items() if sections(before).get(title) != lines}
    assert changed == {"## Keywords", "## Titelfilter"}
    kept = [line for line in sections(after)["## Keywords"] if not line.startswith("- Kernliste")]
    assert kept == [line for line in sections(before)["## Keywords"] if not line.startswith("- Kernliste")]
    assert search_plan.title_terms(after, "ausschluss")[-1] == "Verkauf" and "PhD" not in after


@pytest.mark.parametrize("on", [
    lambda on: with_terms(on, "suchbegriffe", "Erfundener Begriff"),
    lambda on: with_terms(on, "positiv", "Verkauf"),  # proposed, but for another area
    lambda on: {key: value for key, value in on.items() if key != "positiv"},
    lambda on: {**on, "ausschluss": "Praktikum"},
    lambda on: [*on["suchbegriffe"]],
])
def test_the_app_takes_only_current_terms_and_the_proposal(job_search, ai, on):
    proposal = propose(job_search)
    before = profile_of(job_search)

    status, answer = adopt(job_search, proposal, on(taken(proposal)))

    assert status == 400 and answer["fehler"] == term_changes.NOT_OFFERED
    assert post(job_search, "/api/suchbegriffe/endstand",
                {"vorschlag": proposal["vorschlag"], "danach": on(taken(proposal))})[0] == 400
    assert profile_of(job_search) == before


def test_the_app_works_out_the_result_itself_in_the_order_of_the_profile(job_search, ai):
    proposal = propose(job_search)
    on = {area: list(reversed(terms)) for area, terms in taken(proposal).items()}

    answer = outcome_of(job_search, proposal, on)

    assert answer["endstand"] == taken(proposal)
    assert answer["entfaellt"] == ["Engineer"]


def test_nothing_switched_away_from_now_is_refused_with_its_reason(job_search, ai):
    proposal = propose(job_search)

    answer = outcome_of(job_search, proposal, proposal["jetzt"])

    assert answer["grenzen"]["gesperrt"] == "Mit dieser Auswahl bleibt alles wie bisher."
    status, refused = adopt(job_search, proposal, proposal["jetzt"])
    assert status == 400 and refused["fehler"] == "Mit dieser Auswahl bleibt alles wie bisher."


def test_without_any_search_term_the_reason_asks_to_switch_one_on(job_search, ai):
    proposal = propose(job_search)

    answer = outcome_of(job_search, proposal, {**taken(proposal), "suchbegriffe": []})

    assert answer["grenzen"]["gesperrt"] == ("Danach stünde kein Suchbegriff mehr in der Suche. "
                                             "Bitte mindestens einen einschalten.")


# The reasons a choice cannot be taken over, worded by term_changes


def terms(keywords: int, exclude: int = 0) -> term_changes.Terms:
    return term_changes.Terms(tuple(f"Begriff{n}" for n in range(keywords)), (),
                              tuple(f"Wort{n}" for n in range(exclude)))


def test_over_the_limit_from_within_it_names_how_many_to_switch_off():
    found = term_changes.limits(terms(14), terms(17), 1)
    assert found["gesperrt"] == ("Mit dieser Auswahl wären es 17 Suchbegriffe, höchstens 15 gehen. Bitte noch 2 "
                                 "ausschalten, unter «Bisherige Begriffe» oder bei den Vorschlägen.")
    assert found["teile"] == ["Danach: 17 von 15 Suchbegriffen", "bis 17 Suchen pro Portal"]


def test_a_title_area_over_its_limit_names_how_many_to_switch_off_there():
    limit = search_plan.MAX_TITLE_TERMS
    found = term_changes.limits(terms(3, limit), terms(3, limit + 3), 1)
    assert found["gesperrt"] == (f"Mit dieser Auswahl hätte «Titel enthält keines davon» {limit + 3} Begriffe, "
                                 f"höchstens {limit} gehen. Bitte dort noch 3 ausschalten.")
    assert found["zu_viel"] == {"suchbegriffe": 0, "positiv": 0, "ausschluss": 3}
