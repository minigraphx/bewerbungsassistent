"use strict";
// Cut with one click or allow three pages, for this application only (G92, #323, option A item 1 in
// docs/design/seiten-ausgleichen.md), without DOM: the rows to tick under the finding of a CV over its limit, the
// buttons with the main one first, what goes to /api/kuerzungen, and what the step Lebenslauf lists as left out
// (tests/kuerzen_logik.test.cjs). There is no «So lassen» for the CV.
(function (global) {
  const LEGEND = "Für diese Bewerbung weglassen";
  const MAIN = "Gekürzt neu erstellen";
  const THREE = "Drei Seiten erlauben";
  const NEXT_TITLE = "Lebenslauf kürzen";
  const BRING_BACK = "Zurückholen";
  const TAKE_BACK = "Zurücknehmen";
  const THREE_ALLOWED = "Drei Seiten erlaubt, nur für diese Bewerbung.";
  const NOT_ENOUGH = "Der Lebenslauf ist noch zu lang; die nächste Kürzung ist angehakt.";
  const SENTENCE_ID = "befund-kuerzen-satz";  // names the finding without the rows and buttons in it
  const THREE_ID = "drei-seiten";  // cut_choice.THREE_PAGES
  const LEFT_OUT_TITLE = "Für diese Bewerbung weggelassen";
  const DONE = { kuerzen: "Gekürzt", "drei-seiten": "Drei Seiten erlaubt", zurueck: "Zurückgeholt" };

  /** The cuts as rows to tick; the first is preselected. */
  function rows(kuerzen) {
    return ((kuerzen && kuerzen.optionen) || []).map((option, index) => ({ id: option.id, text: option.text, checked: index === 0 }));
  }

  /** The buttons in order: «Gekürzt neu erstellen» first and primary, «Drei Seiten erlauben» where it is offered. */
  function buttons(kuerzen) {
    const list = [];
    if (rows(kuerzen).length) list.push({ action: "kuerzen", text: MAIN, primary: true });
    if (kuerzen && kuerzen.drei_seiten) list.push({ action: THREE_ID, text: THREE, primary: list.length === 0 });
    return list;
  }

  /** The body for /api/kuerzungen; null when nothing is ticked, so nothing is sent. */
  function body(id, action, ticked) {
    if (action === THREE_ID) return { id, drei_seiten: true };
    return ticked.length ? { id, weglassen: [...ticked] } : null;
  }

  /** What the step Lebenslauf lists as left out: each cut with «Zurückholen». */
  function leftOut(kuerzungen) {
    return ((kuerzungen && kuerzungen.weggelassen) || []).map(entry => ({ id: entry.id, text: entry.text, button: BRING_BACK }));
  }

  /** Three pages are allowed, not left out: a line of its own under the list, with «Zurücknehmen»; else null. */
  function threePages(kuerzungen) {
    return kuerzungen && kuerzungen.drei_seiten ? { id: THREE_ID, text: THREE_ALLOWED, button: TAKE_BACK } : null;
  }

  /** Whether the check still finds the CV over its limit, with cuts to tick. */
  const stillOver = befunde => (befunde || []).some(befund => Boolean(befund.kuerzen));

  /** The message after the route answered; stored all the same when the build could not run. */
  function doneMessage(action, answer, over) {
    if (!answer.neu_erstellt) return `Gespeichert, aber nicht neu erstellt: ${answer.fehler}`;
    return `${DONE[action]} und neu erstellt.${action === "kuerzen" && over ? ` ${NOT_ENOUGH}` : ""}`;
  }

  /** A cut that was not enough is a hint like a build that could not run; all else went as asked. */
  function doneLevel(action, answer, over) {
    return answer.neu_erstellt && !(action === "kuerzen" && over) ? "ok" : "hinweis";
  }

  const logik = { LEGEND, MAIN, THREE, NEXT_TITLE, LEFT_OUT_TITLE, THREE_ID, SENTENCE_ID, rows, buttons, body, leftOut,
    threePages, stillOver, doneMessage, doneLevel };
  if (typeof module !== "undefined") module.exports = logik;
  else global.KuerzenLogik = logik;
})(typeof window !== "undefined" ? window : globalThis);
