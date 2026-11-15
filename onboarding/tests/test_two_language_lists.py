"""Keywords and interests take two languages on Meine Angaben (#299, G30), as other values do since #181.

A keyword or an interest in cv.yaml that holds German and English is shown and edited per language, a plain one can
get English, and saving changes only what was edited. All data is invented.
"""
import cv_read
from test_full_cv_edit import changed_lines, errors_of, pdf_text, save, write_cv

ACCOUNTING = {"de": "Buchhaltung", "en": "Accounting"}
PAYROLL = {"de": "Lohnwesen", "en": "Payroll"}
HIKING = {"de": "Wandern", "en": "Hiking"}
COOKING = {"de": "Kochen", "en": "Cooking"}

CV = """\
# Lebenslauf von Hand (frei erfunden)
basics:
  name: Erika Beispiel
  email: erika@example.ch
  location:
    city: Bern

skills:
  - name: {de: Finanzen, en: Finance}
    keywords:
      - {de: Buchhaltung, en: Accounting}
      - name: {de: Lohnwesen, en: Payroll}
        level: 4
      - Excel  # seit 2015
      - name: SAP
        level: B2
interests:
  - name: {de: Wandern, en: Hiking}
    x-icon: mountain
  - name:
      de: Kochen
      en: Cooking
  - name: Lesen
"""


def keywords(data: dict) -> list:
    return data["skills"][0]["keywords"]


def interests(data: dict) -> list:
    return data["interests"]["interests"]


def test_two_language_keywords_and_interests_are_read_per_language(tmp_path):
    write_cv(tmp_path, CV)

    data = cv_read.read_form_data(tmp_path)

    assert keywords(data) == [ACCOUNTING, {"text": PAYROLL, "level": "4"}, "Excel", {"text": "SAP", "level": "4"}]
    assert interests(data) == [HIKING, COOKING, "Lesen"]


def test_a_cv_with_two_language_keywords_and_interests_saves_unchanged(tmp_path):
    path = write_cv(tmp_path, CV)

    assert errors_of(path, None) == []
    save(tmp_path)

    assert path.read_text(encoding="utf-8") == CV


def test_the_english_of_a_keyword_changes_only_in_its_line(tmp_path):
    path = write_cv(tmp_path, CV)

    def edit(data):
        keywords(data)[0] = {"text": {"de": "Buchhaltung", "en": "Bookkeeping"}, "level": ""}

    save(tmp_path, edit)

    assert changed_lines(CV, path.read_text(encoding="utf-8")) == [
        "-       - {de: Buchhaltung, en: Accounting}", "+       - {de: Buchhaltung, en: Bookkeeping}"]


def test_a_keyword_with_a_level_keeps_its_level_when_its_english_changes(tmp_path):
    path = write_cv(tmp_path, CV)

    def edit(data):
        keywords(data)[1] = {"text": {"de": "Lohnwesen", "en": "Payroll accounting"}, "level": "4"}

    cv = save(tmp_path, edit)

    assert keywords(cv)[1] == {"name": {"de": "Lohnwesen", "en": "Payroll accounting"}, "level": 4}
    assert changed_lines(CV, path.read_text(encoding="utf-8")) == [
        "-       - name: {de: Lohnwesen, en: Payroll}", "+       - name: {de: Lohnwesen, en: Payroll accounting}"]


def test_a_two_language_keyword_takes_a_level(tmp_path):
    write_cv(tmp_path, CV)

    def edit(data):
        keywords(data)[0] = {"text": ACCOUNTING, "level": "5"}

    cv = save(tmp_path, edit)

    assert keywords(cv)[0] == {"name": ACCOUNTING, "level": 5}


def test_a_plain_keyword_gets_english_and_keeps_its_comment(tmp_path):
    path = write_cv(tmp_path, CV)

    def edit(data):
        keywords(data)[2] = {"text": {"de": "Excel", "en": "Excel spreadsheets"}, "level": ""}

    save(tmp_path, edit)

    assert changed_lines(CV, path.read_text(encoding="utf-8")) == [
        "-       - Excel  # seit 2015", "+       - {de: Excel, en: Excel spreadsheets} # seit 2015"]


def test_a_keyword_drops_its_english(tmp_path):
    write_cv(tmp_path, CV)

    def edit(data):
        keywords(data)[0] = {"text": "Buchhaltung", "level": ""}
        keywords(data)[1] = {"text": "Lohnwesen", "level": "4"}

    cv = save(tmp_path, edit)

    assert keywords(cv)[:2] == ["Buchhaltung", {"name": "Lohnwesen", "level": 4}]


def test_the_english_of_an_interest_changes_and_its_icon_stays(tmp_path):
    path = write_cv(tmp_path, CV)

    def edit(data):
        interests(data)[0] = {"de": "Wandern", "en": "Hiking trips"}
        interests(data)[1] = {"de": "Kochen", "en": "Cooking classes"}

    cv = save(tmp_path, edit)

    assert cv["interests"][0] == {"name": {"de": "Wandern", "en": "Hiking trips"}, "x-icon": "mountain"}
    assert changed_lines(CV, path.read_text(encoding="utf-8")) == [
        "-   - name: {de: Wandern, en: Hiking}", "+   - name: {de: Wandern, en: Hiking trips}",
        "-       en: Cooking", "+       en: Cooking classes"]


def test_a_plain_interest_gets_english(tmp_path):
    path = write_cv(tmp_path, CV)

    def edit(data):
        interests(data)[2] = {"de": "Lesen", "en": "Reading"}

    save(tmp_path, edit)

    assert changed_lines(CV, path.read_text(encoding="utf-8")) == [
        "-   - name: Lesen", "+   - name: {de: Lesen, en: Reading}"]


def test_new_two_language_keywords_and_interests_are_added(tmp_path):
    write_cv(tmp_path, CV)

    def add(data):
        data["skills"].append({"name": "Werkzeuge", "keywords": [
            {"text": {"de": "Tabellen", "en": "Spreadsheets"}, "level": "3"}, {"de": "Präsentationen", "en": "Slides"}]})
        interests(data).append({"de": "Velofahren", "en": "Cycling"})

    cv = save(tmp_path, add)

    assert keywords({"skills": cv["skills"][1:]}) == [{"name": {"de": "Tabellen", "en": "Spreadsheets"}, "level": 3},
                                                      {"de": "Präsentationen", "en": "Slides"}]
    assert cv["interests"][3] == {"name": {"de": "Velofahren", "en": "Cycling"}}


def test_two_language_keywords_and_interests_typed_anew_follow_the_rules(tmp_path):
    path = write_cv(tmp_path, CV)

    def edit(data):
        keywords(data)[0] = {"text": {"de": "Buch-\nhaltung", "en": "Accounting"}, "level": ""}
        keywords(data)[1] = {"text": PAYROLL, "level": "7"}
        interests(data)[2] = {"de": "Lesen", "en": "Rea-\nding"}

    assert sorted(errors_of(path, edit)) == ["interests.interests.2|newline", "skills.0.keywords.0|newline",
                                            "skills.0.keywords.1.level|option"]


def test_lebenslauf_renders_two_language_keywords_and_interests_in_both_languages(tmp_path):
    path = write_cv(tmp_path / "daten", CV)

    def edit(data):
        keywords(data)[2] = {"text": {"de": "Tabellenkalkulation", "en": "Spreadsheets"}, "level": ""}
        interests(data)[2] = {"de": "Lesen", "en": "Reading"}

    save(tmp_path / "daten", edit)
    german = pdf_text(path, tmp_path / "de")
    english = pdf_text(path, tmp_path / "en", "en")

    assert all(word in german for word in ("Buchhaltung", "Lohnwesen", "Tabellenkalkulation", "Wandern", "Kochen", "Lesen"))
    assert all(word in english for word in ("Accounting", "Payroll", "Spreadsheets", "Hiking", "Cooking", "Reading"))
    assert "Accounting" not in german and "Buchhaltung" not in english


def test_a_new_keyword_in_two_languages_is_written_in_the_short_form(tmp_path):
    path = write_cv(tmp_path, CV)

    save(tmp_path, lambda data: keywords(data).append({"text": {"de": "Kasse", "en": "Till"}, "level": ""}))

    assert changed_lines(CV, path.read_text(encoding="utf-8")) == ["+       - {de: Kasse, en: Till}"]
