"use strict";
// The card «Browser der App» under Einstellungen, Browser und Erweiterung (G99, #369), without DOM so it can be
// tested: the options from GET /api/app/browser, a browser this computer lacks, the lines after saving.
(function (global) {
  const LEGEND = "Die App öffnet sich in";
  const HINT = "Die Browser-Erweiterung läuft in Chrome und Edge. Ist ein anderer Browser der Standard, "
    + "öffnet sich die App besser gleich in Chrome oder Edge.";
  const NOT_FOUND = "auf diesem Computer nicht gefunden";
  const DEFAULT = "standard";
  const ORDER = [DEFAULT, "chrome", "edge"];
  const LABELS = { standard: "Standardbrowser des Computers (Voreinstellung)", chrome: "Google Chrome", edge: "Microsoft Edge" };
  // desktop/dialogs.py LINUX_COMMANDS: Chromium counts for Chrome there.
  const LINUX_CHROME = "Google Chrome oder Chromium";

  function label(value, platform) {
    return value === "chrome" && platform === "linux" ? LINUX_CHROME : LABELS[value];
  }

  /** The options to draw: label, checked, disabled with the reason; a saved choice that is gone stays checked. */
  function options(state) {
    const found = new Map((state.browser || []).map(entry => [entry.wert, entry.gefunden === true]));
    const chosen = ORDER.includes(state.gewaehlt) ? state.gewaehlt : DEFAULT;
    return ORDER.map(value => {
      const there = value === DEFAULT || found.get(value) === true;
      return { value, label: label(value, state.plattform), checked: value === chosen, disabled: !there,
               note: there ? null : NOT_FOUND };
    });
  }

  function savedText(value, platform) {
    const where = value === DEFAULT ? "im Standardbrowser" : `in ${label(value, platform)}`;
    return `Gespeichert. Ab dem nächsten Öffnen erscheint die App ${where}.`;
  }

  const failedText = message => `Nicht gespeichert: ${message}`;

  const logic = { LEGEND, HINT, NOT_FOUND, options, savedText, failedText };
  if (typeof module !== "undefined") module.exports = logic;
  else global.BrowserWahlLogik = logic;
})(typeof window !== "undefined" ? window : globalThis);
