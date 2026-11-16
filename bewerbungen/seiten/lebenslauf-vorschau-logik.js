"use strict";
// The live preview in „Lebenslauf erstellen“ (G76, #294): its words and when the live region speaks. No DOM
// (tests/lebenslauf_vorschau.test.cjs); the page part is lebenslauf-vorschau.js, the build cv_preview.py.
(function (global) {
  // Long enough that typing in Kurzprofil builds once per pause, short enough to feel like it follows.
  const DELAY_MS = 600;
  const FAILED = "Die Vorschau lässt sich gerade nicht erstellen.";
  const NOT_SHOWN = "Die Vorschau lässt sich gerade nicht anzeigen. Bitte nochmals ändern oder die Seite neu laden.";

  const pagesText = pages => `${pages} ${pages === 1 ? "Seite" : "Seiten"}`;

  /** The heading over the preview: with the pages once there is one. */
  const title = pages => (pages ? `Vorschau · ${pagesText(pages)}` : "Vorschau");

  /** A reason from the page (no station chosen) worded like the server's own message. */
  const failedText = reason => (String(reason).startsWith(FAILED) ? String(reason) : `${FAILED} ${reason}`);

  const pageAlt = (page, pages) => `Lebenslauf, Seite ${page} von ${pages}`;

  /**
   * What the live region says when the preview goes from `before` to `after` ({pages} or {failed}). The picture
   * changes with every keystroke; only what the person would miss without looking is said: a new page count, a
   * failure, and that it works again. The first preview after opening is read where it stands.
   */
  function announcement(before, after) {
    if (after.failed) return before && before.failed === after.failed ? "" : after.failed;
    if (!before) return "";
    if (before.failed) return `Die Vorschau ist wieder da, ${pagesText(after.pages)}.`;
    return before.pages === after.pages ? "" : `Die Vorschau hat jetzt ${pagesText(after.pages)}.`;
  }

  const logic = { DELAY_MS, NOT_SHOWN, title, failedText, pageAlt, announcement };
  if (typeof module !== "undefined") module.exports = logic;
  else global.LebenslaufVorschauLogik = logic;
})(typeof window !== "undefined" ? window : globalThis);
