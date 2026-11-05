"""A good grade from a package is looked at again, alone and three times, before it counts (MIN-389)."""
import threading

import pytest

from ai import second_look
from ai.errors import AiError, AnswerError
from test_ai_tasks import PackageClient, gateway_for, rating_entry, daten  # noqa: F401 (fixture)

AD = ("job-a", "Stelle A in Bern.")
OTHER = ("job-b", "Stelle B in Thun.")


def first_rating(grade=5, **extra):
    return {"grade": grade, "summary": "Im Paket", "fits": [], "hooks": [], "new_gaps": [], "suspicious_lines": [],
            "uncertain": "", **extra}


def grades_in_turn(*grades):
    """A client whose next answer has the next grade."""
    left = iter(grades)

    def build(labels):
        grade = next(left)
        if isinstance(grade, Exception):
            raise grade
        return [rating_entry(labels[0], grade, summary=f"Note {grade}")]

    return PackageClient(build)


@pytest.mark.parametrize("grade, expected", [(3.5, False), (4, True), (6, True)])
def test_only_grade_four_or_better_deserves_a_second_look(grade, expected):
    assert second_look.deserved({"grade": grade}) is expected


@pytest.mark.parametrize("grades, expected", [([4, 2, 3], 3), ([2, 5, 5], 5), ([4, 3], 3), ([4.5], 4.5)])
def test_the_middle_grade_counts_and_of_two_the_lower(grades, expected):
    assert second_look.middle_grade(grades) == expected


def test_a_package_grade_is_replaced_by_the_middle_of_three_runs(daten):
    client = grades_in_turn(2, 4, 3)
    gateway, material = gateway_for(daten, client)
    look = second_look.look_again(gateway, material, [AD, OTHER], {"job-a": first_rating(5)})["job-a"]
    assert sorted(look.grades) == [2, 3, 4] and look.first_grade == 5
    assert look.rating["grade"] == 3 and look.rating["summary"] == "Note 3", "the reasons belong to the grade"
    assert len(client.messages.calls) == 3
    assert look.cost_usd > 0


def test_the_runs_of_a_hit_go_out_together(monkeypatch):
    together = threading.Barrier(3, timeout=5)

    def rate(gateway, material, ads):
        together.wait()
        return {"ratings": {ads[0][0]: first_rating(4)}, "missing": [], "model": "m", "cost_usd": 0.01}

    monkeypatch.setattr(second_look.tasks, "rate_package", rate)
    look = second_look.look_again(None, None, [AD, OTHER], {"job-a": first_rating(5)})["job-a"]
    assert look.grades == (4, 4, 4)


def test_every_run_is_alone_with_its_ad(daten):
    client = grades_in_turn(5, 5, 5)
    gateway, material = gateway_for(daten, client)
    second_look.look_again(gateway, material, [AD, OTHER], {"job-a": first_rating()})
    assert all("Stelle B" not in call["messages"][0]["content"] for call in client.messages.calls)


def test_an_ad_that_was_alone_already_counts_as_the_first_run(daten):
    client = grades_in_turn(3, 4)
    gateway, material = gateway_for(daten, client)
    look = second_look.look_again(gateway, material, [AD], {"job-a": first_rating(5)})["job-a"]
    assert look.grades[0] == 5 and sorted(look.grades[1:]) == [3, 4] and look.first_grade is None
    assert look.rating["grade"] == 4
    assert len(client.messages.calls) == 2


def test_suspicious_lines_of_every_run_stay(daten):
    def build(labels):
        return [rating_entry(labels[0], 5, suspicious_lines=["Zeile aus dem Lauf"])]

    gateway, material = gateway_for(daten, PackageClient(build))
    first = first_rating(5, suspicious_lines=["Zeile aus dem Paket"])
    look = second_look.look_again(gateway, material, [AD, OTHER], {"job-a": first})["job-a"]
    assert look.rating["suspicious_lines"] == ["Zeile aus dem Paket", "Zeile aus dem Lauf"]


def test_a_failed_run_leaves_the_others(daten, monkeypatch):
    answers = iter([{"grade": 4}, AnswerError("unbrauchbar", cost_usd=0.01), {"grade": 3}])

    def rate(gateway, material, ads):
        answer = next(answers)
        if isinstance(answer, Exception):
            raise answer
        return {"ratings": {ads[0][0]: first_rating(answer["grade"])}, "missing": [], "model": "m", "cost_usd": 0.02}

    monkeypatch.setattr(second_look.tasks, "rate_package", rate)
    look = second_look.look_again(None, None, [AD, OTHER], {"job-a": first_rating(5)})["job-a"]
    assert sorted(look.grades) == [3, 4] and look.rating["grade"] == 3
    assert look.cost_usd == pytest.approx(0.05), "a useless answer was paid for too"


def test_without_any_run_the_package_rating_stays(daten, monkeypatch):
    def rate(gateway, material, ads):
        return {"ratings": {}, "missing": [ads[0][0]], "model": "m", "cost_usd": 0.02}

    monkeypatch.setattr(second_look.tasks, "rate_package", rate)
    first = first_rating(5)
    look = second_look.look_again(None, None, [AD, OTHER], {"job-a": first})["job-a"]
    assert look.grades == () and look.rating == first and look.first_grade == 5


def test_a_connection_error_ends_all_further_runs(daten, monkeypatch):
    calls = []

    def rate(gateway, material, ads):
        calls.append(ads[0][0])
        raise AiError("Das Budget ist aufgebraucht.")

    monkeypatch.setattr(second_look.tasks, "rate_package", rate)
    looks = second_look.look_again(None, None, [AD, OTHER], {"job-a": first_rating(5), "job-b": first_rating(4)})
    assert calls == ["job-a"] * 3, "no point in asking again for the next hit"
    assert looks["job-a"].grades == () and looks["job-b"].grades == ()
    assert looks["job-b"].rating["grade"] == 4
