"""Conversion of a valid bundle into cv.yaml, suchprofil.md, anschreiben/stil.md and anschreiben/bausteine.md."""
import datetime

import yaml

import convert
from form_cases import base_bundle

TODAY = datetime.date(2026, 11, 2)
FILES = ["cv.yaml", "suchprofil.md", "anschreiben/stil.md", "anschreiben/bausteine.md"]


def files_for(form, bundle):
    return convert.convert_bundle(form, bundle, TODAY)


def test_all_four_files(form):
    assert sorted(files_for(form, base_bundle("job"))) == sorted(FILES)


def test_cv_basics_for_job(form):
    cv = yaml.safe_load(files_for(form, base_bundle("job"))["cv.yaml"])

    assert cv["basics"]["name"] == "Erika Beispiel"
    assert cv["basics"]["email"] == "erika@example.ch"
    assert cv["basics"]["location"] == {"address": "Musterweg 1", "postalCode": "3000", "city": "Bern"}
    assert cv["basics"]["summary"] == "Software-Entwicklerin mit zehn Jahren Praxis."
    assert cv["basics"]["profiles"] == [{"network": "GitHub", "url": "https://github.com/example"}]
    assert "x-beschriftungen" not in cv


def test_cv_sections(form):
    cv = yaml.safe_load(files_for(form, base_bundle("job"))["cv.yaml"])

    assert cv["work"][0] == {
        "position": "Software-Entwicklerin", "name": "Beispiel AG", "location": "Bern",
        "startDate": "2019-03", "endDate": None, "highlights": ["Plattform für Kundendaten", "Datenpipelines"],
    }
    assert cv["work"][1]["endDate"] == "2019"
    assert cv["education"][0]["area"] == "Informatik"
    assert cv["certificates"] == [{"name": "Machine Learning Grundlagen", "issuer": "Online-Kurs", "date": "2023-05"}]
    assert cv["languages"][1] == {"language": "Englisch", "fluency": "Sehr gut (C1)"}
    assert cv["skills"] == [{"name": "Programme", "keywords": ["Python", "SQL"]}]
    assert cv["interests"] == [{"name": "Wandern"}]


def test_cv_drops_empty_values(form):
    bundle = base_bundle("job")
    bundle["data"]["work"][1]["location"] = "  "
    bundle["data"]["work"][1]["highlights"] = ["", "Wartung"]

    cv = yaml.safe_load(files_for(form, bundle)["cv.yaml"])

    assert "location" not in cv["work"][1]
    assert cv["work"][1]["highlights"] == ["Wartung"]


def test_cv_for_apprenticeship_has_school_headings(form):
    cv = yaml.safe_load(files_for(form, base_bundle("apprenticeship"))["cv.yaml"])

    assert cv["x-beschriftungen"] == {"erfahrung": "Schnupperlehren & Erfahrungen", "bildung": "Schule & Eignungstests"}
    assert cv["basics"]["details"] == ["geboren 1. Mai 2011"]
    assert "label" not in cv["basics"]


def test_cv_header_names_the_source(form):
    text = files_for(form, base_bundle("job"))["cv.yaml"]

    assert text.startswith("# Erstellt mit der Einstiegsvorlage am 2.11.2026")


def test_search_profile_for_job(form):
    text = files_for(form, base_bundle("job"))["suchprofil.md"]

    assert "1. Software-Entwicklung (Priorität 1)" in text
    assert "2. Daten (Priorität 2)" in text
    assert "- Kantone (job-room): BE, SO" in text
    assert "- Pensum: 80–100 %" in text
    assert "- Kubernetes noch nicht produktiv eingesetzt" in text
    assert "## Keywords" not in text  # no keywords given


def test_search_profile_for_apprenticeship(form):
    text = files_for(form, base_bundle("apprenticeship"))["suchprofil.md"]

    assert "## Lehrbeginn\n- August 2027" in text
    assert "1. Fachfrau Gesundheit EFZ (Priorität 1)" in text
    assert "- Berufsmaturität: vielleicht" in text
    assert "- Multicheck Gesundheit (2026-10)" in text
    assert "- Spital Beispiel, Schnupperlehre Fachfrau Gesundheit (2026-10)" in text
    assert "LENA" in text


def test_style_profile(form):
    text = files_for(form, base_bundle("job"))["anschreiben/stil.md"]

    assert "- Sachlich und freundlich." in text
    assert "Immer Sie-Form" in text
    assert "- Einstieg: „Ihre Stelle als … spricht mich an, weil …“" in text
    assert "- Gruss: „Freundliche Grüsse“; Ort im Datum: Bern." in text


def test_style_profile_for_apprenticeship_uses_formal_address(form):
    text = files_for(form, base_bundle("apprenticeship"))["anschreiben/stil.md"]

    assert "Sie-Form" in text
    assert "Du-Form" not in text
    assert "Motivationsschreiben" in text


def test_building_blocks_carry_evidence(form):
    text = files_for(form, base_bundle("job"))["anschreiben/bausteine.md"]

    assert "- **Software-Entwicklerin, Beispiel AG, Bern (seit 2019-03)** – Plattform für Kundendaten; Datenpipelines. *Beleg: Arbeitszeugnis.*" in text
    assert "- **Junior-Entwicklerin, Muster GmbH (2015–2019)** – *Beleg: eigene Angabe.*" in text
    assert "- **Erklären** – Interne Schulungen zu Git für 20 Personen. *Beleg: Arbeitszeugnis.*" in text
    assert "- Kündigungsfrist: 3 Monate" in text


def test_markdown_stays_flat(form):
    bundle = base_bundle("job")
    bundle["data"]["strengths"][0]["example"] = "Erste Zeile\n## Keine Überschrift\n- kein Punkt"

    text = files_for(form, bundle)["anschreiben/bausteine.md"]

    assert "\n## Keine" not in text
    assert "Erste Zeile ## Keine Überschrift - kein Punkt" in text


def test_profile_link_with_odd_host_does_not_crash(form):
    bundle = base_bundle("job")
    bundle["data"]["person"]["profiles"] = ["https://[abc", "www.[x"]

    cv = yaml.safe_load(files_for(form, bundle)["cv.yaml"])

    assert [p["url"] for p in cv["basics"]["profiles"]] == ["https://[abc", "https://www.[x"]


def test_exclusions_stay_on_one_line(form):
    bundle = base_bundle("job")
    bundle["data"]["searchJob"]["exclusions"] = ["Callcenter\x0b## Kein Titel"]

    text = files_for(form, bundle)["suchprofil.md"]

    assert "- Ausschluss: Callcenter ## Kein Titel" in text


def test_known_gaps_are_taken_over(form):
    files = files_for(form, base_bundle("job"))

    assert "## Lücken (offen benennen)\n- Kubernetes noch nicht produktiv eingesetzt" in files["anschreiben/bausteine.md"]
    assert "## Typische Haken (offen benennen)\n- Kubernetes noch nicht produktiv eingesetzt" in files["suchprofil.md"]


def test_without_gaps_the_files_say_they_come_later(form):
    for track in ["job", "apprenticeship"]:
        bundle = base_bundle(track)
        bundle["data"].pop("gaps", None)
        files = files_for(form, bundle)

        assert "## Lücken (offen benennen)\n- Noch keine. Die App ergänzt sie nach und nach" in files["anschreiben/bausteine.md"]
        assert "## Typische Haken (offen benennen)\n- Noch keine." in files["suchprofil.md"]


def test_the_wish_for_trial_apprenticeships_reaches_the_search_profile():
    import markdown_files

    sections = dict(markdown_files._search_apprenticeship({"searchApprenticeship": {"offers": "Schnupperlehren"}}))

    assert sections["Gesucht"] == ["- Schnupperlehren"]
