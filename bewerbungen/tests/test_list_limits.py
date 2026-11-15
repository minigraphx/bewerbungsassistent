"""Suche einstellen takes a direction and an own job term as Meine Angaben takes them in onboarding/form.json (#316).

Meine Angaben counts only characters for a keyword, so an own term with many short words is taken too; a direction is
shown and removed in full, as long as the form lets it be. All data is invented.
"""
import json

import pytest

import profile_limits
import search_plan
import search_terms
from test_app import get, post, server  # noqa: F401  (server is a fixture)
from test_career import apprentice, job_seeker  # noqa: F401  (fixtures)

MANY_WORDS = "Leitung Einkauf und Logistik in der Region"


def searched(seeker) -> list[str]:
    _, _, content = get(seeker, "/api/suche/liste")
    return json.loads(content)["gesuchte_berufe"]


def test_an_own_job_term_with_more_than_five_words_is_taken_as_meine_angaben_takes_it(job_seeker):
    assert len(MANY_WORDS.split()) > 5 and len(MANY_WORDS) <= profile_limits.of_term(search_plan.KIND_JOB).chars

    status, answer = post(job_seeker, "/api/beruf/aufnehmen", {"beruf": MANY_WORDS})

    assert status == 200, answer
    assert MANY_WORDS in answer["berufe"] and MANY_WORDS in searched(job_seeker)


def test_suche_einstellen_adds_no_more_directions_than_meine_angaben_takes():
    lines = profile_limits.of(search_plan.KIND_JOB, "directions").lines
    numbered = "".join(f"{n}. Empfang\n" for n in range(1, lines + 1))  # one term, as often as the form takes lines
    text = f"# Suchprofil\n\n## Suchrichtungen\n{numbered}\n## Region\n- Wohnort: Bern\n"

    with pytest.raises(ValueError, match=str(lines)):
        search_terms.added(text, "Kundendienst")


def test_a_direction_as_long_as_meine_angaben_takes_it_is_shown_and_removed_in_full(job_seeker):
    length = profile_limits.of(search_plan.KIND_JOB, "directions").chars
    long = "Sachbearbeitung im Kundendienst " + "x" * (length - len("Sachbearbeitung im Kundendienst "))
    (job_seeker.kontext.daten / search_plan.PROFILE).write_text(
        f"# Suchprofil\n\n## Suchrichtungen\n1. {long}\n2. Empfang\n\n## Region\n- Wohnort: Bern\n", encoding="utf-8")
    assert searched(job_seeker) == [long, "Empfang"]

    status, answer = post(job_seeker, "/api/beruf/entfernen", {"beruf": long})

    assert status == 200, answer
    assert answer["berufe"] == ["Empfang"]
