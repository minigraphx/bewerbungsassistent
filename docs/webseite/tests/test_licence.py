"""The project is licensed under AGPL-3.0, and no file names another licence for it (#132)."""
import hashlib
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[3]
THIS_FILE = pathlib.Path(__file__).resolve().relative_to(ROOT).as_posix()

# SHA-256 of https://www.gnu.org/licenses/agpl-3.0.txt; LICENSE must hold that text unchanged.
AGPL_SHA256 = "0d96a4ff68ad6d4b6f1f30f713b18d5184912ba8dd389f86aa7710db079abcb0"

# LICENSE refers to the plain GNU GPL in its own section 13; third-party licences keep their own text.
EXEMPT_PREFIXES = ("LICENSE", "lebenslauf/fonts/", THIS_FILE)

# "GPL" not preceded by a letter, so "AGPL" passes; plus the plain licence's full English name.
FOREIGN_LICENCE = re.compile(r"(?<![A-Za-z])GPL|GNU General Public Licen[cs]e", re.IGNORECASE)


def tracked_text_files():
    names = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True
    ).stdout.decode("utf-8").split("\0")
    for name in filter(None, names):
        if name.startswith(EXEMPT_PREFIXES):
            continue
        path = ROOT / name
        if not path.is_file():
            continue
        try:
            yield name, path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue


def test_licence_file_is_the_unchanged_agpl_text():
    data = (ROOT / "LICENSE").read_bytes()
    assert data.startswith(b"                    GNU AFFERO GENERAL PUBLIC LICENSE\n")
    assert hashlib.sha256(data).hexdigest() == AGPL_SHA256


def test_notice_names_agpl_and_keeps_the_logo_exception():
    notice = (ROOT / "docs" / "NOTICE").read_text(encoding="utf-8")
    assert "GNU Affero General Public License" in notice
    assert "section 7(b)" in notice
    assert "as-logo.svg" in notice
    assert "All rights in the logo are reserved" in notice


def test_no_file_names_another_licence_for_the_project():
    hits = [
        f"{name}:{number}: ...{line[max(match.start() - 40, 0):match.end() + 40]}..."
        for name, text in tracked_text_files()
        for number, line in enumerate(text.splitlines(), start=1)
        for match in FOREIGN_LICENCE.finditer(line)
    ]
    assert not hits, "\n".join(hits)
