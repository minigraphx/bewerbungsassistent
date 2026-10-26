"""Tests für das Einfrieren genutzter Versionen: Git, wenn vorhanden, sonst Ausweichlösung (MIN-303, MIN-304)."""
import subprocess

import pytest

import versionen


@pytest.fixture
def daten(tmp_path, monkeypatch):
    # Eigene Git-Umgebung ohne Nutzerkonfiguration: prüft den Ersatz-Autor
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.delenv("GIT_AUTHOR_NAME", raising=False)
    monkeypatch.delenv("GIT_COMMITTER_NAME", raising=False)
    ordner = tmp_path / "daten"
    ordner.mkdir()
    (ordner / "cv.yaml").write_text("name: Erika\n", encoding="utf-8")
    (ordner / "notiz.txt").write_text("privat\n", encoding="utf-8")
    return ordner


def git(ordner, *args):
    return subprocess.run(["git", "-C", str(ordner), *args], capture_output=True, text=True, check=True).stdout


def test_waehle_git(daten):
    assert isinstance(versionen.waehle(daten), versionen.GitVersionen)


def test_waehle_ohne_git(daten, monkeypatch):
    monkeypatch.setattr(versionen.shutil, "which", lambda _: None)

    v = versionen.waehle(daten)

    assert isinstance(v, versionen.OhneGit)
    assert "Git" in v.hinweis


def test_friere_ein_legt_repo_an_und_committet_nur_die_dateien(daten):
    commit = versionen.GitVersionen(daten).friere_ein([daten / "cv.yaml"], "Versand: Beispiel AG")

    assert commit
    assert git(daten, "log", "-1", "--format=%s").strip() == "Versand: Beispiel AG"
    assert git(daten, "ls-files").split() == ["cv.yaml"]


def test_ersatz_autor_ohne_git_konfiguration(daten):
    versionen.GitVersionen(daten).friere_ein([daten / "cv.yaml"], "Versand")

    assert git(daten, "log", "-1", "--format=%an").strip() == versionen.ERSATZ_AUTOR


def test_unveraendert_ergibt_keinen_commit(daten):
    v = versionen.GitVersionen(daten)
    v.friere_ein([daten / "cv.yaml"], "eins")

    assert v.friere_ein([daten / "cv.yaml"], "zwei") is None


def test_andere_geaenderte_dateien_bleiben_unberuehrt(daten):
    v = versionen.GitVersionen(daten)
    v.friere_ein([daten / "cv.yaml", daten / "notiz.txt"], "eins")
    (daten / "notiz.txt").write_text("geändert\n", encoding="utf-8")
    (daten / "cv.yaml").write_text("name: Erika B.\n", encoding="utf-8")

    v.friere_ein([daten / "cv.yaml"], "zwei")

    assert "notiz.txt" in git(daten, "status", "--porcelain")
    assert "cv.yaml" not in git(daten, "status", "--porcelain")


def test_datei_ausserhalb(daten, tmp_path):
    fremd = tmp_path / "fremd.txt"
    fremd.write_text("x", encoding="utf-8")

    with pytest.raises(ValueError, match="Datenordner"):
        versionen.GitVersionen(daten).friere_ein([fremd], "nein")


def test_verlauf_und_inhalt(daten):
    v = versionen.GitVersionen(daten)
    commit = v.friere_ein([daten / "cv.yaml"], "Versand: Beispiel AG")
    (daten / "cv.yaml").write_text("name: Neu\n", encoding="utf-8")

    verlauf = v.verlauf()

    assert verlauf[0]["commit"] == commit
    assert verlauf[0]["nachricht"] == "Versand: Beispiel AG"
    assert verlauf[0]["dateien"] == ["cv.yaml"]
    assert v.inhalt(commit, "cv.yaml") == b"name: Erika\n"


def test_ohne_git_friert_nicht_ein(daten):
    v = versionen.OhneGit(daten)

    assert v.friere_ein([daten / "cv.yaml"], "Versand") is None
    assert v.verlauf() == []
