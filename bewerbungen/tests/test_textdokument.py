"""Tests für Markdown-Dateien als PDF (Stilprofil, Bausteine, Suchprofil, Stellentext)."""
import pypdf

import textdokument


def _text(pdf) -> str:
    return "".join(seite.extract_text() for seite in pypdf.PdfReader(pdf).pages)


def test_struktur_ueberschrift_absatz_und_auszeichnung():
    bloecke = textdokument.als_struktur("# Titel\n\nEin **fetter** und *kursiver* Text mit `code`.\n")

    assert bloecke[0] == {"t": "heading", "stufe": 1, "k": [{"t": "text", "text": "Titel"}]}
    absatz = bloecke[1]
    assert absatz["t"] == "paragraph"
    assert {"t": "strong", "k": [{"t": "text", "text": "fetter"}]} in absatz["k"]
    assert {"t": "em", "k": [{"t": "text", "text": "kursiver"}]} in absatz["k"]
    assert {"t": "code_inline", "text": "code"} in absatz["k"]


def test_struktur_listen():
    liste, nummeriert = textdokument.als_struktur("- a\n- b\n\n3. x\n")

    assert liste["t"] == "bullet_list" and len(liste["k"]) == 2
    assert nummeriert == {"t": "ordered_list", "start": 3,
                          "k": [{"t": "list_item", "k": [{"t": "text", "text": "x"}]}]}  # enge Liste: ohne Absatz


def test_struktur_tabelle():
    (tabelle,) = textdokument.als_struktur("| Portal | Modus |\n|---|---|\n| job-room | automatisch |\n| LinkedIn |\n")

    assert tabelle["t"] == "table"
    assert tabelle["spalten"] == 2
    assert tabelle["kopf"] == [[{"t": "text", "text": "Portal"}], [{"t": "text", "text": "Modus"}]]
    assert tabelle["zeilen"] == [[[{"t": "text", "text": "job-room"}], [{"t": "text", "text": "automatisch"}]],
                                 [[{"t": "text", "text": "LinkedIn"}], []]]


def test_html_bleibt_text():
    (absatz,) = textdokument.als_struktur("<script>x</script> und <b>fett</b>\n")

    assert all(teil["t"] in ("text", "softbreak") for teil in absatz["k"])
    assert "<b>fett</b>" in "".join(teil.get("text", "") for teil in absatz["k"])


def test_links_nur_web_und_mail():
    (absatz,) = textdokument.als_struktur("[a](https://x.ch) [b](mailto:a@b.ch) [c](file:///etc/passwd) [d](javascript:x)\n")
    links = [teil for teil in absatz["k"] if teil["t"] == "link"]

    assert [l["href"] for l in links] == ["https://x.ch", "mailto:a@b.ch"]  # Rest bleibt Text


def test_link_ohne_web_schema_ohne_ziel():
    (absatz,) = textdokument.als_struktur("[a](ftp://x.ch/datei)\n")

    assert absatz["k"][0] == {"t": "link", "href": None, "k": [{"t": "text", "text": "a"}]}


def test_bilder_werden_nicht_geladen():
    (absatz,) = textdokument.als_struktur("![Foto](../../geheim.jpg)\n")

    assert absatz["k"] == [{"t": "image", "k": [{"t": "text", "text": "Foto"}]}]


def test_baut_pdf_mit_typst_sonderzeichen(tmp_path):
    text = ("# Suchprofil\n\nKosten: 5 $ und #hashtag @mention <tag> = _x_ \\ \"zitat\"\n\n"
            "- Punkt eins\n  - verschachtelt\n\n> Zitat\n\n```\ncode # $\n```\n\n---\n\n"
            "| A | B |\n|---|---|\n| 1 | 2 |\n")

    pdf = textdokument.baue_pdf(text, "Suchprofil", tmp_path / "build", tmp_path / "aus" / "suchprofil.pdf")

    inhalt = _text(pdf)
    assert "#hashtag @mention <tag>" in inhalt
    assert "Punkt eins" in inhalt and "verschachtelt" in inhalt
    assert "code # $" in inhalt


def test_leerer_text_gibt_pdf(tmp_path):
    pdf = textdokument.baue_pdf("", "Leer", tmp_path / "build", tmp_path / "leer.pdf")

    assert pdf.read_bytes().startswith(b"%PDF")
