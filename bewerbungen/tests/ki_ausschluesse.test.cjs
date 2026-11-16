"use strict";
// Exclusion reasons the AI proposes from dismissed hits on Suche einstellen (#319, G86): the words of the box,
// without DOM. Counts and hits come from the app (routes_ai_exclusions.py); the AI only names the reason.
const test = require("node:test");
const assert = require("node:assert/strict");
const L = require("../seiten/ki-ausschluesse-logik.js");
const Texte = require("../seiten/texte.js");
const TrefferLogik = require("../seiten/treffer-logik.js");

const STAND = { verfuegbar: true, anzahl: 5, mindestens: 3, kosten: 0.02, waehrung: "CHF", guthaben: 4.5,
  danach: 4.48, dauer_minuten: 1, reicht_fuer: null };
const TREFFER = [
  { id: "a", stelle: "Python Entwickler Detailhandel", firma: "Muster Detail AG", ort: "Lyss", pensum: "60%" },
  { id: "b", stelle: "Web Entwickler Detailhandel", firma: "Probe Laden AG", ort: "", pensum: "" },
];
const VORSCHLAG = { nummer: 1, art: "ausschluss", ort: "Im Inserat", kategorie: "Branche", wert: "Detailhandel",
  grund: "Zwei Stellen sind im Detailhandel.", treffer: TREFFER };

test("with enough dismissed hits the box names their count and what goes to the AI, in the address of the set", () => {
  assert.equal(L.zuWenige(STAND), false);
  assert.equal(L.einleitung(STAND, "stelle-sie", Texte),
    "Die KI sucht in den 5 Stellen, die Sie verworfen haben, nach gemeinsamen Gründen, etwa Pensum, Branche, "
    + "Arbeitsort oder Wörter im Titel. Ins Suchprofil kommt nur, was Sie übernehmen.");
  assert.equal(L.einleitung(STAND, "stelle-du", Texte),
    "Die KI sucht in den 5 Stellen, die du verworfen hast, nach gemeinsamen Gründen, etwa Pensum, Branche, "
    + "Arbeitsort oder Wörter im Titel. Ins Suchprofil kommt nur, was du übernimmst.");
  assert.match(L.WAS_GEHT, /^Nur Titel, Firma, Ort und Pensum der verworfenen Stellen\./);
});

test("with too few dismissed hits the box says how many it takes and offers no AI", () => {
  for (const anzahl of [0, 1, 2]) assert.equal(L.zuWenige({ ...STAND, anzahl }), true);
  assert.equal(L.leer({ ...STAND, anzahl: 0 }, "stelle-sie", Texte),
    "Noch keine verworfenen Stellen. Ab 3 verworfenen Stellen kann die KI hier vorschlagen, "
    + "was Sie künftig nicht mehr sehen wollen.");
  assert.equal(L.leer({ ...STAND, anzahl: 1 }, "stelle-du", Texte),
    "Erst 1 verworfene Stelle. Ab 3 verworfenen Stellen kann die KI hier vorschlagen, "
    + "was du künftig nicht mehr sehen willst.");
  assert.match(L.leer({ ...STAND, anzahl: 2 }, "stelle-sie", Texte), /^Erst 2 verworfene Stellen\./);
});

test("the cost line is the one of „Alle prüfen“, with the request link once the credit is used up", () => {
  assert.equal(L.kosten(STAND, TrefferLogik), "Etwa CHF 0.02 und 1 Minute. Danach bleiben CHF 4.48 im Guthaben.");
  assert.equal(L.kosten({ ...STAND, guthaben: 0, danach: 0 }, TrefferLogik),
    "Etwa CHF 0.02 und 1 Minute. Das Guthaben ist aufgebraucht: neuen Code anfordern.");
  assert.equal(L.kosten({ ...STAND, waehrung: "USD", guthaben: null, danach: null }, TrefferLogik), "Etwa USD 0.02 und 1 Minute.");
});

test("each proposal names the hits it rests on", () => {
  assert.equal(L.stuetze(VORSCHLAG), "Aus 2 verworfenen Stellen:");
  assert.equal(L.stuetze({ ...VORSCHLAG, treffer: [...TREFFER, { ...TREFFER[0], id: "c" }] }), "Aus 3 verworfenen Stellen:");
  assert.equal(L.trefferZeile(TREFFER[0]), "Python Entwickler Detailhandel – Muster Detail AG, Lyss, 60%");
  assert.equal(L.trefferZeile(TREFFER[1]), "Web Entwickler Detailhandel – Probe Laden AG");
  assert.equal(L.wo(VORSCHLAG), "Branche, kommt unter «Im Inserat»");
});

test("the button says what it adopts, and the feedback where it went and when it counts", () => {
  assert.equal(L.KNOPF, "Übernehmen");
  assert.equal(L.knopfLabel(VORSCHLAG), "«Detailhandel» übernehmen");
  assert.equal(L.uebernommen(VORSCHLAG), "«Detailhandel» steht jetzt unter «Im Inserat». Gilt ab der nächsten Einschätzung.");
  assert.equal(L.uebernommen({ ...VORSCHLAG, art: "titel_ausschluss", ort: "Im Titel", wert: "Aussendienst" }),
    "«Aussendienst» steht jetzt unter «Im Titel». Gilt ab der nächsten Suche.");
  assert.equal(L.zurueck(VORSCHLAG), "«Detailhandel» steht nicht mehr unter «Im Inserat».");
});

test("the result says how many proposals came and that nothing changed yet", () => {
  assert.equal(L.fertig(0, "stelle-sie", Texte), "Die KI hat keinen gemeinsamen Grund gefunden. Am Suchprofil hat sich nichts geändert.");
  assert.equal(L.fertig(1, "stelle-sie", Texte), "1 Vorschlag. Am Suchprofil ändert sich erst etwas, wenn Sie ihn übernehmen.");
  assert.equal(L.fertig(2, "stelle-du", Texte),"2 Vorschläge. Am Suchprofil ändert sich erst etwas, wenn du einen übernimmst.");
});
