"""Self-test of the package: build a CV and a cover letter from the bundled example data (MIN-342).

Runs in the CI on the built package; exit code 0 means Typst, the fonts and the themes are in place.
The result also goes to selbsttest.txt next to the working folder, since a windowed app has no console.
"""
import pathlib
import tempfile
import traceback

import anschreiben
import build

RESULT_FILE = "selbsttest.txt"


def run(result_dir: pathlib.Path | None = None) -> int:
    target = result_dir or pathlib.Path.cwd()
    try:
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
