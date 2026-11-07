"""Build the static website of the app: the start page and the guide made from docs/installation.md.

The guide has one source: docs/installation.md, the same file GitHub shows. Images, the DM Sans fonts
and the logo come from the repo as well, so the site never drifts from the app.

  python build.py --datenschutz <url> --downloads <url>            # writes build/
  python build.py --datenschutz <url> --downloads <url> --out DIR

The privacy page lives on the hosting because it names the operator, and the packages lie on the
update server; both addresses are passed in, or taken from BEWERBUNGSBEGLEITER_DATENSCHUTZ_URL and
BEWERBUNGSBEGLEITER_UPDATE_URL like in the app's build. The download links follow the layout that
update-ausrollen.yml uploads: <update url>/<version>/<package>.
"""
import argparse
import html
import os
import pathlib
import re
import shutil
import sys
import unicodedata
from urllib.parse import urlparse

from markdown_it import MarkdownIt

ROOT = pathlib.Path(__file__).resolve().parent
REPO = ROOT.parent.parent
TEMPLATES = ROOT / "vorlagen"
GUIDE = REPO / "docs" / "installation.md"
IMAGES = REPO / "docs" / "bilder"
FONTS = REPO / "lebenslauf" / "fonts"
VERSION_FILE = REPO / "desktop" / "version.py"
LOGO = REPO / "bewerbungen" / "seiten" / "as-logo.svg"  # one file for app and website
FONT_FILES = ("DMSans-400.ttf", "DMSans-500.ttf", "DMSans-700.ttf")
START_IMAGES = ("uebersicht.jpg", "treffer.jpg", "bewerbung.jpg")
REPO_URL = "https://github.com/minigraphx/bewerbungsassistent"
PRIVACY_VARIABLE = "BEWERBUNGSBEGLEITER_DATENSCHUTZ_URL"
DOWNLOADS_VARIABLE = "BEWERBUNGSBEGLEITER_UPDATE_URL"
PLACEHOLDER = re.compile(r"\{\{(\w+)\}\}")
MARKER = ".webseite"  # marks a folder this script built, so a rebuild only ever clears its own output


class BuildError(Exception):
    """A build input is missing or invalid; the message says which."""


def read_version(path=VERSION_FILE):
    match = re.search(r'^VERSION = "([0-9][0-9.]*)"$', path.read_text(encoding="utf-8"), re.MULTILINE)
    if not match:
        raise BuildError(f"Keine Version in {path}")
    return match.group(1)


def check_https(url, what):
    parsed = urlparse(url or "")
    if parsed.scheme != "https" or not parsed.netloc:
        raise BuildError(f"Die Adresse {what} fehlt oder beginnt nicht mit https://")
    return url


def check_privacy_url(url):
    return check_https(url, "der Datenschutz-Seite")


def download_links(base, version):
    """Direct links to the packages of this version on the update server."""
    base = check_https(base, "des Update-Servers").rstrip("/")
    return {"download_windows": f"{base}/{version}/Bewerbungsbegleiter-Setup-{version}.exe",
            "download_macos": f"{base}/{version}/Bewerbungsbegleiter-{version}-macOS.zip",
            "download_linux": f"{base}/{version}/Bewerbungsbegleiter-{version}-x86_64.AppImage"}


def fill(template, values):
    """Replace every {{name}}; a placeholder without a value is an error, not an empty string."""
    missing = sorted({name for name in PLACEHOLDER.findall(template) if name not in values})
    if missing:
        raise BuildError(f"Werte fehlen für: {', '.join(missing)}")
    return PLACEHOLDER.sub(lambda m: values[m.group(1)], template)


def slug(text, seen):
    """Anchor like GitHub's, so links such as #schritt-4-ki work on both."""
    base = unicodedata.normalize("NFC", text).strip().lower()
    base = re.sub(r"[^\w\- ]", "", base).replace(" ", "-")
    count = seen.get(base, 0)
    seen[base] = count + 1
    return base if count == 0 else f"{base}-{count}"


def link_target(href):
    """Other Markdown files of the repo stay on GitHub; the site only carries the guide."""
    if re.match(r"^[a-z]+:|^#", href):
        return href
    path, _, anchor = href.partition("#")
    if path.endswith(".md"):
        return f"{REPO_URL}/blob/main/docs/{path}" + (f"#{anchor}" if anchor else "")
    return href


def make_renderer():
    md = MarkdownIt("commonmark", {"html": False}).enable("table")
    seen = {}

    def heading_open(renderer, tokens, idx, options, env):
        inline = tokens[idx + 1]
        tokens[idx].attrSet("id", slug(inline.content, seen))
        return renderer.renderToken(tokens, idx, options, env)

    def link_open(renderer, tokens, idx, options, env):
        tokens[idx].attrSet("href", link_target(tokens[idx].attrGet("href") or ""))
        return renderer.renderToken(tokens, idx, options, env)

    def image(renderer, tokens, idx, options, env):
        tokens[idx].attrSet("loading", "lazy")
        return renderer.image(tokens, idx, options, env)

    md.add_render_rule("heading_open", heading_open)
    md.add_render_rule("link_open", link_open)
    md.add_render_rule("image", image)
    return md


def render_guide(markdown_text):
    """Return (title, body html, image names) of the guide; the title is its first heading."""
    first, _, rest = markdown_text.partition("\n")
    if not first.startswith("# "):
        raise BuildError("docs/installation.md beginnt nicht mit einer Überschrift")
    body = make_renderer().render(rest)
    images = sorted(set(re.findall(r'src="bilder/([^"/]+)"', body)))
    return first[2:].strip(), body, images


def page(layout, title, content, values):
    return fill(layout, {**values, "titel": html.escape(title), "inhalt": content})


def copy_assets(out, images):
    for folder in ("bilder", "fonts"):
        (out / folder).mkdir(parents=True, exist_ok=True)
    for name in images:
        source = IMAGES / name
        if not source.is_file():
            raise BuildError(f"Bild fehlt: docs/bilder/{name}")
        shutil.copy2(source, out / "bilder" / name)
    for name in FONT_FILES:
        shutil.copy2(FONTS / name, out / "fonts" / name)
    shutil.copy2(LOGO, out / "bilder" / LOGO.name)
    shutil.copy2(ROOT / "stil.css", out / "stil.css")


def prepare_output(out):
    if out.exists() and any(out.iterdir()):
        if not (out / MARKER).is_file():
            raise BuildError(f"{out} ist nicht leer und stammt nicht von diesem Build")
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / MARKER).write_text("", encoding="utf-8")


def build(out, privacy_url, downloads_url):
    version = read_version()
    links = download_links(downloads_url, version)
    values = {
        "version": html.escape(version),
        "datenschutz": html.escape(check_privacy_url(privacy_url), quote=True),
        "quellcode": REPO_URL,
        **{name: html.escape(url, quote=True) for name, url in links.items()},
    }
    layout = (TEMPLATES / "rahmen.html").read_text(encoding="utf-8")
    start = fill((TEMPLATES / "start.html").read_text(encoding="utf-8"), values)
    title, guide, guide_images = render_guide(GUIDE.read_text(encoding="utf-8"))
    prepare_output(out)
    copy_assets(out, sorted(set(START_IMAGES) | set(guide_images)))
    (out / "index.html").write_text(page(layout, "Bewerbungsbegleiter", start, values), encoding="utf-8")
    guide_html = f'<article class="wrap prose">\n<h1>{html.escape(title)}</h1>\n{guide}</article>\n'
    (out / "anleitung.html").write_text(page(layout, f"{title} · Bewerbungsbegleiter", guide_html, values), encoding="utf-8")
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description="Baut die Webseite nach build/.")
    parser.add_argument("--datenschutz", default=os.environ.get(PRIVACY_VARIABLE), help="Adresse der Datenschutz-Seite (https://…)")
    parser.add_argument("--downloads", default=os.environ.get(DOWNLOADS_VARIABLE), help="Adresse des Update-Servers (https://…)")
    parser.add_argument("--out", type=pathlib.Path, default=ROOT / "build")
    args = parser.parse_args(argv)
    try:
        out = build(args.out, args.datenschutz, args.downloads)
    except BuildError as error:
        print(f"Webseite nicht gebaut: {error}", file=sys.stderr)
        return 1
    print(f"Webseite gebaut: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
