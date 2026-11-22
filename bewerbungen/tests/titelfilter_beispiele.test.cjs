// Example titles per title filter term in Erweitert › Titelfilter (G104, #382), without DOM. Invented titles only.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const L = require("../seiten/titelfilter-logik.js");
const T = require("../seiten/texte.js");

const SEITE = fs.readFileSync(path.join(__dirname, "..", "seiten", "suche-einstellen.html"), "utf8");
const eintrag = (begriff, anzahl, beispiele = []) => ({ begriff, anzahl, beispiele });
const BEISPIELE = {
  lauf: true,
  positiv: [eintrag("Software", 8, ["Softwareentwickler:in (80–100 %)", "Software Engineer Backend"]), eintrag("Kurs", 0)],
  ausschluss: [eintrag("Sales (ganzes Wort)", 4, ["Sales Manager B2B"])],
  ohne_begriff: eintrag(undefined, 12, ["Buchhalter", "Koch EFZ", "Gärtner"]),
};

test("a term that let titles through names how many, with the examples of the last run", () => {
  assert.equal(L.zeile(BEISPIELE.positiv[0], "positiv"),
    "8 Titel durchgelassen, zum Beispiel „Softwareentwickler:in (80–100 %)“, „Software Engineer Backend“");
  assert.equal(L.zeile(BEISPIELE.ausschluss[0], "ausschluss"), "4 Titel aussortiert, zum Beispiel „Sales Manager B2B“");
  assert.equal(L.zeile(eintrag("Kurs", 2), "positiv"), "2 Titel durchgelassen");
});

test("a term without titles in the last run says so", () => {
  assert.equal(L.zeile(BEISPIELE.positiv[1], "positiv"), "Im letzten Suchlauf kein Titel.");
  assert.equal(L.zeile(undefined, "ausschluss"), "Im letzten Suchlauf kein Titel.");
});

test("the titles without a positive term follow the list", () => {
  assert.equal(L.ohneBegriff(BEISPIELE.ohne_begriff),
    "Ohne passenden Begriff aussortiert: 12 Titel, zum Beispiel „Buchhalter“, „Koch EFZ“, „Gärtner“");
  assert.equal(L.ohneBegriff(eintrag(undefined, 0)), "Ohne passenden Begriff aussortiert: kein Titel.");
});

test("both lists follow the terms of the profile, with their captions", () => {
  const ansicht = L.ansicht(["Software", "Kurs"], ["Sales (ganzes Wort)"], BEISPIELE);
  assert.equal(ansicht.hinweis, "");
  assert.deepEqual(ansicht.gruppen.map(gruppe => gruppe.titel), ["Titel, die passen", "Titel, die nicht passen"]);
  assert.deepEqual(ansicht.gruppen[0].eintraege.map(e => e.begriff), ["Software", "Kurs"]);
  assert.equal(ansicht.gruppen[0].eintraege[1].zeile, "Im letzten Suchlauf kein Titel.");
  assert.equal(ansicht.gruppen[0].nachsatz, "Ohne passenden Begriff aussortiert: 12 Titel, zum Beispiel „Buchhalter“, „Koch EFZ“, „Gärtner“");
  assert.equal(ansicht.gruppen[1].eintraege[0].zeile, "4 Titel aussortiert, zum Beispiel „Sales Manager B2B“");
  assert.equal(ansicht.gruppen[1].nachsatz, "");
});

test("before any run with examples the terms stand alone and one line says when examples come", () => {
  const ansicht = L.ansicht(["Software"], ["Sales (ganzes Wort)"], { lauf: false, positiv: [], ausschluss: [], ohne_begriff: null });
  assert.equal(ansicht.hinweis, "Beispiele gibt es nach dem nächsten Suchlauf.");
  assert.deepEqual(ansicht.gruppen[0].eintraege, [{ begriff: "Software", zeile: "" }]);
  assert.equal(ansicht.gruppen[0].nachsatz, "");
  const ohneDaten = L.ansicht(["Software"], [], null);
  assert.equal(ohneDaten.hinweis, "");
  assert.equal(ohneDaten.gruppen.length, 1, "a list without terms is left out");
});

test("without any term the section says there is no title filter", () => {
  assert.deepEqual(L.ansicht([], [], BEISPIELE), { hinweis: "", gruppen: [], leer: "Kein Titelfilter" });
});

test("the rule of the title filter is said in Sie and du, in both forms", () => {
  const sie = T.text("einstellen.titel-regel", "stelle-sie");
  const du = T.text("einstellen.titel-regel", "stelle-du");
  assert.equal(sie, "Ein Begriff passt auch als Anfang oder Ende eines Worts: „Software“ passt zu „Softwareentwickler“, "
    + "„Bildung“ zu „Erwachsenenbildung“. Soll er nur als ganzes Wort passen, schreiben Sie „(ganzes Wort)“ dahinter, etwa "
    + "„Sales (ganzes Wort)“. Begriffe mit höchstens drei Buchstaben wie „KI“ passen immer nur als ganzes Wort.");
  assert.equal(du, sie.replace("schreiben Sie", "schreib"));
  assert.equal((SEITE.match(/data-text="einstellen\.titel-regel"/g) || []).length, 2, "in the Titelfilter form and under «Im Titel»");
});

test("the card Was Sie nicht sehen wollen links to the examples under «Im Titel»", () => {
  assert.match(SEITE, /<a [^>]*id="titelfilter-link"[^>]*href="#titelfilter"[^>]*>Was der Titelfilter aussortiert hat<\/a>/);
  assert.match(SEITE, /<h3 id="titelfilter-titel" tabindex="-1">Titelfilter<\/h3>/);
  assert.doesNotMatch(SEITE, /id="titelfilter-text"/, "the lists replace the summary");
});
