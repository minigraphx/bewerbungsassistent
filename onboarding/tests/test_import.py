"""Import of an einstieg.json into a data folder: checks, drafts, no silent overwrite, a buildable CV."""
import datetime
import json

import pytest
import yaml
from pypdf import PdfReader

import build
import import_bundle
from conftest import base_bundle

TODAY = datetime.date(2026, 11, 2)
FILES = ["cv.yaml", "suchprofil.md", "anschreiben/stil.md", "anschreiben/bausteine.md"]


def write_bundle(tmp_path, bundle) -> str:
    path = tmp_path / "einstieg.json"
    path.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
    return path


def draft_index(data_dir) -> list[dict]:
    index = data_dir / ".entwuerfe" / "index.yaml"
    return yaml.safe_load(index.read_text(encoding="utf-8")) if index.is_file() else []


def test_writes_the_four_files(tmp_path):
    data_dir = tmp_path / "daten"

    result = import_bundle.import_file(data_dir, write_bundle(tmp_path, base_bundle("job")), TODAY)

    assert result.written == FILES
    assert result.documents == [] and result.incomplete is False
    assert all((data_dir / rel).is_file() for rel in FILES)
    assert {d["datei"] for d in draft_index(data_dir)} == set(FILES)


def test_refuses_to_overwrite_without_force(tmp_path):
    data_dir = tmp_path / "daten"
    data_dir.mkdir()
    (data_dir / "cv.yaml").write_text("basics: {name: Alt}\n", encoding="utf-8")

    with pytest.raises(import_bundle.ImportRejected) as rejected:
        import_bundle.import_file(data_dir, write_bundle(tmp_path, base_bundle("job")), TODAY)

    assert "cv.yaml" in str(rejected.value)
    assert (data_dir / "cv.yaml").read_text(encoding="utf-8") == "basics: {name: Alt}\n"
    assert not (data_dir / "suchprofil.md").exists()


def test_force_keeps_the_old_version_as_draft(tmp_path):
    data_dir = tmp_path / "daten"
    data_dir.mkdir()
    (data_dir / "cv.yaml").write_text("basics: {name: Alt}\n", encoding="utf-8")

    import_bundle.import_file(data_dir, write_bundle(tmp_path, base_bundle("job")), TODAY, force=True)

    drafts = [d for d in draft_index(data_dir) if d["datei"] == "cv.yaml"]
    assert len(drafts) == 2  # old state before, new state after
    assert "Erika Beispiel" in (data_dir / "cv.yaml").read_text(encoding="utf-8")


def test_invalid_bundle_lists_german_messages(tmp_path):
    bundle = base_bundle("job")
    bundle["data"]["person"]["email"] = "keine-adresse"
    del bundle["data"]["person"]["name"]

    with pytest.raises(import_bundle.ImportRejected) as rejected:
        import_bundle.import_file(tmp_path / "daten", write_bundle(tmp_path, bundle), TODAY)

    assert rejected.value.messages == [
        "Person und Kontakt, Vor- und Nachname: Bitte ausfüllen.",
        "Person und Kontakt, E-Mail: Ungültiges Format, zum Beispiel: vorname.nachname@example.ch.",
    ]
    assert not (tmp_path / "daten").exists()


@pytest.mark.parametrize("content, message", [
    (b"{not json", "keine gültige JSON-Datei"),
    (b"\xff\xfe", "keine gültige JSON-Datei"),
    (b"x" * (import_bundle.MAX_BYTES + 1), "zu gross"),
    (b"[" * 100_000, "keine gültige JSON-Datei"),
])
def test_unreadable_files(tmp_path, content, message):
    path = tmp_path / "einstieg.json"
    path.write_bytes(content)

    with pytest.raises(import_bundle.ImportRejected, match=message):
        import_bundle.import_file(tmp_path / "daten", path, TODAY)


def test_cli_reports_errors_without_traceback(tmp_path, capsys):
    path = tmp_path / "einstieg.json"
    path.write_text("{}", encoding="utf-8")

    code = import_bundle.main([str(tmp_path / "daten"), str(path)])

    assert code == 1
    assert "keine Einstiegsdatei" in capsys.readouterr().err


@pytest.mark.parametrize("track, heading", [("job", "BERUFSERFAHRUNG"), ("apprenticeship", "SCHNUPPERLEHREN & ERFAHRUNGEN")])
def test_imported_cv_builds_a_pdf(tmp_path, track, heading):
    data_dir = tmp_path / "daten"
    import_bundle.import_file(data_dir, write_bundle(tmp_path, base_bundle(track)), TODAY)
    out = tmp_path / "cv.pdf"

    build.main([str(data_dir / "cv.yaml"), "--build-dir", str(tmp_path / "build"), "-o", str(out)])

    text = "".join(page.extract_text() for page in PdfReader(out).pages)
    assert heading in text
    assert base_bundle(track)["data"]["person"]["name"].upper() in text.upper()


def test_lone_surrogate_is_rejected_before_writing(tmp_path):
    bundle = base_bundle("job")
    bundle["data"]["strengths"][0]["example"] = "Text \ud800 mit Fehler"
    path = tmp_path / "einstieg.json"
    path.write_text(json.dumps(bundle), encoding="utf-8")

    with pytest.raises(import_bundle.ImportRejected, match="ungültige Zeichen"):
        import_bundle.import_file(tmp_path / "daten", path, TODAY)

    assert not (tmp_path / "daten").exists()
