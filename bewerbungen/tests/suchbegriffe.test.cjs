// Checking the search terms (#210): how the page words the numbers of the app, without DOM.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const L = require("../seiten/suchbegriffe-logik.js");

const BELEG = { begriff: "Engineer", anzahl: 56, unter: 47, alle: 130, beispiele: ["EMSR-Engineer", "Process Engineer"] };

test("the main button counts what is ticked", () => {
  assert.equal(L.hauptknopf(5, 5), "Alle 5 übernehmen");
  assert.equal(L.hauptknopf(4, 5), "4 von 5 übernehmen");
  assert.equal(L.hauptknopf(1, 1), "Änderung übernehmen");
  assert.equal(L.hauptknopf(0, 5), "Übernehmen");
});

test("the hint and the evidence use the numbers of the app", () => {
  assert.equal(L.hinweisText(BELEG), "«Engineer» im Titelfilter: 56 von 130 Treffern, 47 davon unter Note 4, zum Beispiel EMSR-Engineer, Process Engineer.");
  assert.equal(L.belegSatz(BELEG), "56 von 130 Treffern kamen nur über «Engineer» herein, 47 davon unter Note 4.");
  assert.equal(L.belegLink(BELEG), "Diese 56 Treffer ansehen");
  assert.deepEqual(L.balken(BELEG), { anteil: 43, unter: 84 });
});

test("the link to the evidence finds its term again, and nothing else", () => {
  assert.equal(L.belegAusAdresse(new URL(L.belegAdresse({ ...BELEG, begriff: "Full Stack & Co" }), "http://x").hash), "Full Stack & Co");
  assert.equal(L.belegAusAdresse("#andere"), null);
  assert.equal(L.belegAusAdresse("#beleg=%E0%A4%A"), null);
});

test("every mark carries its word, not only a colour", () => {
  const marken = L.marken({ entfaellt: ["Engineer"], neu: ["Backend", "Frontend"] });
  assert.deepEqual(marken.map(m => `${m.begriff}, ${m.wort}`), ["Engineer, entfällt", "Backend, neu", "Frontend, neu"]);
});

test("the result marks new terms and ignores case", () => {
  const jetzt = { suchbegriffe: ["Python"], positiv: ["Engineer", "Web"], ausschluss: [] };
  const danach = { suchbegriffe: ["python", "Fullstack Entwickler"], positiv: ["Web", "Backend"], ausschluss: ["Verkauf"] };
  const bloecke = L.endstand(jetzt, danach);
  assert.deepEqual(bloecke.map(b => b.begriffe.filter(x => x.neu).map(x => x.begriff)), [["Fullstack Entwickler"], ["Backend"], ["Verkauf"]]);
});

test("Sie and du, costs never under a cent", () => {
  assert.match(L.texte("stelle-du").satz, /du entscheidest/);
  assert.match(L.texte("stelle-sie").satz, /Sie entscheiden/);
  assert.equal(L.texte("stelle-sie").gesehen(130, "2026-10-20"),
    "Die KI hat Ihr Suchprofil, Ihren Lebenslauf und 130 Treffer seit dem 20.10.2026 angesehen. Geändert wird nur, was angehakt ist.");
  // #337: the footer comes as parts, so the page can glue each «·» to the part before it
  assert.deepEqual(L.fussTeile({ modell: "claude-haiku-5-5", kosten_usd: 0.004, datum: "2026-11-11", runde: 2, kosten_bisher: 0.008 }),
    ["Claude", "USD\u00a00.01", "11.11.2026", "bisher USD\u00a00.01"]);
  assert.deepEqual(L.fussTeile({ modell: "claude-sonnet-5-5", kosten_usd: 0.03, waehrung: "CHF", datum: "2026-11-16", runde: 1 }),
    ["Claude", "CHF\u00a00.03", "16.11.2026"]);
  assert.deepEqual(L.fussTeile({ modell: "claude-sonnet-5-5", kosten_usd: 0.02, waehrung: "CHF", datum: "2026-11-16", runde: 2,
    kosten_bisher: 0.05 }), ["Claude", "CHF\u00a00.02", "16.11.2026", "bisher CHF\u00a00.05"]);
  assert.deepEqual(L.fussTeile({ kosten_usd: 0.02, waehrung: "CHF", datum: "2026-11-16", runde: 1 }), ["CHF\u00a00.02", "16.11.2026"],
    "without a model no empty part");
});
