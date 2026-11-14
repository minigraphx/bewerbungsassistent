"use strict";
// What the proposal from dismissed hits says on Suche einstellen and where its link leads (#225, G66).
const test = require("node:test");
const assert = require("node:assert/strict");
const L = require("../seiten/verworfen-woerter-logik.js");
const Texte = require("../seiten/texte.js");

const VORSCHLAG = { wort: "Aussendienst", ids: ["t1", "t2", "t3"], verworfen: 3, andere: 1 };

test("the sentence names the count and the word in the address of the set", () => {
  assert.equal(L.satz(VORSCHLAG, "stelle-sie", Texte), "Aus den Stellen, die Sie verworfen haben: 3 haben «Aussendienst» im Titel.");
  assert.equal(L.satz(VORSCHLAG, "stelle-du", Texte), "Aus den Stellen, die du verworfen hast: 3 haben «Aussendienst» im Titel.");
});

test("it says how many hits that are not dismissed the exclusion would also keep away", () => {
  assert.equal(L.andere({ ...VORSCHLAG, andere: 0 }), "Von den übrigen Stellen hat keine dieses Wort im Titel.");
  assert.equal(L.andere(VORSCHLAG), "Auch 1 Stelle, die nicht verworfen ist, hat dieses Wort im Titel.");
  assert.equal(L.andere({ ...VORSCHLAG, andere: 4 }), "Auch 4 Stellen, die nicht verworfen sind, haben dieses Wort im Titel.");
});

test("the three answers of the design", () => {
  assert.equal(L.knopf(VORSCHLAG), "«Aussendienst» nicht mehr zeigen");
  assert.equal(L.link(VORSCHLAG), "Die 3 Stellen ansehen");
});

test("the link leads to exactly these hits and reads back", () => {
  const wort = { ...VORSCHLAG, wort: "Büro & Co" };
  const adresse = L.adresse(wort);
  assert.equal(adresse, "/treffer#verworfen=B%C3%BCro%20%26%20Co");
  assert.equal(L.ausAdresse(adresse.slice("/treffer".length)), "Büro & Co");
  assert.equal(L.ausAdresse("#beleg=Engineer"), null);
  assert.equal(L.ausAdresse("#verworfen=%E0%A4%A"), null);
  assert.equal(L.ausAdresse(""), null);
});

test("the narrowed list says what it shows", () => {
  assert.equal(L.filterText(3, "Aussendienst"), "Gezeigt: 3 verworfene Stellen mit «Aussendienst» im Titel.");
  assert.equal(L.filterText(1, "Aussendienst"), "Gezeigt: 1 verworfene Stelle mit «Aussendienst» im Titel.");
});

test("no sharp s in what the person reads", () => {
  const texte = [L.andere({ andere: 0 }), L.andere({ andere: 2 }), L.uebernommen("Wort"), L.satz(VORSCHLAG, "stelle-du", Texte)];
  assert.deepEqual(texte.filter(text => text.includes("ß")), []);
});
