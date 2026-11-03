"""Import of the ZIP from the template: einstieg.json plus documents into dokumente/, pending for the einstieg skill."""
import copy
import datetime
import json
import zipfile

import pytest
import yaml

import import_bundle
import validation
from conftest import base_bundle

TODAY = datetime.date(2026, 11, 3)
BASICS = ["cv.yaml", "suchprofil.md", "anschreiben/stil.md", "anschreiben/bausteine.md"]
REFERENCE = "dokumente/zeugnisse/2023 Beispiel AG Arbeitszeugnis.pdf"
LETTER = "dokumente/anschreiben-bisher/Anschreiben Muster GmbH.docx"


def make_zip(tmp_path, bundle=None, files=None, name="einstieg.zip"):
    path = tmp_path / name
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        if bundle is not None:
            zf.writestr("einstieg.json", json.dumps(bundle, ensure_ascii=False))
        for entry, data in (files or {}).items():
            zf.writestr(entry, data)
    return path


def documents():
    return {REFERENCE: b"%PDF-1.4 Zeugnis", LETTER: b"PK docx Anschreiben"}


def pending(data_dir):
    return yaml.safe_load((data_dir / "dokumente" / "neu.yaml").read_text(encoding="utf-8"))


def test_complete_bundle_with_documents_writes_basics_and_documents(tmp_path):
    data_dir = tmp_path / "daten"

    result = import_bundle.import_file(data_dir, make_zip(tmp_path, base_bundle("job"), documents()), TODAY)

    assert result.written == BASICS
    assert sorted(result.documents) == sorted([REFERENCE, LETTER])
    assert result.incomplete is False
    assert (data_dir / REFERENCE).read_bytes() == b"%PDF-1.4 Zeugnis"
    assert {e["datei"] for e in pending(data_dir)} == {REFERENCE, LETTER}
    assert all(e["eingang"] == "2026-11-03" for e in pending(data_dir))
    assert "dokumente/" in (data_dir / ".gitignore").read_text(encoding="utf-8").splitlines()


def test_only_documents_and_missing_answers_keep_the_answers_for_the_skill(tmp_path):
    bundle = base_bundle("job")
    bundle["data"] = {"searchJob": bundle["data"]["searchJob"]}
    data_dir = tmp_path / "daten"

    result = import_bundle.import_file(data_dir, make_zip(tmp_path, bundle, documents()), TODAY)

    assert result.incomplete is True
    assert result.written == []
    assert not (data_dir / "cv.yaml").exists()
    assert json.loads((data_dir / "dokumente" / "einstieg.json").read_text(encoding="utf-8")) == bundle
    assert "dokumente/einstieg.json" in {e["datei"] for e in pending(data_dir)}


def test_wrong_answers_are_rejected_even_with_documents(tmp_path):
    bundle = base_bundle("job")
    bundle["data"]["person"]["email"] = "keine-adresse"

    with pytest.raises(import_bundle.ImportRejected, match="Format"):
        import_bundle.import_file(tmp_path / "daten", make_zip(tmp_path, bundle, documents()), TODAY)
    assert not (tmp_path / "daten").exists()


def test_missing_answers_without_documents_are_rejected(tmp_path):
    bundle = base_bundle("job")
    del bundle["data"]["person"]

    with pytest.raises(import_bundle.ImportRejected):
        import_bundle.import_file(tmp_path / "daten", make_zip(tmp_path, bundle, {}), TODAY)


@pytest.mark.parametrize("entry", [
    "../ausserhalb.pdf",
    "dokumente/zeugnisse/../../cv.yaml",
    "dokumente/zeugnisse/unter/ordner.pdf",
    "andere/datei.pdf",
    "/etc/passwd",
    "dokumente/zeugnisse/.versteckt.pdf",
])
def test_unexpected_entries_are_rejected_before_writing(tmp_path, entry):
    files = {**documents(), entry: b"x"}

    with pytest.raises(import_bundle.ImportRejected):
        import_bundle.import_file(tmp_path / "daten", make_zip(tmp_path, base_bundle("job"), files), TODAY)
    assert not (tmp_path / "daten").exists()


@pytest.mark.parametrize("entry, message", [
    ("dokumente/geheim/a.pdf", "Unbekannte Art"),
    ("dokumente/zeugnisse/programm.exe", "Dateityp"),
])
def test_document_rules_apply(tmp_path, entry, message):
    with pytest.raises(import_bundle.ImportRejected, match=message):
        import_bundle.import_file(tmp_path / "daten", make_zip(tmp_path, base_bundle("job"), {entry: b"x"}), TODAY)


def test_zip_without_bundle_is_rejected(tmp_path):
    with pytest.raises(import_bundle.ImportRejected, match="einstieg.json"):
        import_bundle.import_file(tmp_path / "daten", make_zip(tmp_path, None, documents()), TODAY)


def test_damaged_zip_is_rejected(tmp_path):
    path = tmp_path / "einstieg.zip"
    path.write_bytes(b"PK\x03\x04 kaputt")

    with pytest.raises(import_bundle.ImportRejected, match="ZIP"):
        import_bundle.import_file(tmp_path / "daten", path, TODAY)


def test_too_much_content_is_rejected_before_reading(tmp_path, monkeypatch):
    form = copy.deepcopy(validation.load_form())
    form["documents"]["maxTotalBytes"] = 10
    monkeypatch.setattr(validation, "load_form", lambda: form)

    with pytest.raises(import_bundle.ImportRejected, match="zu gross"):
        import_bundle.import_file(tmp_path / "daten", make_zip(tmp_path, base_bundle("job"), documents()), TODAY)


def test_same_document_again_is_not_duplicated_and_a_changed_one_gets_a_new_name(tmp_path):
    data_dir = tmp_path / "daten"
    import_bundle.import_file(data_dir, make_zip(tmp_path, base_bundle("job"), documents()), TODAY)
    changed = {REFERENCE: b"%PDF-1.4 neue Fassung", LETTER: documents()[LETTER]}

    result = import_bundle.import_file(data_dir, make_zip(tmp_path, base_bundle("job"), changed, "zwei.zip"),
                                       TODAY, force=True)

    assert result.documents == ["dokumente/zeugnisse/2023 Beispiel AG Arbeitszeugnis (2).pdf"]
    assert (data_dir / REFERENCE).read_bytes() == b"%PDF-1.4 Zeugnis"
    assert len(pending(data_dir)) == 3


def test_cli_names_the_next_step_for_documents(tmp_path, capsys):
    bundle = base_bundle("job")
    bundle["data"] = {}

    code = import_bundle.main([str(tmp_path / "daten"), str(make_zip(tmp_path, bundle, documents()))])

    out = capsys.readouterr().out
    assert code == 0
    assert "einstieg" in out and "dokumente/neu.yaml" in out
