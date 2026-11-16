"use strict";
// The live preview in „Lebenslauf erstellen“ (G76, #294): its words and when the live region speaks. No DOM
// (tests/lebenslauf_vorschau.test.cjs); the page part is lebenslauf-vorschau.js, the build cv_preview.py.
(function (global) {
  // Long enough that typing in Kurzprofil builds once per pause, short enough to feel like it follows.
  const DELAY_MS = 600;
  // Answers of the server that name a next step (cv_preview.py).
  const CHECK_DATA = "angaben-pruefen";
  const REOPEN = "neu-oeffnen";
  // «gerade» only where trying again can help.
  const NOT_SHOWN = "Die Vorschau lässt sich gerade nicht anzeigen. Bitte nochmals ändern oder die Seite neu laden.";
  const UNREACHABLE = "Die Vorschau lässt sich gerade nicht erstellen: Die App antwortet nicht. Bitte nochmals ändern oder später versuchen.";
  const UNREADABLE = "Die Vorschau lässt sich nicht erstellen: In Meine Angaben steht etwas, das die App nicht lesen kann.";
  const REFUSED = "Die Vorschau lässt sich nicht erstellen.";
  const EMPTY = "Noch keine Station angehakt. Die Vorschau erscheint, sobald mindestens eine angehakt ist.";

  const pagesText = pages => `${pages} ${pages === 1 ? "Seite" : "Seiten"}`;

  /** The heading over the preview: with the pages once there is one; the parts of a «·» line (#342). */
  const title = pages => (pages ? ["Vorschau", pagesText(pages)] : ["Vorschau"]);

  /**
   * What stands instead of the preview when a choice cannot be sent: {text}. No station ticked is a state, not a
   * failure; another reason from the page stands as it is.
   */
  const ofDraft = ({ empty, reason }) => ({ text: empty ? EMPTY : String(reason) });

  /**
   * What stands instead of the preview after a request failed (an Error as App.senden throws it): {text} and, where
   * there is a next step, `link` (Meine Angaben), `reload` («Neu laden») or `details` (the raw message under
   * «Genauer»). `say` gives the words of the person's text set.
   */
  function problem(error, say) {
    const action = error && error.daten ? error.daten.aktion : undefined;
    if (action === CHECK_DATA) return { text: UNREADABLE, link: true, details: error.message };
    if (action === REOPEN) return { text: say("lebenslauf.vorschau-geaendert"), reload: true };
    if (!error || !error.status || error.status >= 500) return { text: UNREACHABLE };
    return { text: `${REFUSED} ${error.message}` };
  }

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

  const logic = { DELAY_MS, CHECK_DATA, REOPEN, NOT_SHOWN, title, ofDraft, problem, pageAlt, announcement };
  if (typeof module !== "undefined") module.exports = logic;
  else global.LebenslaufVorschauLogik = logic;
})(typeof window !== "undefined" ? window : globalThis);
