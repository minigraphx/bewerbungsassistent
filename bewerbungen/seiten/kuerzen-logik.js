"use strict";
// Cut with one click or allow three pages, for this application only (G92, #323, option A item 1 in
// docs/design/seiten-ausgleichen.md), without DOM: the rows to tick under the finding of a CV over its limit, the
// buttons with the main one first, what goes to /api/kuerzungen, and what the step Lebenslauf lists as left out
// (tests/kuerzen_logik.test.cjs). There is no «So lassen» for the CV while a cut or three pages are left (#330).
(function (global) {
  // Texts in the app language through Texte (#428); the page's Texte is found when a text is made.
  const texts = () => (typeof module !== "undefined" ? require("./texte.js") : global.Texte);
  const Texte = { t: (deutsch, werte) => texts().t(deutsch, werte) };
  const legend = () => Texte.t("Für diese Bewerbung weglassen");
  const main = () => Texte.t("Gekürzt neu erstellen");
  const three = () => Texte.t("Drei Seiten erlauben");
  const nextTitle = () => Texte.t("Lebenslauf kürzen");
  const notEnough = () => Texte.t("Der Lebenslauf ist noch zu lang; die nächste Kürzung ist angehakt.");
  const noneLeft = () => Texte.t("Der Lebenslauf ist noch zu lang; weiter kürzen lässt sich mit «Lebenslauf erstellen» oder unter «Meine Angaben».");
  const SENTENCE_ID = "befund-kuerzen-satz";  // names the finding without the rows and buttons in it
  const THREE_ID = "drei-seiten";  // cut_choice.THREE_PAGES
  const leftOutTitle = () => Texte.t("Für diese Bewerbung weggelassen");
  // Whole sentences, so each language says what was done in its own order.
  const DONE = {
    kuerzen: () => Texte.t("Gekürzt und neu erstellt."),
    "drei-seiten": () => Texte.t("Drei Seiten erlaubt und neu erstellt."),
    zurueck: () => Texte.t("Zurückgeholt und neu erstellt."),
  };

  /** The cuts as rows to tick; the first is preselected. */
  function rows(kuerzen) {
    return ((kuerzen && kuerzen.optionen) || []).map((option, index) => ({ id: option.id, text: option.text, checked: index === 0 }));
  }

  /** The buttons in order: «Gekürzt neu erstellen» first and primary, «Drei Seiten erlauben» where it is offered. */
  function buttons(kuerzen) {
    const list = [];
    if (rows(kuerzen).length) list.push({ action: "kuerzen", text: main(), primary: true });
    if (kuerzen && kuerzen.drei_seiten) list.push({ action: THREE_ID, text: three(), primary: list.length === 0 });
    return list;
  }

  /** The body for /api/kuerzungen; null when nothing is ticked, so nothing is sent. */
  function body(id, action, ticked) {
    if (action === THREE_ID) return { id, drei_seiten: true };
    return ticked.length ? { id, weglassen: [...ticked] } : null;
  }

  /** What the step Lebenslauf lists as left out: each cut with «Zurückholen». */
  function leftOut(kuerzungen) {
    return ((kuerzungen && kuerzungen.weggelassen) || []).map(entry => ({ id: entry.id, text: entry.text, button: Texte.t("Zurückholen") }));
  }

  /** Three pages are allowed, not left out: a line of its own under the list, with «Zurücknehmen»; else null. */
  function threePages(kuerzungen) {
    return kuerzungen && kuerzungen.drei_seiten
      ? { id: THREE_ID, text: Texte.t("Drei Seiten erlaubt, nur für diese Bewerbung."), button: Texte.t("Zurücknehmen") } : null;
  }

  /** Whether the check still finds the CV over its limit, with cuts to tick. */
  const stillOver = befunde => (befunde || []).some(befund => Boolean(befund.kuerzen));

  /** Whether the CV is still over its limit with three pages allowed and no cut left, not yet confirmed (#330). */
  const noCutLeft = befunde => (befunde || []).some(befund => Boolean(befund.cv_over) && !befund.bestaetigt);

  /**
   * The message after the route answered; stored all the same when the build could not run. A cut that was not
   * enough names the next cut ticked (`over`) or, with none left, where it can still be cut (`noneLeft`).
   */
  function doneMessage(action, answer, over, nothingLeft = false) {
    if (!answer.neu_erstellt) return Texte.t("Gespeichert, aber nicht neu erstellt: {fehler}", { fehler: answer.fehler });
    const still = action !== "kuerzen" ? "" : over ? ` ${notEnough()}` : nothingLeft ? ` ${noneLeft()}` : "";
    return `${DONE[action]()}${still}`;
  }

  /** A cut that was not enough is a hint like a build that could not run; all else went as asked. */
  function doneLevel(action, answer, over, noneLeft = false) {
    return answer.neu_erstellt && !(action === "kuerzen" && (over || noneLeft)) ? "ok" : "hinweis";
  }

  // The texts are read when shown, so they follow the language of the page.
  const logik = { get LEGEND() { return legend(); }, get MAIN() { return main(); }, get THREE() { return three(); },
    get NEXT_TITLE() { return nextTitle(); }, get LEFT_OUT_TITLE() { return leftOutTitle(); }, THREE_ID, SENTENCE_ID, rows,
    buttons, body, leftOut, threePages, stillOver, noCutLeft, doneMessage, doneLevel };
  if (typeof module !== "undefined") module.exports = logik;
  else global.KuerzenLogik = logik;
})(typeof window !== "undefined" ? window : globalThis);
