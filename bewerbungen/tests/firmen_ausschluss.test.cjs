// Follow-ups to excluding a company (#303, G65): the sidebar counts the new hits again, Was nicht saves in one
// request, and a hit, Firmen and an application use the same words for the action. Only invented companies.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const texte = require("../seiten/texte.js");
const sidebarLogic = require("../seiten/sidebar-logic.js");

const PAGES = path.join(__dirname, "..", "seiten");
const read = name => fs.readFileSync(path.join(PAGES, name), "utf8");
const settle = () => new Promise(resolve => setImmediate(resolve));
// Objects from the page's context compare by value only after crossing over.
const plain = value => JSON.parse(JSON.stringify(value));

/** An element that keeps what the scripts set and read; children by selector stay the same objects. */
function fakeElement() {
  const children = new Map();
  const handlers = {};
  return {
    hidden: false, disabled: false, textContent: "", value: "", dataset: {}, style: {}, attributes: {}, handlers,
    setAttribute(name, value) { this.attributes[name] = value; },
    getAttribute(name) { return this.attributes[name] ?? null; },
    toggleAttribute() {}, contains: () => false, focus() {}, replaceChildren() {},
    addEventListener(type, handler) { (handlers[type] ||= []).push(handler); },
    querySelector(selector) {
      if (!children.has(selector)) children.set(selector, fakeElement());
      return children.get(selector);
    },
    querySelectorAll: () => [],
  };
}

function fakeDocument() {
  const elements = new Map();
  const handlers = {};
  const fired = [];
  const nav = fakeElement();
  return {
    fired, nav, hidden: false, documentElement: { dataset: {} },
    getElementById(id) {
      if (!elements.has(id)) elements.set(id, fakeElement());
      return elements.get(id);
    },
    querySelector: selector => (selector === ".app-nav" ? nav : null),
    addEventListener(type, handler) { (handlers[type] ||= []).push(handler); },
    dispatchEvent(event) {
      fired.push(event.type);
      for (const handler of handlers[event.type] || []) handler(event);
      return true;
    },
  };
}

class FakeEvent {
  constructor(type, init = {}) { this.type = type; this.detail = init.detail; }
}

function context(document, extra) {
  const window = {
    App: {}, SidebarLogic: sidebarLogic, Texte: texte,
    addEventListener() {}, ...extra,
  };
  return vm.createContext({
    window, document, CustomEvent: FakeEvent, location: { pathname: "/treffer", origin: "http://127.0.0.1:1" },
    sessionStorage: { getItem: () => null, setItem() {} }, setTimeout: () => 0, console, Promise, Map, Set,
    Number, String, Array, Object, JSON, Math, Date, Infinity, Error,
  });
}

const run = (ctx, ...files) => { for (const file of files) vm.runInContext(read(file), ctx, { filename: file }); };

// The sidebar's „N neu“ next to Stellen

test("the sidebar counts the new hits again when hits change, without reloading the page", async () => {
  const document = fakeDocument();
  let hits = [{ zustand: "neu" }, { zustand: "neu" }, { zustand: "gemerkt" }];
  const holen = async pfad => {
    if (pfad === "/api/suche/liste") return { treffer: hits };
    if (pfad === "/api/rav/auswahl") return { sichtbar: false, bewerbungen: [] };
    return { bewerbungen: [] };
  };
  const ctx = context(document, {
    App: { holen }, UebersichtLogik: { stehtAn: () => [], mitSchritten: () => [] },
  });
  ctx.window.window = ctx.window;
  run(ctx, "sidebar.js");
  await settle();
  const long = document.getElementById("badge-stellen").querySelector(".app-nav__count-long");
  assert.equal(long.textContent, "2 neu");

  hits = [{ zustand: "neu" }];
  document.dispatchEvent(new FakeEvent(sidebarLogic.HITS_CHANGED));
  await settle();

  assert.equal(long.textContent, "1 neu");
});

test("the tabs of Stellen on Firmen count again too", async () => {
  const document = fakeDocument();
  const tabs = document.getElementById("reiter");
  tabs.dataset.zaehlen = "ja";
  let hits = [{ zustand: "neu" }, { zustand: "neu" }];
  const ctx = context(document, { App: { holen: async () => ({ treffer: hits }) } });
  run(ctx, "stellen-reiter.js");
  await settle();
  const fresh = tabs.querySelector('[data-zahl="neu"]');
  assert.equal(fresh.textContent, "2");

  hits = [];
  document.dispatchEvent(new FakeEvent(sidebarLogic.HITS_CHANGED));
  await settle();

  assert.equal(fresh.textContent, "0");
});

// One place for the requests, so every page tells the sidebar

function helper() {
  const document = fakeDocument();
  const posted = [];
  const answers = {
    "/api/firmen/ausschliessen": { firma: { schluessel: "muster bau", ausgeschlossen: true } },
    "/api/firmen/wieder-zeigen": { firma: { schluessel: "muster bau", ausgeschlossen: false } },
  };
  let failing = false;
  const senden = async (pfad, body) => {
    posted.push([pfad, plain(body)]);
    if (failing) throw new Error("Nicht erreichbar.");
    return answers[pfad];
  };
  const ctx = context(document, { App: { senden } });
  run(ctx, "firmen-ausschluss.js");
  return { api: ctx.window.FirmenAusschluss, posted, document, fail: () => { failing = true; } };
}

test("excluding a company sends its name once and tells the sidebar", async () => {
  const { api, posted, document } = helper();

  const firma = await api.ausschliessen("Muster Bau AG");

  assert.deepEqual(posted, [["/api/firmen/ausschliessen", { name: "Muster Bau AG" }]]);
  assert.equal(firma.ausgeschlossen, true);
  assert.deepEqual(document.fired, [sidebarLogic.HITS_CHANGED]);
});

test("taking a company back sends its key once and tells the sidebar", async () => {
  const { api, posted, document } = helper();

  const firma = await api.wiederZeigen("muster bau");

  assert.deepEqual(posted, [["/api/firmen/wieder-zeigen", { schluessel: "muster bau" }]]);
  assert.equal(firma.ausgeschlossen, false);
  assert.deepEqual(document.fired, [sidebarLogic.HITS_CHANGED]);
});

test("a failed change tells nobody and reaches the page", async () => {
  const { api, document, fail } = helper();
  fail();

  await assert.rejects(api.ausschliessen("Muster Bau AG"), /Nicht erreichbar/);
  assert.deepEqual(document.fired, []);
});

// The same words on a hit, on Firmen and on an application

const ACTION_PAGES = ["treffer.js", "firmen.js", "firma-ausschliessen.js"];
const OWN_WORDS = ["Nicht mehr zeigen", "Wieder zeigen", "Wieder in der Suche zeigen", "nicht ausgeschlossen",
  "nicht wieder gezeigt", "zeigt die Inserate wieder", "Rückgängig", "wird nicht wieder gezeigt"];
const SHARED_KEYS = ["firmen.ausschliessen", "firmen.wieder-zeigen", "firmen.ausgeschlossen", "firmen.wieder-gezeigt",
  "firmen.nicht-geaendert"];

test("hit, Firmen and application name the action with the same texts", () => {
  for (const name of ACTION_PAGES) {
    const code = read(name);
    for (const words of OWN_WORDS) assert.ok(!code.includes(`"${words}`) && !code.includes(`\`${words}`) && !code.includes(` ${words}.`), `${name}: own words „${words}“`);
    for (const key of SHARED_KEYS) assert.ok(code.includes(`"${key}"`), `${name}: ${key}`);
    assert.ok(!code.includes('"/api/firmen/ausschliessen"') && !code.includes('"/api/firmen/wieder-zeigen"'), `${name}: requests in firmen-ausschluss.js`);
    assert.match(code, /FirmenAusschluss\.ausschliessen\(/, name);
    assert.match(code, /FirmenAusschluss\.wiederZeigen\(/, name);
  }
});

test("the shared texts speak of a Lehrbetrieb for apprenticeships", () => {
  const values = { firma: "Muster Schreinerei" };
  for (const key of SHARED_KEYS) {
    assert.ok(texte.TEXTE[key], key);
    assert.match(texte.text(key, "lehrstelle-du", values), /Lehrbetrieb|Lehrstellen/, key);
    assert.doesNotMatch(texte.text(key, "stelle-sie", values), /Lehrbetrieb|Lehrstelle/, key);
  }
  assert.equal(texte.text("firmen.wieder-zeigen", "stelle-sie"), "Diese Firma wieder zeigen");
  assert.equal(texte.text("firmen.wieder-zeigen", "lehrstelle-du"), "Diesen Lehrbetrieb wieder zeigen");
});

test("every page with the action loads the shared script before its own", () => {
  for (const [html, own] of [["treffer.html", "/treffer.js"], ["firmen.html", "/firmen.js"], ["bewerbung.html", "/firma-ausschliessen.js"]]) {
    const scripts = [...read(html).matchAll(/<script src="([^"]+)"/g)].map(m => m[1]);
    assert.ok(scripts.includes("/firmen-ausschluss.js"), html);
    assert.ok(scripts.indexOf("/firmen-ausschluss.js") < scripts.indexOf(own), html);
  }
  assert.match(fs.readFileSync(path.join(__dirname, "..", "app.py"), "utf8"), /"\/firmen-ausschluss\.js": "firmen-ausschluss\.js"/);
});

// Was Sie nicht sehen wollen on Suche einstellen

function settingsPage(lehrstelle) {
  const document = fakeDocument();
  const posted = [];
  const senden = async (pfad, body) => { posted.push([pfad, plain(body)]); return {}; };
  const status = (element, text, art) => { element.textContent = text; element.dataset.level = art; };
  const ctx = context(document, { App: { senden, status, el: () => fakeElement() } });
  run(ctx, "suche-rahmen-logik.js", "suche-rahmen.js");
  ctx.window.SucheRahmen.zeige({ werte: { ausschluss: ["Schicht"], titel_ausschluss: [] } }, lehrstelle, [{ name: "Muster Bau AG" }]);
  return { document, posted, $: id => document.getElementById(id) };
}

async function saveNicht(page, values) {
  for (const handler of page.$("nicht-aendern").handlers.click) handler();
  for (const [id, value] of Object.entries(values)) page.$(id).value = value;
  for (const handler of page.$("nicht-form").handlers.submit) handler({ preventDefault() {} });
  await settle();
}

test("saving Was nicht sends exclusions and companies in one request", async () => {
  const page = settingsPage(false);

  await saveNicht(page, { "nicht-inserat": "Schicht\nPikett", "nicht-im-titel": "Praktikum", "nicht-firmen": "Muster Bau AG\nBeispiel Holz" });

  assert.deepEqual(page.posted, [["/api/suche/was-nicht",
    { ausschluss: ["Schicht", "Pikett"], titel_ausschluss: ["Praktikum"], firmen: ["Muster Bau AG", "Beispiel Holz"] }]]);
  assert.ok(page.document.fired.includes(sidebarLogic.HITS_CHANGED), "the sidebar counts again");
  assert.ok(page.document.fired.includes("suchprofil-geaendert"));
});

test("an apprenticeship's Was nicht sends only the companies, in the same request", async () => {
  const page = settingsPage(true);

  await saveNicht(page, { "nicht-firmen": "Muster Schreinerei" });

  assert.deepEqual(page.posted, [["/api/suche/was-nicht", { firmen: ["Muster Schreinerei"] }]]);
});

test("the other cards still save only the profile", async () => {
  const page = settingsPage(false);
  for (const handler of page.$("titelfilter-aendern").handlers.click) handler();
  page.$("titelfilter-positiv").value = "Python";
  for (const handler of page.$("titelfilter-form").handlers.submit) handler({ preventDefault() {} });
  await settle();

  assert.deepEqual(page.posted, [["/api/suche/rahmen", { titel_positiv: ["Python"], titel_ausschluss: [] }]]);
  assert.ok(!page.document.fired.includes(sidebarLogic.HITS_CHANGED));
});
