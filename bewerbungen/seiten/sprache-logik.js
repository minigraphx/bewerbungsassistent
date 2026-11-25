"use strict";
// What the card «Sprache» shows (G10, G12, #94, A10), without DOM so it can be tested: the language of the app and the
// languages the person applies in, from GET /api/sprachen. Until the person changes a box, the suggestion from the CV
// is the setting, and a ticked language other than German says where it came from (UI/UX ruling on #94).
(function (global) {
  // Loaded before this file on the page; required in the tests. Texts in the app language through Texte.t (#417).
  const texts = () => (typeof module !== "undefined" ? require("./texte.js") : global.Texte);
  // Each language of the app is named in its own language, so a French or English reader finds it; these names are
  // the same in every language of the app.
  const APP_LANGUAGES = [
    { value: "de", label: "Deutsch", lang: "de" },  // kein UI-Text: named in its own language
    { value: "fr", label: "Français", lang: "fr" },
    { value: "en", label: "English", lang: "en" },  // kein UI-Text: named in its own language
  ];
  /** The languages one applies in, named in the app language (#417). */
  function applicationLanguages() {
    const Texte = texts();
    return [
      { value: "de", label: Texte.t("Deutsch") },
      { value: "en", label: Texte.t("Englisch") },
      { value: "fr", label: Texte.t("Französisch") },
    ];
  }
  const APPLICATION_VALUES = ["de", "en", "fr"];
  const DEFAULT_APP = "de";
  const DEFAULT_APPLICATIONS = ["de"];
  // Until the pages are translated (#95), a choice of fr or en is kept and said to be coming, in that language. #434
  // removes the line with the switch.
  const PENDING_TRANSLATION = {
    fr: { text: "La traduction arrive bientôt. D'ici là, l'application reste en allemand.", lang: "fr" },  // kein UI-Text: already French
    en: { text: "The translation is on its way. Until then, the app stays in German.", lang: "en" },  // kein UI-Text: already English
  };

  const knownApp = value => (APP_LANGUAGES.some(option => option.value === value) ? value : DEFAULT_APP);
  const knownApplications = values => {
    const list = Array.isArray(values) ? values.filter(value => APPLICATION_VALUES.includes(value)) : [];
    return list.length ? list : DEFAULT_APPLICATIONS;
  };

  /** The level each suggested language has in the CV, as the CV writes it. */
  function levelsOf(state) {
    const entries = Array.isArray(state.vorschlag) ? state.vorschlag : [];
    return new Map(entries.filter(entry => entry && entry.stufe).map(entry => [entry.sprache, String(entry.stufe)]));
  }

  /** The card from GET /api/sprachen: the app's language, its translation line, and the checkboxes with their notes. */
  function view(state) {
    const current = state || {};
    const app = knownApp(current.app);
    const checked = knownApplications(current.bewerbung);
    const suggesting = current.bewerbung_gewaehlt !== true;
    const levels = levelsOf(current);
    const Texte = texts();
    const options = applicationLanguages().map(({ value, label }) => {
      const on = checked.includes(value);
      const noted = suggesting && on && value !== DEFAULT_APP && levels.has(value);
      // The level stays as the CV writes it.
      return { value, label, checked: on,
               note: noted ? Texte.t("vorgeschlagen: im Lebenslauf «{stufe}»", { stufe: levels.get(value) }) : null };
    });
    return { app, options, pending: PENDING_TRANSLATION[app] || null };
  }

  /** The values of the checked boxes, in the order of the list, as POST /api/sprachen takes them. */
  function checkedValues(boxes) {
    const on = new Set(boxes.filter(box => box.checked).map(box => box.value));
    return APPLICATION_VALUES.filter(value => on.has(value));
  }

  // The switch in the sidebar and on Einrichtung (#435): one label in the three languages, whatever the app speaks, so
  // a person who does not read German hears what the group is.
  const SWITCH_LABEL = "Sprache · Langue · Language";  // kein UI-Text: the same in every language of the app

  /**
   * The switch from GET /api/sprachen: the three languages, the stored one pressed, and, while the translation is off
   * (`uebersetzung`, #434), the line that says it is coming, as the card shows it.
   */
  function switchView(state) {
    const current = state || {};
    const app = knownApp(current.app);
    const translated = current.uebersetzung === true;
    return { app, translated, options: APP_LANGUAGES.map(option => ({ ...option, pressed: option.value === app })),
             pending: translated ? null : PENDING_TRANSLATION[app] || null };
  }

  /** The note on Einrichtung when the chosen data folder kept its own app language (`sprache` of the setup's answer). */
  function folderNote(carried) {
    const own = carried && carried.ergebnis === "eigene" && APP_LANGUAGES.find(option => option.value === carried.app);
    if (!own) return null;
    const Texte = texts();
    return Texte.t("In diesem Ordner war schon eine Sprache der App gespeichert: {sprache}. Sie gilt jetzt.",
                   { sprache: own.label });
  }

  const logic = {
    APP_LANGUAGES, get APPLICATION_LANGUAGES() { return applicationLanguages(); }, PENDING_TRANSLATION, view, checkedValues,
    SWITCH_LABEL, switchView, folderNote,
  };
  if (typeof module !== "undefined") module.exports = logic;
  else global.SpracheLogik = logic;
})(typeof window !== "undefined" ? window : globalThis);
