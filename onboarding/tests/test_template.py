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


def test_file_for_sharing_never_talks_to_a_server():
    page = build_template.build()

    assert "createAppBackend()" not in page.replace('typeof createAppBackend === "function" ? createAppBackend()', "")
    assert "fetch(" not in page
    assert "data-app" not in page
    assert "__TOKEN__" not in page


def test_page_of_the_app_may_only_talk_to_the_app():
    page = build_template.build(app=True)
    policy = re.search(r'http-equiv="Content-Security-Policy" content="([^"]+)"', page).group(1)

    assert "connect-src 'self'" in policy
    assert "form-action 'none'" in policy
    assert "unsafe-inline" not in policy
    assert 'name="token" content="__TOKEN__"' in page
    assert not re.search(r"https?://(?!www\.w3\.org)", page.split("<script", 1)[0])


def test_form_definition_cannot_close_its_script_element():
    page = build_template.build()
    definition = page.split('id="form-definition">', 1)[1].split("</script>", 1)[0]

    assert '"format": "bewerbungsassistent-einstieg"' in definition


def test_only_the_page_of_the_app_can_send_documents_to_the_ai():
    shared = build_template.build()
    app_page = build_template.build(app=True)
    assert "vorbefuellen" not in shared and "connect-src 'none'" in shared and "fetch(" not in shared
    assert "/api/angaben/vorbefuellen" in app_page and "PREFILL_TEXT = " in app_page
