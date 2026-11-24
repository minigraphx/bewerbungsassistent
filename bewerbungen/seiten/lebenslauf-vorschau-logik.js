"use strict";
// The live preview in „Lebenslauf erstellen“ (G76, #294): its words and when the live region speaks. No DOM
// (tests/lebenslauf_vorschau.test.cjs); the page part is lebenslauf-vorschau.js, the build cv_preview.py.
(function (global) {
  // Long enough that typing in Kurzprofil builds once per pause, short enough to feel like it follows.
  const DELAY_MS = 600;
  // Answers of the server that name a next step (cv_preview.py).
  const CHECK_DATA = "angaben-pruefen";
  const REOPEN = "neu-oeffnen";
  // Texts in the app language through Texte (#428); the page's Texte is found when a text is made.
  const texts = () => (typeof module !== "undefined" ? require("./texte.js") : global.Texte);
  const Texte = { t: (deutsch, werte) => texts().t(deutsch, werte) };
  // «gerade» only where trying again can help.
  const notShown = () => Texte.t("Die Vorschau lässt sich gerade nicht anzeigen. Bitte nochmals ändern oder die Seite neu laden.");
  const unreachable = () => Texte.t("Die Vorschau lässt sich gerade nicht erstellen: Die App antwortet nicht. Bitte nochmals ändern oder später versuchen.");
  const unreadable = () => Texte.t("Die Vorschau lässt sich nicht erstellen: In Meine Angaben steht etwas, das die App nicht lesen kann.");
  const empty = () => Texte.t("Noch keine Station angehakt. Die Vorschau erscheint, sobald mindestens eine angehakt ist.");

  const pagesText = pages => (pages === 1 ? Texte.t("1 Seite") : Texte.t("{anzahl} Seiten", { anzahl: pages }));

  /** The heading over the preview: with the pages once there is one; the parts of a «·» line (#342). */
  const title = pages => (pages ? [Texte.t("Vorschau"), pagesText(pages)] : [Texte.t("Vorschau")]);

  /**
   * What stands instead of the preview when a choice cannot be sent: {text}. No station ticked is a state, not a
   * failure; another reason from the page stands as it is.
   */
  const ofDraft = ({ empty: none, reason }) => ({ text: none ? empty() : String(reason) });

  /**
   * What stands instead of the preview after a request failed (an Error as App.senden throws it): {text} and, where
   * there is a next step, `link` (Meine Angaben), `reload` («Neu laden») or `details` (the raw message under
   * «Genauer»). `say` gives the words of the person's text set.
   */
  function problem(error, say) {
    const action = error && error.daten ? error.daten.aktion : undefined;
    if (action === CHECK_DATA) return { text: unreadable(), link: true, details: error.message };
    if (action === REOPEN) return { text: say("lebenslauf.vorschau-geaendert"), reload: true };
    if (!error || !error.status || error.status >= 500) return { text: unreachable() };
    return { text: Texte.t("Die Vorschau lässt sich nicht erstellen. {grund}", { grund: error.message }) };
  }

  const pageAlt = (page, pages) => Texte.t("Lebenslauf, Seite {seite} von {seiten}", { seite: page, seiten: pages });

  /**
   * What the live region says when the preview goes from `before` to `after` ({pages} or {failed}). The picture
   * changes with every keystroke; only what the person would miss without looking is said: a new page count, a
   * failure, and that it works again. The first preview after opening is read where it stands.
   */
  function announcement(before, after) {
    if (after.failed) return before && before.failed === after.failed ? "" : after.failed;
    if (!before) return "";
    if (before.failed) return Texte.t("Die Vorschau ist wieder da, {seiten}.", { seiten: pagesText(after.pages) });
    return before.pages === after.pages ? "" : Texte.t("Die Vorschau hat jetzt {seiten}.", { seiten: pagesText(after.pages) });
  }

  const logic = { DELAY_MS, CHECK_DATA, REOPEN, get NOT_SHOWN() { return notShown(); }, title, ofDraft, problem, pageAlt,
                  announcement };
  if (typeof module !== "undefined") module.exports = logic;
  else global.LebenslaufVorschauLogik = logic;
})(typeof window !== "undefined" ? window : globalThis);
