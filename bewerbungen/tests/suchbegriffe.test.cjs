// Checking the search terms (#210): how the page words the numbers of the app, without DOM.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const L = require("../seiten/suchbegriffe-logik.js");

const BELEG = { begriff: "Engineer", anzahl: 56, unter: 47, alle: 130, beispiele: ["EMSR-Engineer", "Process Engineer"] };

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
    "Die KI hat Ihr Suchprofil, Ihren Lebenslauf und 130 Treffer seit dem 20.10.2026 angesehen. Geändert wird nur, was eingeschaltet ist.");
  assert.equal(L.texte("stelle-du").gesehen(130, null),
    "Die KI hat dein Suchprofil, deinen Lebenslauf und 130 Treffer angesehen. Geändert wird nur, was eingeschaltet ist.");
  assert.equal(L.texte("stelle-sie").gesehen(0, null),
    "Die KI hat Ihr Suchprofil und Ihren Lebenslauf angesehen. Geändert wird nur, was eingeschaltet ist.");
  assert.equal(L.texte("stelle-du").gesehen(0, null),
    "Die KI hat dein Suchprofil und deinen Lebenslauf angesehen. Geändert wird nur, was eingeschaltet ist.");
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

test("the heading and the round line come as parts, so the page can glue each «·» to the part before it (#340)", () => {
  assert.deepEqual(L.kopfTeile(1), ["Vorschlag der KI", "1 Änderung"]);
  assert.deepEqual(L.kopfTeile(5), ["Vorschlag der KI", "5 Änderungen"]);
  assert.deepEqual(L.rundeTeile({ runde: 2 }, "stelle-sie"), ["Vorschlag 2", "nach Ihrem Hinweis"]);
  assert.deepEqual(L.rundeTeile({ runde: 3 }, "stelle-du"), ["Vorschlag 3", "nach deinem Hinweis"]);
  assert.deepEqual(L.rundeTeile({ runde: 1 }, "stelle-sie"), [], "the first proposal has no round line");
});
