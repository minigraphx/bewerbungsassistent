// „N neu“ in the sidebar after a hit changes its state on Stellen and Lehrstellen (#311): the page tells the
// sidebar to count again whenever the number of new hits changes, as excluding a company does since #303.
// The summary under the title („N Treffer, M neu“) follows the same changes without a reload (#317).
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const anzeige = require("../seiten/suche-anzeige.js");
const logik = require("../seiten/treffer-logik.js");
const texte = require("../seiten/texte.js");
const sidebarLogic = require("../seiten/sidebar-logic.js");
const DotLine = require("../seiten/dot-line.js");
const { shown, seenLine } = require("./dot_line_text.cjs");

const CODE = fs.readFileSync(path.join(__dirname, "..", "seiten", "treffer.js"), "utf8");
const ORIGIN = "http://127.0.0.1:1";
const NEW_HIT = { id: "h1", stelle: "Data Engineer", firma: "Muster AG", portal: "jobs.ch", link: "https://www.jobs.ch/x", zustand: "neu", gefunden_am: "2026-11-01" };
const OTHER_HIT = { ...NEW_HIT, id: "h2", stelle: "Data Analyst", firma: "Beispiel GmbH" };
const GRADE = { note: 4.5, zusammenfassung: "Passt gut.", passt: [], haken: [] };

/** A stand-in element that keeps what the page sets, and the children it gets as plain values. */
function element(tag = "div", attrs = {}, children = []) {
  const handlers = {};
  return {
    tag, attrs, children, hidden: false, disabled: false, textContent: "", value: "", dataset: {}, attributes: {},
    addEventListener(type, handler) { handlers[type] = handler; },
    fire(type) { return handlers[type]({ target: { checked: false } }); },
    setAttribute(key, value) { this.attributes[key] = value; },
    removeAttribute(key) { delete this.attributes[key]; },
    replaceChildren(...items) { this.children = items; },
    scrollIntoView() {}, focus() {},
    classList: { toggle() {}, add() {}, remove() {} },
  };
}

const textOf = node => (node && typeof node === "object" ? (node.children || []).flat().map(textOf).join("") : String(node ?? ""));
const nodes = node => (node && typeof node === "object" ? [node, ...(node.children || []).flat().flatMap(nodes)] : []);

/**
 * The page with a stand-in app that keeps the hits like the real one: Merken and Verwerfen change the stored
 * state, and every load returns the stored hits. `failing` names routes that are refused.
 */
function page({ hits = [NEW_HIT], art = "stelle", hash = "", failing = [], zeitraum = {} } = {}) {
  const elements = new Map();
  const $ = id => { if (!elements.has(id)) elements.set(id, element()); return elements.get(id); };
  const selected = new Map();
  const select = selector => { if (!selected.has(selector)) selected.set(selector, element()); return selected.get(selector); };
  for (const id of ["lauf-box", "bewerten-box"]) $(id).hidden = true;
  const stored = structuredClone(hits);
  const fired = [];
  let watch = null;
  const change = (id, fields) => {
    const index = stored.findIndex(hit => hit.id === id);
    stored[index] = { ...stored[index], ...fields };
    return structuredClone(stored[index]);
  };
  const routes = {
    "/api/suche/uebernehmen": (_, { id }) => change(id, { zustand: "uebernommen", bewerbung_id: "b7" }),
    "/api/suche/verwerfen": ({ zurueck }, { id }) => change(id, { zustand: zurueck ? "neu" : "verworfen" }),
    "/api/suche/bewerten": (_, { id }) => change(id, { bewertung: GRADE }),
    "/api/bewerbungen/stand": () => ({}),
  };
  const document = {
    title: "", getElementById: $, querySelectorAll: () => [], querySelector: select, addEventListener() {},
    dispatchEvent: event => fired.push(event.type),
    documentElement: { dataset: { bewerbungsbegleiterErweiterung: "1" } },
  };
  const window = {
    App: {
      holen: async pfad => {
        if (pfad === "/api/suche/liste") {
          return {
            treffer: structuredClone(stored), einstellungen: { auto_bewerten: false, zuschauen: false, beruf_sterne: {}, sortierung: "note" },
            paket: 10, grenze: 30, art, portale: ["jobs.ch"], portale_wahl: [], gesuchte_berufe: ["Data Engineer"],
            gesuchte_schluessel: [], hinweise: [], hinweis_ziele: {}, letzte_suche: { datum: "2026-11-01", portale: { "jobs.ch": {} } },
            region: { kantone: [], orte: ["Bern"], umkreis_km: 25, schweizweit: false }, sperrgrund: "", zeitraum,
          };
        }
        if (pfad === "/api/firmen") return { firmen: [], heute: "2026-11-02" };
        if (pfad === "/api/suche/alle-pruefen") return { anzahl: 0 };
        throw new Error(`unexpected ${pfad}`);
      },
      senden: async (pfad, body = {}, query = {}) => {
        if (failing.includes(pfad)) throw new Error("Nicht erreichbar.");
        if (!routes[pfad]) return {};
        return routes[pfad](body, query);
      },
      el: (tag, attrs, ...children) => element(tag, attrs || {}, children),
      status() {}, datum: String, beobachten: callback => { watch = callback; }, textsatz: async () => "stelle-sie",
    },
    TrefferLogik: logik,
    SuchlaufLogik: require("../seiten/suchlauf-logik.js"),
    SucheAnzeige: anzeige,
    DotLine,
    Texte: texte,
    SidebarLogic: sidebarLogic,
    Meldungen: { zeige() {}, leere() {} },
    FirmenLogik: { nachTreffer: () => new Map() },
    TrefferFirma: { zeile: () => null, marke: () => null },
    PortalWahl: { zeige() {} },
    Suchbegriffe: { zeige() {} },
    SuchbegriffeStart: { zeige() {}, ids: () => null },
    Sidebar: { currency: Promise.resolve("USD") },
    addEventListener() {},
    postMessage() {},
    matchMedia: () => ({ matches: false }),
  };
  const context = {
    window, document, URLSearchParams, console,
    CustomEvent: class { constructor(type) { this.type = type; } },
    localStorage: { getItem: () => null, setItem() {} },
    location: { origin: ORIGIN, hash, pathname: "/treffer", search: "", href: "" },
    history: { replaceState() {} },
    setTimeout: () => 0,
    clearTimeout() {},
  };
  vm.runInNewContext(CODE, context);
  const button = label => nodes({ children: $("detail").children }).find(n => n.tag === "button" && textOf(n) === label);
  const press = async label => {
    const found = button(label);
    assert.ok(found, `a button ${label}`);
    if (found.attrs.onclick) found.attrs.onclick();
    else found.fire("click");
    await settle();
  };
  const addHit = hit => stored.push(structuredClone(hit));
  const summary = () => shown($("letzte"));
  const newTab = () => select("[data-zahl=neu]").textContent;
  return { fired, press, addHit, summary, newTab, look: async () => { await watch(); await settle(); } };
}

const settle = async () => { for (let i = 0; i < 10; i += 1) await new Promise(resolve => setImmediate(resolve)); };
const CHANGED = sidebarLogic.HITS_CHANGED;

test("loading the page leaves the count to the sidebar", async () => {
  const p = page();
  await settle();
  assert.deepEqual(p.fired, []);
});

test("Merken tells the sidebar to count the new hits again", async () => {
  const p = page();
  await settle();
  await p.press("Merken");
  assert.deepEqual(p.fired, [CHANGED]);
});

test("Verwerfen tells the sidebar to count again", async () => {
  const p = page();
  await settle();
  await p.press("Verwerfen");
  assert.deepEqual(p.fired, [CHANGED]);
});

test("Zurückholen, the undo of Verwerfen, tells the sidebar to count again", async () => {
  const p = page({ hits: [{ ...NEW_HIT, zustand: "verworfen" }], hash: "#verworfen" });
  await settle();
  await p.press("Zurückholen");
  assert.deepEqual(p.fired, [CHANGED]);
});

test("on Lehrstellen Merken and Verwerfen count again too", async () => {
  const p = page({ hits: [NEW_HIT, OTHER_HIT], art: "lehrstelle" });
  await settle();
  await p.press("Merken");
  await p.press("Verwerfen");
  assert.deepEqual(p.fired, [CHANGED, CHANGED]);
});

test("a refused Merken or Verwerfen changes no count", async () => {
  const p = page({ failing: ["/api/suche/uebernehmen", "/api/suche/verwerfen"] });
  await settle();
  await p.press("Verwerfen");
  await p.press("Merken");
  assert.deepEqual(p.fired, []);
});

test("Bewerbung vorbereiten that saved the hit but could not set Bewerben still counts again", async () => {
  const p = page({ failing: ["/api/bewerbungen/stand"] });
  await settle();
  await p.press("Bewerbung vorbereiten");
  assert.deepEqual(p.fired, [CHANGED]);
});

test("rating a hit keeps it new, so the sidebar is not asked", async () => {
  const p = page();
  await settle();
  await p.press("Bewerten");
  assert.deepEqual(p.fired, []);
});

test("hits that arrive while the page is open count again, an unchanged list does not", async () => {
  const p = page();
  await settle();
  await p.look();
  assert.deepEqual(p.fired, []);
  p.addHit(OTHER_HIT);
  await p.look();
  assert.deepEqual(p.fired, [CHANGED]);
});

// A «·» line of whole parts (#342): each «·» is glued to the part before it
const LAST_RUN = seenLine(["Letzte Suche am 2026-11-01", "jobs.ch", ""]);

test("Merken updates the summary under the title, as the tab shows it", async () => {
  const p = page();
  await settle();
  assert.equal(p.summary(), `${LAST_RUN}1 Treffer, 1 neu`);
  await p.press("Merken");
  assert.equal(p.summary(), `${LAST_RUN}1 Treffer, 0 neu`);
  assert.equal(p.newTab(), "0");
});

test("Verwerfen updates the summary under the title", async () => {
  const p = page();
  await settle();
  await p.press("Verwerfen");
  assert.equal(p.summary(), `${LAST_RUN}1 Treffer, 0 neu`);
  assert.equal(p.newTab(), "0");
});

test("Zurückholen updates the summary under the title", async () => {
  const p = page({ hits: [{ ...NEW_HIT, zustand: "verworfen" }], hash: "#verworfen" });
  await settle();
  assert.equal(p.summary(), `${LAST_RUN}1 Treffer, 0 neu`);
  await p.press("Zurückholen");
  assert.equal(p.summary(), `${LAST_RUN}1 Treffer, 1 neu`);
  assert.equal(p.newTab(), "1");
});

test("on Lehrstellen the summary follows Merken and Verwerfen too", async () => {
  const p = page({ hits: [NEW_HIT, OTHER_HIT], art: "lehrstelle" });
  await settle();
  await p.press("Merken");
  assert.equal(p.summary(), `${LAST_RUN}2 Treffer, 1 neu`);
  await p.press("Verwerfen");
  assert.equal(p.summary(), `${LAST_RUN}2 Treffer, 0 neu`);
  assert.equal(p.newTab(), "0");
});

test("the summary keeps the day of the last search when the count changes", async () => {
  const p = page({ zeitraum: { letzte: "heute" } });
  await settle();
  await p.press("Merken");
  assert.equal(p.summary(), seenLine(["Letzte Suche heute", "jobs.ch", "1 Treffer, 0 neu"]));
});

test("a refused Merken or Verwerfen leaves the summary as it was", async () => {
  const p = page({ failing: ["/api/suche/uebernehmen", "/api/suche/verwerfen"] });
  await settle();
  await p.press("Verwerfen");
  await p.press("Merken");
  assert.equal(p.summary(), `${LAST_RUN}1 Treffer, 1 neu`);
});
