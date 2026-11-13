// „Lebenslauf erstellen“ on the page of an application (G17, #118): stations, order and the request, without DOM.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const L = require("../seiten/lebenslauf-erstellen-logik.js");

const ANSWER = {
  stand: "abc",
  abschnitte: [
    { abschnitt: "work", titel: "Berufserfahrung", stationen: [
      { index: 1, titel: "Junior", zusatz: "Muster GmbH", zeit: "2015 – 2019", gewaehlt: true },
      { index: 0, titel: "Entwicklerin", zusatz: "Beispiel AG", zeit: "2019-03 – heute", gewaehlt: true },
      { index: 2, titel: "Praktikum", zusatz: "Probe AG", zeit: "2014", gewaehlt: false },
    ] },
    { abschnitt: "education", titel: "Bildung und Weiterbildung", stationen: [
      { index: 0, titel: "Bachelor Informatik", zusatz: "Hochschule", zeit: "", gewaehlt: true },
    ] },
  ],
  berufsbezeichnung: "Entwicklerin", kurzprofil: "Alt", design: "zweispaltig", bezeichnung: "Data Engineer, Beispiel AG",
};

const texts = { berufsbezeichnung: "Data Engineer", kurzprofil: "Neu", bezeichnung: "Daten" };

test("the start keeps the order of the answer and what is chosen", () => {
  const state = L.start(ANSWER);
  assert.deepEqual(state.sections[0].order, [1, 0, 2]);
  assert.deepEqual(state.sections[0].chosen, [1, 0]);
  assert.equal(state.design, "zweispaltig");
});

test("the request names every section with the chosen stations in their order", () => {
  const body = L.request(L.start(ANSWER), { id: "b1", ...texts });
  assert.deepEqual(body, { id: "b1", stand: "abc", stationen: { work: [1, 0], education: [0] }, design: "zweispaltig",
                           berufsbezeichnung: "Data Engineer", kurzprofil: "Neu", bezeichnung: "Daten" });
});

test("ticking a station adds it in its place, unticking removes it, and the state before stays", () => {
  const before = L.start(ANSWER);
  const added = L.toggle(before, "work", 2);
  assert.deepEqual(added.sections[0].chosen, [1, 0, 2]);
  assert.deepEqual(before.sections[0].chosen, [1, 0]);
  const removed = L.toggle(added, "work", 1);
  assert.deepEqual(removed.sections[0].chosen, [0, 2]);
  assert.deepEqual(removed.sections[0].order, [1, 0, 2]);
});

test("moving a station changes the order of what is sent; at the edge nothing moves", () => {
  const state = L.move(L.start(ANSWER), "work", 0, -1);
  assert.deepEqual(state.sections[0].order, [0, 1, 2]);
  assert.deepEqual(L.request(state, { id: "b1", ...texts }).stationen.work, [0, 1]);
  assert.deepEqual(L.move(state, "work", 0, -1).sections[0].order, [0, 1, 2]);
  assert.deepEqual(L.move(state, "work", 2, 1).sections[0].order, [0, 1, 2]);
});

test("whether a station can move up or down", () => {
  const state = L.start(ANSWER);
  assert.deepEqual(L.canMove(state, "work", 1), { up: false, down: true });
  assert.deepEqual(L.canMove(state, "work", 2), { up: true, down: false });
});

test("without any station chosen the request is refused with a German message", () => {
  let state = L.start(ANSWER);
  for (const [name, index] of [["work", 1], ["work", 0], ["education", 0]]) state = L.toggle(state, name, index);
  assert.throws(() => L.request(state, { id: "b1", ...texts }), /mindestens eine Station/);
});

test("the design is one of the two that build a CV alone", () => {
  const state = L.choose(L.start(ANSWER), "einspaltig");
  assert.equal(L.request(state, { id: "b1", ...texts }).design, "einspaltig");
  assert.throws(() => L.choose(state, "dossier-siegel"), /Zweispaltig oder Einspaltig/);
});

test("the message after saving says whether the PDF is there", () => {
  assert.match(L.savedText({ variante: { beschreibung: "Daten" }, gebaut: true, hinweis: null }), /«Daten».*PDF/);
  assert.equal(L.savedText({ variante: { beschreibung: "Daten" }, gebaut: false, hinweis: "Später." }), "Später.");
});
