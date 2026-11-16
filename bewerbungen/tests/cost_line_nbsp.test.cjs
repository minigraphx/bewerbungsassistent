// Cost lines keep number and unit together (#336, G45): at 375 px «und 1 Minute» broke between «1» and «Minute».
// Only the amount with its currency and the minutes with their unit are joined; the rest of the sentence still wraps,
// and with each no-break space read as a space the words are the ones from before. Invented numbers only.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const logik = require("../seiten/treffer-logik.js");
const texte = require("../seiten/texte.js");

const NBSP = "\u00a0";
const MEDIATION = { anzahl: 1, kosten: 0.03, dauer_minuten: 1, guthaben: 4.25, danach: 4.22, reicht_fuer: null, waehrung: "CHF" };
const OWN_KEY = { ...MEDIATION, dauer_minuten: 3, guthaben: null, danach: null, waehrung: "USD" };

const spoken = text => text.replaceAll(NBSP, " ");
const joined = text => [...text.matchAll(/\S+\u00a0\S+/g)].map(found => found[0]);
// A plain space between a number and its unit is where the line could still break.
const breakable = text => /(CHF|USD) \d|\d (Minute|Minuten)\b/.test(text);

test("the estimate joins currency and amount, minutes and unit, with a no-break space", () => {
  const line = logik.estimateLine(MEDIATION);
  assert.deepEqual(joined(line), [`CHF${NBSP}0.03`, `1${NBSP}Minute.`, `CHF${NBSP}4.22`]);
  assert.equal(breakable(line), false);
  assert.deepEqual(joined(logik.estimateLine(OWN_KEY)), [`USD${NBSP}0.03`, `3${NBSP}Minuten.`]);
});

test("every case of the cost line keeps number and unit together", () => {
  const cases = [MEDIATION, OWN_KEY, { ...MEDIATION, guthaben: 0.01, danach: 0 }, { ...MEDIATION, guthaben: 0, danach: 0 },
    { ...MEDIATION, anzahl: 3, reicht_fuer: 2 }];
  for (const estimate of cases) {
    const { text } = logik.costLine(estimate);
    assert.ok(text.includes(NBSP), text);
    assert.equal(breakable(text), false, text);
  }
  assert.deepEqual(joined(logik.costLine({ ...MEDIATION, guthaben: 0.01, danach: 0 }).text),
    [`CHF${NBSP}0.03`, `1${NBSP}Minute.`, `CHF${NBSP}0.01,`]);
});

test("read aloud, the cost line says the same words as before", () => {
  assert.equal(spoken(logik.costLine(OWN_KEY).text), "Etwa USD 0.03 und 3 Minuten.");
  assert.equal(spoken(logik.costLine(MEDIATION).text), "Etwa CHF 0.03 und 1 Minute. Danach bleiben CHF 4.22 im Guthaben.");
  assert.equal(spoken(logik.costLine({ ...MEDIATION, guthaben: 0.01, danach: 0 }).text),
    "Etwa CHF 0.03 und 1 Minute. Im Guthaben sind noch CHF 0.01, das reicht vielleicht nicht.");
  assert.equal(spoken(logik.estimateLine({ ...MEDIATION, anzahl: 3, reicht_fuer: 2 })),
    "Etwa CHF 0.03 und 1 Minute. Das Guthaben reicht für etwa 2 Stellen.");
});

test("only number and unit are joined, the rest of the sentence still wraps", () => {
  const line = logik.costLine({ ...MEDIATION, guthaben: 0, danach: 0 }).text;
  assert.equal(line.split(NBSP).length - 1, 2);
  assert.match(line, / und 1\u00a0Minute\. Das Guthaben ist aufgebraucht: neuen Code anfordern\.$/);
});

test("the used-up line keeps its request link with the joined units", () => {
  const el = (tag, attrs, ...children) => ({ tag, attrs, children });
  const parts = texte.withCodeRequestLink(logik.estimateLine({ ...MEDIATION, guthaben: 0, danach: 0 }), el);
  assert.equal(parts[0], `Etwa CHF${NBSP}0.03 und 1${NBSP}Minute. Das Guthaben ist aufgebraucht: neuen Code `);
  assert.equal(parts[1].children[0], "anfordern");
});
