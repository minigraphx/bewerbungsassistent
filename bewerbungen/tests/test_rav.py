"""Entering applications in Job-Room (MIN-347): what can be chosen, what goes into the form, the reminder and the routes."""
import datetime
import json

import pytest

import rav
import routes_ai
from register import Register, pruefe_bewerbung
from test_app import get, post, server  # noqa: F401  (fixtures)


def applied(**fields) -> dict:
    return {"id": "muster-ag-dev", "firma": "Muster AG", "stelle": "Entwickler", "status": "Beworben",
            "beworben_am": "2026-10-20", **fields}


def add(k_dir, **fields) -> dict:
    return Register(k_dir).speichere(applied(**fields))


# What can be chosen


def test_only_applications_sent_and_not_entered_can_be_chosen():
    assert rav.blocker(applied()) is None
    assert rav.blocker(applied(rav_eingetragen_am="2026-10-21")) == rav.ALREADY_ENTERED
    assert rav.blocker({"id": "a", "firma": "A", "stelle": "B", "status": "Gemerkt"}) == rav.NOT_APPLIED


def test_the_register_keeps_the_date_it_was_entered():
    assert pruefe_bewerbung(applied(rav_eingetragen_am="21.10.2026"))["rav_eingetragen_am"] == "2026-10-21"
    with pytest.raises(ValueError):
        pruefe_bewerbung(applied(rav_eingetragen_am="gestern"))


# What goes into the form


def test_values_of_an_electronic_application():
    values = rav.form_values(applied(kontaktperson="Eva Beispiel", pensum="80-100%", formular_link="https://example.org/jobs/1",
                                     kontakt="Eva Beispiel, eva@example.org, +41 31 555 01 02", adresse="Musterweg 12, 3000 Bern"))
    assert values == {
        "date": "20.10.2026", "channel": "electronic", "company": "Muster AG", "contact_person": "Eva Beispiel",
        "occupation": "Entwickler", "email": "eva@example.org", "phone": "+41 31 555 01 02",
        "url": "https://example.org/jobs/1", "workload": "part", "through_rav": False, "result": "open", "interview": False,
    }


def test_the_address_goes_along_only_when_the_channel_needs_it():
    address = "Muster AG, Musterweg 12a, Postfach 77, CH-3000 Bern"
    values = rav.form_values(applied(adresse=address, versand={"art": "schriftlich", "datum": "2026-10-20"}))
    assert values["channel"] == "letter"
    assert (values["street"], values["house_number"], values["po_box"], values["postal_city"]) == ("Musterweg", "12a", "77", "3000 Bern")
    personal = rav.form_values(applied(adresse="Musterweg, 3000 Bern", versand={"art": "persönlich"}))
    assert personal["channel"] == "personal" and personal["street"] == "Musterweg" and "house_number" not in personal
    assert "street" not in rav.form_values(applied(adresse=address, versand={"art": "telefonisch"}))


@pytest.mark.parametrize("address, expected", [
    ("Musterweg 1, 3000 Bern, Schweiz", {"street": "Musterweg", "house_number": "1", "postal_city": "3000 Bern"}),
    ("Musterweg 1\n3000 Bern\nCH", {"street": "Musterweg", "house_number": "1", "postal_city": "3000 Bern"}),
    ("Musterweg 1 3000 Bern", {"street": "Musterweg", "house_number": "1", "postal_city": "3000 Bern"}),
    ("Musterweg 1 / 3000 Bern", {"street": "Musterweg", "house_number": "1", "postal_city": "3000 Bern"}),
    ("Muster AG, c/o Beispiel, Musterweg 1, 3000 Bern", {"street": "Musterweg", "house_number": "1", "postal_city": "3000 Bern"}),
    ("Musterweg 1, Abteilung Personal, 3000 Bern", {"street": "Musterweg", "house_number": "1", "postal_city": "3000 Bern"}),
    ("Muster AG, 3000 Bern", {"postal_city": "3000 Bern"}),
    ("Rue de la Gare 3, 1700 Fribourg", {"street": "Rue de la Gare", "house_number": "3", "postal_city": "1700 Fribourg"}),
])
def test_addresses_as_people_write_them(address, expected):
    values = rav.form_values(applied(adresse=address, versand={"art": "schriftlich"}))
    found = {key: values[key] for key in ("street", "house_number", "po_box", "postal_city") if key in values}
    assert found == expected


@pytest.mark.parametrize("contact, email, phone", [
    ("Frau Meier (meier@example.org)", "meier@example.org", None),
    ("<a@example.org>; 031 555 01 02", "a@example.org", "031 555 01 02"),
    ("031 555 01 02 / 079 123 45 67", None, "031 555 01 02"),
    ("031/555 01 02", None, "031/555 01 02"),
])
def test_contact_details_as_people_write_them(contact, email, phone):
    values = rav.form_values(applied(kontakt=contact))
    assert (values.get("email"), values.get("phone")) == (email, phone)


@pytest.mark.parametrize("fields, result, interview", [
    ({"status": "Beworben"}, "open", False),
    ({"status": "Gespräch"}, "open", True),
    ({"status": "Beworben", "gespraech_am": "2026-10-25"}, "open", True),
    ({"status": "Absage", "absage_am": "2026-10-28", "gespraech_am": "2026-10-25"}, "rejected", True),
    ({"status": "Zusage"}, "employed", False),
])
def test_result_and_interview_are_separate_in_the_form(fields, result, interview):
    values = rav.form_values(applied(**fields))
    assert (values["result"], values["interview"]) == (result, interview)


def test_unknown_workload_stays_open_and_assignment_is_carried():
    values = rav.form_values(applied(rav_zuweisung=True))
    assert "workload" not in values and values["through_rav"] is True


def test_the_link_of_the_ad_is_used_without_a_form_link():
    assert rav.form_values(applied(link="https://example.org/inserat"))["url"] == "https://example.org/inserat"


# Reminder


@pytest.mark.parametrize("today, month, deadline", [
    (datetime.date(2026, 10, 25), "Oktober 2026", "05.11.2026"),
    (datetime.date(2026, 11, 5), "Oktober 2026", "05.11.2026"),
])
def test_reminder_in_the_days_around_the_end_of_the_month(today, month, deadline):
    entries = [applied(id="a"), applied(id="b", rav_eingetragen_am="2026-10-21"), applied(id="c", beworben_am="2026-09-03")]
    found = rav.reminder(entries, today)
    assert found == {"ids": ["a"], "monat": month, "frist": deadline}


def test_reminder_turns_the_year():
    entries = [applied(id="a", beworben_am="2026-12-03"), applied(id="b", beworben_am="2026-01-03", rav_eingetragen_am="2026-01-04")]
    assert rav.reminder(entries, datetime.date(2027, 1, 2)) == {"ids": ["a"], "monat": "Dezember 2026", "frist": "05.01.2027"}


def test_no_reminder_in_the_middle_of_the_month_when_all_is_entered_or_for_people_not_using_it():
    used = applied(id="b", rav_eingetragen_am="2026-10-21")
    assert rav.reminder([applied(id="a"), used], datetime.date(2026, 10, 15)) is None
    assert rav.reminder([used], datetime.date(2026, 10, 28)) is None
    assert rav.reminder([applied(id="a")], datetime.date(2026, 10, 28)) is None


# Routes


def test_choice_lists_reason_and_reminder(server, datenordner):
    add(datenordner)
    add(datenordner, id="b", rav_eingetragen_am="2026-10-21")
    status, _, content = get(server, "/api/rav/auswahl")
    answer = json.loads(content)
    assert status == 200 and answer["sichtbar"] is True and answer["hoechstens"] == rav.MAX_PER_RUN
    reasons = {row["id"]: row["grund"] for row in answer["bewerbungen"]}
    assert reasons["muster-ag-dev"] is None and reasons["b"] == rav.ALREADY_ENTERED
    assert answer["erinnerung"]["ids"] == ["muster-ag-dev"]


def test_people_looking_for_an_apprenticeship_do_not_see_it(server, datenordner):
    (datenordner / "suchprofil.md").write_text("# Suchprofil\n\n## Lehrbeginn\n2027\n", encoding="utf-8")
    _, _, content = get(server, "/api/rav/auswahl")
    assert json.loads(content)["sichtbar"] is False


def test_start_checks_and_writes_nothing(server, datenordner):
    add(datenordner)
    add(datenordner, id="b", rav_eingetragen_am="2026-10-21")
    before = (datenordner / "bewerbungen.yaml").read_bytes()
    status, answer = post(server, "/api/rav/start", {"ids": ["muster-ag-dev", "b"]})
    assert status == 200
    assert answer["bereit"] == [{"id": "muster-ag-dev", "firma": "Muster AG", "stelle": "Entwickler",
                                 "beworben_am": Register(datenordner).hole("muster-ag-dev")["beworben_am"]}]
    assert answer["textsatz"] == "stelle-sie"
    assert [row["id"] for row in answer["abgelehnt"]] == ["b"]
    assert (datenordner / "bewerbungen.yaml").read_bytes() == before


@pytest.mark.parametrize("body", [{}, {"ids": []}, {"ids": "a"}, {"ids": [1]}, {"ids": [f"a{n}" for n in range(rav.MAX_PER_RUN + 1)]}])
def test_start_refuses_a_bad_choice(server, body):
    status, answer = post(server, "/api/rav/start", body)
    assert status == 400 and answer["fehler"]


def test_unknown_application_is_not_found(server):
    assert post(server, "/api/rav/start", {"ids": ["fehlt"]})[0] == 404
    assert get(server, "/api/rav/angaben", id="fehlt")[0] == 404
    assert post(server, "/api/rav/eingetragen", {"id": "fehlt"})[0] == 404


def test_values_never_touch_the_ai(server, datenordner, monkeypatch):
    def no_ai(*_args, **_kwargs):
        raise AssertionError("RAV data must not reach the AI")
    monkeypatch.setattr(routes_ai, "new_client", no_ai)
    add(datenordner)
    status, _, content = get(server, "/api/rav/angaben", id="muster-ag-dev")
    assert status == 200 and json.loads(content)["werte"]["company"] == "Muster AG"
    assert post(server, "/api/rav/eingetragen", {"id": "muster-ag-dev"})[0] == 200


def test_values_of_an_entered_application_are_refused(server, datenordner):
    add(datenordner, rav_eingetragen_am="2026-10-21")
    assert get(server, "/api/rav/angaben", id="muster-ag-dev")[0] == 400


def test_entered_records_the_day_once(server, datenordner):
    add(datenordner)
    status, answer = post(server, "/api/rav/eingetragen", {"id": "muster-ag-dev"})
    assert status == 200 and answer == {"rav_eingetragen_am": "2026-10-26"}
    assert Register(datenordner).hole("muster-ag-dev")["rav_eingetragen_am"] == "2026-10-26"
    Register(datenordner).speichere({**Register(datenordner).hole("muster-ag-dev"), "rav_eingetragen_am": "2026-10-21"})
    assert post(server, "/api/rav/eingetragen", {"id": "muster-ag-dev"})[1] == {"rav_eingetragen_am": "2026-10-21"}


def test_only_an_application_that_was_sent_can_be_entered(server, datenordner):
    Register(datenordner).speichere({"id": "offen", "firma": "A", "stelle": "B", "status": "Gemerkt"})
    assert post(server, "/api/rav/eingetragen", {"id": "offen"})[0] == 400


def test_undo_makes_it_choosable_again(server, datenordner):
    add(datenordner, rav_eingetragen_am="2026-10-21")
    status, answer = post(server, "/api/rav/zuruecksetzen", {"id": "muster-ag-dev"})
    assert status == 200 and answer == {"rav_eingetragen_am": None}
    assert "rav_eingetragen_am" not in Register(datenordner).hole("muster-ag-dev")


def test_saving_the_page_does_not_change_the_date(server, datenordner):
    entry = add(datenordner, rav_eingetragen_am="2026-10-21")
    status, saved = post(server, "/api/bewerbung", {**entry, "notiz": "Neu", "rav_eingetragen_am": "2026-01-01"})
    assert status == 200 and saved["rav_eingetragen_am"] == "2026-10-21"
    gone = {key: value for key, value in entry.items() if key != "rav_eingetragen_am"}
    assert post(server, "/api/bewerbung", gone)[1]["rav_eingetragen_am"] == "2026-10-21"


@pytest.mark.parametrize("chosen, visible", [
    ("gesucht: stelle\nanrede: sie\nrav: false\n", False),
    ("gesucht: lehrstelle\nanrede: du\nrav: true\n", True),
])
def test_the_choice_in_the_setup_decides_over_the_profile(server, datenordner, chosen, visible):
    (datenordner / "einrichtung.yaml").write_text(chosen, encoding="utf-8")
    _, _, content = get(server, "/api/rav/auswahl")
    assert json.loads(content)["sichtbar"] is visible
