"use strict";
// The page Bewerbungen (#261, A5): discarding the ticked applications in one step (G29), the column Bis wann and the
// view from the address. Rows come from UebersichtLogik.mitSchritten. No DOM, so it can be tested
// (tests/bewerbungen_seite.test.cjs). Texts in the app language through Texte.t (#420,
// tests/applications_languages.test.cjs).
(function (global) {
  const L = typeof module !== "undefined" ? require("./uebersicht-logik.js") : global.UebersichtLogik;
  // Loaded before this file on every page; required in the tests.
  const texts = () => (typeof module !== "undefined" ? require("./texte.js") : global.Texte);

  // The same ends as the button on the application (bewerbung-logik.beenden): before sending it is discarded,
  // after it withdrawn. A finished application stays as it is.
  const END_STAGE = { Gemerkt: "Verworfen", Bewerben: "Verworfen", Beworben: "Zurückgezogen", "Gespräch": "Zurückgezogen" };
  const VIEWS = ["gemerkt", "beworben", "abgeschlossen", "alle"];
  const NO_DATE = "–";

  function applications(count) {
    const Texte = texts();
    return count === 1 ? Texte.t("1 Bewerbung") : Texte.t("{anzahl} Bewerbungen", { anzahl: count });
  }

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
    const Texte = texts();
    return Texte.t("{bewerbungen} verwerfen?", { bewerbungen: applications(discardCount(plan)) });
  }

  /** What the question adds: which ones are withdrawn rather than discarded, and which stay. */
  function discardNotes(plan) {
    const Texte = texts();
    const withdrawn = plan["Zurückgezogen"].length;
    const kept = plan.kept.length;
    return [
      withdrawn === 1 ? Texte.t("1 schon verschickte wird zurückgezogen.") : "",
      withdrawn > 1 ? Texte.t("{anzahl} schon verschickte werden zurückgezogen.", { anzahl: withdrawn }) : "",
      kept === 1 ? Texte.t("1 abgeschlossene bleibt, wie sie ist.") : "",
      kept > 1 ? Texte.t("{anzahl} abgeschlossene bleiben, wie sie sind.", { anzahl: kept }) : "",
    ].filter(Boolean);
  }

  function discardDone(plan) {
    const Texte = texts();
    const discarded = plan.Verworfen.length;
    const withdrawn = plan["Zurückgezogen"].length;
    if (!discarded) {
      return withdrawn === 1 ? Texte.t("1 Bewerbung zurückgezogen.")
        : Texte.t("{anzahl} Bewerbungen zurückgezogen.", { anzahl: withdrawn });
    }
    if (!withdrawn) {
      return discarded === 1 ? Texte.t("1 Bewerbung verworfen.")
        : Texte.t("{anzahl} Bewerbungen verworfen.", { anzahl: discarded });
    }
    const zurueckgezogen = withdrawn === 1 ? Texte.t("1 zurückgezogen") : Texte.t("{anzahl} zurückgezogen", { anzahl: withdrawn });
    return discarded === 1 ? Texte.t("1 Bewerbung verworfen, {zurueckgezogen}.", { zurueckgezogen })
      : Texte.t("{anzahl} Bewerbungen verworfen, {zurueckgezogen}.", { anzahl: discarded, zurueckgezogen });
  }

  function selectionHint(count) {
    const Texte = texts();
    if (count <= 0) return Texte.t("Zuerst Bewerbungen anhaken.");
    return count === 1 ? Texte.t("1 angehakt") : Texte.t("{anzahl} angehakt", { anzahl: count });
  }

  /** The column Bis wann: the deadline or the date of the interview, the day to follow up, or a dash. */
  function dueText({ bewerbung: b, schritt }) {
    const Texte = texts();
    if (schritt.frist) return L.datum(schritt.frist);
    if (schritt.art === "warten" && schritt.zusatz) return Texte.t("nachfragen ab {datum}", { datum: L.datum(schritt.zusatz) });
    if (b.status === "Gespräch") return Texte.t("offen");
    return NO_DATE;
  }

  /** The column heads as each cell repeats them on a narrow screen (data-label). */
  function columnLabels() {
    const Texte = texts();
    return { stand: Texte.t("Stand"), note: Texte.t("Note"), schritt: Texte.t("Nächster Schritt"), bis: Texte.t("Bis wann"),
             erfasst: Texte.t("Erfasst"), geaendert: Texte.t("Stand geändert") };
  }

  /** The texts of a row besides its title and grade: { stand, schritt, bis, erfasst, geaendert } in the set `satz`.
   *  Entries from before G135 have no date of a change of stage: an empty cell, like Erfasst without a date. */
  function rowTexts(row, satz) {
    const Texte = texts();
    const step = L.schrittText(row.schritt, 1, (key, values) => Texte.text(key, satz, values));
    return { stand: Texte.statusName(row.bewerbung.status, satz), schritt: step.titel || NO_DATE, bis: dueText(row),
             erfasst: L.datum(row.bewerbung.eingetragen_am), geaendert: L.datum(row.bewerbung.stand_geaendert_am) };
  }

  // Grade 1–6 as in the design: value, six bars, a word
  function gradeWord(grade) {
    const Texte = texts();
    if (grade >= 5.5) return Texte.t("passt sehr gut");
    if (grade >= 4.5) return Texte.t("passt gut");
    return grade >= 4 ? Texte.t("passt knapp") : Texte.t("passt wenig");
  }

  function gradeLabel(grade) {
    const Texte = texts();
    return Texte.t("Note {note} von 6, {wort}", { note: Texte.notenText(grade), wort: gradeWord(grade) });
  }

  function noGrade() {
    const Texte = texts();
    return Texte.t("keine Note");
  }

  /** A view named in the address (#gemerkt), or null to keep the stored one. */
  function viewFromHash(hash) {
    const name = typeof hash === "string" ? hash.replace(/^#/, "") : "";
    return VIEWS.includes(name) ? name : null;
  }

  const logic = { discardPlan, discardCount, discardQuestion, discardNotes, discardDone, selectionHint, dueText, viewFromHash,
                  columnLabels, rowTexts, gradeWord, gradeLabel, noGrade };
  if (typeof module !== "undefined") module.exports = logic;
  else global.BewerbungenLogic = logic;
})(typeof window !== "undefined" ? window : globalThis);
