"use strict";
// The page Bewerbungen (#261, A5): discarding the ticked applications in one step (G29), the column Bis wann and the
// view from the address. Rows come from UebersichtLogik.mitSchritten. No DOM, so it can be tested
// (tests/bewerbungen_seite.test.cjs).
(function (global) {
  const L = typeof module !== "undefined" ? require("./uebersicht-logik.js") : global.UebersichtLogik;

  // The same ends as the button on the application (bewerbung-logik.beenden): before sending it is discarded,
  // after it withdrawn. A finished application stays as it is.
  const END_STAGE = { Gemerkt: "Verworfen", Bewerben: "Verworfen", Beworben: "Zurückgezogen", "Gespräch": "Zurückgezogen" };
  const VIEWS = ["gemerkt", "beworben", "abgeschlossen", "alle"];
  const NO_DATE = "–";

  const applications = count => (count === 1 ? "1 Bewerbung" : `${count} Bewerbungen`);

  /** The ticked ids by the stage that ends them: { Verworfen, Zurückgezogen, kept }, each in the order of the rows. */
  function discardPlan(rows, ids) {
    const ticked = new Set(ids);
    const plan = { Verworfen: [], "Zurückgezogen": [], kept: [] };
    for (const { bewerbung: b } of rows) {
      if (!ticked.has(b.id)) continue;
      const stage = END_STAGE[b.status];
      plan[stage || "kept"] = [...plan[stage || "kept"], b.id];
    }
    return plan;
  }

  const discardCount = plan => plan.Verworfen.length + plan["Zurückgezogen"].length;

  function discardQuestion(plan) {
    return `${applications(discardCount(plan))} verwerfen?`;
  }

  /** What the question adds: which ones are withdrawn rather than discarded, and which stay. */
  function discardNotes(plan) {
    const withdrawn = plan["Zurückgezogen"].length;
    const kept = plan.kept.length;
    return [
      withdrawn ? `${withdrawn} schon ${withdrawn === 1 ? "verschickte wird" : "verschickte werden"} zurückgezogen.` : "",
      kept ? `${kept} ${kept === 1 ? "abgeschlossene bleibt, wie sie ist" : "abgeschlossene bleiben, wie sie sind"}.` : "",
    ].filter(Boolean);
  }

  function discardDone(plan) {
    const discarded = plan.Verworfen.length;
    const withdrawn = plan["Zurückgezogen"].length;
    if (!discarded) return `${applications(withdrawn)} zurückgezogen.`;
    return `${applications(discarded)} verworfen${withdrawn ? `, ${withdrawn} zurückgezogen` : ""}.`;
  }

  function selectionHint(count) {
    return count > 0 ? `${count} angehakt` : "Zuerst Bewerbungen anhaken.";
  }

  /** The column Bis wann: the deadline or the date of the interview, the day to follow up, or a dash. */
  function dueText({ bewerbung: b, schritt }) {
    if (schritt.frist) return L.datum(schritt.frist);
    if (schritt.art === "warten" && schritt.zusatz) return `nachfragen ab ${L.datum(schritt.zusatz)}`;
    if (b.status === "Gespräch") return "offen";
    return NO_DATE;
  }

  /** A view named in the address (#gemerkt), or null to keep the stored one. */
  function viewFromHash(hash) {
    const name = typeof hash === "string" ? hash.replace(/^#/, "") : "";
    return VIEWS.includes(name) ? name : null;
  }

  const logic = { discardPlan, discardCount, discardQuestion, discardNotes, discardDone, selectionHint, dueText, viewFromHash };
  if (typeof module !== "undefined") module.exports = logic;
  else global.BewerbungenLogic = logic;
})(typeof window !== "undefined" ? window : globalThis);
