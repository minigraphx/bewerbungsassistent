"use strict";
// What the card «Sprache» shows (G10, G12, #94, A10), without DOM so it can be tested: the language of the app and the
// languages the person applies in, from GET /api/sprachen. Until the person changes a box, the suggestion from the CV
// is the setting, and a ticked language other than German says where it came from (UI/UX ruling on #94).
(function (global) {
  // Each language of the app is named in its own language, so a French or English reader finds it.
  const APP_LANGUAGES = [
    { value: "de", label: "Deutsch", lang: "de" },
    { value: "fr", label: "Français", lang: "fr" },
    { value: "en", label: "English", lang: "en" },
  ];
  const APPLICATION_LANGUAGES = [
    { value: "de", label: "Deutsch" },
    { value: "en", label: "Englisch" },
    { value: "fr", label: "Französisch" },
  ];
  const DEFAULT_APP = "de";
  const DEFAULT_APPLICATIONS = ["de"];
  // Until the pages are translated (#95), a choice of fr or en is kept and said to be coming, in that language.
  const PENDING_TRANSLATION = {
    fr: { text: "La traduction arrive bientôt. D'ici là, l'application reste en allemand.", lang: "fr" },
    en: { text: "The translation is on its way. Until then, the app stays in German.", lang: "en" },
  };

  const knownApp = value => (APP_LANGUAGES.some(option => option.value === value) ? value : DEFAULT_APP);
  const knownApplications = values => {
    const list = Array.isArray(values) ? values.filter(value => APPLICATION_LANGUAGES.some(o => o.value === value)) : [];
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
    const options = APPLICATION_LANGUAGES.map(({ value, label }) => {
      const on = checked.includes(value);
      const noted = suggesting && on && value !== DEFAULT_APP && levels.has(value);
      return { value, label, checked: on, note: noted ? `vorgeschlagen: im Lebenslauf «${levels.get(value)}»` : null };
    });
    return { app, options, pending: PENDING_TRANSLATION[app] || null };
  }

  /** The values of the checked boxes, in the order of the list, as POST /api/sprachen takes them. */
  function checkedValues(boxes) {
    const on = new Set(boxes.filter(box => box.checked).map(box => box.value));
    return APPLICATION_LANGUAGES.map(option => option.value).filter(value => on.has(value));
  }

  const logic = { APP_LANGUAGES, APPLICATION_LANGUAGES, PENDING_TRANSLATION, view, checkedValues };
  if (typeof module !== "undefined") module.exports = logic;
  else global.SpracheLogik = logic;
})(typeof window !== "undefined" ? window : globalThis);
