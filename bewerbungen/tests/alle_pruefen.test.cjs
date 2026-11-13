// „Alle prüfen“ on Stellen (G44, #209): the line above the list, the question before the run and the words after it,
// from the estimate of GET /api/suche/alle-pruefen. Invented numbers only.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const logik = require("../seiten/treffer-logik.js");

const read = name => fs.readFileSync(path.join(__dirname, "..", "seiten", name), "utf8");
const ESTIMATE = { anzahl: 2, kosten_usd: 0.06, dauer_minuten: 1, laden: [], nicht_ladbar: [], budget_usd: 6.8, danach_usd: 6.74, reicht_fuer: null };

test("the line above the list names cost, duration and the budget afterwards, as in the design", () => {
  assert.equal(logik.estimateLine(ESTIMATE), "Etwa USD 0.06 und 1 Minute. Danach bleiben USD 6.74 im Budget.");
  assert.equal(logik.estimateLine({ ...ESTIMATE, dauer_minuten: 3, budget_usd: null, danach_usd: null }), "Etwa USD 0.06 und 3 Minuten.");
  assert.equal(logik.estimateLine({ ...ESTIMATE, reicht_fuer: 1, danach_usd: 0 }), "Etwa USD 0.06 und 1 Minute. Das Budget reicht für etwa 1 Stelle.");
  assert.equal(logik.estimateLine(null), "");
});

test("the question before the run names number, cost, budget and duration", () => {
  const question = logik.confirmation({ ...ESTIMATE, anzahl: 12, kosten_usd: 0.35, dauer_minuten: 3, budget_usd: 6.8, danach_usd: 6.45 }, false, true);
  assert.equal(question.title, "12 Stellen prüfen?");
  assert.deepEqual(question.sentences, [
    "Die KI prüft 12 Stellen, die noch keine Note haben.",
    "Das kostet etwa USD 0.35 und dauert etwa 3 Minuten.",
    "Im Budget sind noch USD 6.80, danach etwa USD 6.45.",
  ]);
  assert.equal(question.warning, "");
  assert.deepEqual(question.notLoadable, []);
  assert.equal(logik.confirmation({ ...ESTIMATE, anzahl: 1 }, true, true).title, "1 Lehrstelle prüfen?");
});

test("without a budget to name, the question leaves the budget out", () => {
  const question = logik.confirmation({ ...ESTIMATE, budget_usd: null, danach_usd: null }, false, true);
  assert.equal(question.sentences.length, 2);
});

test("a budget too small is a warning that the run stops when it is used up", () => {
  const question = logik.confirmation({ ...ESTIMATE, anzahl: 20, budget_usd: 0.1, danach_usd: 0, reicht_fuer: 4 }, false, true);
  assert.equal(question.warning, "Das Budget von USD 0.10 reicht für etwa 4 von 20 Stellen. Ist es aufgebraucht, hält die Prüfung an; was geprüft ist, bleibt.");
});

test("hits without text: the extension loads them first, the others stay open with their reason", () => {
  const estimate = { ...ESTIMATE, anzahl: 3, laden: ["a", "b"],
    nicht_ladbar: [{ id: "c", stelle: "Data Analyst", firma: "Muster AG", grund: "example.ch ist keines der Portale, die automatisches Laden erlauben." }] };
  const question = logik.confirmation(estimate, false, true);
  assert.ok(question.sentences.includes("Für 2 Stellen holt die Erweiterung zuerst den Text des Inserats."));
  assert.equal(question.notLoadableTitle, "1 Stelle ohne Text bleibt offen:");
  assert.deepEqual(question.notLoadable, ["Data Analyst, Muster AG: example.ch ist keines der Portale, die automatisches Laden erlauben."]);
  const offline = logik.confirmation(estimate, false, false);
  assert.ok(offline.sentences.includes("Für 2 Stellen fehlt der Text. Ohne Erweiterung bleiben sie offen."));
  assert.ok(logik.confirmation({ ...estimate, laden: ["a"] }, false, false).sentences.includes("Für 1 Stelle fehlt der Text. Ohne Erweiterung bleibt sie offen."));
});

test("after the run the page says how many are left, also when the budget ran out", () => {
  const stand = { bewertet: 10, von: 14, offen: [], ohneText: 0, kosten: 0.123, fehler: "Das Budget für die KI ist für diesen Monat aufgebraucht.", gestoppt: false };
  assert.equal(logik.schlussText(stand, 4), "10 von 14 Treffern bewertet, noch 4 offen. Kosten: 0.12 USD.");
  assert.equal(logik.schlussText({ ...stand, fehler: "", gestoppt: true }, 4), "10 von 14 Treffern bewertet, angehalten, noch 4 offen. Kosten: 0.12 USD.");
  assert.equal(logik.schlussText({ ...stand, bewertet: 14, fehler: "" }, 0), "14 von 14 Treffern bewertet. Kosten: 0.12 USD.");
});

test("the page offers one button „Alle prüfen“ and asks before it starts", () => {
  const html = read("treffer.html");
  assert.match(html, /<button type="button" class="btn btn--sm" id="alle-pruefen">Alle prüfen<\/button>/);
  assert.match(html, /<dialog class="dialog" id="alle-dialog"/);
  assert.match(html, /id="alle-abbrechen"[^>]*>Abbrechen</);
  assert.match(html, /id="alle-ok"[^>]*>Jetzt prüfen</);
  const script = read("treffer.js");
  assert.match(script, /holen\("\/api\/suche\/alle-pruefen"\)/);
  assert.match(script, /\$\("alle-dialog"\)\.showModal\(\)/);
});

test("the extension is asked for the missing texts of exactly these hits", () => {
  const script = read("treffer.js");
  assert.match(script, /art: "inserate-holen", ids/);
  const bridge = fs.readFileSync(path.join(__dirname, "..", "..", "erweiterung", "app-bridge.js"), "utf8");
  assert.match(bridge, /data\.art === 'inserate-holen'\) ask\(\{ art: data\.art, ids: data\.ids \}\)/);
});
