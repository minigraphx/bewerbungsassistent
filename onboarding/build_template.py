"""Assemble the onboarding template into one self-contained HTML file.

The sources in src/ (HTML skeleton, CSS, JS) and form.json are inlined, so the result works from a
link and as a downloaded file opened by double-click. The Content Security Policy allows only these
inline parts (by hash) and no network access at all, so the page cannot send data anywhere.

The same sources also give the page „Meine Angaben“ of the app (bewerbungen/seiten/angaben.html, MIN-366): with
appbackend.js, which keeps state and documents in the data folder, and network access only to the app itself.

  python build_template.py            # writes dist/einstieg.html and the page of the app
  python build_template.py --check    # fails if one of them is out of date
"""
import argparse
import base64
import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent
SRC = ROOT / "src"
OUTPUT = ROOT / "dist" / "einstieg.html"
OUTPUT_APP = ROOT.parent / "bewerbungen" / "seiten" / "angaben.html"
SCRIPTS = ["validate.js", "model.js", "steps.js", "dom.js", "documents.js", "zip.js", "uploadstore.js", "uploads.js", "app.js"]  # order matters: later files use earlier ones


TITLE = "Einstieg"
TITLE_APP = "Meine Angaben"
APP_SCRIPTS = ["appbackend.js", "prefill.js"]  # only in the app; loaded before app.js
PRIVACY = "Alles bleibt auf diesem Gerät. Die Seite verschickt nichts; am Schluss entsteht eine Datei zum Speichern."
HEAD_APP = '<meta name="token" content="__TOKEN__">\n<meta name="bewerbungsbegleiter" content="app">'
TOP_SHARED = f'<header class="top"><p class="brand">Bewerbungsbegleiter</p><p class="privacy">{PRIVACY}</p></header>'
# In the app the page shares the menu of the other pages (taken from the overview) and their scripts: app.js for the
# menu, the text set and the messages of the packaged app; texte.js for the words that follow the setup.
MENU_SOURCE = ROOT.parent / "bewerbungen" / "seiten" / "uebersicht.html"
APP_PAGE_SCRIPTS = '<script src="/texte.js"></script>\n<script src="/app.js"></script>\n'
# DM Sans comes from the app (bewerbungen/app.py FONT_FILES); the shared file loads nothing and uses the system font.
APP_FONTS = "".join(
    f'@font-face {{ font-family: "DM Sans"; src: url("/fonts/DMSans-{name}.ttf") format("truetype"); '
    f"font-weight: {weight}; font-style: {style}; font-display: swap; }}\n"
    for name, weight, style in (("400", 400, "normal"), ("400i", 400, "italic"), ("500", 500, "normal"), ("700", 700, "normal")))


def _sha256(text: str) -> str:
    return "'sha256-" + base64.b64encode(hashlib.sha256(text.encode("utf-8")).digest()).decode("ascii") + "'"


def app_menu() -> str:
    """The navigation of the app, the same on every page (bewerbungen/tests/test_app.py checks that)."""
    found = re.search(r'<nav class="app-nav".*?</nav>', MENU_SOURCE.read_text(encoding="utf-8"), re.S)
    if not found:
        raise ValueError(f"{MENU_SOURCE.name} has no navigation")
    return found.group(0)


def build(app: bool = False) -> str:
    style = (APP_FONTS if app else "") + (SRC / "style.css").read_text(encoding="utf-8")
    if app:
        style += (SRC / "appnav.css").read_text(encoding="utf-8")
    names = [*SCRIPTS[:-1], *APP_SCRIPTS, SCRIPTS[-1]] if app else SCRIPTS
    script = "\n".join((SRC / name).read_text(encoding="utf-8") for name in names)
    form = json.dumps(json.loads((ROOT / "form.json").read_text(encoding="utf-8")), ensure_ascii=False)
    form = form.replace("</", "<\\/")  # keep the JSON from closing its script element
    csp = "; ".join([
        "default-src 'none'",
        f"script-src 'self' {_sha256(script)}" if app else f"script-src {_sha256(script)}",
        f"style-src {_sha256(style)}",
        "font-src 'self'" if app else "font-src 'none'",
        "img-src 'none'",
        f"connect-src {chr(39)}self{chr(39)}" if app else "connect-src 'none'",
        "form-action 'none'",
        "base-uri 'none'",
    ])
    page = (SRC / "template.html").read_text(encoding="utf-8")
    parts = (("{{CSP}}", csp), ("{{STYLE}}", style), ("{{FORM}}", form), ("{{SCRIPT}}", script),
             ("{{HTML_ATTR}}", ' data-app="1"' if app else ""), ("{{HEAD}}", HEAD_APP if app else ""),
             ("{{TOP}}", app_menu() if app else TOP_SHARED), ("{{APP_SCRIPTS}}", APP_PAGE_SCRIPTS if app else ""),
             ("{{TITLE}}", TITLE_APP if app else TITLE), ("{{HEADING}}", TITLE_APP if app else TITLE))
    for placeholder, value in parts:
        if page.count(placeholder) != 1:
            raise ValueError(f"template.html must contain {placeholder} exactly once")
        page = page.replace(placeholder, value)
    return page


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Einstiegsvorlage als eine HTML-Datei bauen")
    ap.add_argument("--check", action="store_true", help="nur prüfen, ob dist/einstieg.html aktuell ist")
    args = ap.parse_args(argv)
    pages = {OUTPUT: build(), OUTPUT_APP: build(app=True)}
    if args.check:
        stale = [path.name for path, page in pages.items()
                 if not path.is_file() or path.read_text(encoding="utf-8") != page]
        if stale:
            print(f"{', '.join(stale)} nicht aktuell: python build_template.py", file=sys.stderr)
            return 1
        return 0
    for path, page in pages.items():
        path.parent.mkdir(exist_ok=True)
        path.write_text(page, encoding="utf-8")
        print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
