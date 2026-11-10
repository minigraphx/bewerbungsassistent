// Setup quick wins (#219, UX findings 2 and 4): fewer steps that are no question, one store button, an honest end.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const logik = require("../seiten/einrichtung-logik.js");

const HTML = fs.readFileSync(path.join(__dirname, "..", "seiten", "einrichtung.html"), "utf8");
const UA = {
  chrome: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
  edge: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0",
  firefox: "Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0",
  safari: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/19.0 Safari/605.1.15",
  opera: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 OPR/120.0.0.0",
};

/** The section of one step, from its opening tag to the next section. */
function abschnitt(id) {
  const start = HTML.indexOf(`<section class="card" id="${id}"`);
  assert.notEqual(start, -1, `section ${id} is missing`);
  return HTML.slice(start, HTML.indexOf("</section>", start));
}

test("without an einstieg file in Downloads the step Datei is not among the steps", () => {
  assert.deepEqual(logik.schritte({ installiert: true, einstiegDatei: null }), ["gesucht", "ki", "erweiterung"]);
});

test("with an einstieg file in Downloads the step Datei comes after the first step", () => {
  assert.deepEqual(logik.schritte({ installiert: true, einstiegDatei: "/Users/x/Downloads/einstieg.zip" }),
    ["gesucht", "vorlage", "ki", "erweiterung"]);
});

test("opened from Erweitert, the step Datei shows in the list while it is the current one", () => {
  assert.deepEqual(logik.schritte({ installiert: true, einstiegDatei: null, jetzt: "vorlage" }),
    ["gesucht", "vorlage", "ki", "erweiterung"]);
});

test("the plain app only knows the first step, and the data folder is never a step of its own", () => {
  assert.deepEqual(logik.schritte({ installiert: false, einstiegDatei: null }), ["gesucht"]);
  for (const einstiegDatei of [null, "einstieg.json"]) {
    assert.ok(!logik.schritte({ installiert: true, einstiegDatei }).includes("datenordner"));
  }
  assert.ok(!HTML.includes('data-schritt="datenordner"'));
});

test("the data folder is one line with the path and Ändern in the first step", () => {
  const gesucht = abschnitt("gesucht");
  assert.match(gesucht, /id="ordner-zeile"/);
  assert.match(gesucht, /<button type="button" class="btn btn--quiet btn--sm" id="ordner-aendern"[^>]*>Ändern<\/button>/);
  assert.match(gesucht, /<div id="ordner-feld" hidden>/);
});

test("the import of an einstieg file sits under Erweitert when no file was found", () => {
  const erweitert = HTML.slice(HTML.indexOf('<details id="erweitert"'));
  assert.match(erweitert, /^<details id="erweitert" class="setup__more" hidden>\s*<summary>Erweitert<\/summary>/);
  assert.match(erweitert.slice(0, erweitert.indexOf("</details>")), /href="#vorlage"/);
});

test("the browser of the page is recognised", () => {
  assert.equal(logik.browserVon(UA.chrome), "chrome");
  assert.equal(logik.browserVon(UA.edge), "edge");
  for (const andere of [UA.firefox, UA.safari, UA.opera, ""]) assert.equal(logik.browserVon(andere), "andere");
});

test("only the store of the own browser is the main button, the other one a quiet link", () => {
  assert.deepEqual(logik.storeKnoepfe("edge"), { haupt: "edge", leise: "chrome" });
  assert.deepEqual(logik.storeKnoepfe("chrome"), { haupt: "chrome", leise: "edge" });
  assert.deepEqual(logik.storeKnoepfe("andere"), { haupt: "chrome", leise: "edge" });
  const store = HTML.slice(HTML.indexOf('id="erweiterung-store"'), HTML.indexOf('id="erweiterung-hand"'));
  assert.equal((store.match(/btn--primary/g) || []).length, 1);
  assert.match(store, /class="btn btn--quiet btn--sm" id="store-leise"/);
});

test("loading by hand sits in a collapsed Klappt es nicht?", () => {
  const erweiterung = abschnitt("erweiterung");
  const klappe = erweiterung.indexOf('<details id="erweiterung-hand" class="setup__more">');
  assert.notEqual(klappe, -1);
  assert.match(erweiterung.slice(klappe), /^<details id="erweiterung-hand" class="setup__more">\s*<summary>Klappt es nicht\?<\/summary>/);
  assert.ok(erweiterung.indexOf('id="erweiterung-schritte"') > klappe);
  assert.match(erweiterung, /Zurück in diesem Tab geht es von selbst weiter\./);
});

test("the end says Fast fertig and lists what is open, with one button each", () => {
  const offen = logik.offenePunkte({ kiVerbunden: false, erweiterungMoeglich: true, erweiterungGeladen: "" });
  assert.deepEqual(offen.map(p => [p.id, p.knopf, p.ziel]),
    [["ki", "KI einrichten", "#ki"], ["erweiterung", "Erweiterung laden", "#erweiterung"]]);
  assert.equal(logik.abschlussTitel(offen), "Fast fertig");
  assert.deepEqual(logik.offenePunkte({ kiVerbunden: true, erweiterungMoeglich: true, erweiterungGeladen: "" }).map(p => p.id),
    ["erweiterung"]);
});

test("Alles eingerichtet only when nothing is open", () => {
  const nichts = logik.offenePunkte({ kiVerbunden: true, erweiterungMoeglich: true, erweiterungGeladen: "0.2.17" });
  assert.deepEqual(nichts, []);
  assert.equal(logik.abschlussTitel(nichts), "Alles eingerichtet");
  assert.deepEqual(logik.offenePunkte({ kiVerbunden: true, erweiterungMoeglich: false, erweiterungGeladen: "" }), []);
  assert.doesNotMatch(abschnitt("fertig"), />Alles eingerichtet</);
});

test("no function of the page is declared twice, so none hides another and step 1 shows the stored choice", () => {
  const js = fs.readFileSync(path.join(__dirname, "..", "seiten", "einrichtung.js"), "utf8");
  const namen = [...js.matchAll(/^\s*(?:async\s+)?function\s+(\w+)/gm)].map(m => m[1]);
  assert.deepEqual(namen.filter((name, i) => namen.indexOf(name) !== i), []);
});
