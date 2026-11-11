// Mark and accent colour of the dossier (G18, option B of docs/design/monogramm.md): names, sentences and the colour
// check of the page, with the same cases as lebenslauf/mark.py.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const Z = require("../seiten/zeichen-logik.js");

const FAELLE = JSON.parse(fs.readFileSync(path.join(__dirname, "../../lebenslauf/tests/accent_cases.json"), "utf8"));
const lies = datei => fs.readFileSync(path.join(__dirname, "../seiten", datei), "utf8");
const ALLE = design => ({ deckblatt: design, anschreiben: design, lebenslauf: design, weitere: design });
const zustand = (felder = {}) => ({ zeichen: "passend", akzent: "passend", initialen: "", initialen_wirksam: "LB", logo: null, ...felder });

test("own colours get the same answer as in lebenslauf/mark.py", () => {
  for (const fall of FAELLE.cases) {
    const geprueft = Z.pruefeFarbe(fall.farbe);
    assert.equal(geprueft.ok, fall.ok, fall.farbe);
    if (fall.ok) assert.equal(geprueft.schrift, fall.schrift, fall.farbe);
    else assert.deepEqual([geprueft.problem, geprueft.vorschlag], [fall.problem, fall.vorschlag], fall.farbe);
  }
  for (const falsch of FAELLE.invalid) assert.equal(Z.pruefeFarbe(falsch).meldung, "Bitte eine Farbe wie #38495d eingeben.");
});

test("a colour too light or in the middle says why and is not stored", () => {
  assert.match(Z.pruefeFarbe("#e0b84a").meldung, /^Zu hell: Ring, Linien und Punkte wären auf dem Papier kaum zu sehen\./);
  assert.match(Z.pruefeFarbe("#7f7f7f").meldung, /^Weder weisse noch dunkle Schrift/);
  assert.equal(Z.pruefeFarbe("#38495d").meldung, "Gut lesbar: weisse Schrift auf der Farbe, Linien gut sichtbar auf dem Papier.");
});

test("interlaced is blocked without exactly two letters", () => {
  assert.equal(Z.gesperrt("verschraenkt", "LB"), "");
  assert.equal(Z.gesperrt("verschraenkt", "L"), "Nur mit zwei Buchstaben");
  assert.equal(Z.gesperrt("verschraenkt", "LMB"), "Nur mit zwei Buchstaben");
  assert.equal(Z.gesperrt("ring", "LMB"), "");
});

test("the sentence under the design names mark and colour of each design without a choice", () => {
  assert.equal(Z.satzUnterDesign(zustand(), ALLE("siegel")),
    "Zeichen: Ring mit LB · Akzentfarbe: Schieferblau · beides passend zu Siegel · Ändern unter «Erweitert».");
  assert.equal(Z.satzUnterDesign(zustand(), ALLE("raster")),
    "Zeichen: Initialen im Band · Akzentfarbe: Weinrot · beides passend zu Raster · Ändern unter «Erweitert».");
  assert.equal(Z.satzUnterDesign(zustand(), ALLE("register")),
    "Zeichen: Punkt mit LB im Anhänger · Akzentfarbe: Tannengrün · beides passend zu Register · Ändern unter «Erweitert».");
});

test("the sentence with pages in several designs, an own choice and a logo", () => {
  const gemischt = { ...ALLE("siegel"), deckblatt: "raster" };
  assert.equal(Z.satzUnterDesign(zustand(), gemischt),
    "Zeichen: passend zum Design jeder Seite · Akzentfarbe: Weinrot, passend zum Deckblatt in Raster · Ändern unter «Erweitert».");
  assert.equal(Z.satzUnterDesign(zustand({ zeichen: "ring", akzent: "#38495d" }), ALLE("siegel")),
    "Zeichen: Ring mit LB · Akzentfarbe: Schieferblau · Ändern unter «Erweitert».");
  const logo = { farbe: "#a35a2b" };
  assert.equal(Z.satzUnterDesign(zustand({ zeichen: "logo", akzent: "#a35a2b", logo }), ALLE("raster")),
    "Zeichen: Ihr Logo · Akzentfarbe: Aus dem Logo (#a35a2b) · Ändern unter «Erweitert».");
  assert.match(Z.satzUnterDesign(zustand({ zeichen: "logo", logo }), ALLE("raster"), true), /^Zeichen: Dein Logo/);
  assert.equal(Z.satzUnterDesign(zustand({ akzent: "#1d5c6b" }), ALLE("register")),
    "Zeichen: Punkt mit LB im Anhänger, passend zu Register · Akzentfarbe: Petrol · Ändern unter «Erweitert».");
});

test("„Passend zum Design“ follows the design, a named colour stays", () => {
  assert.equal(Z.wirksameFarbe(zustand(), "raster").farbe, "#7a2e3a");
  assert.equal(Z.wirksameFarbe(zustand(), "register").farbe, "#2f5d50");
  assert.equal(Z.wirksameFarbe(zustand({ akzent: "#38495d" }), "raster").name, "Schieferblau");
  assert.equal(Z.wirksameFarbe(zustand({ akzent: "#123456" }), "raster").name, "Eigene Farbe (#123456)");
  assert.equal(Z.passendSatz("raster"), "Block bei Raster, wie das Design es vorsieht");
  assert.equal(Z.FARBEN.length, 7);
});

test("a design draws its own mark for „passend“, a missing logo and blocked letters", () => {
  assert.equal(Z.gezeichnet(zustand(), "siegel"), "ring");
  assert.equal(Z.gezeichnet(zustand({ zeichen: "logo" }), "register"), "punkt");
  assert.equal(Z.gezeichnet(zustand({ zeichen: "verschraenkt", initialen_wirksam: "LMB" }), "raster"), "band");
  assert.equal(Z.gezeichnet(zustand({ zeichen: "linie" }), "raster"), "linie");
  assert.equal(Z.vorschauLabel(zustand(), "raster"), "Vorschau Deckblatt: Raster, Initialen im Band, Weinrot");
});

test("the page has the section with real radio groups, a file field and a live status line", () => {
  const html = lies("bewerbung.html");
  assert.match(html, /<h3 id="d-zeichen-titel">Zeichen und Farbe<\/h3>/);
  assert.match(html, /<fieldset class="mark-group" id="d-zeichen-wahl"><legend>Zeichen<\/legend>/);
  assert.match(html, /<fieldset class="mark-group" id="d-akzent-wahl"><legend>Akzentfarbe<\/legend>/);
  assert.match(html, /<input type="file" id="d-logo-datei"[^>]*accept="\.png,\.jpg,\.jpeg,\.svg/);
  assert.match(html, /id="d-zeichen-status" role="status" aria-live="polite"/);
  assert.match(html, /Gilt für alle Dossiers\. Schon erstellte bleiben, wie sie sind; mit «Unterlagen erstellen» entsteht dieses neu\./);
  assert.match(html, /Zurück zur Voreinstellung/);
  assert.ok(html.indexOf("Zeichen und Farbe") < html.indexOf("Design pro Seite"));
  assert.doesNotMatch(lies("zeichen.js"), /innerHTML|style=/);
});
