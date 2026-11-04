"""Self-test of the package: build a CV and a cover letter from the bundled example data (MIN-342).

Runs in the CI on the built package; exit code 0 means Typst, the fonts and the themes are in place, and the
modules loaded only on a real start (setup, dialogs, import of the einstieg file) are in the package.
The result also goes to selbsttest.txt next to the working folder, since a windowed app has no console.
"""
import importlib
import pathlib
import sys
import tempfile
import traceback

import anschreiben
import build

RESULT_FILE = "selbsttest.txt"
# Imported inside functions at runtime; importing them here by name checks that PyInstaller packed them.
LATE_MODULES = ("app", "routes_app", "routes_setup", "dialogs", "setup", "import_bundle", "routes_ai", "ai.gateway",
                "routes_search", "search_plan", "hits", "ai.invitation", "updates", "truststore")
EXTENSION_FILES = ("manifest.json", "background.js", "popup.html", "app-bridge.js", "portals/common.js",
                   "portals/jobroom.js", "lib/search.js", "lib/senders.js")


def check_modules() -> None:
    for name in LATE_MODULES:
        importlib.import_module(name)
    importlib.import_module("validation").load_form()  # form.json next to the modules


def check_extension(bundle: pathlib.Path) -> None:
    """The developer add-on is in the package, without its tests (MIN-339)."""
    folder = bundle / "erweiterung"
    missing = [name for name in EXTENSION_FILES if not (folder / name).is_file()]
    if missing or (folder / "tests").exists():
        raise RuntimeError(f"Erweiterung unvollständig: fehlt {missing}" if missing else "Tests der Erweiterung im Paket")


def run(result_dir: pathlib.Path | None = None) -> int:
    target = result_dir or pathlib.Path.cwd()
    try:
        check_modules()
        if getattr(sys, "frozen", False):
            check_extension(pathlib.Path(sys._MEIPASS))
        with tempfile.TemporaryDirectory() as folder:
            work = pathlib.Path(folder)
            cv = build.main([str(build.ROOT / "data" / "beispiel.yaml"), "--build-dir", str(work / "b1"),
                             "-o", str(work / "lebenslauf.pdf")])
            letter = anschreiben.main([str(build.ROOT / "data" / "anschreiben-beispiel.yaml"),
                                       "--build-dir", str(work / "b2"), "-o", str(work / "anschreiben.pdf")])
            sizes = [pathlib.Path(cv).stat().st_size, pathlib.Path(letter).stat().st_size]
        if min(sizes) < 1000:
            raise RuntimeError(f"PDF zu klein: {sizes}")
        (target / RESULT_FILE).write_text(f"ok {sizes}\n", encoding="utf-8")
        return 0
    except Exception:  # noqa: BLE001  (report everything, the CI shows the file)
        (target / RESULT_FILE).write_text(traceback.format_exc(), encoding="utf-8")
        return 1
