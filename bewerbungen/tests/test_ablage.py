"""Tests für die Ablage der Entwürfe: automatisch beim Speichern, löschbar solange ungenutzt (MIN-303)."""
import pytest

from ablage import Ablage


@pytest.fixture
def daten(tmp_path):
    ordner = tmp_path / "daten"
    ordner.mkdir()
    (ordner / "cv.yaml").write_text("name: Erika\n", encoding="utf-8")
    return ordner


@pytest.fixture
def ablage(daten):
    return Ablage(daten)


def schreibe(pfad, text):
    pfad.write_text(text, encoding="utf-8")


def test_speichern_legt_entwurf_an(ablage, daten):
    entwurf = ablage.speichere(daten / "cv.yaml", "Ausgangsstand")

    assert entwurf.datei == "cv.yaml"
    assert entwurf.beschreibung == "Ausgangsstand"
    assert not entwurf.genutzt
    assert ablage.inhalt(entwurf.id) == b"name: Erika\n"


def test_gleicher_inhalt_ergibt_keinen_neuen_entwurf(ablage, daten):
    ablage.speichere(daten / "cv.yaml", "eins")

    assert ablage.speichere(daten / "cv.yaml", "zwei") is None
    assert len(ablage.liste()) == 1


def test_jeder_inhalt_liegt_nur_einmal(ablage, daten):
    schreibe(daten / "a.yaml", "gleich\n")
    schreibe(daten / "b.yaml", "gleich\n")

    ablage.speichere(daten / "a.yaml", "a")
    ablage.speichere(daten / "b.yaml", "b")

    assert len(list((daten / ".entwuerfe" / "objekte").iterdir())) == 1


def test_liste_neueste_zuerst_und_nach_datei(ablage, daten):
    ablage.speichere(daten / "cv.yaml", "eins")
    schreibe(daten / "cv.yaml", "name: Erika B.\n")
    ablage.speichere(daten / "cv.yaml", "zwei")
    schreibe(daten / "brief.yaml", "text: Hallo\n")
    ablage.speichere(daten / "brief.yaml", "Brief")

    assert [e.beschreibung for e in ablage.liste(daten / "cv.yaml")] == ["zwei", "eins"]
    assert len(ablage.liste()) == 3


def test_datei_ausserhalb_des_datenordners(ablage, tmp_path):
    fremd = tmp_path / "fremd.yaml"
    schreibe(fremd, "x\n")

    with pytest.raises(ValueError, match="Datenordner"):
        ablage.speichere(fremd, "nein")


def test_wiederherstellen(ablage, daten):
    alt = ablage.speichere(daten / "cv.yaml", "alt")
    schreibe(daten / "cv.yaml", "name: Neu\n")
    ablage.speichere(daten / "cv.yaml", "neu")

    ablage.stelle_her(alt.id)

    assert (daten / "cv.yaml").read_text(encoding="utf-8") == "name: Erika\n"


def test_wiederherstellen_sichert_ungesicherten_stand(ablage, daten):
    alt = ablage.speichere(daten / "cv.yaml", "alt")
    schreibe(daten / "cv.yaml", "name: Von Hand geändert\n")

    ablage.stelle_her(alt.id)

    inhalte = [ablage.inhalt(e.id) for e in ablage.liste(daten / "cv.yaml")]
    assert "name: Von Hand geändert\n".encode() in inhalte


def test_loeschen(ablage, daten):
    eins = ablage.speichere(daten / "cv.yaml", "eins")
    schreibe(daten / "cv.yaml", "name: B\n")
    ablage.speichere(daten / "cv.yaml", "zwei")

    ablage.loesche(eins.id)

    assert [e.beschreibung for e in ablage.liste()] == ["zwei"]
    assert len(list((daten / ".entwuerfe" / "objekte").iterdir())) == 1


def test_genutzter_entwurf_ist_nicht_loeschbar(ablage, daten):
    entwurf = ablage.speichere(daten / "cv.yaml", "eins")

    ablage.markiere_genutzt([daten / "cv.yaml"], "Versand Beispiel AG")

    with pytest.raises(ValueError, match="genutzt"):
        ablage.loesche(entwurf.id)
    assert ablage.liste()[0].genutzt
    assert ablage.liste()[0].genutzt_fuer == ("Versand Beispiel AG",)


def test_markiere_genutzt_legt_fehlenden_entwurf_an(ablage, daten):
    ablage.markiere_genutzt([daten / "cv.yaml"], "Versand")

    assert ablage.liste()[0].genutzt


def test_unbekannter_entwurf(ablage):
    with pytest.raises(KeyError):
        ablage.loesche("gibt-es-nicht")


def test_vergleich(ablage, daten):
    eins = ablage.speichere(daten / "cv.yaml", "eins")
    schreibe(daten / "cv.yaml", "name: Erika B.\n")
    zwei = ablage.speichere(daten / "cv.yaml", "zwei")

    diff = ablage.vergleiche(eins.id, zwei.id)

    assert "-name: Erika\n" in diff
    assert "+name: Erika B.\n" in diff


def test_vergleich_binaer(ablage, daten):
    (daten / "a.pdf").write_bytes(b"%PDF\x00\x01")
    eins = ablage.speichere(daten / "a.pdf", "eins")
    (daten / "a.pdf").write_bytes(b"%PDF\x00\x02")
    zwei = ablage.speichere(daten / "a.pdf", "zwei")

    assert "binär" in ablage.vergleiche(eins.id, zwei.id)


def test_index_ueberlebt_neue_instanz(ablage, daten):
    ablage.speichere(daten / "cv.yaml", "eins")

    assert len(Ablage(daten).liste()) == 1


def test_gitignore_wird_ergaenzt(daten):
    (daten / ".gitignore").write_text(".build/\n", encoding="utf-8")

    Ablage(daten).sichere_gitignore()
    Ablage(daten).sichere_gitignore()

    zeilen = (daten / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert zeilen.count(".entwuerfe/") == 1
    assert ".build/" in zeilen
