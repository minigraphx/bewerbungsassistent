"""A finished cover letter per application, uploaded and used as it is."""
import base64
import dataclasses
import datetime
import io
import json

import pytest
from pypdf import PdfWriter

import apply
import inhalte
import own_files
import pruefung
import routes_ai
import routes_own_files
import unterlagen
import versand
from register import Register
from test_app import get, post, server  # noqa: F401  (server is a fixture)
from test_own_files import CountingLock, new_entry, upload

PDF = b"%PDF-1.4\n" + b"x" * 300
UPLOAD = "/api/dateien/anschreiben"
REMOVE = "/api/dateien/anschreiben/entfernen"
TODAY = datetime.date(2026, 11, 5)


def blank_pdf(pages: int = 1) -> bytes:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=200, height=200)
    stream = io.BytesIO()
    writer.write(stream)
    return stream.getvalue()


def upload_letter(s, entry_id, data=PDF, name="Mein Brief.pdf"):
    return post(s, UPLOAD, {"id": entry_id, "name": name, "daten": base64.b64encode(data).decode()})


def details(s, entry_id) -> dict:
    return json.loads(get(s, "/api/bewerbung", id=entry_id)[2])


def letter_findings(found) -> dict[str, list[str]]:
    letters = [b for b in found if b.text.startswith("Anschreiben")]
    return {level: [b.text for b in letters if b.stufe == level] for level in ("fehler", "hinweis", "ok")}


def send(s, entry_id):
    k = s.kontext
    return versand.erfasse_versand(k.daten, entry_id, k.heute(), k.versionierung)


def test_the_letter_counts_for_this_application_only_and_stays_unchanged(server):  # noqa: F811
    first, second = new_entry(server), new_entry(server)

    assert upload_letter(server, first["id"])[0] == 200

    assert unterlagen.own_letter_path(server.kontext.daten, first["id"]).read_bytes() == PDF
    assert get(server, "/api/pdf", id=first["id"], art="anschreiben")[2] == PDF
    shown = details(server, first["id"])
    assert (shown["eigenes_anschreiben"], shown["hat_anschreiben"], shown["pdfs"]["anschreiben"]) == (True, True, True)
    other = details(server, second["id"])
    assert (other["eigenes_anschreiben"], other["hat_anschreiben"], other["pdfs"]["anschreiben"]) == (False, False, False)


@pytest.mark.parametrize("name, data, message", [
    ("brief.docx", PDF, own_files.LETTER_ONLY_PDF),
    ("brief.png", b"\x89PNG\r\n\x1a\n", own_files.LETTER_ONLY_PDF),
    ("brief.pdf", b"kein pdf", "kein echtes PDF"),
    ("../../brief.exe", PDF, own_files.LETTER_ONLY_PDF),
])
def test_only_a_real_pdf_is_kept(server, name, data, message):  # noqa: F811
    entry = new_entry(server)

    code, answer = upload_letter(server, entry["id"], data, name)

    assert code == 400 and message in answer["fehler"]
    assert not unterlagen.own_letter_path(server.kontext.daten, entry["id"]).exists()


def test_a_letter_that_is_too_large_is_refused():
    with pytest.raises(ValueError, match="zu gross"):
        own_files.check_letter("brief.pdf", PDF + b"x" * own_files.MAX_FILE_BYTES)


def test_a_letter_up_to_the_limit_gets_through_the_server(server):  # noqa: F811
    entry = new_entry(server)
    large = PDF + b"x" * (3 * 1024 * 1024)  # above the general limit for requests

    assert upload_letter(server, entry["id"], large)[0] == 200


@pytest.mark.parametrize("wanted, expected", [("gibt-es-nicht", 404), (["liste"], 400), (None, 400), ("../..", 404)])
def test_the_application_must_exist(server, wanted, expected):  # noqa: F811
    assert upload_letter(server, wanted)[0] == expected
    assert post(server, REMOVE, {"id": wanted})[0] == expected


def test_it_goes_before_a_draft_and_building_leaves_it_alone(server):  # noqa: F811
    entry = new_entry(server)
    k = server.kontext
    upload(server, "lebenslauf", "cv.pdf")
    upload_letter(server, entry["id"])
    source = unterlagen.letter_source(k.daten, entry["id"])
    source.write_text("kaputt: [", encoding="utf-8")  # would stop the build if it were read

    built = unterlagen.baue(k.daten, Register(k.daten).hole(entry["id"]), k.build)

    assert built["anschreiben"] == unterlagen.own_letter_path(k.daten, entry["id"])
    assert not unterlagen.pdf_pfade(k.daten, entry["id"])["anschreiben"].exists()
    assert get(server, "/api/pdf", id=entry["id"], art="anschreiben")[2] == PDF


def test_after_removing_it_the_built_letter_counts_again(server):  # noqa: F811
    entry = new_entry(server)
    daten = server.kontext.daten
    built = unterlagen.pdf_pfade(daten, entry["id"])["anschreiben"]
    built.parent.mkdir(parents=True, exist_ok=True)
    built.write_bytes(PDF + b"gebaut")
    upload_letter(server, entry["id"])

    assert post(server, REMOVE, {"id": entry["id"]})[0] == 200

    assert not unterlagen.own_letter_path(daten, entry["id"]).exists()
    assert get(server, "/api/pdf", id=entry["id"], art="anschreiben")[2] == PDF + b"gebaut"
    assert details(server, entry["id"])["eigenes_anschreiben"] is False


def test_removing_what_is_not_there_says_so(server):  # noqa: F811
    code, answer = post(server, REMOVE, {"id": new_entry(server)["id"]})

    assert code == 400 and answer["fehler"] == own_files.NOT_THERE


def test_a_replaced_or_removed_letter_can_be_brought_back(server):  # noqa: F811
    entry = new_entry(server)
    upload_letter(server, entry["id"], PDF + b"alt")
    upload_letter(server, entry["id"], PDF + b"neu")
    post(server, REMOVE, {"id": entry["id"]})
    path = unterlagen.own_letter_path(server.kontext.daten, entry["id"])
    old = next(e for e in server.kontext.ablage.liste(path) if server.kontext.ablage.inhalt(e.id) == PDF + b"alt")

    assert post(server, "/api/entwurf/wiederherstellen", {"id": old.id})[0] == 200

    assert get(server, "/api/pdf", id=entry["id"], art="anschreiben")[2] == PDF + b"alt"


def test_a_scan_of_several_pages_is_for_the_person_to_decide(server):  # noqa: F811
    entry = new_entry(server)
    upload_letter(server, entry["id"], blank_pdf(pages=3))

    found = letter_findings(pruefung.pruefe(server.kontext.daten, Register(server.kontext.daten).hole(entry["id"]), TODAY))

    assert found["fehler"] == []
    assert any("kaum Text" in text for text in found["hinweis"])
    assert any("3 Seiten" in text for text in found["hinweis"])


def test_a_letter_that_cannot_be_read_stays_an_error(server):  # noqa: F811
    entry = new_entry(server)
    upload_letter(server, entry["id"])

    found = letter_findings(pruefung.pruefe(server.kontext.daten, Register(server.kontext.daten).hole(entry["id"]), TODAY))

    assert any("lässt sich nicht lesen" in text for text in found["fehler"])


def test_the_wrong_company_or_a_placeholder_only_gets_a_hint(server, monkeypatch):  # noqa: F811
    entry = new_entry(server)
    upload_letter(server, entry["id"], blank_pdf())
    monkeypatch.setattr(pruefung, "_seiten", lambda pdf: ["Bewerbung bei einer anderen Firma, {{FIRMA}}. " + "Text " * 60])

    found = letter_findings(pruefung.pruefe(server.kontext.daten, Register(server.kontext.daten).hole(entry["id"]), TODAY))

    assert found["fehler"] == []
    assert any("kommt nicht vor" in text for text in found["hinweis"])
    assert any("Platzhalter" in text for text in found["hinweis"])


def test_a_built_letter_is_still_held_to_the_rules(server, monkeypatch):  # noqa: F811
    entry = new_entry(server)
    built = unterlagen.pdf_pfade(server.kontext.daten, entry["id"])["anschreiben"]
    built.parent.mkdir(parents=True, exist_ok=True)
    built.write_bytes(blank_pdf(pages=3))
    monkeypatch.setattr(pruefung, "_seiten", lambda pdf: ["Andere Firma. " + "Text " * 60] * 3)

    found = letter_findings(pruefung.pruefe(server.kontext.daten, Register(server.kontext.daten).hole(entry["id"]), TODAY))

    assert any("kommt nicht vor" in text for text in found["fehler"])
    assert any("3 Seiten" in text for text in found["fehler"])


def test_what_a_draft_says_about_the_contact_does_not_count_against_it(server):  # noqa: F811
    entry = new_entry(server)
    daten = server.kontext.daten
    unterlagen.letter_source(daten, entry["id"]).parent.mkdir(parents=True, exist_ok=True)
    unterlagen.letter_source(daten, entry["id"]).write_text(
        "empfaenger: [Frau Petra Meier]\nanrede: Sehr geehrter Herr Muster\n", encoding="utf-8")
    upload_letter(server, entry["id"], blank_pdf())

    found = pruefung.pruefe(daten, Register(daten).hole(entry["id"]), TODAY)

    assert not any("Anrede" in b.text for b in found)


def test_without_any_letter_the_check_names_both_ways(server):  # noqa: F811
    entry = new_entry(server)

    found = letter_findings(pruefung.pruefe(server.kontext.daten, entry, TODAY))
    all_found = pruefung.pruefe(server.kontext.daten, entry, TODAY)

    assert found["fehler"] == []
    assert any(b.stufe == "hinweis" and "eigenes PDF" in b.text for b in all_found)


def test_it_is_what_the_form_gets(server):  # noqa: F811
    entry = new_entry(server)
    upload_letter(server, entry["id"], PDF + b"meins")

    files = apply.uploads(server.kontext.daten, Register(server.kontext.daten).hole(entry["id"]))

    assert files["anschreiben"].path.read_bytes() == PDF + b"meins"
    assert files["anschreiben"].name.endswith(".pdf")


def test_an_own_letter_does_not_open_the_way_without_a_cv(server):  # noqa: F811
    entry = new_entry(server, link="https://example.com/stelle")
    upload_letter(server, entry["id"])

    assert apply.blocker(server.kontext.daten, Register(server.kontext.daten).hole(entry["id"])) == apply.NO_CV


def test_after_sending_what_went_out_stays(server):  # noqa: F811
    entry = new_entry(server)
    upload(server, "lebenslauf", "cv.pdf")
    upload_letter(server, entry["id"], PDF + b"gesendet")
    daten = server.kontext.daten

    sent = send(server, entry["id"])["bewerbung"]["versand"]["dateien"]["anschreiben"]
    unterlagen.own_letter_path(daten, entry["id"]).write_bytes(PDF + b"spaeter von Hand")

    assert (daten / sent).read_bytes() == PDF + b"gesendet"
    assert get(server, "/api/pdf", id=entry["id"], art="anschreiben")[2] == PDF + b"gesendet"
    shown = details(server, entry["id"])
    assert (shown["eigenes_anschreiben"], shown["hat_anschreiben"]) == (False, True)


def test_after_sending_it_can_neither_be_replaced_nor_removed(server):  # noqa: F811
    entry = new_entry(server)
    upload(server, "lebenslauf", "cv.pdf")
    upload_letter(server, entry["id"], PDF + b"gesendet")
    send(server, entry["id"])
    path = unterlagen.own_letter_path(server.kontext.daten, entry["id"])

    assert upload_letter(server, entry["id"], PDF + b"neu")[0] == 400
    assert post(server, REMOVE, {"id": entry["id"]})[0] == 400

    assert path.read_bytes() == PDF + b"gesendet"


def test_a_built_letter_that_went_out_stays_as_well(server):  # noqa: F811
    entry = new_entry(server)
    daten = server.kontext.daten
    upload(server, "lebenslauf", "cv.pdf")
    built = unterlagen.pdf_pfade(daten, entry["id"])["anschreiben"]
    built.parent.mkdir(parents=True, exist_ok=True)
    built.write_bytes(PDF + b"gesendet")
    unterlagen.letter_source(daten, entry["id"]).write_text("anrede: Guten Tag\n", encoding="utf-8")

    send(server, entry["id"])
    built.write_bytes(PDF + b"neu gebaut")

    assert get(server, "/api/pdf", id=entry["id"], art="anschreiben")[2] == PDF + b"gesendet"
    assert details(server, entry["id"])["hat_anschreiben"] is True


def test_a_draft_that_did_not_go_out_is_not_marked_as_used(server):  # noqa: F811
    entry = new_entry(server)
    daten = server.kontext.daten
    upload(server, "lebenslauf", "cv.pdf")
    source = unterlagen.letter_source(daten, entry["id"])
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("anrede: Guten Tag\n", encoding="utf-8")
    server.kontext.ablage.speichere(source, "Entwurf")
    upload_letter(server, entry["id"])

    send(server, entry["id"])

    assert all(not e.genutzt_fuer for e in server.kontext.ablage.liste(source))


def test_the_check_and_the_file_change_in_one_turn(server, monkeypatch):  # noqa: F811
    entry = new_entry(server)
    lock = CountingLock()
    monkeypatch.setattr(server, "kontext", dataclasses.replace(server.kontext, sperre=lock))
    checked_under_lock = []
    original = routes_own_files._refuse_when_sent

    def recording(k, entry_id):
        checked_under_lock.append(lock.lock.locked())
        original(k, entry_id)

    monkeypatch.setattr(routes_own_files, "_refuse_when_sent", recording)

    upload_letter(server, entry["id"])
    assert lock.times == 1

    post(server, REMOVE, {"id": entry["id"]})
    assert lock.times == 2
    assert checked_under_lock == [True, True]  # a dispatch cannot come between the check and the file


def test_the_form_help_of_the_ai_does_not_follow_a_draft_that_no_longer_counts(server, monkeypatch):  # noqa: F811
    entry = new_entry(server)
    daten = server.kontext.daten
    source = unterlagen.letter_source(daten, entry["id"])
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("text: Was im alten Entwurf steht\n", encoding="utf-8")
    seen = []
    monkeypatch.setattr(routes_ai, "ai_gateway", lambda k, e, letter: (seen.append(letter), {}))
    monkeypatch.setattr(routes_ai.form_help, "assist", lambda gateway, material, e, ad, letter, fields: seen.append(letter) or {})

    routes_ai.form_fields(server.kontext, Register(daten).hole(entry["id"]), [])
    assert "alten Entwurf" in seen[-1]

    upload_letter(server, entry["id"])
    seen.clear()
    routes_ai.form_fields(server.kontext, Register(daten).hole(entry["id"]), [])

    assert seen == [None, ""]


def test_a_sent_application_is_not_built_again(server):  # noqa: F811
    entry = new_entry(server)
    daten = server.kontext.daten
    upload(server, "lebenslauf", "cv.pdf")
    send(server, entry["id"])
    unterlagen.letter_source(daten, entry["id"]).parent.mkdir(parents=True, exist_ok=True)
    unterlagen.letter_source(daten, entry["id"]).write_text("anrede: Guten Tag\n", encoding="utf-8")

    code, answer = post(server, "/api/unterlagen", {}, id=entry["id"])

    assert code == 400 and "versendet" in answer["fehler"]
    assert details(server, entry["id"])["pdfs"]["anschreiben"] is False


def test_bringing_it_back_after_sending_changes_nothing(server):  # noqa: F811
    entry = new_entry(server)
    upload(server, "lebenslauf", "cv.pdf")
    upload_letter(server, entry["id"], PDF + b"alt")
    upload_letter(server, entry["id"], PDF + b"gesendet")
    send(server, entry["id"])
    path = unterlagen.own_letter_path(server.kontext.daten, entry["id"])
    old = next(e for e in server.kontext.ablage.liste(path) if server.kontext.ablage.inhalt(e.id) == PDF + b"alt")

    assert post(server, "/api/entwurf/wiederherstellen", {"id": old.id})[0] == 200

    assert get(server, "/api/pdf", id=entry["id"], art="anschreiben")[2] == PDF + b"gesendet"


def test_the_list_of_drafts_names_it_as_a_letter():
    assert inhalte.titel(f"bewerbungen/muster-ag/{unterlagen.OWN_LETTER}") == "Eigenes Anschreiben muster-ag"
    assert inhalte.titel("bewerbungen/muster-ag/stelle.md") == "Stellenausschreibung muster-ag"


@pytest.mark.parametrize("route", ["/api/ki/anschreiben", "/api/ki/pruefen"])
def test_the_ai_stays_away_from_it(server, monkeypatch, route):  # noqa: F811
    def no_client():
        raise AssertionError("no call to the AI")

    monkeypatch.setattr(routes_ai, "new_client", no_client)
    entry = new_entry(server)
    daten = server.kontext.daten
    upload_letter(server, entry["id"])
    source = unterlagen.letter_source(daten, entry["id"])
    source.write_text("anrede: Guten Tag\n", encoding="utf-8")

    code, answer = post(server, route, {}, id=entry["id"])

    assert code == 400 and "eigene Anschreiben" in answer["fehler"]
    assert source.read_text(encoding="utf-8") == "anrede: Guten Tag\n"


def test_the_page_offers_it(server):  # noqa: F811
    entry = new_entry(server)

    page = get(server, "/bewerbung", id=entry["id"])[2].decode()

    assert 'id="eigenes-anschreiben"' in page and "/eigenes-anschreiben.js" in page
    assert get(server, "/eigenes-anschreiben.js")[0] == 200
