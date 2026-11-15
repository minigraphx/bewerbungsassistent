"""An own term on Suche einstellen may be as long as Meine Angaben takes it in the field it lands in (#310).

A job term goes into the line Kernliste, which Meine Angaben edits as its keywords; a profession goes into the list of
professions. The limits come from onboarding/form.json, as for the other values of the profile (#302). All data is
invented.
"""
import json

import pytest

import profile_limits
import search_plan
import search_terms
from test_app import get, post, server  # noqa: F401  (server is a fixture)
from test_career import apprentice, job_seeker  # noqa: F401  (fixtures)

FIELDS = {search_plan.KIND_JOB: "keywords", search_plan.KIND_APPRENTICESHIP: "professions"}
STARTS = {search_plan.KIND_JOB: "Sachbearbeitung Kundendienst ",
          search_plan.KIND_APPRENTICESHIP: "Lebensmitteltechnologin/Lebensmitteltechnologe EFZ, Fachrichtung "}
SERVERS = {search_plan.KIND_JOB: "job_seeker", search_plan.KIND_APPRENTICESHIP: "apprentice"}


def limit(kind: str) -> int:
    return profile_limits.of(kind, FIELDS[kind]).chars


def term(kind: str, length: int) -> str:
    return STARTS[kind] + "x" * (length - len(STARTS[kind]))


@pytest.fixture(params=list(FIELDS))
def kind(request):
    return request.param


@pytest.fixture
def seeker(kind, request):
    return request.getfixturevalue(SERVERS[kind])


def searched(seeker) -> tuple[str, ...]:
    return search_terms.current((seeker.kontext.daten / search_plan.PROFILE).read_text(encoding="utf-8"))


def test_an_own_term_as_long_as_meine_angaben_takes_it_is_searched_in_full(seeker, kind):
    name = term(kind, limit(kind))

    status, answer = post(seeker, "/api/beruf/aufnehmen", {"beruf": name})

    assert status == 200, answer
    assert name in answer["berufe"] and name in searched(seeker)


def test_an_own_term_longer_than_meine_angaben_takes_is_refused_with_the_limit(seeker, kind):
    path = seeker.kontext.daten / search_plan.PROFILE
    before = path.read_bytes()

    status, answer = post(seeker, "/api/beruf/aufnehmen", {"beruf": term(kind, limit(kind) + 1)})

    assert status == 400 and f"höchstens {limit(kind)} Zeichen" in answer["fehler"]
    assert path.read_bytes() == before


def test_a_term_at_the_limit_can_be_removed_again(seeker, kind):
    name = term(kind, limit(kind))
    assert post(seeker, "/api/beruf/aufnehmen", {"beruf": name})[0] == 200

    status, answer = post(seeker, "/api/beruf/entfernen", {"beruf": name})

    assert status == 200 and name not in answer["berufe"] and name not in searched(seeker)


def test_the_page_learns_how_long_an_own_term_may_be(seeker, kind):
    _, _, content = get(seeker, "/api/suche/liste")

    assert json.loads(content)["begriff_laenge"] == limit(kind)


def test_the_search_reads_a_profession_as_long_as_meine_angaben_takes_it():
    name = term(search_plan.KIND_APPRENTICESHIP, limit(search_plan.KIND_APPRENTICESHIP))
    text = f"## Berufe (mit Priorität)\n1. {name}\n\n## Lehrbeginn\n- 2027\n\n## Region\n- Wohnort: Bern\n"

    assert search_plan.parse(text).keywords == (name,)
