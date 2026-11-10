"""„Lebenslauf anpassen“ where the CV is shown (#119): on the page of an application and under „Meine Dateien“."""
import pathlib
import re
import subprocess

from sample_folder import BRIEF_ID
from test_app import get, server  # noqa: F401  (server is a fixture)

TESTS = pathlib.Path(__file__).parent


def page(s, path, **parameter) -> str:
    status, _, content = get(s, path, **parameter)
    assert status == 200
    return content.decode("utf-8")


def test_the_application_page_has_the_button_and_the_note(server):
    html = page(server, "/bewerbung", id=BRIEF_ID)
    section = html[html.index('id="s-lebenslauf"'):html.index('id="s-anschreiben"')]

    assert re.search(r'<a [^>]*id="cv-anpassen"[^>]*>Lebenslauf anpassen</a>', section)
    assert 'id="cv-wie-es-ist"' in section and "so verwendet, wie es ist" in section
    assert html.index("/lebenslauf-anpassen.js") < html.index("/bewerbung.js")


def test_meine_dateien_has_the_button_and_the_note(server):
    html = page(server, "/dateien")

    assert re.search(r'<a [^>]*id="cv-anpassen"[^>]*>Lebenslauf anpassen</a>', html)
    assert 'id="cv-wie-es-ist" data-text="dateien.wie-es-ist"' in html
    assert html.index("/lebenslauf-anpassen.js") < html.index("/dateien.js")


def test_the_script_is_served(server):
    assert get(server, "/lebenslauf-anpassen.js")[0] == 200


def test_the_three_cases():
    result = subprocess.run(["node", "--test", "tests/lebenslauf_anpassen.test.cjs"], cwd=TESTS.parent,
                            capture_output=True, text=True, timeout=120)

    assert result.returncode == 0, result.stdout + result.stderr
