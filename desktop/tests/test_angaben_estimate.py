"""Cost and time before „Vorbefüllen“ (G85, #271): the app reads the pending files only on this computer, within the
limits of `read_documents.collect_texts`, and prices what would go to the AI the way „Alle prüfen“ does (G44): every
character at the full input price of the model, a fixed answer, rounded up to the cent and to the minute. With the
mediation the amounts are in CHF with the credit left (G46, G80), otherwise in USD. Invented files only; no AI client,
no network: the mediation's account is simulated.
"""
import inspect
import json
import pathlib
import urllib.parse
import urllib.request

import anthropic
import pytest
import yaml

import mcp_tools
import native_host
import prefill
import prefill_estimate
import rate_all
import read_documents
import routes_ai
import routes_angaben
import validation
from ai import connection, prompts, tasks, usage
from ai.connection import ACCESS_VARIABLE, KEY_VARIABLE, URL_VARIABLE
from import_documents import READ_MARK
from test_angaben import call, consent_given, started, upload  # noqa: F401  (fixtures)

ROUTE = routes_angaben.PREFILL_ESTIMATE_ROUTE
FORM = validation.load_form()
CV_TEXT = "Erika Beispiel\nEntwicklerin bei Muster GmbH, 2019 bis heute.\n" * 20
LONG_TEXT = "Zeugnis der Beispiel AG. " * 2_000  # longer than one document may be
PNG = b"\x89PNG\r\n\x1a\n erfunden"


@pytest.fixture(autouse=True)
def no_ai_set_up(monkeypatch):
    for name in (URL_VARIABLE, ACCESS_VARIABLE, KEY_VARIABLE):
        monkeypatch.delenv(name, raising=False)


def mediation(monkeypatch, spent: float, credit: float = 5.0) -> list:
    asked = []
    monkeypatch.setenv(URL_VARIABLE, "https://ki.example.ch")
    monkeypatch.setenv(ACCESS_VARIABLE, "bwa_test")

    def account(url, access):
        asked.append(url)
        return {"credit_chf": credit, "spent_chf": spent}

    monkeypatch.setattr(routes_ai.invitation, "account", account)
    return asked


def estimate(server, track="job") -> dict:
    query = urllib.parse.urlencode({"track": track, "t": server.token})
    with urllib.request.urlopen(f"{server.url.rstrip('/')}{ROUTE}?{query}", timeout=20) as response:
        assert response.status == 200
        return json.loads(response.read())


def three_files(server):
    upload(server, name="Lebenslauf_Erika_Beispiel.txt", data=CV_TEXT.encode())
    upload(server, name="Zeugnis_Scan.png", category="zeugnisse", data=PNG)
    upload(server, name="Zeugnis_lang.txt", category="zeugnisse", data=LONG_TEXT.encode())


def test_it_counts_the_files_for_the_ai_and_names_those_left_out_or_shortened(started):
    server, _, _ = started
    three_files(server)

    answer = estimate(server)

    assert answer["anzahl"] == 2
    assert answer["nicht_gelesen"] == [{"name": "Zeugnis_Scan.png", "grund": read_documents.IMAGE}]
    assert answer["gekuerzt"] == ["Zeugnis_lang.txt"]
    assert answer["kosten"] >= 0.01 and answer["dauer_minuten"] >= 1


def test_without_documents_nothing_goes_to_the_ai(started):
    server, _, _ = started

    answer = estimate(server)

    assert (answer["anzahl"], answer["kosten"], answer["nicht_gelesen"], answer["gekuerzt"]) == (0, 0, [], [])


def test_with_an_own_key_or_without_ai_the_amounts_are_in_usd_without_credit(started, monkeypatch):
    server, _, _ = started
    three_files(server)

    without_ai = estimate(server)
    monkeypatch.setenv(KEY_VARIABLE, "sk-test")
    own_key = estimate(server)

    for answer in (without_ai, own_key):
        assert answer["waehrung"] == "USD"
        assert answer["guthaben"] is None and answer["danach"] is None


def test_with_the_mediation_it_names_the_credit_now_and_afterwards_in_chf(started, monkeypatch):
    server, _, _ = started
    three_files(server)
    mediation(monkeypatch, spent=0.79)

    answer = estimate(server)

    assert answer["waehrung"] == "CHF"
    assert answer["guthaben"] == pytest.approx(4.21)
    assert answer["danach"] == pytest.approx(round(4.21 - answer["kosten"], 2))


def test_a_used_up_credit_is_zero(started, monkeypatch):
    server, _, _ = started
    three_files(server)
    mediation(monkeypatch, spent=5.0)

    answer = estimate(server)

    assert answer["guthaben"] == 0 and answer["danach"] == 0


def test_without_files_for_the_ai_the_mediation_is_not_asked(started, monkeypatch):
    server, _, _ = started
    upload(server, name="Zeugnis_Scan.png", category="zeugnisse", data=PNG)
    asked = mediation(monkeypatch, spent=1.0)

    answer = estimate(server)

    assert answer["anzahl"] == 0 and asked == []


def test_the_cost_follows_the_current_input_price_of_the_prefill_model(started, monkeypatch):
    server, _, _ = started
    upload(server, name="Lebenslauf.txt", data=("Erfundener Lebenslauf. " * 1_700).encode())
    model = tasks.MODELS["prefill"]
    price_in, price_out = usage.PRICES_USD[model]
    monkeypatch.setitem(usage.PRICES_USD, model, (price_in, 0.0))
    before = estimate(server)["kosten"]
    monkeypatch.setitem(usage.PRICES_USD, model, (price_in * 3, 0.0))

    after = estimate(server)["kosten"]

    assert after == pytest.approx(before * 3, abs=0.02)


def reading(*texts: str, shortened: bool = False) -> read_documents.Reading:
    return read_documents.Reading(tuple(read_documents.DocumentText("lebenslauf-bisher", f"cv{i}.txt", f"d/cv{i}.txt", text,
                                                                    shortened) for i, text in enumerate(texts)), ())


def test_every_character_sent_is_priced_at_the_full_input_price_with_a_fixed_answer():
    texts = ("Erfundener Lebenslauf. " * 300, "Erfundenes Zeugnis. " * 200)
    documents = reading(*texts)
    found = prefill_estimate.estimate(FORM, "job", documents)
    sent = (len(prompts.PREFILL_RULES) + len(tasks.prefill_instructions(prefill.field_guide(FORM, "job")))
            + len(prefill.documents_prompt(FORM, "job", documents.texts)))
    assert all(text in prefill.documents_prompt(FORM, "job", documents.texts) for text in texts)
    price_in, price_out = usage.PRICES_USD[tasks.MODELS["prefill"]]
    exact = (rate_all.tokens(sent) * price_in + prefill_estimate.OUTPUT_TOKENS * price_out) / usage.PER_MILLION

    assert found.count == 2
    assert found.cost_usd == pytest.approx(rate_all.cents_up(exact))
    assert exact <= found.cost_usd < exact + rate_all.CENT
    assert prefill_estimate.OUTPUT_TOKENS <= tasks.MAX_TOKENS["prefill"]


def test_cost_and_duration_have_a_floor_and_grow_with_the_text(monkeypatch):
    monkeypatch.setitem(usage.PRICES_USD, tasks.MODELS["prefill"], (0.0, 0.0))
    free = prefill_estimate.estimate(FORM, "job", reading("Kurz."))
    monkeypatch.undo()
    short = prefill_estimate.estimate(FORM, "job", reading("Kurz."))
    long = prefill_estimate.estimate(FORM, "job", reading(*["Lang. " * 6_000] * 3))

    assert free.cost_usd == rate_all.CENT and free.minutes >= 1
    assert long.cost_usd > short.cost_usd and long.minutes > short.minutes
    assert prefill_estimate.estimate(FORM, "job", reading()) == rate_all.Estimate(0, 0.0, 0)


def snapshot(folder: pathlib.Path) -> dict:
    return {str(path.relative_to(folder)): (path.read_bytes(), path.stat().st_mtime_ns)
            for path in sorted(folder.rglob("*")) if path.is_file()}


@pytest.mark.parametrize("via_mediation", [False, True])
def test_it_creates_no_ai_client_writes_nothing_and_marks_no_file_read(started, monkeypatch, via_mediation):
    server, folder, _ = started
    three_files(server)
    call(server, "/api/angaben/stand")
    if via_mediation:
        mediation(monkeypatch, spent=1.0)
    else:
        monkeypatch.setenv(KEY_VARIABLE, "sk-test")
    created = []

    def no_client(*args, **kwargs):
        created.append(args)
        raise AssertionError("the estimate must not create an AI client")

    monkeypatch.setattr(routes_ai, "new_client", no_client)
    monkeypatch.setattr(routes_ai, "consented_client", no_client)
    monkeypatch.setattr(connection, "make_client", no_client)
    monkeypatch.setattr(anthropic, "Anthropic", no_client)
    before = snapshot(folder)

    answer = estimate(server)

    assert answer["anzahl"] == 2 and created == []
    assert snapshot(folder) == before
    pending = yaml.safe_load((folder / "dokumente" / "neu.yaml").read_text(encoding="utf-8"))
    assert not any(entry.get(READ_MARK) for entry in pending)


def test_neither_the_extension_nor_claude_reach_the_estimate():
    assert ROUTE.startswith(routes_angaben.PREFILL_ROUTE)
    assert not [route for route in native_host.ALLOWED if route[1].startswith("/api/angaben")]
    source = inspect.getsource(mcp_tools)
    assert ROUTE not in source and "/api/angaben" not in source
