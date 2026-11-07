"""Applying through a form (MIN-346): what may be opened, the values for the fields, the parts of a file."""
import base64
import json

import pytest
import yaml

import apply
import pruefung
import routes_apply
from register import Register
from test_app import get, post, server  # noqa: F401  (server is a fixture)


def ready(server, firma="Muster AG", stelle="Entwicklerin", link="https://example.ch/stelle", **fields):
    """An application whose documents exist, as far as the routes look at them."""
    data = server.kontext.daten
    entry = Register(data).neu(firma=firma, stelle=stelle, link=link, status="Bewerben", **fields)
    folder = data / "bewerbungen" / entry["id"]
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "lebenslauf.pdf").write_bytes(b"%PDF-1.4 cv")
    (folder / "anschreiben.pdf").write_bytes(b"%PDF-1.4 letter")
    return entry


@pytest.fixture
def checked(monkeypatch):
    """The formal check reads real PDFs; here it finds nothing unless a test says so."""
    findings = []
    monkeypatch.setattr(routes_apply.pruefung, "pruefe", lambda *a: list(findings))
    return findings


def test_prefers_the_form_link_and_accepts_only_web_addresses():
    assert apply.form_link({"formular_link": "https://a.ch/form", "link": "https://a.ch/ad"}) == "https://a.ch/form"
    assert apply.form_link({"link": "https://a.ch/ad"}) == "https://a.ch/ad"
    assert apply.form_link({"link": "javascript:alert(1)"}) is None
    assert apply.form_link({}) is None


@pytest.mark.parametrize("change, reason", [
    ({"versand": {"datum": "2026-10-01"}}, apply.ALREADY_SENT),
    ({"status": "Absage"}, "Status „Absage“"),
    ({"link": None}, apply.NO_LINK),
])
def test_says_why_an_application_cannot_be_opened(tmp_path, change, reason):
    entry = {"id": "a", "status": "Bewerben", "link": "https://a.ch", **change}

    assert apply.blocker(tmp_path, entry) == reason


def test_needs_the_cv_as_pdf(tmp_path):
    entry = {"id": "a", "status": "Bewerben", "link": "https://a.ch"}

    assert apply.blocker(tmp_path, entry) == apply.NO_CV
    (tmp_path / "bewerbungen" / "a").mkdir(parents=True)
    (tmp_path / "bewerbungen" / "a" / "lebenslauf.pdf").write_bytes(b"x")
    assert apply.blocker(tmp_path, entry) is None


def test_finds_a_running_application_and_two_in_one_run():
    everyone = [{"id": "a", "firma": "Muster AG", "stelle": "A", "status": "Bewerben"},
                {"id": "b", "firma": "Muster", "stelle": "B", "status": "Beworben"},
                {"id": "c", "firma": "Andere GmbH", "stelle": "C", "status": "Bewerben"},
                {"id": "d", "firma": "Andere", "stelle": "D", "status": "Bewerben"},
                {"id": "e", "firma": "Dritte", "stelle": "E", "status": "Absage"},
                {"id": "f", "firma": "Dritte", "stelle": "F", "status": "Bewerben"}]

    found = apply.duplicates(everyone, [everyone[0], everyone[2], everyone[3], everyone[5]])

    assert [(d["id"], d["stelle"]) for d in found] == [("a", "B"), ("c", "D"), ("d", "C")]


def test_a_company_without_a_name_is_no_duplicate():
    everyone = [{"id": "a", "firma": "AG", "status": "Bewerben"}, {"id": "b", "firma": "GmbH", "status": "Beworben"}]

    assert apply.duplicates(everyone, everyone[:1]) == []


@pytest.mark.parametrize("name, first, last", [
    ("Erika Beispiel", "Erika", "Beispiel"),
    ("Anna Maria Muster", "Anna Maria", "Muster"),
    ("Hans von Allmen", "Hans", "von Allmen"),
    ("Dr. Erika Beispiel", "Erika", "Beispiel"),
    ("Cher", "", "Cher"),
])
def test_splits_a_name(name, first, last):
    assert apply._split_name(name) == (first, last)


def write_cv(folder, **basics):
    (folder / "cv.yaml").write_text(yaml.safe_dump({"basics": basics}, allow_unicode=True), encoding="utf-8")


def test_values_come_from_the_cv_and_the_frame(tmp_path):
    write_cv(tmp_path, name="Erika Beispiel", email="erika@example.ch", phone="079 000 00 00", url="www.example.ch",
             location={"address": "Musterweg 1", "postalCode": "3000", "city": "Bern"},
             profiles=[{"network": "LinkedIn", "url": "https://linkedin.com/in/x"}, {"network": "Xing", "url": "https://x"}])
    (tmp_path / "anschreiben").mkdir()
    (tmp_path / "anschreiben" / "bausteine.md").write_text(
        "## Rahmen\n\n- Verfügbar ab: 1. März\n- Kündigungsfrist: 3 Monate\n- Referenz: geheim\n", encoding="utf-8")

    assert apply.form_values(tmp_path) == {
        "full_name": "Erika Beispiel", "first_name": "Erika", "last_name": "Beispiel", "last_first": "Beispiel, Erika",
        "postal_city": "3000 Bern", "email": "erika@example.ch",
        "phone": "079 000 00 00", "street": "Musterweg 1", "postal_code": "3000", "city": "Bern", "country": "Schweiz",
        "website": "www.example.ch", "linkedin": "https://linkedin.com/in/x", "availability": "1. März",
        "notice": "3 Monate"}


def test_a_foreign_postal_code_leaves_the_country_open(tmp_path):
    write_cv(tmp_path, name="Erika Beispiel", location={"postalCode": "79100"})

    assert "country" not in apply.form_values(tmp_path)


def test_a_cv_without_a_person_is_refused(tmp_path):
    (tmp_path / "cv.yaml").write_text("work: []\n", encoding="utf-8")

    with pytest.raises(ValueError, match="fehlen"):
        apply.form_values(tmp_path)


def test_parts_cover_the_file_and_join_to_valid_base64(tmp_path, monkeypatch):
    path = tmp_path / "datei.bin"
    content = bytes(range(256)) * 40
    path.write_bytes(content)
    upload = apply.Upload(path, "datei.bin")
    monkeypatch.setattr(apply, "PART_BYTES", 3000)

    first, parts = apply.read_part(upload, 0)
    rest = [apply.read_part(upload, nr)[0] for nr in range(1, parts)]
    joined = "".join(base64.b64encode(part).decode() for part in [first, *rest])

    assert parts == 4 and base64.b64decode(joined) == content
    with pytest.raises(ValueError):
        apply.read_part(upload, parts)
    with pytest.raises(ValueError):
        apply.read_part(upload, -1)


def test_a_part_stays_below_the_limit_of_the_host():
    assert apply.PART_BYTES % 3 == 0 and apply.PART_BYTES * 4 / 3 < 950_000


def test_an_empty_file_has_one_empty_part(tmp_path):
    path = tmp_path / "leer.pdf"
    path.write_bytes(b"")

    assert apply.read_part(apply.Upload(path, "leer.pdf"), 0) == (b"", 1)


def test_the_overview_shows_what_can_be_chosen(server):
    entry = ready(server)
    other = Register(server.kontext.daten).neu(firma="Ohne Link", stelle="X", status="Bewerben")

    status, _, content = get(server, "/api/bewerben/auswahl")
    reasons = {row["id"]: row["grund"] for row in json.loads(content)["bewerbungen"]}

    assert status == 200 and reasons[entry["id"]] is None and reasons[other["id"]] == apply.NO_LINK


def test_start_gives_the_links_and_changes_nothing(server, checked):
    entry = ready(server, formular_link="https://example.ch/form")

    status, answer = post(server, "/api/bewerben/start", {"ids": [entry["id"]]})

    assert status == 200 and answer["bereit"] == [{"id": entry["id"], "firma": "Muster AG", "stelle": "Entwicklerin",
                                                   "link": "https://example.ch/form"}]
    assert (answer["textsatz"], answer["rav"]) == ("stelle-sie", True), "the bar speaks like the app (MIN-369)"
    assert "ausfuellen" not in Register(server.kontext.daten).hole(entry["id"])


def test_start_refuses_a_failed_check_with_its_reason(server, checked):
    entry = ready(server)
    checked.append(pruefung.Befund("fehler", "Lebenslauf hat zu viele Seiten"))

    _, answer = post(server, "/api/bewerben/start", {"ids": [entry["id"]]})

    assert answer["bereit"] == [] and answer["abgelehnt"][0]["grund"] == "Prüfung: Lebenslauf hat zu viele Seiten"


def test_a_hint_of_the_check_does_not_stop_it(server, checked):
    entry = ready(server)
    checked.append(pruefung.Befund("hinweis", "Kein Anschreiben"))

    _, answer = post(server, "/api/bewerben/start", {"ids": [entry["id"]]})

    assert len(answer["bereit"]) == 1


def test_start_asks_about_duplicates_and_goes_on_when_confirmed(server, checked):
    entry = ready(server)
    Register(server.kontext.daten).neu(firma="Muster", stelle="Früher", status="Beworben")

    _, first = post(server, "/api/bewerben/start", {"ids": [entry["id"]]})
    _, second = post(server, "/api/bewerben/start", {"ids": [entry["id"]], "bestaetigt": True})

    assert first["bereit"] == [] and first["doppelt"][0]["stelle"] == "Früher"
    assert len(second["bereit"]) == 1


def test_confirming_does_not_pass_a_refusal(server, checked):
    entry = ready(server)
    checked.append(pruefung.Befund("fehler", "Falsch"))

    _, answer = post(server, "/api/bewerben/start", {"ids": [entry["id"]], "bestaetigt": True})

    assert answer["bereit"] == []


@pytest.mark.parametrize("ids, status", [([], 400), ("a", 400), ([1], 400), (["fehlt"], 404)])
def test_start_checks_its_input(server, ids, status):
    assert post(server, "/api/bewerben/start", {"ids": ids})[0] == status


def test_start_allows_only_so_many(server):
    ids = [f"a{nr}" for nr in range(apply.MAX_PER_RUN + 1)]

    status, answer = post(server, "/api/bewerben/start", {"ids": ids})

    assert status == 400 and "höchstens" in answer["fehler"]


def test_values_and_files_for_an_open_application(server):
    entry = ready(server)
    data = server.kontext.daten
    (data / "dokumente" / "zeugnisse").mkdir(parents=True)
    (data / "dokumente" / "zeugnisse" / "Zeugnis Beispiel AG.pdf").write_bytes(b"z" * 10)
    (data / "bewerbungen" / entry["id"] / "zertifikate.zip").write_bytes(b"zip")

    status, _, content = get(server, "/api/bewerben/daten", id=entry["id"])
    answer = json.loads(content)
    names = {f["schluessel"]: f["name"] for f in answer["dateien"]}
    reference = next(key for key in names if key.startswith("zeugnis-"))

    assert status == 200 and answer["werte"]["email"] and "beispiel" in names["lebenslauf"].lower()
    assert names[reference] == "Zeugnis Beispiel AG.pdf" and names["zertifikate"].endswith(".zip")

    status, _, content = get(server, "/api/bewerben/datei", id=entry["id"], schluessel=reference)
    part = json.loads(content)
    assert status == 200 and base64.b64decode(part["daten"]) == b"z" * 10
    assert part["typ"] == "application/pdf" and part["teile"] == 1


def test_only_files_of_the_application_can_be_asked_for(server):
    entry = ready(server)

    for key in ("../cv.yaml", "cv.yaml", "zeugnis-9"):
        status, _, _ = get(server, "/api/bewerben/datei", id=entry["id"], schluessel=key)
        assert status == 400


def test_a_sent_application_gives_no_values_any_more(server):
    entry = ready(server, firma="Versendet AG")
    register = Register(server.kontext.daten)
    register.speichere({**register.hole(entry["id"]), "versand": {"datum": "2026-10-01"}})

    assert get(server, "/api/bewerben/daten", id=entry["id"])[0] == 400
    assert get(server, "/api/bewerben/datei", id=entry["id"], schluessel="lebenslauf")[0] == 400


def test_the_state_is_kept_and_the_tab_cannot_claim_a_dispatch(server):
    entry = ready(server)
    register = Register(server.kontext.daten)

    assert post(server, "/api/bewerben/stand", {"id": entry["id"], "stand": "geoeffnet"})[0] == 200
    assert register.hole(entry["id"])["ausfuellen"] == "geoeffnet"
    assert post(server, "/api/bewerben/stand", {"id": entry["id"], "stand": "abgeschickt"})[0] == 400
    assert post(server, "/api/bewerben/stand", {"id": entry["id"], "stand": "irgendwas"})[0] == 400
    assert register.hole(entry["id"])["ausfuellen"] == "geoeffnet"


def test_saving_the_page_form_keeps_the_state(server):
    entry = ready(server)
    post(server, "/api/bewerben/stand", {"id": entry["id"], "stand": "ausgefuellt"})
    current = Register(server.kontext.daten).hole(entry["id"])

    post(server, "/api/bewerbung", {**current, "ausfuellen": "geoeffnet", "notiz": "neu"})

    saved = Register(server.kontext.daten).hole(entry["id"])
    assert saved["ausfuellen"] == "ausgefuellt" and saved["notiz"] == "neu"


def test_sent_records_the_dispatch_like_the_page_does(server):
    entry = ready(server)

    status, answer = post(server, "/api/bewerben/abgeschickt", {"id": entry["id"]})
    saved = Register(server.kontext.daten).hole(entry["id"])

    assert status == 200 and answer["stand"] == "abgeschickt"
    assert saved["ausfuellen"] == "abgeschickt" and saved["status"] == "Beworben"
    assert saved["versand"]["datum"] == server.kontext.heute().isoformat() and "lebenslauf" in saved["versand"]["dateien"]


def test_sent_twice_is_refused_and_a_late_state_changes_nothing(server):
    entry = ready(server)
    post(server, "/api/bewerben/abgeschickt", {"id": entry["id"]})

    assert post(server, "/api/bewerben/abgeschickt", {"id": entry["id"]})[0] == 400
    assert post(server, "/api/bewerben/stand", {"id": entry["id"], "stand": "ausgefuellt"})[0] == 200
    assert Register(server.kontext.daten).hole(entry["id"])["ausfuellen"] == "abgeschickt"
