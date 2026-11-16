// Suggestions of the AI in „Lebenslauf erstellen“ (#293, G75): applied on opening, each recommendation undone as a
// whole, the person's own changes stay. Without DOM; invented data.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const L = require("../seiten/lebenslauf-erstellen-logik.js");

const ANSWER = {
  stand: "abc", ki: "bereit", eigene_variante: null,
  abschnitte: [
    { abschnitt: "work", titel: "Berufserfahrung", stationen: [
      { index: 0, titel: "Entwicklerin", zusatz: "Beispiel AG", zeit: "2019 – heute", gewaehlt: true },
      { index: 1, titel: "Junior", zusatz: "Muster GmbH", zeit: "2015 – 2019", gewaehlt: true },
    ] },
    { abschnitt: "projects", titel: "Projekte", stationen: [
      { index: 0, titel: "datenatlas", zusatz: "", zeit: "", gewaehlt: true },
      { index: 1, titel: "kurs-tools", zusatz: "", zeit: "", gewaehlt: true },
      { index: 2, titel: "Spiel", zusatz: "", zeit: "", gewaehlt: true },
    ] },
  ],
  berufsbezeichnung: "Entwicklerin", kurzprofil: "Erster Satz. Zweiter Satz.", design: "zweispaltig", bezeichnung: "Daten",
};

const SUGGESTION = { empfehlungen: [
  { nummer: 0, was: "«Spiel» weglassen, «kurs-tools» nach vorne", grund: "Kurse passen.",
    weglassen: [{ abschnitt: "projects", index: 2 }], voran: [{ abschnitt: "projects", index: 1 }], kurzprofil: null },
  { nummer: 1, was: "«Junior, Muster GmbH» weglassen, Kurzprofil gekürzt", grund: "Keine Webstelle.",
    weglassen: [{ abschnitt: "work", index: 1 }], voran: [], kurzprofil: "Zweiter Satz." },
] };

const section = (state, name) => state.sections.find(part => part.name === name);
const texts = { berufsbezeichnung: "Entwicklerin", kurzprofil: "", bezeichnung: "Daten" };

test("the suggestion is applied as a whole: stations left out, moved up, and the shorter summary", () => {
  const state = L.suggest(L.start(ANSWER), SUGGESTION);
  assert.deepEqual(section(state, "projects").order, [1, 0, 2]);
  assert.deepEqual(section(state, "projects").chosen, [1, 0]);
  assert.deepEqual(section(state, "work").chosen, [0]);
  assert.equal(L.summary(state), "Zweiter Satz.");
  assert.deepEqual(state.recommendations.map(r => r.on), [true, true]);
  assert.deepEqual(L.request(state, { id: "b1", ...texts }).stationen, { work: [0], projects: [1, 0] });
});

test("undoing one recommendation brings back exactly its changes and keeps the others", () => {
  const applied = L.suggest(L.start(ANSWER), SUGGESTION);
  const undone = L.setRecommendation(applied, 0, false);
  assert.deepEqual(section(undone, "projects").order, [0, 1, 2]);
  assert.deepEqual(section(undone, "projects").chosen, [0, 1, 2]);
  assert.deepEqual(section(undone, "work").chosen, [0]);
  assert.equal(L.summary(undone), "Zweiter Satz.");
  assert.deepEqual(section(applied, "projects").chosen, [1, 0], "the state before stays");
  const summaryBack = L.setRecommendation(undone, 1, false);
  assert.equal(L.summary(summaryBack), "Erster Satz. Zweiter Satz.");
  assert.deepEqual(section(summaryBack, "work").chosen, [0, 1]);
  assert.deepEqual(section(L.setRecommendation(summaryBack, 0, true), "projects").order, [1, 0, 2]);
});

test("changes by hand stay when a recommendation is undone", () => {
  let state = L.suggest(L.start(ANSWER), SUGGESTION);
  state = L.toggle(state, "work", 0);
  state = L.move(state, "projects", 0, -1);
  assert.deepEqual(section(state, "projects").order, [0, 1, 2]);
  state = L.setRecommendation(state, 1, false);
  assert.deepEqual(section(state, "work").chosen, [1]);
  assert.deepEqual(section(state, "projects").order, [0, 1, 2]);
  assert.deepEqual(section(state, "projects").chosen, [0, 1]);
});

test("the AI suggests on opening only when it can and the application has no CV of its own yet", () => {
  assert.equal(L.autoSuggest(ANSWER), true);
  assert.equal(L.autoSuggest({ ...ANSWER, eigene_variante: "b1" }), false);
  assert.equal(L.autoSuggest({ ...ANSWER, ki: "aus" }), false);
  assert.equal(L.autoSuggest({ ...ANSWER, ki: "ohne_inserat" }), false);
});

test("without AI the state is the one of today and nothing is recommended", () => {
  const state = L.start({ ...ANSWER, ki: "aus" });
  assert.deepEqual(state.recommendations, []);
  assert.equal(L.summary(state), "Erster Satz. Zweiter Satz.");
  assert.deepEqual(L.request(state, { id: "b1", ...texts }).stationen, { work: [0, 1], projects: [0, 1, 2] });
});

test("what the page says about the suggestion and each undo", () => {
  assert.equal(L.suggestedText(SUGGESTION.empfehlungen.length), "Vorschlag der KI angewendet: 2 Empfehlungen.");
  assert.equal(L.suggestedText(1), "Vorschlag der KI angewendet: 1 Empfehlung.");
  assert.equal(L.suggestedText(0), "Die KI schlägt für diese Stelle nichts anderes vor.");
  const rec = SUGGESTION.empfehlungen[0];
  assert.equal(L.recommendationText(rec, false), "Zurückgenommen: «Spiel» weglassen, «kurs-tools» nach vorne.");
  assert.equal(L.recommendationText(rec, true), "Wieder angewendet: «Spiel» weglassen, «kurs-tools» nach vorne.");
  assert.match(L.aiLine("ohne_inserat"), /Stellentext/);
  assert.match(L.aiLine("aus"), /KI/);
});
