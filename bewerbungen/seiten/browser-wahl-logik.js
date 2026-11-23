"use strict";
// The card «Browser der App» under Einstellungen, Browser und Erweiterung (G99, #369), without DOM so it can be
// tested: the options from GET /api/app/browser, a browser this computer lacks, the lines after saving.
(function (global) {
  // Loaded before this file on the page; required in the tests. Texts in the app language through Texte.t (#417).
  const texts = () => (typeof module !== "undefined" ? require("./texte.js") : global.Texte);
  const DEFAULT = "standard";
  const ORDER = [DEFAULT, "chrome", "edge"];
  // Product names stay as they are in every language.
  const BRANDS = { chrome: "Google Chrome", edge: "Microsoft Edge" };  // kein UI-Text: product names

  /** The fixed texts of the card in the app language; the page's HTML says the same in its legend and hint. */
  function words() {
    const Texte = texts();
    return {
      legend: Texte.t("Die App öffnet sich in"),
      hint: Texte.t("Die Browser-Erweiterung läuft in Chrome und Edge. Ist ein anderer Browser der Standard, öffnet sich die App besser gleich in Chrome oder Edge."),
      notFound: Texte.t("auf diesem Computer nicht gefunden"),
      // A saved choice that is gone: desktop/app_browser.py opens the default browser until it is back or changed.
      notFoundChosen: Texte.t("auf diesem Computer nicht gefunden; bis dahin öffnet sich die App im Standardbrowser"),
      standard: Texte.t("Standardbrowser des Computers (Voreinstellung)"),
      // desktop/dialogs.py LINUX_COMMANDS: Chromium counts for Chrome there.
      linuxChrome: Texte.t("Google Chrome oder Chromium"),
    };
  }

  function label(value, platform) {
    if (value === DEFAULT) return words().standard;
    return value === "chrome" && platform === "linux" ? words().linuxChrome : BRANDS[value];
  }

  /** The options to draw: label, checked, disabled with the reason; a saved choice that is gone stays checked. */
  function options(state) {
    const found = new Map((state.browser || []).map(entry => [entry.wert, entry.gefunden === true]));
    const chosen = ORDER.includes(state.gewaehlt) ? state.gewaehlt : DEFAULT;
    const { notFound, notFoundChosen } = words();
    return ORDER.map(value => {
      const there = value === DEFAULT || found.get(value) === true;
      const checked = value === chosen;
      const missing = checked ? notFoundChosen : notFound;
      return { value, label: label(value, state.plattform), checked, disabled: !there, note: there ? null : missing };
    });
  }

  function savedText(value, platform) {
    const Texte = texts();
    return value === DEFAULT
      ? Texte.t("Gespeichert. Ab dem nächsten Öffnen erscheint die App im Standardbrowser.")
      : Texte.t("Gespeichert. Ab dem nächsten Öffnen erscheint die App in {browser}.", { browser: label(value, platform) });
  }

  function failedText(message) {
    const Texte = texts();
    return Texte.t("Nicht gespeichert: {grund}", { grund: message });
  }

  const logic = {
    get LEGEND() { return words().legend; }, get HINT() { return words().hint; }, get NOT_FOUND() { return words().notFound; },
    options, savedText, failedText,
  };
  if (typeof module !== "undefined") module.exports = logic;
  else global.BrowserWahlLogik = logic;
})(typeof window !== "undefined" ? window : globalThis);
