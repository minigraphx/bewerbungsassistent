// The switch for remote niche hits outside the region (G125, #390, extends G111), without DOM: when Suche einstellen
// shows it, and the four texts that say «mit Remote» or «ohne Remote» in their variant for the switch turned off.
// Invented terms; the cantons and towns are those of the invented template profile, or far from it.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const Anzeige = require("../seiten/suche-anzeige.js");
const Rahmen = require("../seiten/suche-rahmen-logik.js");
const Ertrag = require("../seiten/suche-ertrag-logik.js");

const REGION = { kantone: ["BE", "SO"], orte: ["Bern"], umkreis_km: 20, schweizweit: false, nischen: 2 };
const AUS = { ...REGION, nischen_remote: false };

test("the switch shows only in a job search with niches and chosen cantons", () => {
  assert.equal(Anzeige.nischenSchalter(REGION, false), true);
  assert.equal(Anzeige.nischenSchalter(AUS, false), true);
  assert.equal(Anzeige.nischenSchalter(REGION, true), false, "not for apprenticeships");
  assert.equal(Anzeige.nischenSchalter({ ...REGION, nischen: 0 }, false), false, "not without niches");
  assert.equal(Anzeige.nischenSchalter({ ...REGION, kantone: [], schweizweit: true }, false), false, "not without cantons");
  assert.equal(Anzeige.nischenSchalter(null, false), false);
});

test("the Nischen row keeps its wording while the switch is on, also when the page does not say", () => {
  const an = "Ohne Ort gesucht. Behalten werden Stellen in BE und SO, an Ihren Orten oder mit Remote.";
  assert.equal(Anzeige.nischenText(REGION, false), an);
  assert.equal(Anzeige.nischenText({ ...REGION, nischen_remote: true }, false), an);
});

test("with the switch off the Nischen row leaves out remote work, in the person's form of address", () => {
  assert.equal(Anzeige.nischenText(AUS, false), "Ohne Ort gesucht. Behalten werden Stellen in BE und SO und an Ihren Orten.");
  assert.equal(Anzeige.nischenText(AUS, false, true), "Ohne Ort gesucht. Behalten werden Stellen in BE und SO und an deinen Orten.");
  assert.equal(Anzeige.nischenText({ ...AUS, kantone: [], schweizweit: true }, false), "Ohne Ort gesucht, in der ganzen Schweiz.");
});

test("with the switch off the hint under the cantons says the app keeps no jobs outside them", () => {
  const ohne = "Ohne Auswahl sucht die App in der ganzen Schweiz, Stellen nahe dem Wohnort zuerst.";
  assert.equal(Rahmen.kantoneHinweis(false, 2, false), `${ohne} Nischen sucht die App ohne Ort; Stellen ausserhalb dieser `
    + "Kantone behält sie nicht.");
  assert.equal(Rahmen.kantoneHinweis(false, 2, true), `${ohne} Nischen sucht die App ohne Ort; Stellen ausserhalb dieser `
    + "Kantone behält sie nur, wenn das Inserat Remote nennt.");
  assert.equal(Rahmen.kantoneHinweis(false, 0, false), ohne);
});

const NISCHE = { portal: "", ort: "", ort_name: "", nischen: true, suchen: 30, treffer: 15, neu: 4, ab_note_4: 1, aussortiert: 0,
  ausserhalb_region: 31, ohne_ertrag: false,
  ausserhalb_orte: [{ ort: "Lugano", anzahl: 12 }, { ort: "St. Gallen", anzahl: 7 }], ausserhalb_andere: 12 };

test("with the switch off the caption under the niche row names no remote work", () => {
  assert.equal(Ertrag.ausserhalbOrte(NISCHE, false), "Ausserhalb der Region: Lugano 12, St. Gallen 7, andere 12");
  assert.equal(Ertrag.ausserhalbOrte(NISCHE, true), "Ausserhalb der Region, ohne Remote: Lugano 12, St. Gallen 7, andere 12");
  assert.equal(Ertrag.ausserhalbOrte(NISCHE), "Ausserhalb der Region, ohne Remote: Lugano 12, St. Gallen 7, andere 12");
});

test("with the switch off «Ausserhalb der Region» is explained without remote work", () => {
  const vorher = "Aus den letzten 3 Suchläufen, gezählt wie bei den Suchbegriffen. „Ohne Ort“ sind Suchen ohne Ortsangabe, etwa für die Nischen.";
  assert.equal(Ertrag.ortHinweis(3, true, false, false),
    `${vorher} „Ausserhalb der Region“: Die Stelle liegt ausserhalb Ihrer Kantone und Orte.`);
  assert.equal(Ertrag.ortHinweis(3, true, true, false),
    `${vorher} „Ausserhalb der Region“: Die Stelle liegt ausserhalb deiner Kantone und Orte.`);
  assert.match(Ertrag.ortHinweis(3, true, false, true), /und das Inserat nennt kein Remote\.$/);
  assert.equal(Ertrag.ortHinweis(3, false, false, false), vorher);
});

class FakeElement {
  constructor() { Object.assign(this, { attrs: new Map(), listeners: {}, checked: false, text: "" }); }
  setAttribute(name, value) { this.attrs.set(name, String(value)); }
  getAttribute(name) { return this.attrs.has(name) ? this.attrs.get(name) : null; }
  get hidden() { return this.attrs.has("hidden"); }
  set hidden(value) { if (value) this.attrs.set("hidden", ""); else this.attrs.delete("hidden"); }
  get textContent() { return this.text; }
  set textContent(value) { this.text = String(value); }
  replaceChildren(...nodes) { this.text = nodes.map(String).join(""); }
  addEventListener(type, handler) { (this.listeners[type] ||= []).push(handler); }
  querySelectorAll() { return []; }
}

const settle = async () => { for (let i = 0; i < 10; i += 1) await new Promise(resolve => setImmediate(resolve)); };

/** suche-einstellen.js with the stand-ins it needs; `region` as /api/suche/liste gives it, `senden` the POST. */
async function settingsPage(region, senden) {
  const elements = new Map();
  const events = [];
  const said = [];
  const doc = {
    getElementById(id) { if (!elements.has(id)) elements.set(id, new FakeElement()); return elements.get(id); },
    addEventListener() {},
    dispatchEvent(event) { events.push(event.type); },
  };
  const routes = {
    "/api/suche/liste": { art: "stelle", region, einstellungen: { auto_bewerten: false, zuschauen: false }, grenze: 1, portale: [] },
    "/api/suche/rahmen": { pensum: "", ausschluss: [], titel_ausschluss: [], titel_positiv: [], werte: {} },
    "/api/firmen/ausgeschlossen": { firmen: [] },
    "/api/suchbegriffe/schaetzung": { verfuegbar: false },
    "/api/suche/ertrag": { art: "stelle", begriffe: [], orte: [], laeufe: 0 },
  };
  const window = {
    App: { el: () => new FakeElement(), holen: async route => routes[route], senden,
      status: (zeile, text, stufe) => said.push({ zeile, text, stufe }), textsatz: async () => "stelle-sie" },
    Texte: { ...require("../seiten/texte.js"), anwenden: () => {} },
    SucheAnzeige: Anzeige, DotLine: { render: () => [] }, TrefferLogik: { wahlAus: () => "lehrstelle" },
    SuchbegriffeLogik: {}, SucheRahmen: { zeige() {} }, TitelfilterBeispiele: { begriffe() {}, beispiele() {} },
    Suchbegriffe: { zeige() {} }, Suchliste: { portale() {}, pflicht() {} }, PortalWahl: { zeige() {} },
    SucheErtrag: { zeige() {} }, DoppeltGesucht: { lade() {} }, OrteHinweise: { lade() {} },
  };
  const context = { window, document: doc, console, setTimeout, CustomEvent: class { constructor(type) { this.type = type; } } };
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.join(__dirname, "..", "seiten", "suche-einstellen.js"), "utf8"), context);
  await settle();
  const schalter = doc.getElementById("nischen-remote-schalter");
  const umschalten = async () => {
    schalter.checked = !schalter.checked;
    for (const handler of schalter.listeners.change || []) handler({ target: schalter });
    await settle();
  };
  return { section: doc.getElementById("nischen-remote"), schalter, umschalten, events, said };
}

test("the page shows the switch where it applies, set as the profile says", async () => {
  const an = await settingsPage(REGION, async () => ({}));
  assert.equal(an.section.hidden, false);
  assert.equal(an.schalter.checked, true);
  const aus = await settingsPage(AUS, async () => ({}));
  assert.equal(aus.schalter.checked, false);
  const ohneKantone = await settingsPage({ ...REGION, kantone: [], schweizweit: true }, async () => ({}));
  assert.equal(ohneKantone.section.hidden, true);
});

test("switching saves through the card route and reloads the page, a refusal puts the switch back", async () => {
  const sent = [];
  const page = await settingsPage(REGION, async (route, body) => { sent.push([route, body]); return {}; });
  await page.umschalten();
  assert.deepEqual(JSON.parse(JSON.stringify(sent)), [["/api/suche/rahmen", { nischen_remote: false }]]);  // from the page's realm
  assert.deepEqual(page.events, ["suchprofil-geaendert"]);
  assert.deepEqual(page.said.map(m => [m.text, m.stufe]), [["Gespeichert. Gilt ab der nächsten Suche.", "ok"]]);

  const refused = await settingsPage(REGION, async () => { throw new Error("Zuerst Meine Angaben abschliessen."); });
  await refused.umschalten();
  assert.equal(refused.schalter.checked, true);
  assert.deepEqual(refused.events, []);
  assert.deepEqual(refused.said.map(m => [m.text, m.stufe]), [["Nicht gespeichert. Zuerst Meine Angaben abschliessen.", "fehler"]]);
});

test("Suche einstellen has the switch in its own section Nischen under Erweitert, after Titelfilter and before Ablauf", () => {
  const html = fs.readFileSync(path.join(__dirname, "..", "seiten", "suche-einstellen.html"), "utf8");
  const erweitert = html.slice(html.indexOf('<details id="erweitert"'));
  const titelfilter = erweitert.indexOf('id="titelfilter"');
  const nischen = erweitert.indexOf('<section id="nischen-remote"');
  const ablauf = erweitert.indexOf('aria-labelledby="ablauf-titel"');
  assert.ok(titelfilter > 0 && titelfilter < nischen && nischen < ablauf);
  const teil = erweitert.slice(nischen, ablauf);
  assert.match(teil, /<h3 id="nischen-remote-titel">Nischen<\/h3>/);
  assert.match(teil, /<label class="switch"><input type="checkbox" role="switch" id="nischen-remote-schalter"/);
  assert.match(teil, /Nischen-Treffer ausserhalb der Region behalten, wenn das Inserat Remote nennt/);
  assert.match(teil, /<span class="search__hint">Gilt auch, wenn das Suchprofil Remote ausschliesst\. Ist der Schalter aus, sortiert die App sie aus wie andere Treffer ausserhalb der Region\.<\/span>/);
  assert.match(teil, /<section id="nischen-remote"[^>]* hidden>/, "hidden until the page knows it applies");
});
