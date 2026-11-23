"""The shared search logic in French and English (#421, G10, docs/design/sprachen.md).

The scripts that the pages Stellen, Suche einstellen, Suchbegriffe prüfen and Firmen share have every text in the
catalog in fr and en, so they are in FERTIG and the gate keeps them so. What the scripts say at run time is tested in
tests/search_logic_languages.test.cjs. The lines of the search profile are data the person finds in the profile under
these words, so the catalog never translates them.
"""
import pytest

import sprachen_pruefen
import translation_catalog

SCRIPTS = ("seiten/treffer-logik.js", "seiten/suchbegriffe-logik.js", "seiten/verworfen-woerter-logik.js",
           "seiten/suche-anzeige.js", "seiten/firmen-logik.js", "seiten/kununu-pruefen.js", "seiten/firmen-ausschluss.js")
# Search profile grammar (vorlagen/suchprofil.md): the scripts show it as it stands in the profile.
PROFILE_LINES = ("Nischen (ohne Ort suchen)", "Nur {portale}", "(ganzes Wort)")


def test_the_shared_search_scripts_are_finished():
    finished = {str(path.relative_to(sprachen_pruefen.BASE)) for path in sprachen_pruefen.FERTIG
                if path.is_relative_to(sprachen_pruefen.BASE)}

    assert set(SCRIPTS) <= finished


def test_the_shared_search_scripts_have_no_gap():
    catalog = translation_catalog.load(translation_catalog.CATALOG_DIR)

    assert sprachen_pruefen.gaps([sprachen_pruefen.BASE / script for script in SCRIPTS], catalog) == ()


def test_the_lines_of_the_search_profile_are_never_translated():
    catalog = translation_catalog.load(translation_catalog.CATALOG_DIR)

    assert [line for line in PROFILE_LINES if catalog.text(line, "fr") or catalog.text(line, "en")] == []


# The wording of the UI/UX review (#421): a search run is a «série de recherches», the title filter is a label of the
# app and named in the language of the app, a hit left without a grade is «sans note» or unrated.
NBSP = chr(0xA0)
REVIEWED = {
    "Jeder Suchbegriff hat in den letzten 3 Suchläufen eigene Treffer gebracht.": (
        "Chaque mot-clé a apporté ses propres résultats lors des 3 dernières séries de recherches.",
        "Every search term brought results of its own in the last 3 search runs."),
    "Für diese Zahlen braucht die App {noetig} Suchläufe seit Version {version}, bisher gibt es noch keinen.": (
        f"Pour ces chiffres, l'app a besoin de {{noetig}} séries de recherches depuis la version {{version}}{NBSP}; "
        "il n'y en a encore aucune.",
        "For these numbers the app needs {noetig} search runs since version {version}; there are none yet."),
    "vom Titelfilter aussortiert": ("filtré par le filtre de titre", "filtered out by the title filter"),
    "{anzahl} vom Titelfilter": ("{anzahl} par le filtre de titre", "{anzahl} by the title filter"),
    "Entfällt: {begriffe}": (f"Retrait{NBSP}: {{begriffe}}", "Removed: {begriffe}"),
    "Alle sind eingeschaltet. Was Sie ausschalten, entfällt beim Übernehmen.": (
        "Tous sont activés. Ce que vous désactivez est retiré lorsque vous appliquez.",
        "All are switched on. Whatever you switch off is removed when you apply."),
    "Alle sind eingeschaltet. Was du ausschaltest, entfällt beim Übernehmen.": (
        "Tous sont activés. Ce que tu désactives est retiré lorsque tu appliques.",
        "All are switched on. Whatever you switch off is removed when you apply."),
    "Das KI-Budget ist aufgebraucht, wieder ab {datum}.": (
        "Le budget IA est épuisé, à nouveau disponible le {datum}.",
        "The AI budget is used up, available again on {datum}."),
    "Ist es aufgebraucht, hält die Prüfung an; was geprüft ist, bleibt.": (
        f"S'il est épuisé, l'évaluation s'arrête{NBSP}; ce qui a été évalué reste.",
        "If it runs out, the rating stops; what has been rated stays."),
    "Das KI-Budget für {monat} ist aufgebraucht. Ab {datum} prüft die KI wieder; was geprüft ist, bleibt.": (
        f"Le budget IA pour {{monat}} est épuisé. L'IA évalue à nouveau dès le {{datum}}{NBSP}; ce qui a été évalué reste.",
        "The AI budget for {monat} is used up. The AI rates again from {datum}; what has been rated stays."),
    "Die Erweiterung hat keine Suche am Laufen. Bitte nochmals „Jetzt suchen“ drücken, sonst die Seite neu laden.": (
        f"L'extension n'a aucune recherche en cours. Cliquer à nouveau sur «{NBSP}Rechercher maintenant{NBSP}», "
        "sinon recharger la page.",
        "The extension has no search running. Please click “Search now” again, or else reload the page."),
    "Noch nichts in Bewerbungen": ("Encore rien dans Candidatures", "Nothing in Applications yet"),
    "Mit Merken oder Bewerbung vorbereiten kommt ein Treffer hierher.": (
        f"Avec «{NBSP}Mettre de côté{NBSP}» ou «{NBSP}Préparer la candidature{NBSP}», un résultat arrive ici.",
        "With “Save” or “Prepare application”, a result comes here."),
    "Ohne Ort gesucht. Behalten werden Stellen in {kantone}, an Ihren Orten oder mit Remote.": (
        "Recherche sans lieu. Sont conservées les offres dans {kantone}, dans vos localités ou en télétravail.",
        "Searched without a place. Jobs in {kantone}, in your places or with remote work are kept."),
    "{name}: mehrere Treffer bei kununu. Bitte den passenden wählen.": (
        f"{{name}}{NBSP}: plusieurs résultats sur kununu. Merci de choisir le bon.",
        "{name}: several results on kununu. Please choose the matching one."),
    "Nicht geprüft. kununu war nicht erreichbar. Bitte später nochmals prüfen.": (
        "Non vérifié. kununu n'était pas joignable. Merci de vérifier à nouveau plus tard.",
        "Not checked. kununu could not be reached. Please check again later."),
    "KI prüft Ihre Suchbegriffe": ("L'IA vérifie vos mots-clés", "The AI is checking your search terms"),
    "KI prüft deine Suchbegriffe": ("L'IA vérifie tes mots-clés", "The AI is checking your search terms"),
}


@pytest.mark.parametrize("german", REVIEWED)
def test_the_reviewed_wording_is_in_the_catalog(german):
    catalog = translation_catalog.load(translation_catalog.CATALOG_DIR)

    assert (catalog.text(german, "fr"), catalog.text(german, "en")) == REVIEWED[german]


def test_the_title_filter_is_named_as_a_label_never_quoted_as_profile_text():
    catalog = translation_catalog.load(translation_catalog.CATALOG_DIR)
    german = [key for key in catalog.entries if "Titelfilter" in key and not key.startswith("texte:")]

    assert german and [key for key in german for language in ("fr", "en")
                       if "Titelfilter" in (catalog.text(key, language) or "")] == []
