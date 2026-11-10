"""Own search terms on Stellen suchen, and Rückgängig after Entfernen (#216). Profiles are the invented templates."""
import hashlib
import pathlib
import shutil

import pytest

import search_plan
import search_terms
from test_app import post, server  # noqa: F401  (server is a fixture)

VORLAGEN = pathlib.Path(__file__).resolve().parents[2] / "vorlagen"
SEITEN = pathlib.Path(__file__).resolve().parents[1] / "seiten"
JOB_TERMS = ["Python", "TypeScript", "Softwareentwickler", "Data Engineer", "E-Learning"]
PROFESSIONS = ["Fachfrau Gesundheit EFZ", "Fachfrau Betreuung EFZ, Fachrichtung Kinder", "Assistentin Gesundheit und Soziales EBA"]


@pytest.fixture
def job_seeker(server):  # noqa: F811
    shutil.copy(VORLAGEN / "suchprofil.md", server.kontext.daten / search_plan.PROFILE)
    return server


@pytest.fixture
def apprentice(server):  # noqa: F811
    shutil.copy(VORLAGEN / "suchprofil-lehrstelle.md", server.kontext.daten / search_plan.PROFILE)
    return server


def profile(s) -> str:
    return (s.kontext.daten / search_plan.PROFILE).read_text(encoding="utf-8")


def drafts(s) -> list[str]:
    return [d.beschreibung for d in s.kontext.ablage.liste(s.kontext.daten / search_plan.PROFILE)]


# Adding a term of one's own


def test_an_own_term_joins_the_search_with_a_draft_before_and_after(job_seeker):
    status, answer = post(job_seeker, "/api/beruf/aufnehmen", {"beruf": "  Projektleitung Bau "})

    assert status == 200
    assert answer["berufe"] == [*JOB_TERMS, "Projektleitung Bau"]
    assert "Projektleitung Bau" in search_plan.for_folder(job_seeker.kontext.daten).keywords
    assert drafts(job_seeker) == ["In die Suche aufgenommen: Projektleitung Bau",
                                  "Stand vor: In die Suche aufgenommen: Projektleitung Bau"]


@pytest.mark.parametrize("typed", ["", "   ", None])
def test_an_empty_field_is_refused_with_a_clear_message(job_seeker, typed):
    before = profile(job_seeker)

    status, answer = post(job_seeker, "/api/beruf/aufnehmen", {"beruf": typed})

    assert status == 400 and answer["fehler"] == "Bitte einen Suchbegriff eintragen."
    assert profile(job_seeker) == before


def test_an_empty_field_names_what_an_apprenticeship_needs(apprentice):
    status, answer = post(apprentice, "/api/beruf/aufnehmen", {"beruf": " "})

    assert status == 400 and answer["fehler"] == "Bitte einen Beruf mit EFZ oder EBA eintragen."


@pytest.mark.parametrize("typed", ["Python", "python", " Data  Engineer "])
def test_a_term_that_is_searched_already_is_refused(job_seeker, typed):
    before = profile(job_seeker)

    status, answer = post(job_seeker, "/api/beruf/aufnehmen", {"beruf": typed})

    assert status == 400 and answer["fehler"] == f"„{' '.join(typed.split())}“ wird schon gesucht."
    assert profile(job_seeker) == before


def test_a_profession_that_is_searched_already_is_refused(apprentice):
    status, answer = post(apprentice, "/api/beruf/aufnehmen", {"beruf": PROFESSIONS[0]})

    assert status == 400 and "wird schon gesucht" in answer["fehler"]


def test_past_the_limit_the_existing_hint_comes(job_seeker):
    for number in range(search_plan.MAX_KEYWORDS - len(JOB_TERMS)):
        assert post(job_seeker, "/api/beruf/aufnehmen", {"beruf": f"Begriff {chr(65 + number)}"})[0] == 200

    status, answer = post(job_seeker, "/api/beruf/aufnehmen", {"beruf": "Noch einer"})

    assert status == 400 and answer["fehler"] == search_terms.FULL.format(limit=search_plan.MAX_KEYWORDS)


# Rückgängig after Entfernen


def remove(s, name) -> dict:
    status, answer = post(s, "/api/beruf/entfernen", {"beruf": name})
    assert status == 200
    return answer


@pytest.mark.parametrize("fixture, name, terms", [
    ("job_seeker", "Softwareentwickler", JOB_TERMS),
    ("apprentice", PROFESSIONS[1], PROFESSIONS),
])
def test_undo_puts_the_term_back_at_its_former_place(request, fixture, name, terms):
    s = request.getfixturevalue(fixture)
    before = profile(s)
    removed = remove(s, name)
    assert name not in removed["berufe"]

    status, answer = post(s, "/api/beruf/rueckgaengig", {"beruf": name, "vorher": removed["rueckgaengig"]})

    assert status == 200
    assert answer["berufe"] == terms and answer["am_ende"] is False
    assert profile(s) == before  # remark, priority and numbering as they were
    assert drafts(s)[0] == f"Wieder in die Suche aufgenommen: {name}"


def test_undo_after_another_change_still_brings_the_term_back_at_the_end(job_seeker):
    removed = remove(job_seeker, "TypeScript")
    assert post(job_seeker, "/api/beruf/aufnehmen", {"beruf": "Projektleitung Bau"})[0] == 200

    status, answer = post(job_seeker, "/api/beruf/rueckgaengig", {"beruf": "TypeScript", "vorher": removed["rueckgaengig"]})

    assert status == 200 and answer["am_ende"] is True
    assert answer["berufe"] == ["Python", "Softwareentwickler", "Data Engineer", "E-Learning", "Projektleitung Bau", "TypeScript"]


def test_undo_never_restores_more_than_the_removed_term(job_seeker):
    """A draft that differs in more than the term must not come back through Rückgängig."""
    path = job_seeker.kontext.daten / search_plan.PROFILE
    old = path.read_text(encoding="utf-8")
    path.write_text(old.replace("- Remote: ja", "- Remote: nein"), encoding="utf-8")
    job_seeker.kontext.ablage.speichere(path, "eine andere Änderung")
    path.write_text(old, encoding="utf-8")
    removed = remove(job_seeker, "Python")
    other = hashlib.sha256(old.replace("- Remote: ja", "- Remote: nein").encode()).hexdigest()

    status, answer = post(job_seeker, "/api/beruf/rueckgaengig", {"beruf": "Python", "vorher": other})

    assert status == 200 and answer["am_ende"] is True
    assert "- Remote: ja" in profile(job_seeker) and removed["rueckgaengig"] != other


@pytest.mark.parametrize("body", [{}, {"beruf": "Python"}, {"beruf": "Python", "vorher": "kaputt"}, {"beruf": "", "vorher": "0" * 64}])
def test_undo_wants_a_term_and_its_former_state(job_seeker, body):
    assert post(job_seeker, "/api/beruf/rueckgaengig", body)[0] == 400


def test_removing_nothing_offers_nothing_to_undo(job_seeker):
    assert remove(job_seeker, "Cobol")["rueckgaengig"] is None


# The page


def test_the_list_has_a_field_to_add_and_the_removal_offers_rueckgaengig():
    html = (SEITEN / "treffer.html").read_text(encoding="utf-8")
    script = (SEITEN / "beruf-vorschlag.js").read_text(encoding="utf-8")
    box = html[html.index('<section id="suchliste"'):html.index("</section>", html.index('<section id="suchliste"'))]

    assert 'id="suchliste-neu"' in box and 'for="suchliste-neu"' in box and 'id="suchliste-aufnehmen"' in box
    assert '"/api/beruf/aufnehmen"' in script and '"/api/beruf/rueckgaengig"' in script
    assert 'RUECKGAENGIG = "Rückgängig"' in script  # what it does: tests/beruf_vorschlag.test.cjs
