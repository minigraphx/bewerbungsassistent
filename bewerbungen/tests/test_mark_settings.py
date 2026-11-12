"""Mark and accent colour of the dossier, once per person (G18, docs/design/monogramm.md, option B).

The page saves every choice at once into cv.yaml, with drafts; a logo is checked on upload and never goes to the AI.
Invented data and logos drawn here.
"""
import base64
import datetime
import io
import json
import re

import pytest
import yaml
from PIL import Image

import dossier_data
import logo_file
import mark_settings
import pruefung
from ai.personal import secrets_from_cv
from ai.pseudonym import Pseudonymizer, Secret
from test_app import get, post, server  # noqa: F401  (server is a fixture)

SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 110"><rect width="110" height="110" rx="20" '
       'fill="#a35a2b"/><rect x="130" y="40" width="250" height="30" fill="#27333f"/></svg>')


def png(width: int, height: int, colour=(163, 90, 43, 255), background=(0, 0, 0, 0)) -> bytes:
    image = Image.new("RGBA", (width, height), background)
    image.paste(Image.new("RGBA", (width // 2, height // 2), colour), (width // 4, height // 4))
    out = io.BytesIO()
    image.save(out, "PNG")
    return out.getvalue()


def basics(s) -> dict:
    return yaml.safe_load((s.kontext.daten / "cv.yaml").read_text(encoding="utf-8"))["basics"]


def upload(s, data: bytes):
    return post(s, "/api/dossier/logo", {"daten": base64.b64encode(data).decode()})


def state(s) -> dict:
    return json.loads(get(s, "/api/dossier/zeichen")[2])


def test_without_a_choice_everything_fits_the_design(server):  # noqa: F811
    shown = state(server)
    assert (shown["zeichen"], shown["akzent"], shown["logo"], shown["logo_fehlt"]) == ("passend", "passend", None, False)
    assert shown["initialen_wirksam"]


def test_each_choice_is_saved_at_once_with_drafts(server):  # noqa: F811
    cv = server.kontext.daten / "cv.yaml"
    before = len(server.kontext.ablage.liste(cv))

    status, answer = post(server, "/api/dossier/zeichen", {"zeichen": "ring"})
    assert status == 200 and answer["meldung"].startswith("Zeichen gespeichert.")
    status, answer = post(server, "/api/dossier/zeichen", {"akzent": "#1d5c6b"})
    assert answer["meldung"].startswith("Akzentfarbe gespeichert.")
    post(server, "/api/dossier/zeichen", {"initialen": "EKB"})

    assert {k: basics(server).get(k) for k in ("x-zeichen", "x-akzent", "x-monogramm")} == {
        "x-zeichen": "ring", "x-akzent": "#1d5c6b", "x-monogramm": "EKB"}
    assert len(server.kontext.ablage.liste(cv)) >= before + 2
    assert "# " in cv.read_text(encoding="utf-8")  # comments of cv.yaml stay


def test_a_colour_that_reads_badly_is_refused_with_a_darker_one(server):  # noqa: F811
    status, answer = post(server, "/api/dossier/zeichen", {"akzent": "#e0b84a"})
    assert status == 400 and "Vorschlag #927119" in answer["fehler"]
    assert "x-akzent" not in basics(server)
    assert post(server, "/api/dossier/zeichen", {"akzent": "rot"})[0] == 400


def test_interlaced_needs_two_letters_and_initials_are_letters(server):  # noqa: F811
    post(server, "/api/dossier/zeichen", {"initialen": "EKB"})
    status, answer = post(server, "/api/dossier/zeichen", {"zeichen": "verschraenkt"})
    assert status == 400 and answer["fehler"] == "Nur mit zwei Buchstaben"
    assert post(server, "/api/dossier/zeichen", {"initialen": "EB", "zeichen": "verschraenkt"})[0] == 200
    assert post(server, "/api/dossier/zeichen", {"initialen": "E1"})[0] == 400
    assert post(server, "/api/dossier/zeichen", {"initialen": ""})[0] == 200
    assert "x-monogramm" not in basics(server)


def test_the_logo_needs_an_upload_first(server):  # noqa: F811
    status, answer = post(server, "/api/dossier/zeichen", {"zeichen": "logo"})
    assert status == 400 and answer["fehler"] == "Zuerst ein Logo wählen."


def test_an_uploaded_logo_becomes_the_mark_and_offers_its_colour(server):  # noqa: F811
    status, answer = upload(server, png(1200, 330))

    assert status == 200 and answer["meldung"].startswith("Logo gespeichert.")
    assert answer["zeichen"] == "logo" and answer["logo"]["breite"] == 1200
    assert answer["logo"]["durchsichtig"] is True
    found = answer["logo"]["farbe"]
    assert all(abs(int(found[i:i + 2], 16) - int("a35a2b"[i - 1:i + 1], 16)) <= 3 for i in (1, 3, 5)), found
    assert basics(server)["x-logo"].startswith("logos/logo-")
    assert answer["akzent"] == "passend"  # „Aus dem Logo“ is offered, never chosen by itself
    typ, data = get(server, "/api/dossier/logo")[1:]
    assert typ == "image/png" and data.startswith(b"\x89PNG")


def test_an_svg_logo_is_kept_as_it_is(server):  # noqa: F811
    status, answer = upload(server, SVG.encode())
    assert status == 200 and answer["logo"]["vektor"] is True
    assert (server.kontext.daten / basics(server)["x-logo"]).read_text(encoding="utf-8") == SVG


SVG11 = '<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">'


@pytest.mark.parametrize("start", ["", '<?xml version="1.0" encoding="UTF-8"?>\n'])
def test_an_svg_logo_with_a_plain_doctype_is_stored_without_it(server, start):  # noqa: F811
    """Older editor exports carry the SVG 1.1 DOCTYPE; the stored logo never does (#243)."""
    status, answer = upload(server, (start + SVG11 + "\n" + SVG).encode())
    assert status == 200 and answer["logo"]["vektor"] is True
    assert (server.kontext.daten / basics(server)["x-logo"]).read_text(encoding="utf-8") == start + "\n" + SVG


@pytest.mark.parametrize(("data", "reason"), [
    ((SVG11[:-1] + ' [<!ENTITY x "y">]>' + SVG).encode(), "nicht sicher prüfen"),
    (b'<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "https://example.com/svg11.dtd">' + SVG.encode(), "nicht sicher prüfen"),
    (b"GIF89a....", "kein Bild in PNG, JPG oder SVG"),
    (b'<svg xmlns="http://www.w3.org/2000/svg"><image href="https://example.com/a.png"/></svg>', "lädt Inhalte aus dem Internet"),
    (b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>', "enthält ein Skript"),
    (b"\x89PNG\r\n\x1a\n" + b"0" * (logo_file.MAX_BYTES + 1), "grösser als 5 MB"),
])
def test_a_logo_of_another_kind_or_too_large_is_refused(server, data, reason):  # noqa: F811
    status, answer = upload(server, data)
    assert status == 400 and reason in answer["fehler"]
    assert "x-logo" not in basics(server)


def test_hints_for_a_small_wide_or_white_logo(tmp_path):
    hints = logo_file.inspect("png", png(300, 60), tmp_path)["hinweise"]
    assert any(h.startswith("Sehr breit") for h in hints)
    assert any("300 × 60 Pixel" in h for h in hints)
    high = logo_file.inspect("png", png(400, 900), tmp_path)["hinweise"]
    assert any(h.startswith("Sehr hoch") for h in high)
    white = logo_file.inspect("png", png(1200, 600, background=(255, 255, 255, 255)), tmp_path)
    assert white["durchsichtig"] is False and any(h.startswith("Das Logo hat einen weissen Hintergrund") for h in white["hinweise"])
    grey = logo_file.inspect("png", png(1200, 600, colour=(90, 90, 90, 255)), tmp_path)
    assert grey["farbe"] is None and grey["hinweise"] == []


def test_a_light_logo_colour_is_darkened_until_it_reads_well(tmp_path):
    found = logo_file.inspect("png", png(1200, 600, colour=(240, 192, 64, 255)), tmp_path)["farbe"]
    import mark
    assert found != "#f0c040" and mark.readable(found)


def test_removing_the_logo_and_resetting(server):  # noqa: F811
    upload(server, png(1200, 330))
    post(server, "/api/dossier/zeichen", {"akzent": "#5b3f6b"})

    status, answer = post(server, "/api/dossier/logo-entfernen", {})
    assert status == 200 and answer["zeichen"] == "passend" and answer["logo"] is None
    status, answer = post(server, "/api/dossier/zeichen-zuruecksetzen", {})
    assert answer["meldung"] == "Zeichen und Farbe stehen wieder auf «Passend zum Design»."
    assert not {"x-zeichen", "x-akzent", "x-logo"} & set(basics(server))


def test_a_missing_logo_shows_in_the_check_of_a_dossier(server):  # noqa: F811
    upload(server, png(1200, 330))
    (server.kontext.daten / basics(server)["x-logo"]).unlink()
    assert state(server)["logo_fehlt"] is True
    assert mark_settings.state_of_logo(server.kontext.daten) == "fehlt"
    entry = {"id": "muster-ag-test", "firma": "Muster AG", "unterlagen": "dossier"}
    found = [b.text for b in pruefung.pruefe(server.kontext.daten, entry, datetime.date(2026, 11, 11))]
    assert pruefung.LOGO_MISSING in found
    assert pruefung.LOGO_MISSING not in [b.text for b in pruefung.pruefe(
        server.kontext.daten, {**entry, "unterlagen": "einzeln"}, datetime.date(2026, 11, 11))]


# #248: initials that YAML 1.1 reads as yes, no or null stay text; PyYAML (safe_load) is YAML 1.1
YAML_11_WORDS = ("NO", "ON", "OFF", "Y", "N", "YES", "No", "on")


@pytest.mark.parametrize("initials", YAML_11_WORDS)
def test_initials_that_read_as_yes_or_no_are_saved_as_text(server, initials):  # noqa: F811
    status, _ = post(server, "/api/dossier/zeichen", {"initialen": initials})
    found = basics(server)

    assert status == 200 and found["x-monogramm"] == initials
    assert dossier_data.monogram(found) == initials
    assert Secret("MONOGRAM", initials, "initials") in secrets_from_cv({"basics": found})
    masked = Pseudonymizer(secrets_from_cv({"basics": found})).mask(
        (server.kontext.daten / "cv.yaml").read_text(encoding="utf-8"))
    assert re.search(r"x-monogramm: ([\"']?)\{\{MONOGRAM\}\}\1\n", masked)


def test_initials_written_unquoted_before_the_fix_still_show_and_get_quoted(server):  # noqa: F811
    cv = server.kontext.daten / "cv.yaml"
    cv.write_text(cv.read_text(encoding="utf-8").replace("basics:\n", "basics:\n  x-monogramm: NO\n", 1),
                  encoding="utf-8")

    assert state(server)["initialen"] == "NO"
    post(server, "/api/dossier/zeichen", {"zeichen": "ring"})
    assert basics(server)["x-monogramm"] == "NO"  # the next save writes them in quotes
