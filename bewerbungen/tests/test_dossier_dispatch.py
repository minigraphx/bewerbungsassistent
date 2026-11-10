"""The dossier in the checks and the dispatch (G40): read by the checks, sent where one PDF goes, recorded when sent."""
import base64
import datetime

import typst

import apply
import merged_pdf
import pruefung
import unterlagen
import versand
from register import Register
from test_app import get, post, server  # noqa: F401  (server is a fixture)
from test_apply import ready
from test_merged_pdf import choose_certificate, keys_of, pages_of, part_of, pdf_with_pages

TODAY = datetime.date(2026, 11, 10)
FILLER = "Erfundene Beispieltexte für eine Prüfung, die genug Text braucht, um ihn als lesbar zu zählen. " * 4


def text_pdf(tmp_path, pages: int, text: str = FILLER) -> bytes:
    """A PDF with real text on each page, so the checks can read it."""
    source = tmp_path / f"seiten-{pages}-{abs(hash(text))}.typ"
    source.write_text("\n#pagebreak()\n".join([f"#[{text}]"] * pages), encoding="utf-8")
    return typst.compile(str(source))


def entry_with(s, tmp_path, choice=None, dossier_pages=5, dossier_text=FILLER):
    """An application with CV, letter and a dossier.pdf in its folder; `choice` is what the person chose."""
    entry = ready(s, **({"unterlagen": choice} if choice else {}))
    folder = unterlagen.bewerbungsordner(s.kontext.daten, entry["id"])
    (folder / "lebenslauf.pdf").write_bytes(text_pdf(tmp_path, 2))
    (folder / "anschreiben.pdf").write_bytes(text_pdf(tmp_path, 1))
    if dossier_pages:
        (folder / "dossier.pdf").write_bytes(text_pdf(tmp_path, dossier_pages, dossier_text))
    return entry


def findings(s, entry):
    return [f.text for f in pruefung.pruefe(s.kontext.daten, Register(s.kontext.daten).hole(entry["id"]), TODAY)]


def dispatch(s, entry, from_form=False):
    k = s.kontext
    return versand.erfasse_versand(k.daten, entry["id"], TODAY, k.versionierung, from_form=from_form)


# Checks


def test_the_checks_read_the_chosen_dossier(server, tmp_path):
    entry = entry_with(server, tmp_path, "dossier")

    texts = findings(server, entry)

    assert "Dossier: Text extrahierbar (5 Seiten)" in texts
    assert "Lebenslauf: Text extrahierbar (2 Seiten)" in texts and "Anschreiben: Text extrahierbar (1 Seite)" in texts


def test_a_placeholder_in_the_dossier_is_an_error(server, tmp_path):
    entry = entry_with(server, tmp_path, "dossier", dossier_text=FILLER + " TODO")

    found = pruefung.pruefe(server.kontext.daten, Register(server.kontext.daten).hole(entry["id"]), TODAY)

    assert pruefung.Befund("fehler", "Dossier: Platzhalter gefunden (TODO)") in found


def test_a_chosen_dossier_that_is_not_built_yet_is_an_error(server, tmp_path):
    entry = entry_with(server, tmp_path, "dossier", dossier_pages=0)

    found = pruefung.pruefe(server.kontext.daten, Register(server.kontext.daten).hole(entry["id"]), TODAY)

    assert any(f.stufe == "fehler" and f.text.startswith("Dossier: PDF fehlt") for f in found)


def test_with_the_preset_the_checks_leave_the_dossier_alone(server, tmp_path):
    entry = entry_with(server, tmp_path)  # a dossier.pdf from an earlier choice lies in the folder

    assert not any(text.startswith("Dossier") for text in findings(server, entry))


# One PDF for a form


def test_a_form_with_one_field_gets_the_dossier(server, tmp_path):
    entry = entry_with(server, tmp_path, "dossier")

    keys = keys_of(server, entry)
    status, part = part_of(server, entry, merged_pdf.ALL)

    assert keys[merged_pdf.ALL].startswith("Dossier")
    assert status == 200 and pages_of(base64.b64decode(part["daten"])) == 5
    assert {"lebenslauf", "anschreiben"} <= set(keys), "portals with separate uploads still get both files"


def test_with_proofs_the_one_pdf_is_the_dossier_and_the_proofs(server, tmp_path):
    entry = entry_with(server, tmp_path, "dossier")
    choose_certificate(server, entry, "Kurs.pdf", pdf_with_pages(4))

    paths = merged_pdf.sources(server.kontext.daten, Register(server.kontext.daten).hole(entry["id"]))[merged_pdf.ALL]
    status, part = part_of(server, entry, merged_pdf.ALL)

    assert [p.name for p in paths] == ["dossier.pdf", "Kurs.pdf"]
    assert status == 200 and pages_of(base64.b64decode(part["daten"])) == 5 + 4


def test_with_the_preset_one_pdf_joins_letter_and_cv_as_before(server, tmp_path):
    entry = entry_with(server, tmp_path)

    paths = merged_pdf.sources(server.kontext.daten, Register(server.kontext.daten).hole(entry["id"]))[merged_pdf.ALL]

    assert [p.name for p in paths] == ["anschreiben.pdf", "lebenslauf.pdf"]
    assert keys_of(server, entry)[merged_pdf.ALL].startswith("Unterlagen")


def test_the_folder_for_uploading_by_hand_holds_the_dossier(server, tmp_path):
    entry = entry_with(server, tmp_path, "dossier")
    data = server.kontext.daten

    folder = apply.prepare_folder(data, Register(data).hole(entry["id"]))

    dossier = [name for name in folder.names if name.startswith("Dossier")]
    assert len(dossier) == 1 and pages_of((folder.path / dossier[0]).read_bytes()) == 5


# Dispatch


def test_the_dispatch_records_the_dossier_with_the_two_files(server, tmp_path):
    entry = entry_with(server, tmp_path, "dossier")

    sent = dispatch(server, entry)["bewerbung"]["versand"]["dateien"]

    assert set(sent) == {"lebenslauf", "anschreiben", "dossier"}
    assert pages_of((server.kontext.daten / sent["dossier"]).read_bytes()) == 5


def test_after_the_dispatch_the_sent_dossier_counts(server, tmp_path):
    entry = entry_with(server, tmp_path, "dossier")
    dispatch(server, entry)
    built = unterlagen.dossier_path(server.kontext.daten, entry["id"])
    built.write_bytes(text_pdf(tmp_path, 7))  # changed afterwards, never sent

    code, _, body = get(server, "/api/pdf", id=entry["id"], art="dossier")

    assert code == 200 and pages_of(body) == 5
    assert "Dossier: Text extrahierbar (5 Seiten)" in findings(server, entry)


def test_a_form_that_got_the_dossier_is_recorded_as_such(server, tmp_path):
    entry = entry_with(server, tmp_path, "dossier")
    part_of(server, entry, merged_pdf.ALL)

    sent = dispatch(server, entry, from_form=True)["bewerbung"]["versand"]["dateien"]

    assert pages_of((server.kontext.daten / sent[merged_pdf.ALL]).read_bytes()) == 5


def test_with_the_preset_the_dispatch_leaves_the_dossier_out(server, tmp_path):
    entry = entry_with(server, tmp_path)

    sent = dispatch(server, entry)["bewerbung"]["versand"]["dateien"]

    assert set(sent) == {"lebenslauf", "anschreiben"}
    assert get(server, "/api/pdf", id=entry["id"], art="dossier")[0] == 400
