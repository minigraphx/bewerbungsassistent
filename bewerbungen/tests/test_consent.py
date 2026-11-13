"""Consent before the first AI call (MIN-401): the app is for adults; the kind of search decides the wording."""
import dataclasses
import datetime
import json

import pytest

import app
import preferences
import routes_ai
import routes_apply
import search_plan
from ai import consent, errors, invitation, tasks
from ai.connection import ACCESS_VARIABLE, URL_VARIABLE
from ai.errors import AiError
from server import SEITEN as PAGES
from test_app import get, post, server  # noqa: F401  (server is a fixture)

pytestmark = pytest.mark.real_consent
NOW = datetime.datetime(2026, 11, 5, 21, 0, tzinfo=datetime.timezone.utc)
JOB, APPRENTICESHIP = search_plan.KIND_JOB, search_plan.KIND_APPRENTICESHIP
APPRENTICESHIP_CHOSEN = "gesucht: lehrstelle\nanrede: du\nrav: false\n"


def test_nothing_is_given_at_first(tmp_path):
    assert not consent.is_given(tmp_path, JOB)
    with pytest.raises(AiError, match="Einwilligung"):
        consent.require(tmp_path, JOB)


def test_given_consent_is_kept_with_version_kind_and_time(tmp_path):
    consent.give(tmp_path, JOB, consent.VERSION, NOW)
    consent.require(tmp_path, JOB)
    saved = json.loads((tmp_path / consent.FILE).read_text(encoding="utf-8"))
    assert saved == {"fassung": consent.VERSION, "art": JOB, "zeit": "2026-11-05T21:00:00+00:00"}


def test_the_wording_asks_for_an_adult_in_both_kinds():
    assert "mindestens 18" in consent.WORDING[JOB]
    assert "Elternteil oder gesetzliche Vertretung" in consent.WORDING[APPRENTICESHIP]
    assert "mindestens 18" in consent.WORDING[APPRENTICESHIP]
    assert "Arbeitslosigkeit" in consent.WORDING[JOB]
    for wording in consent.WORDING.values():
        assert "Anthropic" in wording and "USA" in wording


def test_consent_of_an_older_wording_no_longer_counts(tmp_path, monkeypatch):
    consent.give(tmp_path, JOB, consent.VERSION, NOW)
    monkeypatch.setattr(consent, "VERSION", "neuer")
    assert not consent.is_given(tmp_path, JOB)


def test_consent_for_the_other_kind_of_search_does_not_count(tmp_path):
    consent.give(tmp_path, JOB, consent.VERSION, NOW)
    assert not consent.is_given(tmp_path, APPRENTICESHIP)


def test_giving_consent_to_a_wording_the_page_did_not_show_is_refused(tmp_path):
    with pytest.raises(ValueError, match="neu laden"):
        consent.give(tmp_path, JOB, "alt", NOW)
    assert not (tmp_path / consent.FILE).exists()


@pytest.mark.parametrize("content", ["kein json", "[]", '{"fassung": 3}'])
def test_a_damaged_file_counts_as_no_consent(tmp_path, content):
    (tmp_path / consent.FILE).write_text(content, encoding="utf-8")
    assert not consent.is_given(tmp_path, JOB)


def test_withdrawing_ends_it_and_can_be_repeated(tmp_path):
    consent.give(tmp_path, JOB, consent.VERSION, NOW)
    consent.withdraw(tmp_path)
    consent.withdraw(tmp_path)
    assert not consent.is_given(tmp_path, JOB)


def test_receipt_names_version_and_kind_only(tmp_path):
    assert consent.receipt(tmp_path) == ""
    consent.give(tmp_path, APPRENTICESHIP, consent.VERSION, NOW)
    assert consent.receipt(tmp_path) == f"{consent.VERSION} {APPRENTICESHIP}"


def test_state_tells_the_page_what_to_show(tmp_path, monkeypatch):
    monkeypatch.delenv(consent.PAGE_VARIABLE, raising=False)
    state = consent.state(tmp_path, APPRENTICESHIP)
    assert state == {"erteilt": False, "fassung": consent.VERSION, "text": consent.WORDING[APPRENTICESHIP], "link": ""}
    monkeypatch.setenv(consent.PAGE_VARIABLE, "https://beispiel.example/datenschutz")
    assert consent.state(tmp_path, APPRENTICESHIP)["link"] == "https://beispiel.example/datenschutz"


def _consented(server):
    daten = server.kontext.daten
    consent.give(daten, search_plan.kind_of_folder(daten), consent.VERSION, NOW)
    return daten


def test_the_way_to_the_ai_is_closed_without_consent(tmp_path):
    k = dataclasses.make_dataclass("K", ["daten"])(tmp_path)
    with pytest.raises(AiError, match="Einwilligung"):
        routes_ai.ai_gateway(k)


def test_status_tells_the_page_about_consent(server):  # noqa: F811
    assert get(server, "/api/ki/status")[0] == 200
    assert json.loads(get(server, "/api/ki/status")[2])["einwilligung"]["erteilt"] is False
    _consented(server)
    assert json.loads(get(server, "/api/ki/status")[2])["einwilligung"]["erteilt"] is True


def test_routes_give_and_withdraw_consent(server):  # noqa: F811
    status, answer = post(server, "/api/ki/einwilligung", {"fassung": consent.VERSION, "zustimmung": True})
    assert status == 200 and answer["einwilligung"]["erteilt"] is True
    status, answer = post(server, "/api/ki/einwilligung/widerruf", {})
    assert status == 200 and answer["einwilligung"]["erteilt"] is False


def test_route_needs_the_explicit_tick(server):  # noqa: F811
    status, answer = post(server, "/api/ki/einwilligung", {"fassung": consent.VERSION})
    assert status == 400 and "bestätigen" in answer["fehler"]
    assert not (server.kontext.daten / consent.FILE).exists()


def test_a_code_without_consent_waits_and_is_redeemed_after_it(server, monkeypatch):  # noqa: F811
    redeemed = []
    monkeypatch.setattr(routes_ai.invitation, "redeem", lambda url, code, receipt="": redeemed.append((code, receipt)))
    monkeypatch.setattr(routes_ai, "mediation_url", lambda: "https://vermittlung.example")
    status, answer = post(server, "/api/ki/einladung", {"code": "ABCD"})
    assert status == 400 and "Einwilligung" in answer["fehler"] and redeemed == []
    post(server, "/api/ki/einwilligung", {"fassung": consent.VERSION, "zustimmung": True})
    assert redeemed == [("ABCD", f"{consent.VERSION} {JOB}")]
    post(server, "/api/ki/einwilligung/widerruf", {})
    post(server, "/api/ki/einwilligung", {"fassung": consent.VERSION, "zustimmung": True})
    assert len(redeemed) == 1  # used once


def test_the_receipt_goes_along_when_a_code_is_redeemed(server, monkeypatch):  # noqa: F811
    seen = {}
    monkeypatch.setattr(routes_ai.invitation, "redeem", lambda url, code, receipt="": seen.update(receipt=receipt))
    monkeypatch.setattr(routes_ai, "mediation_url", lambda: "https://vermittlung.example")
    _consented(server)
    assert post(server, "/api/ki/einladung", {"code": "ABCD"})[0] == 200
    assert seen["receipt"] == f"{consent.VERSION} {JOB}"


def test_a_failed_waiting_code_is_named_but_the_consent_stays(server, monkeypatch):  # noqa: F811
    def refuse(url, code, receipt=""):
        raise AiError("Der Code gilt nicht.")
    monkeypatch.setattr(routes_ai.invitation, "redeem", refuse)
    monkeypatch.setattr(routes_ai, "mediation_url", lambda: "https://vermittlung.example")
    post(server, "/api/ki/einladung", {"code": "ABCD"})
    status, answer = post(server, "/api/ki/einwilligung", {"fassung": consent.VERSION, "zustimmung": True})
    assert status == 200 and answer["einwilligung"]["erteilt"] is True and "Der Code gilt nicht." in answer["einladung_fehler"]


@pytest.mark.questions_page
def test_chat_is_refused_on_the_apprenticeship_track(server):  # noqa: F811
    (server.kontext.daten / preferences.FILE).write_text(APPRENTICESHIP_CHOSEN, encoding="utf-8")
    status, answer = post(server, "/api/fragen/senden", {"frage": "Was fehlt noch?"})
    assert status == 400 and "18" in answer["fehler"]
    assert json.loads(get(server, "/api/fragen/stand")[2])["erlaubt"] is False


def test_the_invitation_link_waits_visibly_and_survives_choosing_the_folder(server, monkeypatch, tmp_path):  # noqa: F811
    monkeypatch.setenv(URL_VARIABLE, "https://ki.example.ch")
    monkeypatch.delenv(ACCESS_VARIABLE, raising=False)
    monkeypatch.setattr("ai.connection._keyring_access", lambda: None)
    post(server, "/api/ki/einladung", {"code": "ABCD-EFGH"})
    assert json.loads(get(server, "/api/ki/status")[2])["einwilligung"]["code_wartet"] is True
    new = app.erstelle_kontext(tmp_path)
    routes_ai.hand_over_waiting_code(server.kontext, new)
    assert new.cache[routes_ai.WAITING_CODE] == "ABCD-EFGH"


@pytest.mark.parametrize("page", ["/einstellungen", "/bewerbung"])
def test_the_pages_with_the_consent_block_load_its_script(server, page):  # noqa: F811
    assert b'id="ki-einwilligung"' in get(server, page)[2] or b'id="einwilligung-offen"' in get(server, page)[2]
    assert b'src="/einwilligung.js"' in get(server, page)[2]
    assert get(server, "/einwilligung.js")[0] == 200


def test_the_setup_shows_the_consent_in_the_window_ki_einrichten(server):  # noqa: F811
    page = get(server, "/einrichtung")[2]
    assert b'id="ki-einwilligung"' not in page, "no step KI (G60)"
    for script in (b'src="/einwilligung.js"', b'src="/ki-zugang.js"', b'src="/ki-fenster.js"'):
        assert script in page


@pytest.mark.parametrize("setup, profile, expected", [
    (None, None, JOB),
    ("gesucht: lehrstelle\nanrede: du\nrav: false\n", None, APPRENTICESHIP),
    ("gesucht: stelle\nanrede: sie\nrav: true\n", None, JOB),
    (None, search_plan.APPRENTICESHIP_MARK, APPRENTICESHIP),
    ("gesucht: stelle\nanrede: sie\nrav: true\n", search_plan.APPRENTICESHIP_MARK, APPRENTICESHIP),
])
def test_an_apprenticeship_anywhere_counts_as_the_stricter_kind(tmp_path, setup, profile, expected):
    if setup:
        (tmp_path / preferences.FILE).write_text(setup, encoding="utf-8")
    if profile:
        (tmp_path / search_plan.PROFILE).write_text(profile, encoding="utf-8")
    assert preferences.strictest_kind(tmp_path) == expected


def test_the_choice_in_the_setup_is_enough_for_the_wording(server):  # noqa: F811
    (server.kontext.daten / preferences.FILE).write_text(APPRENTICESHIP_CHOSEN, encoding="utf-8")
    assert "Elternteil" in json.loads(get(server, "/api/ki/status")[2])["einwilligung"]["text"]


def test_a_waiting_code_that_failed_on_the_way_says_to_open_the_link_again(server, monkeypatch):  # noqa: F811
    def offline(url, code, receipt=""):
        raise AiError(errors.OFFLINE)
    monkeypatch.setattr(routes_ai.invitation, "redeem", offline)
    monkeypatch.setattr(routes_ai, "mediation_url", lambda: "https://vermittlung.example")
    post(server, "/api/ki/einladung", {"code": "ABCD"})
    answer = post(server, "/api/ki/einwilligung", {"fassung": consent.VERSION, "zustimmung": True})[1]
    assert errors.OFFLINE in answer["einladung_fehler"] and "Einladungslink nochmals" in answer["einladung_fehler"]


def test_an_invalid_waiting_code_does_not_send_the_person_back_to_the_link(server, monkeypatch):  # noqa: F811
    def invalid(url, code, receipt=""):
        raise AiError(invitation.CODE_INVALID)
    monkeypatch.setattr(routes_ai.invitation, "redeem", invalid)
    monkeypatch.setattr(routes_ai, "mediation_url", lambda: "https://vermittlung.example")
    post(server, "/api/ki/einladung", {"code": "ABCD"})
    answer = post(server, "/api/ki/einwilligung", {"fassung": consent.VERSION, "zustimmung": True})[1]
    assert answer["einladung_fehler"] == invitation.CODE_INVALID


def test_the_extension_hears_of_the_ai_only_with_consent(server, monkeypatch):  # noqa: F811
    monkeypatch.setattr(routes_ai, "connected", lambda: True)
    monkeypatch.setattr(routes_apply.apply, "blocker", lambda *args: None)
    monkeypatch.setattr(routes_apply.apply, "form_values", lambda *args: {})
    monkeypatch.setattr(routes_apply.apply, "uploads", lambda *args: [])
    monkeypatch.setattr(routes_apply.apply, "describe_uploads", lambda *args: [])
    entry = server.kontext.register().neu(firma="A", stelle="B")
    assert json.loads(get(server, "/api/bewerben/daten", id=entry["id"])[2])["ki"] is False
    _consented(server)
    assert json.loads(get(server, "/api/bewerben/daten", id=entry["id"])[2])["ki"] is True


def test_the_choice_in_the_setup_makes_the_material_that_of_a_minor(tmp_path):
    (tmp_path / search_plan.PROFILE).write_text("# Ein altes Profil für eine Stelle\n", encoding="utf-8")
    assert tasks.load_material(tmp_path, partial=True).minor is False
    (tmp_path / preferences.FILE).write_text(APPRENTICESHIP_CHOSEN, encoding="utf-8")
    assert tasks.load_material(tmp_path, partial=True).minor is True


def test_the_career_page_follows_the_choice_in_the_setup(server):  # noqa: F811
    daten = server.kontext.daten
    (daten / search_plan.PROFILE).write_text("# Ein altes Profil für eine Stelle\n", encoding="utf-8")
    (daten / preferences.FILE).write_text(APPRENTICESHIP_CHOSEN, encoding="utf-8")
    status, answer = post(server, "/api/beruf/vorschlag", {})
    assert status == 400 and answer["fehler"].startswith("Schreib zu beidem")


def test_the_mediation_gets_the_receipt_with_the_code():
    sent = []

    def opener(request):
        sent.append(json.loads(request.data))
        raise invitation.AiError("stop")

    with pytest.raises(AiError):
        invitation.redeem("https://ki.example.ch", "ABCD-EFGH", opener=opener, receipt="2026-11 stelle")
    assert sent[0]["consent"] == "2026-11 stelle" and sent[0]["code"] == "ABCD-EFGH"


def test_the_wording_writes_datenschutzerklaerung_as_one_word():
    page = (PAGES / "einwilligung.js").read_text(encoding="utf-8")

    for text in [*consent.WORDING.values(), page]:
        assert "Datenschutz-Erklärung" not in text
    assert all("Datenschutzerklärung" in text for text in consent.WORDING.values())
    assert "Datenschutzerklärung lesen" in page
