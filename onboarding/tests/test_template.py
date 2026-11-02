"""The built template is current, self-contained and cannot send data anywhere."""
import re

import build_template


def test_built_file_is_current():
    assert build_template.main(["--check"]) == 0, "python build_template.py ausführen und dist/ committen"


def test_no_external_resources():
    page = build_template.build()

    assert not re.search(r"<script[^>]*\ssrc=", page)
    assert "<link" not in page
    assert "@import" not in page


def test_policy_blocks_network_and_allows_only_the_inline_parts():
    page = build_template.build()
    policy = re.search(r'http-equiv="Content-Security-Policy" content="([^"]+)"', page).group(1)

    assert "default-src 'none'" in policy
    assert "connect-src 'none'" in policy
    assert "form-action 'none'" in policy
    assert "unsafe-inline" not in policy
    assert len(re.findall(r"'sha256-", policy)) == 2


def test_form_definition_cannot_close_its_script_element():
    page = build_template.build()
    definition = page.split('id="form-definition">', 1)[1].split("</script>", 1)[0]

    assert '"format": "bewerbungsassistent-einstieg"' in definition
