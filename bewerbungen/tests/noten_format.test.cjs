// One notation for grades (#221, UX finding 7): a decimal point everywhere, as the design system says (4.5, never 4,5).
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const texte = require("../seiten/texte.js");
const trefferLogik = require("../seiten/treffer-logik.js");
const firmenLogik = require("../seiten/firmen-logik.js");

const ROOT = path.join(__dirname, "..", "..");
const lies = (...teile) => fs.readFileSync(path.join(ROOT, ...teile), "utf8");

test("the AI grade is written with a decimal point", () => {
  assert.equal(texte.notenText(4.5), "4.5");
  assert.equal(texte.notenText("5.5"), "5.5");
  assert.equal(texte.notenText(4), "4");
});

test("the second look on Stellen suchen names its grades with a decimal point", () => {
  const text = trefferLogik.nachpruefungText({ nachpruefung: { noten: [4.5, 5, 5.5], im_paket: 4.5 } }, texte.notenText);
  assert.equal(text, "Nachgeprüft: einzeln Noten 4.5, 5 und 5.5, es zählt die mittlere. Im Paket zuerst: Note 4.5.");
});

test("the kununu badge on Stellen suchen reads kununu 3.8 von 5", () => {
  const firma = { name: "Muster Industrie AG", kununu: { zustand: "gefunden", wert: 3.8, bewertungen: 214, geprueft_am: new Date().toISOString().slice(0, 10) } };
  const marke = firmenLogik.marke(firma);
  assert.equal(marke.text, "kununu 3.8 von 5");
  const wenige = firmenLogik.marke({ ...firma, kununu: { ...firma.kununu, bewertungen: 3 } });
  assert.equal(wenige.text, "kununu 3.8 von 5, wenige Bewertungen");
});

test("the popup of the extension titles a check with a decimal point", async () => {
  const { describeCheck } = await import(pathToFileURL(path.join(ROOT, "erweiterung", "lib", "page-ad.js")).href);
  assert.equal(describeCheck({ bewertung: { note: 4.5 }, vorhanden: null, hinweis: "" }).titel, "Note 4.5");
});

test("no page turns a decimal point into a comma", () => {
  const ordner = [["bewerbungen", "seiten"], ["erweiterung", "lib"]];
  const komma = /replace\(\s*["']\.["']\s*,\s*["'],["']\s*\)/;
  for (const teile of ordner) {
    for (const datei of fs.readdirSync(path.join(ROOT, ...teile)).filter(name => name.endsWith(".js"))) {
      assert.doesNotMatch(lies(...teile, datei), komma, `${teile.join("/")}/${datei}`);
    }
  }
  assert.doesNotMatch(lies("bewerbungen", "seiten", "foto.html"), /\d,\d+ cm/);
});

test("the comparison with the design marks the notation of numbers as decided", () => {
  const zeile = lies("docs", "design", "abgleich.md").split("\n").find(z => z.startsWith("| 1 | Noten und Dezimalzahlen"));
  assert.ok(zeile, "row 1 is missing");
  assert.match(zeile, /entschieden/i);
});
