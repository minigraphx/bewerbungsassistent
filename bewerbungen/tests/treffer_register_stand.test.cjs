// #373: each hit taken into the register shows the stage of its application on Stellen, as on Bewerbungen. Finished
// ones (Zusage, Absage, Verworfen, Zurückgezogen, or the application deleted) leave the tab and its count; the footer
// «Abgeschlossen: …» shows them with «Anzeigen». The page runs with a stand-in app; all data is invented.
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

const SEITEN = path.join(__dirname, "..", "seiten");
const CODE = fs.readFileSync(path.join(SEITEN, "treffer.js"), "utf8");
const TABS_CODE = fs.readFileSync(path.join(SEITEN, "stellen-reiter.js"), "utf8");
const ORIGIN = "http://127.0.0.1:1";
const HIT = { id: "h1", stelle: "Data Engineer", firma: "Muster AG", portal: "jobs.ch", link: "https://www.jobs.ch/x", zustand: "neu",
  gefunden_am: "2026-11-01", bewertung: { note: 5, zusammenfassung: "Passt gut.", passt: [], haken: [] } };
const OTHER = { ...HIT, id: "h2", stelle: "Data Analyst", firma: "Beispiel GmbH", bewertung: { ...HIT.bewertung, note: 4 } };
const SAVED = { ...HIT, zustand: "uebernommen", bewerbung_id: "b1", stand: "Gemerkt" };

function element(tag = "div", attrs = {}, children = []) {
  const handlers = {};
  return {
    tag, attrs, children, hidden: false, disabled: false, textContent: "", value: "", dataset: {}, attributes: {},
    addEventListener(type, handler) { handlers[type] = handler; },
    fire(type) { return handlers[type]({ target: { checked: false } }); },
    setAttribute(key, value) { this.attributes[key] = value; },
    removeAttribute(key) { delete this.attributes[key]; },
    replaceChildren(...items) { this.children = items; },
    scrollIntoView() {}, focus() { this.focused = true; },
    classList: { toggle() {}, add() {}, remove() {} },
  };
}

const textOf = node => (node && typeof node === "object"
  ? (node.children || []).flat().map(textOf).join("") || node.textContent || "" : String(node ?? ""));
const nodes = node => (node && typeof node === "object" ? [node, ...(node.children || []).flat().flatMap(nodes)] : []);

/** The page Stellen with a stand-in app that keeps the hits; `stage` changes an application as Bewerbungen would. */
function page({ hits = [HIT], art = "stelle", hash = "#in-bewerbungen", satz = "stelle-sie" } = {}) {
  const elements = new Map();
  const $ = id => { if (!elements.has(id)) elements.set(id, element()); return elements.get(id); };
  const selected = new Map();
  const select = selector => { if (!selected.has(selector)) selected.set(selector, element()); return selected.get(selector); };
  for (const id of ["lauf-box", "bewerten-box"]) $(id).hidden = true;
  let stored = structuredClone(hits);
  let watch = null;
  const change = (id, fields) => {
    stored = stored.map(hit => (hit.id === id ? { ...hit, ...fields } : hit));
    return structuredClone(stored.find(hit => hit.id === id));
  };
  const routes = {
    "/api/suche/uebernehmen": (_, { id }) => change(id, { zustand: "uebernommen", bewerbung_id: `b-${id}`, stand: "Gemerkt" }),
    "/api/bewerbungen/stand": () => ({}),
  };
  const document = {
    title: "", getElementById: $, querySelectorAll: () => [], querySelector: select, addEventListener() {}, dispatchEvent() {},
    documentElement: { dataset: { bewerbungsbegleiterErweiterung: "1" } },
  };
  const window = {
    App: {
      holen: async pfad => {
        if (pfad === "/api/suche/liste") {
          return {
            treffer: structuredClone(stored), einstellungen: { auto_bewerten: false, zuschauen: false, beruf_sterne: {}, sortierung: "note" },
            paket: 10, grenze: 30, art, portale: ["jobs.ch"], portale_wahl: [], gesuchte_berufe: [], gesuchte_schluessel: [],
            hinweise: [], hinweis_ziele: {}, letzte_suche: { datum: "2026-11-01", portale: { "jobs.ch": {} } },
            region: null, sperrgrund: "", zeitraum: {},
          };
        }
        if (pfad === "/api/firmen") return { firmen: [], heute: "2026-11-02" };
        if (pfad === "/api/suche/alle-pruefen") return { anzahl: 0 };
        throw new Error(`unexpected ${pfad}`);
      },
      senden: async (pfad, body = {}, query = {}) => (routes[pfad] ? routes[pfad](body, query) : {}),
      el: (tag, attrs, ...children) => element(tag, attrs || {}, children),
      status() {}, datum: String, beobachten: callback => { watch = callback; }, textsatz: async () => satz,
    },
    TrefferLogik: logik, SuchlaufLogik: require("../seiten/suchlauf-logik.js"), SucheAnzeige: anzeige, DotLine, Texte: texte,
    SidebarLogic: sidebarLogic, Meldungen: { zeige() {}, leere() {} }, FirmenLogik: { nachTreffer: () => new Map() },
    TrefferFirma: { zeile: () => null, marke: () => null }, WiederLogik: require("../seiten/wieder-logik.js"),
    TrefferWieder: { zeile: () => null, vermittler: () => null, marke: () => "", gleicheInserate: () => null }, HakenAusschluss: { liste: () => null }, PortalWahl: { zeige() {} }, Suchbegriffe: { zeige() {} },
    SuchbegriffeStart: { zeige() {}, ids: () => null }, Sidebar: { currency: Promise.resolve("USD") },
    addEventListener() {}, postMessage() {}, matchMedia: () => ({ matches: false }),
  };
  const location = { origin: ORIGIN, hash, pathname: "/treffer", search: "", href: "" };
  let hashchange = null;
  window.addEventListener = (type, handler) => { if (type === "hashchange") hashchange = handler; };
  vm.runInNewContext(CODE, {
    window, document, URLSearchParams, console, CustomEvent: class { constructor(type) { this.type = type; } },
    localStorage: { getItem: () => null, setItem() {} }, location, history: { replaceState() {} },
    setTimeout: () => 0, clearTimeout() {},
  });
  const rows = () => $("liste").hidden ? [] : $("liste").children;
  const detailButton = label => nodes({ children: $("detail").children }).find(n => ["button", "a"].includes(n.tag) && textOf(n) === label);
  const toggle = $("liste-fuss-knopf");
  return {
    $, rows, detailButton, toggle,
    count: () => select("[data-zahl=uebernommen]").textContent,
    footer: () => ($("liste-fuss").hidden ? "" : `${$("liste-fuss-text").textContent} ${toggle.textContent}`),
    stage: async (id, stand) => { change(id, { stand }); await watch(); await settle(); },
    remove: async id => { change(id, { stand: null }); await watch(); await settle(); },
    press: async label => { const found = detailButton(label); assert.ok(found, label); found.fire("click"); await settle(); },
    tab: async newHash => { location.hash = newHash; hashchange(); await settle(); },
    pressToggle: async () => { toggle.fire("click"); await settle(); },
  };
}

const settle = async () => { for (let i = 0; i < 10; i += 1) await new Promise(resolve => setImmediate(resolve)); };
const isBadge = n => ((n.attrs || {}).class || "").split(" ").includes("marke-status");
const badgeOf = row => nodes(row).find(isBadge);

test("a hit set to Beworben shows «Beworben» in its row and still counts", async () => {
  const p = page({ hits: [{ ...SAVED }] });
  await settle();
  await p.stage("h1", "Beworben");
  assert.equal(p.rows().length, 1);
  const badge = badgeOf(p.rows()[0]);
  assert.equal(textOf(badge), "Beworben");
  assert.equal(badge.attrs["data-status"], "Beworben");
  assert.match(textOf(p.rows()[0]), /Data Engineer.*Muster AG.*Beworben/, "the badge comes after the company line, in the row's name");
  assert.equal(p.count(), "1");
  assert.equal(p.footer(), "", "no footer while nothing is finished");
});

test("a hit set to Absage leaves the count and shows only after «Anzeigen»", async () => {
  const p = page({ hits: [{ ...SAVED }, { ...OTHER, zustand: "uebernommen", bewerbung_id: "b2", stand: "Beworben" }] });
  await settle();
  assert.equal(p.count(), "2");
  await p.stage("h1", "Absage");
  assert.equal(p.count(), "1");
  assert.deepEqual(p.rows().map(row => textOf(badgeOf(row))), ["Beworben"]);
  assert.equal(p.footer(), "Abgeschlossen: 1 Absage. Anzeigen");
  assert.equal(p.toggle.attributes["aria-expanded"], "false");
  await p.pressToggle();
  assert.deepEqual(p.rows().map(row => textOf(badgeOf(row))), ["Beworben", "Absage"], "the finished ones come at the end");
  assert.equal(p.footer(), "Abgeschlossen: 1 Absage. Ausblenden");
  assert.equal(p.toggle.attributes["aria-expanded"], "true");
  assert.equal(p.count(), "1", "showing them leaves the count alone");
  await p.pressToggle();
  assert.equal(p.rows().length, 1);
});

test("the footer names each finished stage in the words of Bewerbungen", async () => {
  const finished = ["Zusage", "Absage", "Absage", "Absage", "Verworfen", "Verworfen", "Zurückgezogen"].map((stand, i) => (
    { ...SAVED, id: `f${i}`, bewerbung_id: `b${i}`, stand }));
  const p = page({ hits: [...finished, { ...SAVED, id: "gone", bewerbung_id: "bx", stand: null }] });
  await settle();
  assert.equal(p.count(), "0");
  assert.equal(p.footer(),
    "Abgeschlossen: 1 Zusage, 3 Absagen, 2 verworfen, 1 zurückgezogen, 1 nicht mehr unter Bewerbungen. Anzeigen");
});

// one wording for Sie and du, from the UI/UX build review of #373
const ALL_FINISHED = {
  titel: "Alles abgeschlossen",
  text: "Jede Bewerbung aus diesen Treffern ist abgeschlossen. „Anzeigen“ unten zeigt sie.",
};

test("the tab with only finished hits says so and points to «Anzeigen»", () => {
  assert.deepEqual(anzeige.leer("uebernommen", true, "", true), ALL_FINISHED);
  assert.deepEqual(anzeige.leer("uebernommen", false, "", true), ALL_FINISHED);
});

test("with every saved hit finished, the empty tab still offers «Anzeigen»", async () => {
  const p = page({ hits: [{ ...SAVED, stand: "Zusage" }] });
  await settle();
  assert.equal(p.rows().length, 0);
  assert.equal(p.$("leer").hidden, false);
  assert.equal(p.$("leer-titel").textContent, ALL_FINISHED.titel);
  assert.equal(p.$("leer-text").textContent, ALL_FINISHED.text);
  assert.equal(p.$("ergebnisse").hidden, false, "the footer stays reachable");
  assert.equal(p.footer(), "Abgeschlossen: 1 Zusage. Anzeigen");
  await p.pressToggle();
  assert.equal(p.rows().length, 1);
  assert.equal(p.$("leer").hidden, true);
});

test("a deleted application reads «Nicht mehr unter Bewerbungen» without «Zur Bewerbung»", async () => {
  const p = page({ hits: [{ ...SAVED, stand: null }] });
  await settle();
  await p.pressToggle();
  assert.equal(textOf(badgeOf(p.rows()[0])), "Nicht mehr unter Bewerbungen");
  assert.equal(p.detailButton("Zur Bewerbung"), undefined);
  assert.equal(textOf(badgeOf({ children: p.$("detail").children })), "Nicht mehr unter Bewerbungen");
});

test("the detail shows the badge, then «Zur Bewerbung»", async () => {
  const p = page({ hits: [{ ...SAVED, stand: "Bewerben" }] });
  await settle();
  const all = nodes({ children: p.$("detail").children });
  const badge = all.findIndex(isBadge);
  const link = all.findIndex(n => n.tag === "a" && textOf(n) === "Zur Bewerbung");
  assert.ok(badge >= 0 && link > badge, "badge before the link");
});

test("on Lehrstellen an interview reads «Einladung», from the texts, not the stage", async () => {
  const p = page({ hits: [{ ...SAVED, stand: "Gespräch" }], art: "lehrstelle", satz: "lehrstelle-du" });
  await settle();
  const badge = badgeOf(p.rows()[0]);
  assert.equal(textOf(badge), "Einladung");
  assert.equal(badge.attrs["data-status"], "Gespräch");
});

test("Merken shows the new hit as Gemerkt under the tab", async () => {
  const p = page({ hash: "#neu" });
  await settle();
  await p.press("Merken");
  await p.tab("#in-bewerbungen");
  assert.equal(textOf(badgeOf(p.rows()[0])), "Gemerkt");
  assert.equal(p.count(), "1");
});

test("the caption stands only over the tab In Bewerbungen, the old address #gemerkt leads there too (#374)", async () => {
  const p = page({ hits: [{ ...SAVED }, { ...OTHER }], hash: "#neu" });
  await settle();
  assert.equal(p.$("reiter-erklaerung").hidden, true);
  await p.tab("#in-bewerbungen");
  assert.equal(p.$("reiter-erklaerung").hidden, false);
  assert.deepEqual(p.rows().map(row => textOf(badgeOf(row))), ["Gemerkt"]);
  await p.tab("#verworfen");
  assert.equal(p.$("reiter-erklaerung").hidden, true);
  await p.tab("#gemerkt");
  assert.equal(p.$("reiter-erklaerung").hidden, false);
  assert.deepEqual(p.rows().map(row => textOf(badgeOf(row))), ["Gemerkt"]);
});

test("the empty tab In Bewerbungen says how a hit comes there (#374)", async () => {
  const p = page({ hash: "#in-bewerbungen" });
  await settle();
  assert.equal(p.$("leer").hidden, false);
  assert.equal(p.$("leer-titel").textContent, "Noch nichts in Bewerbungen");
  assert.equal(p.$("leer-text").textContent, "Mit Merken oder Bewerbung vorbereiten kommt ein Treffer hierher.");
  assert.equal(p.$("reiter-erklaerung").hidden, false);
});

test("the stage never changes the order: a lower grade stays below", async () => {
  const p = page({ hits: [{ ...SAVED, stand: "Gemerkt" }, { ...OTHER, zustand: "uebernommen", bewerbung_id: "b2", stand: "Gespräch" }] });
  await settle();
  assert.deepEqual(p.rows().map(row => textOf(badgeOf(row))), ["Gemerkt", "Gespräch"]);
});

test("finished means the view «Abgeschlossen» of Bewerbungen, or deleted", () => {
  const uebersicht = require("../seiten/uebersicht-logik.js");
  for (const stand of ["Gemerkt", "Bewerben", "Beworben", "Gespräch"]) {
    assert.equal(logik.istAbgeschlossen({ ...SAVED, stand }), false, stand);
  }
  for (const stand of uebersicht.ABGESCHLOSSEN) assert.equal(logik.istAbgeschlossen({ ...SAVED, stand }), true, stand);
  assert.deepEqual([...uebersicht.ABGESCHLOSSEN].sort(), ["Absage", "Verworfen", "Zurückgezogen", "Zusage"]);
  assert.equal(logik.istAbgeschlossen({ ...SAVED, stand: null }), true);
  assert.equal(logik.istAbgeschlossen({ ...SAVED, stand: undefined }), false, "without word from the app it stays");
  assert.equal(logik.istAbgeschlossen({ ...HIT, stand: "Absage" }), false, "only hits taken over");
});

test("on Firmen the tab counts the saved hits without the finished ones", async () => {
  const counts = {};
  const tabs = {
    dataset: { zaehlen: "ja" },
    querySelector: selector => ({ set textContent(value) { counts[selector] = value; } }),
  };
  const hits = [{ ...HIT }, { ...SAVED }, { ...SAVED, id: "h3", stand: "Absage" }, { ...SAVED, id: "h4", stand: null },
    { ...OTHER, zustand: "verworfen" }];
  vm.runInNewContext(TABS_CODE, {
    document: { getElementById: () => tabs, addEventListener() {} },
    window: { App: { holen: async () => ({ treffer: hits }) }, TrefferLogik: logik },
  });
  await settle();
  assert.deepEqual(counts, { '[data-zahl="neu"]': "1", '[data-zahl="uebernommen"]': "1", '[data-zahl="verworfen"]': "1" });
});
