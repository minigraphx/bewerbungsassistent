// „Prüfen“ through the extension (G35, #189): what the page says after a check, and a value entered by hand.
// Invented companies only.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const logik = require("../seiten/firmen-logik.js");

test("after a check the page says what kununu gave", () => {
  assert.deepEqual(logik.pruefErgebnis({ gelesen: true, kununu: { zustand: "gefunden", wert: 3.8, bewertungen: 214 } }, "Muster AG"),
    { text: "Muster AG: kununu 3.8 von 5, 214 Bewertungen.", stufe: "success", vonHand: false });
  assert.equal(logik.pruefErgebnis({ gelesen: true, kununu: { zustand: "keine" } }, "Muster AG").text, "Muster AG: bei kununu noch keine Bewertungen.");
  assert.equal(logik.pruefErgebnis({ gelesen: true, kununu: { zustand: "nicht_gefunden" } }, "Muster AG").text, "Muster AG: bei kununu nicht gefunden.");
  assert.equal(logik.pruefErgebnis({ gelesen: true, kununu: { zustand: "mehrere" } }, "Muster AG").text,
    "Muster AG: mehrere Treffer bei kununu. Bitte den passenden wählen.");
});

test("a page that could not be read keeps the tab open and offers to enter the value by hand", () => {
  assert.deepEqual(logik.pruefErgebnis({ gelesen: false }, "Muster AG"), {
    text: "Bei kununu liess sich für Muster AG kein Wert lesen. Der Tab bleibt offen; der Wert lässt sich von Hand eintragen.",
    stufe: "warning", vonHand: true });
});

test("an error of the extension is shown as it is, and without the extension nothing needs saying", () => {
  assert.deepEqual(logik.pruefErgebnis({ fehler: "Es läuft schon eine Prüfung bei kununu." }, "Muster AG"),
    { text: "Es läuft schon eine Prüfung bei kununu.", stufe: "warning", vonHand: false });
  assert.equal(logik.pruefErgebnis({ geoeffnet: true }, "Muster AG"), null);
  assert.equal(logik.pruefErgebnis(undefined, "Muster AG").stufe, "warning");
});

test("a value by hand is read as the page shows it: with point or comma, counts with apostrophes", () => {
  assert.deepEqual(logik.vonHandWerte("3.8", "214"), { wert: 3.8, bewertungen: 214 });
  assert.deepEqual(logik.vonHandWerte(" 4,2 ", "1’312"), { wert: 4.2, bewertungen: 1312 });
  assert.deepEqual(logik.vonHandWerte("5", "0"), { wert: 5, bewertungen: 0 });
});

test("a value by hand outside 1 to 5 or a count that is no whole number is refused with a reason", () => {
  assert.deepEqual(logik.vonHandWerte("0.9", "12"), { fehler: "Der Wert muss eine Zahl von 1 bis 5 sein.", feld: "wert" });
  assert.deepEqual(logik.vonHandWerte("5.1", "12"), { fehler: "Der Wert muss eine Zahl von 1 bis 5 sein.", feld: "wert" });
  assert.deepEqual(logik.vonHandWerte("gut", "12"), { fehler: "Der Wert muss eine Zahl von 1 bis 5 sein.", feld: "wert" });
  assert.deepEqual(logik.vonHandWerte("3.8", "12.5"), { fehler: "Die Anzahl Bewertungen muss eine ganze Zahl ab 0 sein.", feld: "bewertungen" });
  assert.deepEqual(logik.vonHandWerte("3.8", ""), { fehler: "Die Anzahl Bewertungen muss eine ganze Zahl ab 0 sein.", feld: "bewertungen" });
});

test("a value entered by hand says so instead of naming a site of kununu", () => {
  assert.equal(logik.seite({ zustand: "gefunden", wert: 3.9, bewertungen: 48, von_hand: true }), "von Hand eingetragen");
  assert.equal(logik.seite({ zustand: "gefunden", von_hand: true, link: "https://www.kununu.com/de/muster", seite: "de" }),
    "kununu.com/de, von Hand eingetragen");
  assert.equal(logik.seite({ zustand: "gefunden", seite: "ch" }), "kununu.com/ch");
});

test("on Stellen suchen a page that could not be read says where to enter the value by hand", () => {
  assert.equal(logik.pruefErgebnis({ gelesen: false }, "Muster AG", { wo: "Firmen" }).text,
    "Bei kununu liess sich für Muster AG kein Wert lesen. Der Tab bleibt offen; der Wert lässt sich unter Firmen von Hand eintragen.");
  assert.equal(logik.pruefErgebnis({ gelesen: false }, "Muster AG", { wo: "Lehrbetriebe" }).vonHand, true);
});
