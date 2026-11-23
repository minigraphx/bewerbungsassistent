// Texts of the scripts in the app language (#414, G10): Texte.t looks a German text up in the catalog the server
// hands the page (/uebersetzung.js), Texte.text does the same for a text set; German stays as it is.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const texte = require("../seiten/texte.js");

const FRENCH = {
  sprache: "fr",
  texte: { "Abgabe bis {datum}": "À remettre d'ici le {datum}", "Gespeichert.": "Enregistré." },
  saetze: {
    "fragen.label": { sie: "Votre question", du: "Ta question" },
    "nav.suche": { sie: "Chercher des postes", du: "Chercher des postes", lehrstelle: "Chercher des places d'apprentissage" },
  },
};
const ENGLISH = { sprache: "en", texte: {}, saetze: { "fragen.label": { sie: "Your question" } } };

test.afterEach(() => texte.setzeSprache());

test("in German a text stays and its values fill in", () => {
  assert.equal(texte.t("Abgabe bis {datum}", { datum: "20.11.2026" }), "Abgabe bis 20.11.2026");
  assert.equal(texte.t("Gespeichert."), "Gespeichert.");
});

test("in French a text comes from the catalog, with its values", () => {
  texte.setzeSprache("fr", FRENCH);

  assert.equal(texte.t("Abgabe bis {datum}", { datum: "20.11.2026" }), "À remettre d'ici le 20.11.2026");
  assert.equal(texte.t("Gespeichert."), "Enregistré.");
});

test("a text missing in the catalog falls back to German", () => {
  texte.setzeSprache("fr", FRENCH);

  assert.equal(texte.t("Nicht im Katalog: {anzahl}", { anzahl: 3 }), "Nicht im Katalog: 3");
  assert.equal(texte.t("constructor"), "constructor");
});

test("a catalog of another language is not used", () => {
  texte.setzeSprache("en", FRENCH);

  assert.equal(texte.t("Gespeichert."), "Gespeichert.");
});

test("text sets follow the language; English du falls back to Sie", () => {
  texte.setzeSprache("fr", FRENCH);
  assert.equal(texte.text("fragen.label", "stelle-sie"), "Votre question");
  assert.equal(texte.text("fragen.label", "stelle-du"), "Ta question");
  assert.equal(texte.text("fragen.label", "lehrstelle-du"), "Ta question");
  assert.equal(texte.text("nav.suche", "lehrstelle-du"), "Chercher des places d'apprentissage");

  texte.setzeSprache("en", ENGLISH);
  assert.equal(texte.text("fragen.label", "stelle-du"), "Your question");
  assert.equal(texte.text("fragen.label", "lehrstelle-du"), "Your question");
});

test("a text set missing in the catalog stays German, and the German forms are unchanged", () => {
  texte.setzeSprache("fr", FRENCH);
  assert.equal(texte.text("dateien.ihr-pdf", "stelle-du"), "Dein PDF");

  texte.setzeSprache();
  assert.equal(texte.text("fragen.label", "stelle-sie"), "Ihre Frage");
  assert.equal(texte.text("fragen.label", "stelle-du"), "Deine Frage");
  assert.equal(texte.text("nav.suche", "lehrstelle-du"), "Lehrstellen suchen");
  assert.equal(texte.text("einrichtung.ki.aufgabe", "lehrstelle-du"), "Die KI schätzt Lehrstellen ein und entwirft Anschreiben.");
});

test("in a page the language comes from <html lang> and the catalog from /uebersetzung.js", () => {
  const context = { document: { documentElement: { lang: "fr" } }, Uebersetzung: FRENCH };
  context.window = context;
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.join(__dirname, "..", "seiten", "texte.js"), "utf8"), context);

  assert.equal(context.Texte.t("Gespeichert."), "Enregistré.");
  context.document.documentElement.lang = "de-CH";
  assert.equal(context.Texte.t("Gespeichert."), "Gespeichert.");
});
