"""The choice from the setup (MIN-369): what is sought, the form of address, RAV; stored in the data folder."""
import pytest
import yaml

import preferences
from test_app import get, post, server  # noqa: F401  (server is a fixture)

APPRENTICESHIP_PROFILE = "# Suchprofil Lehrstelle\n\n## Lehrbeginn\n\nAugust 2027\n"


def test_without_a_choice_a_job_profile_means_a_job_with_sie_and_rav(tmp_path):
    choice = preferences.load(tmp_path)

    assert choice.as_dict() == {"gesucht": "stelle", "anrede": "sie", "rav": True, "gewaehlt": False, "textsatz": "stelle-sie"}


def test_without_a_choice_an_apprenticeship_profile_means_du(tmp_path):
    (tmp_path / "suchprofil.md").write_text(APPRENTICESHIP_PROFILE, encoding="utf-8")

    assert preferences.load(tmp_path).text_set == "lehrstelle-du"


def test_an_apprenticeship_is_always_du():
    choice = preferences.parse({"gesucht": "lehrstelle", "anrede": "sie", "rav": False})

    assert (choice.address, choice.text_set, choice.chosen) == ("du", "lehrstelle-du", True)


@pytest.mark.parametrize("values, message", [
    ({"gesucht": "praktikum", "anrede": "sie", "rav": True}, preferences.BAD_SOUGHT),
    ({"gesucht": "stelle", "anrede": "ihr", "rav": True}, preferences.BAD_ADDRESS),
    ({"gesucht": "stelle", "anrede": "du", "rav": "ja"}, preferences.BAD_RAV),
    ("stelle", preferences.BAD_SOUGHT),
])
def test_a_bad_choice_is_refused_in_german(values, message):
    with pytest.raises(ValueError, match=message):
        preferences.parse(values)


def test_a_broken_file_falls_back_to_the_profile(tmp_path):
    (tmp_path / preferences.FILE).write_text("gesucht: [kaputt", encoding="utf-8")

    assert preferences.load(tmp_path).as_dict()["gewaehlt"] is False


def test_the_page_stores_the_choice_with_drafts_and_reads_it_back(server):  # noqa: F811
    folder = server.kontext.daten
    status, answer = post(server, "/api/einrichtung/wahl", {"gesucht": "stelle", "anrede": "du", "rav": False})

    assert status == 200 and answer["textsatz"] == "stelle-du" and answer["gewaehlt"] is True
    assert yaml.safe_load((folder / preferences.FILE).read_text(encoding="utf-8")) == {"gesucht": "stelle", "anrede": "du", "rav": False}
    status, _, body = get(server, "/api/einrichtung/wahl")
    assert status == 200 and b'"rav": false' in body
    post(server, "/api/einrichtung/wahl", {"gesucht": "lehrstelle", "anrede": "du", "rav": True})
    assert len(server.kontext.ablage.liste(folder / preferences.FILE)) >= 2


def test_the_page_gets_a_german_error_for_a_bad_choice(server):  # noqa: F811
    status, answer = post(server, "/api/einrichtung/wahl", {"gesucht": "stelle", "rav": True})

    assert status == 400 and answer["fehler"] == preferences.BAD_ADDRESS
