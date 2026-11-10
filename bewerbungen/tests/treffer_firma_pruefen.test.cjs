// „Jetzt prüfen“ on Stellen suchen (G35, #191): the same check as on the page Firmen, through kununu-pruefen.js.
// treffer-firma.js runs against a small stand-in for App.el; invented companies only.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");
const logik = require("../seiten/firmen-logik.js");

const SCRIPT = path.join(__dirname, "../seiten/treffer-firma.js");
const el = (tag, attrs = {}, ...kinder) => ({ tag, attrs, kinder: kinder.flat().filter(k => k !== null && k !== undefined) });
const knoepfe = knoten => (typeof knoten !== "object" ? [] : [
  ...(knoten.tag === "button" ? [knoten] : []), ...knoten.kinder.flatMap(knoepfe)]);
const text = knoten => (typeof knoten === "object" ? knoten.kinder.map(text).join("") : String(knoten));

function seite(antwort) {
  const geprueft = [];
  const geoeffnet = [];
  global.document = { documentElement: { dataset: { bewerbungsbegleiterErweiterung: "1" } } };
  global.window = {
    App: { el }, FirmenLogik: logik, open: href => geoeffnet.push(href),
    KununuPruefen: { pruefe: async firma => { geprueft.push(firma.schluessel); return antwort; } },
  };
  delete require.cache[require.resolve(SCRIPT)];
  require(SCRIPT);
  return { treffer: global.window.TrefferFirma, geprueft, geoeffnet };
}

const firma = { schluessel: "muster-industrie-ag", name: "Muster Industrie AG", ort: "Bern", treffer: [{ id: "jobs-ch-1" }],
                bewerbungen: [], kununu: null, suche: "https://www.kununu.com/ch/search?q=Muster%20Industrie%20AG" };

test("Jetzt prüfen reads kununu through the extension and hands the result back to the page", async () => {
  const { treffer, geprueft, geoeffnet } = seite({ gelesen: true, kununu: { zustand: "gefunden", wert: 3.8, bewertungen: 214 } });
  const ergebnisse = [];
  const zeile = treffer.zeile(firma, "2026-11-09", { alle: "Alle Firmen", nachPruefen: e => ergebnisse.push(e) });
  const knopf = knoepfe(zeile).find(k => text(k).startsWith("Jetzt prüfen"));
  await knopf.attrs.onclick({ currentTarget: knopf.attrs });
  assert.deepEqual(geprueft, ["muster-industrie-ag"]);
  assert.deepEqual(geoeffnet, []);
  assert.deepEqual(ergebnisse, [{ text: "Muster Industrie AG: kununu 3.8 von 5, 214 Bewertungen.", stufe: "success", vonHand: false }]);
});

test("a page that could not be read sends the person to the page Firmen to enter the value", async () => {
  const { treffer } = seite({ gelesen: false });
  const ergebnisse = [];
  const zeile = treffer.zeile(firma, "2026-11-09", { alle: "Alle Firmen", wo: "Firmen", nachPruefen: e => ergebnisse.push(e) });
  const knopf = knoepfe(zeile).find(k => text(k).startsWith("Jetzt prüfen"));
  await knopf.attrs.onclick({ currentTarget: knopf.attrs });
  assert.match(ergebnisse[0].text, /lässt sich unter Firmen von Hand eintragen\.$/);
});

test("without the extension kununu opens in a tab and nothing needs saying", async () => {
  const { treffer } = seite({ geoeffnet: true });
  const ergebnisse = [];
  const zeile = treffer.zeile(firma, "2026-11-09", { alle: "Alle Firmen", nachPruefen: e => ergebnisse.push(e) });
  const knopf = knoepfe(zeile).find(k => text(k).startsWith("Jetzt prüfen"));
  await knopf.attrs.onclick({ currentTarget: knopf.attrs });
  assert.deepEqual(ergebnisse, []);
});
