"""Assemble the onboarding template into one self-contained HTML file.

The sources in src/ (HTML skeleton, CSS, JS) and form.json are inlined, so the result works from a
link and as a downloaded file opened by double-click. The Content Security Policy allows only these
inline parts (by hash) and no network access at all, so the page cannot send data anywhere.

  python build_template.py            # writes dist/einstieg.html
  python build_template.py --check    # fails if dist/einstieg.html is out of date
"""
import argparse
import base64
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
SRC = ROOT / "src"
OUTPUT = ROOT / "dist" / "einstieg.html"
SCRIPTS = ["validate.js", "model.js", "dom.js", "documents.js", "zip.js", "uploads.js", "app.js"]  # order matters: later files use earlier ones


def _sha256(text: str) -> str:
    return "'sha256-" + base64.b64encode(hashlib.sha256(text.encode("utf-8")).digest()).decode("ascii") + "'"


def build() -> str:
    style = (SRC / "style.css").read_text(encoding="utf-8")
    script = "\n".join((SRC / name).read_text(encoding="utf-8") for name in SCRIPTS)
    form = json.dumps(json.loads((ROOT / "form.json").read_text(encoding="utf-8")), ensure_ascii=False)
    form = form.replace("</", "<\\/")  # keep the JSON from closing its script element
    csp = "; ".join([
        "default-src 'none'",
        f"script-src {_sha256(script)}",
        f"style-src {_sha256(style)}",
        "img-src 'none'",
        "connect-src 'none'",
        "form-action 'none'",
        "base-uri 'none'",
    ])
    page = (SRC / "template.html").read_text(encoding="utf-8")
    for placeholder, value in (("{{CSP}}", csp), ("{{STYLE}}", style), ("{{FORM}}", form), ("{{SCRIPT}}", script)):
        if page.count(placeholder) != 1:
            raise ValueError(f"template.html must contain {placeholder} exactly once")
        page = page.replace(placeholder, value)
    return page


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Einstiegsvorlage als eine HTML-Datei bauen")
    ap.add_argument("--check", action="store_true", help="nur prüfen, ob dist/einstieg.html aktuell ist")
    args = ap.parse_args(argv)
    page = build()
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != page:
            print("dist/einstieg.html ist nicht aktuell: python build_template.py", file=sys.stderr)
            return 1
        return 0
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(page, encoding="utf-8")
    print(OUTPUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
