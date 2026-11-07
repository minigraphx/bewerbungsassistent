import pathlib
import re
import sys

import pytest
from urllib.parse import unquote

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import build  # noqa: E402

PRIVACY = "https://example.ch/datenschutz"
DOWNLOADS = "https://updates.example.ch/app/"


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    return build.build(tmp_path_factory.mktemp("site") / "out", PRIVACY, DOWNLOADS)


def read(site, name):
    return (site / name).read_text(encoding="utf-8")


def local_refs(text):
    refs = re.findall(r'(?:src|href)="([^"]+)"', text) + re.findall(r'url\("([^"]+)"\)', text)
    return [ref for ref in refs if not re.match(r"^[a-z]+:|^#", ref)]


def test_slug_matches_github_anchors():
    seen = {}
    assert build.slug("Schritt 4: KI", seen) == "schritt-4-ki"
    assert build.slug("Für Lehrstellen", seen) == "für-lehrstellen"
    assert build.slug("1. App herunterladen und starten", seen) == "1-app-herunterladen-und-starten"
    assert build.slug("Eigenes Claude-Abo (freiwillig)", seen) == "eigenes-claude-abo-freiwillig"
    assert build.slug("Für Lehrstellen", seen) == "für-lehrstellen-1"


def test_other_markdown_files_link_to_github():
    assert build.link_target("eigenes-abo.md") == f"{build.REPO_URL}/blob/main/docs/eigenes-abo.md"
    assert build.link_target("eigenes-abo.md#teil") == f"{build.REPO_URL}/blob/main/docs/eigenes-abo.md#teil"
    assert build.link_target("https://example.ch/a.md") == "https://example.ch/a.md"
    assert build.link_target("#schritt-4-ki") == "#schritt-4-ki"


@pytest.mark.parametrize("url", [None, "", "http://example.ch/datenschutz", "datenschutz.html", "https://"])
def test_privacy_url_must_be_https(url):
    with pytest.raises(build.BuildError):
        build.check_privacy_url(url)


def test_fill_refuses_a_missing_value():
    with pytest.raises(build.BuildError, match="version"):
        build.fill("Version {{version}}", {})


def test_fill_does_not_expand_placeholders_inside_values():
    assert build.fill("<main>{{inhalt}}</main>", {"inhalt": "{{x}}"}) == "<main>{{x}}</main>"


def test_pages_carry_version_and_privacy_link(site):
    index = read(site, "index.html")
    assert f"Aktuelle Version {build.read_version()}." in index
    for name in ("index.html", "anleitung.html"):
        text = read(site, name)
        assert f'href="{PRIVACY}"' in text
        assert "{{" not in text
        assert "/_blob/" not in text


def test_privacy_url_is_escaped(tmp_path):
    site = build.build(tmp_path / "out", 'https://example.ch/"><script>', DOWNLOADS)
    assert "<script>" not in read(site, "index.html")


def test_guide_buttons_point_to_the_guide_page(site):
    index = read(site, "index.html")
    assert index.count('href="anleitung.html"') >= 3
    assert "docs/installation.md" not in index


def test_guide_is_built_from_installation_md(site):
    guide = read(site, "anleitung.html")
    source = build.GUIDE.read_text(encoding="utf-8")
    assert "<h1>Installation und erste Schritte</h1>" in guide
    for heading in re.findall(r"^#{2,3} (.+)$", source, re.MULTILINE):
        assert f">{heading}</h" in guide.replace("&amp;", "&")


def test_every_anchor_in_the_guide_exists(site):
    guide = read(site, "anleitung.html")
    ids = set(re.findall(r'id="([^"]+)"', guide))
    # browsers percent-decode the fragment before matching it against ids
    anchors = [unquote(a) for a in re.findall(r'href="#([^"]+)"', guide)]
    assert anchors
    assert [a for a in anchors if a not in ids] == []


def test_every_local_reference_exists(site):
    missing = []
    for name in ("index.html", "anleitung.html", "stil.css"):
        for ref in local_refs(read(site, name)):
            path = ref.split("#")[0]
            if path in ("", "./"):
                continue
            if not (site / path).is_file():
                missing.append(f"{name}: {ref}")
    assert missing == []


def test_language_choice_stays_hidden(site):
    css = read(site, "stil.css")
    assert re.search(r"\.lang \{ display: none;", css)


def test_no_scripts_and_a_strict_policy(site):
    for name in ("index.html", "anleitung.html"):
        text = read(site, name)
        assert "<script" not in text
        assert "default-src 'none'" in text


def test_rebuild_removes_stale_files(tmp_path):
    out = tmp_path / "out"
    build.build(out, PRIVACY, DOWNLOADS)
    (out / "alt.html").write_text("alt", encoding="utf-8")
    build.build(out, PRIVACY, DOWNLOADS)
    assert not (out / "alt.html").exists()


def test_refuses_to_clear_a_foreign_folder(tmp_path):
    (tmp_path / "wichtig.txt").write_text("bleibt", encoding="utf-8")
    with pytest.raises(build.BuildError, match="nicht leer"):
        build.build(tmp_path, PRIVACY, DOWNLOADS)
    assert (tmp_path / "wichtig.txt").read_text(encoding="utf-8") == "bleibt"


def test_main_without_privacy_url_fails(monkeypatch, tmp_path, capsys):
    monkeypatch.delenv(build.PRIVACY_VARIABLE, raising=False)
    monkeypatch.setenv(build.DOWNLOADS_VARIABLE, DOWNLOADS)
    assert build.main(["--out", str(tmp_path / "out")]) == 1
    assert "Datenschutz" in capsys.readouterr().err
    assert not (tmp_path / "out").exists()


def test_main_without_downloads_url_fails(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv(build.PRIVACY_VARIABLE, PRIVACY)
    monkeypatch.delenv(build.DOWNLOADS_VARIABLE, raising=False)
    assert build.main(["--out", str(tmp_path / "out")]) == 1
    assert "Update-Server" in capsys.readouterr().err


def test_main_takes_the_addresses_from_the_environment(monkeypatch, tmp_path):
    monkeypatch.setenv(build.PRIVACY_VARIABLE, PRIVACY)
    monkeypatch.setenv(build.DOWNLOADS_VARIABLE, DOWNLOADS)
    assert build.main(["--out", str(tmp_path / "out")]) == 0
    assert (tmp_path / "out" / "index.html").is_file()


def test_download_buttons_point_to_this_version_on_the_update_server(site):
    index = read(site, "index.html")
    version = build.read_version()
    assert f'href="https://updates.example.ch/app/{version}/Bewerbungsbegleiter-Setup-{version}.exe"' in index
    assert f'href="https://updates.example.ch/app/{version}/Bewerbungsbegleiter-{version}-macOS.zip"' in index
    assert f'href="https://updates.example.ch/app/{version}/Bewerbungsbegleiter-{version}-x86_64.AppImage"' in index
    assert "releases/latest" not in index


def test_linux_is_offered_next_to_windows_and_macos(site):
    index = read(site, "index.html")
    assert "Für Linux laden" in index and "Noch nicht bereit</button>" not in index.split("Linux</div>")[1].split("download__title")[0]
    assert index.count("Für Windows, macOS und Linux") == 2  # description and the note under the title


def test_package_names_match_what_the_rollout_uploads():
    workflow = (build.REPO / ".github" / "workflows" / "update-ausrollen.yml").read_text(encoding="utf-8")
    checked = next(line for line in workflow.splitlines() if line.strip().startswith("for name in"))
    for url in build.download_links("https://x.example", "$version").values():
        name = url.rsplit("/", 1)[1]
        assert f'"pakete/{name}"' in workflow and f'"{name}"' in checked


def test_downloads_url_must_be_https():
    with pytest.raises(build.BuildError, match="Update-Server"):
        build.download_links("http://updates.example.ch", "1.0.0")


def test_both_browser_extensions_link_to_their_store(site):
    index = read(site, "index.html")
    assert 'href="https://microsoftedge.microsoft.com/addons/detail/mcbcijjbklfeffbollnemgkgnabnmfmp"' in index
    assert 'href="https://chromewebstore.google.com/detail/nopiegcdnjpkekgfakgglegkeifpmopo"' in index
    chrome = index.split("Browser-Erweiterung für Chrome</div>")[1].split("download__title")[0]
    assert "Verfügbar" in chrome and "disabled" not in chrome


def test_the_site_writes_datenschutzerklaerung_as_one_word(site):
    for name in ("index.html", "anleitung.html"):
        assert "Datenschutz-Erklärung" not in read(site, name)
    assert "Datenschutzerklärung" in read(site, "anleitung.html")
