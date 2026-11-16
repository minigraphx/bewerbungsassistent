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

// Photo, colour and mark of this CV (G77, #295)

const LOOKED = { ...ANSWER, aussehen: { foto: true, zeichen: "passend", akzent: "passend" },
                 aussehen_angebot: { foto_vorhanden: true, initialen: "EB", logo: false } };

test("the look starts as the answer gives it and goes along with the request", () => {
  const state = L.start(LOOKED);
  assert.deepEqual(L.request(state, { id: "b1", ...texts }).aussehen, { foto: true, zeichen: "passend", akzent: "passend" });
});

test("photo, mark and colour each change on their own and the state before stays", () => {
  const before = L.start(LOOKED);
  const after = L.setLook(L.setLook(L.setLook(before, { foto: false }), { zeichen: "ring" }), { akzent: "#7a2e3a" });
  assert.deepEqual(after.look, { foto: false, zeichen: "ring", akzent: "#7a2e3a" });
  assert.deepEqual(before.look, { foto: true, zeichen: "passend", akzent: "passend" });
});

test("a mark or colour the panel does not offer is refused", () => {
  const state = L.start(LOOKED);
  assert.throws(() => L.setLook(state, { zeichen: "stern" }), /Zeichen/);
  assert.throws(() => L.setLook(state, { zeichen: "logo" }), /Logo/);
  assert.throws(() => L.setLook(state, { akzent: "#ff00ff" }), /Farbe/);
});

test("the photo can be chosen only with a photo and a design that shows one", () => {
  assert.deepEqual(L.photoChoice(L.start(LOOKED)), { available: true, checked: true, reason: null });
  assert.deepEqual(L.photoChoice(L.choose(L.start(LOOKED), "einspaltig")),
                   { available: false, checked: false, reason: "lebenslauf.foto-einspaltig" });
  const without = L.start({ ...LOOKED, aussehen_angebot: { ...LOOKED.aussehen_angebot, foto_vorhanden: false } });
  assert.deepEqual(L.photoChoice(without), { available: false, checked: false, reason: "lebenslauf.foto-fehlt" });
});

test("the marks say why one cannot be chosen: two letters for Verschränkt, a logo for the logo", () => {
  const marks = L.markChoices(L.start({ ...LOOKED, aussehen_angebot: { ...LOOKED.aussehen_angebot, initialen: "EBX" } }));
  assert.deepEqual(marks.map(m => m.id), ["passend", "ring", "block", "verschraenkt", "linie", "punkt", "logo"]);
  assert.equal(marks[0].name, "lebenslauf.zeichen-ohne");
  assert.equal(marks.find(m => m.id === "verschraenkt").locked, "Nur mit zwei Buchstaben");
  assert.equal(marks.find(m => m.id === "logo").locked, "lebenslauf.logo-fehlt");
  assert.equal(marks.find(m => m.id === "ring").locked, null);
  const withLogo = L.markChoices(L.start({ ...LOOKED, aussehen_angebot: { ...LOOKED.aussehen_angebot, logo: true } }));
  assert.equal(withLogo.find(m => m.id === "logo").locked, null);
});

test("a blocked «Mit Foto» shows no tick, and the choice comes back with Zweispaltig", () => {
  const single = L.choose(L.start(LOOKED), "einspaltig");
  assert.equal(L.photoChoice(single).checked, false);
  assert.equal(single.look.foto, true, "the choice itself stays");
  assert.equal(L.photoChoice(L.choose(single, "zweispaltig")).checked, true);
});

test("the colours are the design's own, named by its swatch, and the other swatches of the dossier", () => {
  const colours = L.accentChoices(L.start(LOOKED));
  assert.deepEqual(colours[0], { id: "passend", name: "lebenslauf.farbe-passend", colour: "#38495d", note: "Schieferblau" });
  assert.deepEqual(colours.slice(1).map(c => c.name), ["Weinrot", "Tannengrün", "Petrol", "Aubergine", "Bronze", "Graphit"]);
  const single = L.accentChoices(L.choose(L.start(LOOKED), "einspaltig"));
  assert.deepEqual(single[0], { id: "passend", name: "lebenslauf.farbe-passend", colour: "#2f5d4a", note: "Tannengrün" });
  assert.deepEqual(single.slice(1).map(c => c.name), ["Schieferblau", "Weinrot", "Petrol", "Aubergine", "Bronze", "Graphit"]);
});

test("a colour that is now the design's own becomes «Passend zum Design», on start and on a new design", () => {
  const stored = L.start({ ...LOOKED, aussehen: { foto: true, zeichen: "passend", akzent: "#38495d" } });
  assert.equal(stored.look.akzent, "passend");
  const green = L.setLook(L.start(LOOKED), { akzent: "#2f5d50" });
  assert.equal(L.choose(green, "einspaltig").look.akzent, "passend");
  assert.equal(L.choose(L.setLook(L.start(LOOKED), { akzent: "#7a2e3a" }), "einspaltig").look.akzent, "#7a2e3a");
});

test("each mark of initials has its sentence; none and the logo have none", () => {
  const notes = Object.fromEntries(L.markChoices(L.start(LOOKED)).map(m => [m.id, m.note]));
  assert.deepEqual(notes, { passend: null, ring: "Initialen im Ring", block: "Initialen in einer Fläche",
                            verschraenkt: "Zwei Buchstaben ineinander", linie: "Initialen auf einer Linie",
                            punkt: "Punkt vor den Initialen", logo: null });
});

test("a stored mark that cannot be drawn any more starts as none", () => {
  const state = L.start({ ...LOOKED, aussehen: { foto: true, zeichen: "logo", akzent: "#7a2e3a" } });
  assert.deepEqual(state.look, { foto: true, zeichen: "passend", akzent: "#7a2e3a" });
});

test("the line beside the button names mark and colour", () => {
  const say = key => ({ "lebenslauf.zeichen-ohne": "Ohne Zeichen", "lebenslauf.farbe-passend-zeile": "passend zum Design" })[key] || key;
  assert.deepEqual(L.lookParts(L.start(LOOKED), say), ["Ohne Zeichen", "Farbe: passend zum Design"]);
  assert.equal(L.lookLine(L.start(LOOKED), say), "Ohne Zeichen · Farbe: passend zum Design");
  assert.equal(L.lookLine(L.setLook(L.setLook(L.start(LOOKED), { zeichen: "ring" }), { akzent: "#7a2e3a" }), say),
               "Zeichen: Ring · Farbe: Weinrot");
});

test("the message after saving says whether the PDF is there", () => {
  assert.match(L.savedText({ variante: { beschreibung: "Daten" }, gebaut: true, hinweis: null }), /«Daten».*PDF/);
  assert.equal(L.savedText({ variante: { beschreibung: "Daten" }, gebaut: false, hinweis: "Später." }), "Später.");
});
