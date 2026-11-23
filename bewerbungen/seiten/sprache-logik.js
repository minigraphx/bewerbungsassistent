"use strict";
// What the card «Sprache» shows (G10, G12, #94, A10), without DOM so it can be tested: the language of the app and the
// languages the person applies in, from GET /api/sprachen. A suggestion from the CV names the CV's level.
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
  // Until the pages are translated (#95), a choice of fr or en is kept and said to be coming.
  const PENDING_TRANSLATION = "Die Übersetzung folgt. Bis dahin bleibt die App auf Deutsch.";

  const knownApp = value => (APP_LANGUAGES.some(option => option.value === value) ? value : DEFAULT_APP);
  const knownApplications = values => {
    const list = Array.isArray(values) ? values.filter(value => APPLICATION_LANGUAGES.some(o => o.value === value)) : [];
    return list.length ? list : DEFAULT_APPLICATIONS;
  };

  /** The card from GET /api/sprachen: the app's language, the checkboxes with their parts, whether to confirm. */
  function view(state) {
    const current = state || {};
    const app = knownApp(current.app);
    const checked = knownApplications(current.bewerbung);
    const levels = new Map((Array.isArray(current.vorschlag) ? current.vorschlag : [])
      .filter(entry => entry && entry.stufe).map(entry => [entry.sprache, entry.stufe]));
    const options = APPLICATION_LANGUAGES.map(({ value, label }) => ({
      value, label, checked: checked.includes(value),
      parts: levels.has(value) ? [label, `vorgeschlagen: im Lebenslauf «${levels.get(value)}»`] : [label],
    }));
    return { app, options, confirm: current.bewerbung_gewaehlt !== true,
             pending: app === DEFAULT_APP ? null : PENDING_TRANSLATION };
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
