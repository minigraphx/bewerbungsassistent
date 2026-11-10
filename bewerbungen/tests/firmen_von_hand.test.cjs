// „Von Hand eintragen“ on the page Firmen (G35, #191): offered for every company without a stored kununu value, also
// right after the page loads, so a check that failed on Stellen suchen leads to a button the person sees.
// firmen.js runs against a small stand-in for the DOM and App; invented companies only.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");
const logik = require("../seiten/firmen-logik.js");

const SCRIPT = path.join(__dirname, "../seiten/firmen.js");
const el = (tag, attrs = {}, ...kinder) => ({ tag, attrs, kinder: kinder.flat().filter(k => k !== null && k !== undefined && k !== false) });
const text = knoten => (typeof knoten === "object" ? knoten.kinder.map(text).join("") : String(knoten));
const knoepfe = knoten => (typeof knoten !== "object" ? [] : [...(knoten.tag === "button" ? [knoten] : []), ...knoten.kinder.flatMap(knoepfe)]);

function element(id) {
  return { id, textContent: "", value: "", placeholder: "", hidden: false, dataset: {}, kinder: [], classList: { toggle() {} },
           addEventListener() {}, setAttribute() {}, removeAttribute() {}, focus() {}, showModal() {}, close() {},
           querySelector: () => null, replaceChildren(...kinder) { this.kinder = kinder; } };
}

async function frischGeladen(firmen) {
  const elemente = new Map();
  global.document = {
    title: "", documentElement: { dataset: {} },
    getElementById: id => elemente.get(id) || elemente.set(id, element(id)).get(id),
    querySelectorAll: () => [], querySelector: () => null,
  };
  global.window = {
    FirmenLogik: logik, KununuPruefen: { pruefe: async () => ({ geoeffnet: true }) },
    Texte: { text: schluessel => schluessel, statusName: status => status },
    App: { el, senden: async () => ({}), holen: async () => ({ firmen, heute: "2026-11-09" }), textsatz: async () => "stelle-sie" },
  };
  delete require.cache[require.resolve(SCRIPT)];
  require(SCRIPT);
  await new Promise(fertig => setImmediate(fertig));
  return new Map(document.getElementById("liste").kinder.map(zeile => [zeile.attrs["data-schluessel"], knoepfe(zeile).map(text)]));
}

const firma = (name, kununu) => ({ schluessel: name.toLowerCase().replace(/\W+/g, "-"), name, ort: "Bern", treffer: [{ id: "jobs-ch-1" }],
  bewerbungen: [], kununu, suche: `https://www.kununu.com/ch/search?q=${encodeURIComponent(name)}` });
const LINK = "https://www.kununu.com/ch/muster-industrie";

test("a fresh page offers Von Hand eintragen for every company without a stored value", async () => {
  const zeilen = await frischGeladen([
    firma("Muster Industrie AG", null),
    firma("Beispiel Bau AG", { zustand: "zugeordnet", link: LINK }),
    firma("Testlogistik GmbH", { zustand: "fehler" }),
    firma("Probe Handel AG", { zustand: "nicht_gefunden" }),
  ]);
  for (const schluessel of ["muster-industrie-ag", "beispiel-bau-ag", "testlogistik-gmbh", "probe-handel-ag"]) {
    assert.ok(zeilen.get(schluessel).includes("Von Hand eintragen"), schluessel);
  }
});

test("a company with a stored value gets no Von Hand eintragen", async () => {
  const zeilen = await frischGeladen([
    firma("Muster Industrie AG", { zustand: "gefunden", wert: 3.8, bewertungen: 214, geprueft_am: "2026-11-05", link: LINK, seite: "ch" }),
    firma("Beispiel Bau AG", { zustand: "gefunden", wert: 4.6, bewertungen: 3, geprueft_am: "2026-11-05", link: LINK, seite: "ch" }),
  ]);
  assert.deepEqual([...zeilen.values()].flat().filter(name => name === "Von Hand eintragen"), []);
});

const ALT = { zustand: "gefunden", wert: 3.2, bewertungen: 57, geprueft_am: "2026-07-02", link: LINK, seite: "ch" };

test("a failed Neu prüfen on Stellen suchen for a stale value leads to Von Hand eintragen on a fresh Firmen page", async () => {
  const stale = firma("Muster Industrie AG", ALT);
  const ergebnisse = [];
  global.document = { documentElement: { dataset: { bewerbungsbegleiterErweiterung: "1" } } };
  global.window = { App: { el }, FirmenLogik: logik, KununuPruefen: { pruefe: async () => ({ gelesen: false }) } };
  const trefferFirma = path.join(__dirname, "../seiten/treffer-firma.js");
  delete require.cache[require.resolve(trefferFirma)];
  require(trefferFirma);
  const zeile = window.TrefferFirma.zeile(stale, "2026-11-09", { wo: "Firmen", nachPruefen: e => ergebnisse.push(e) });
  const neu = knoepfe(zeile).find(k => text(k).startsWith("Neu prüfen"));
  await neu.attrs.onclick({ currentTarget: neu.attrs });
  assert.match(ergebnisse[0].text, /unter Firmen von Hand eintragen\.$/);

  const zeilen = await frischGeladen([stale]);  // nothing was stored, so the old value comes back
  assert.ok(zeilen.get("muster-industrie-ag").includes("Von Hand eintragen"));
});

test("every company Stellen suchen offers a check for gets Von Hand eintragen on Firmen", () => {
  const faelle = [null, { zustand: "zugeordnet", link: LINK }, { zustand: "fehler" }, { zustand: "nicht_gefunden" }, { zustand: "mehrere" },
    { zustand: "gefunden", bewertungen: 0, geprueft_am: "2026-07-02" }, ALT, { ...ALT, bewertungen: 4 },
    { ...ALT, geprueft_am: "2026-11-05" }, { ...ALT, bewertungen: 4, geprueft_am: "2026-11-05" }];
  for (const kununu of faelle) {
    const f = firma("Muster Industrie AG", kununu);
    const pruefbar = logik.firmenZeile(f, "2026-11-09").aktionen.some(a => a.art === "pruefen");
    if (pruefbar) assert.equal(logik.vonHandAnbieten(f, "2026-11-09"), true, JSON.stringify(kununu));
  }
});
