// Stellen suchen quick wins (#220, UX findings 8 and 9, quick win 13): clearer words, closed settings with a summary,
// the reason under a disabled „Jetzt suchen“, the right empty texts and one name for tab and page.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const anzeige = require("../seiten/suche-anzeige.js");
const logik = require("../seiten/treffer-logik.js");
const texte = require("../seiten/texte.js");

const SEITEN = path.join(__dirname, "..", "seiten");
const ROOT = path.join(__dirname, "..");
const HTML = fs.readFileSync(path.join(SEITEN, "treffer.html"), "utf8");
const CODE = fs.readFileSync(path.join(SEITEN, "treffer.js"), "utf8");
const ORIGIN = "http://127.0.0.1:1";
const HIT = { id: "h1", stelle: "Data Engineer", firma: "Muster AG", portal: "jobs.ch", link: "https://www.jobs.ch/x", zustand: "neu", gefunden_am: "2026-11-01" };

/** A stand-in element that keeps what the page sets, and the children it gets as plain values. */
function element(tag = "div", attrs = {}, children = []) {
  const handlers = {};
  return {
    tag, attrs, children, hidden: false, disabled: false, textContent: "", value: "", dataset: {}, attributes: {},
    addEventListener(type, handler) { handlers[type] = handler; },
    fire(type) { return handlers[type]({ target: { checked: false } }); },
    setAttribute(key, value) { this.attributes[key] = value; },
    replaceChildren(...items) { this.children = items; },
    scrollIntoView() {}, focus() {},
    classList: { toggle() {}, add() {}, remove() {} },
  };
}

/** Text of an element made with App.el, children included. */
const textOf = node => (node && typeof node === "object" ? (node.children || []).flat().map(textOf).join("") : String(node ?? ""));

function page({ liste = {}, uebernehmen = {}, erweiterung = true } = {}) {
  const elements = new Map();
  const $ = id => { if (!elements.has(id)) elements.set(id, element()); return elements.get(id); };
  for (const id of ["lauf-box", "bewerten-box", "einstellen"]) $(id).hidden = true;  // hidden in treffer.html
  const messages = [];
  const timers = [];
  const daten = {
    treffer: [], einstellungen: { auto_bewerten: false, zuschauen: false, beruf_sterne: {}, sortierung: "note" },
    paket: 10, grenze: 30, art: "stelle", portale: ["job-room", "jobs.ch", "jobscout24", "ictjobs"], portale_wahl: [],
    gesuchte_berufe: ["Data Engineer", "Analyst"], gesuchte_schluessel: [], hinweise: [], hinweis_ziele: {},
    letzte_suche: null, region: { kantone: [], orte: ["Bern"], umkreis_km: 25, schweizweit: false }, sperrgrund: "", ...liste,
  };
  const document = {
    title: "", getElementById: $, querySelectorAll: () => [], querySelector: () => element(), addEventListener() {},
    documentElement: { dataset: erweiterung ? { bewerbungsbegleiterErweiterung: "1" } : {} },
  };
  const window = {
    App: {
      holen: async pfad => {
        if (pfad === "/api/suche/liste") return structuredClone(daten);
        if (pfad === "/api/firmen") return { firmen: [], heute: "2026-11-02" };
        if (pfad === "/api/angaben/offen") return { offen: false };
        throw new Error(`unexpected ${pfad}`);
      },
      senden: async pfad => (pfad === "/api/suche/uebernehmen" ? { ...HIT, zustand: "uebernommen", bewerbung_id: "b7", ...uebernehmen } : {}),
      el: (tag, attrs, ...children) => element(tag, attrs || {}, children),
      status() {}, datum: String, beobachten() {}, textsatz: async () => "stelle-sie",
    },
    TrefferLogik: logik,
    SucheAnzeige: anzeige,
    Texte: texte,
    Meldungen: { zeige: (el, inhalt, stufe) => messages.push({ el, inhalt, stufe }), leere() {} },
    FirmenLogik: { nachTreffer: () => new Map() },
    TrefferFirma: { zeile: () => null, marke: () => null },
    PortalWahl: { zeige() {} },
    Suchbegriffe: { zeige() {} },
    addEventListener() {},
    postMessage() {},
    matchMedia: () => ({ matches: false }),
  };
  const context = {
    window, document, URLSearchParams, console,
    localStorage: { getItem: () => "1", setItem() {} },  // an old „keep open“ must not open the settings any more
    location: { origin: ORIGIN },
    setTimeout: (f, ms) => { timers.push({ f, ms }); return timers.length; },
    clearTimeout() {},
  };
  vm.runInNewContext(CODE, context);
  return { $, messages, document, timers };
}

const settle = async () => { for (let i = 0; i < 5; i += 1) await new Promise(resolve => setImmediate(resolve)); };

test("the browser tab and the page both say Stellen suchen", async () => {
  assert.match(HTML, /<title>Stellen suchen<\/title>/);
  assert.match(HTML, /<h1 id="titel" data-text="nav.suche">Stellen suchen<\/h1>/);
  const p = page();
  await settle();
  assert.equal(p.document.title, "Stellen suchen");
});

test("Suche einstellen is closed on opening and sums itself up in one line with Ändern", async () => {
  const p = page({ liste: { treffer: [] } });
  await settle();
  assert.equal(p.$("einstellen").hidden, true);
  assert.equal(p.$("einstellen-zeile").hidden, false);
  assert.equal(p.$("einstellen-text").textContent, "Sucht nach Data Engineer, Analyst · ganze Schweiz, nahe Bern zuerst · 4 Portale");
  assert.match(HTML, /id="einstellen-zeile"[^>]*hidden><span id="einstellen-text"><\/span> <button[^>]*id="einstellen-aendern"[^>]*>Ändern<\/button>/);

  p.$("einstellen-aendern").fire("click");
  assert.equal(p.$("einstellen").hidden, false);
  assert.equal(p.$("einstellen-zeile").hidden, true);
});

test("the summary names cantons, a radius for apprenticeships, a missing term and caps a long list", () => {
  assert.equal(anzeige.zusammenfassung({ begriffe: ["A"], region: { kantone: ["BE", "SO"], orte: ["Bern"] }, portale: 1 }),
    "Sucht nach A · Kantone BE und SO · 1 Portal");
  assert.equal(anzeige.zusammenfassung({ begriffe: ["Koch EFZ"], region: { orte: ["Thun"], umkreis_km: 25 }, portale: 2, lehrstelle: true }),
    "Sucht nach Koch EFZ · 25 km um Thun · 2 Portale");
  assert.equal(anzeige.zusammenfassung({ begriffe: [], region: null, portale: 4 }), "Noch keine Suchbegriffe · 4 Portale");
  assert.equal(anzeige.zusammenfassung({ begriffe: ["A", "B", "C", "D", "E"], portale: 4 }), "Sucht nach A, B, C und 2 weiteren · 4 Portale");
});

test("the reason a disabled Jetzt suchen is disabled stands directly under it", async () => {
  assert.match(HTML, /<button type="button" class="btn btn--primary" id="suchen" aria-describedby="suchen-grund" disabled>Jetzt suchen<\/button>\s*<p id="suchen-grund" class="btn-reason"><\/p>/);

  const ohneProfil = page({ liste: { sperrgrund: "Zuerst Meine Angaben abschliessen." } });
  await settle();
  assert.equal(ohneProfil.$("suchen").disabled, true);
  assert.equal(ohneProfil.$("suchen-grund").textContent, "Zuerst Meine Angaben abschliessen.");

  const ohneErweiterung = page({ erweiterung: false });
  await settle();
  assert.equal(ohneErweiterung.$("suchen-grund").textContent, "", "no reason while the page still waits for the extension");
  ohneErweiterung.timers.find(t => t.ms === 1500).f();
  assert.equal(ohneErweiterung.$("suchen").disabled, true);
  assert.equal(ohneErweiterung.$("suchen-grund").textContent, "Zuerst die Erweiterung einrichten.");

  const bereit = page();
  await settle();
  assert.equal(bereit.$("suchen").disabled, false);
  assert.equal(bereit.$("suchen-grund").textContent, "");
});

test("without a search profile the app gives the short reason and keeps it out of the hints", () => {
  const routes = fs.readFileSync(path.join(ROOT, "routes_search.py"), "utf8");
  assert.match(routes, /BLOCKED_WITHOUT_PROFILE = "Zuerst Meine Angaben abschliessen\."/);
  assert.match(routes, /"sperrgrund": blocked/);
});

test("before the first search the list says Noch nicht gesucht, not Keine neuen Treffer", async () => {
  const p = page({ liste: { treffer: [], letzte_suche: null } });
  await settle();
  assert.equal(p.$("leer-titel").textContent, "Noch nicht gesucht.");
  assert.equal(p.$("leer-text").textContent, "Die erste Suche dauert einige Minuten.");
  assert.notEqual(p.$("letzte").textContent, "Noch keine Suche.");

  const danach = page({ liste: { treffer: [], letzte_suche: { datum: "2026-11-01", portale: { "jobs.ch": {} } } } });
  await settle();
  assert.equal(danach.$("leer-titel").textContent, "Keine neuen Treffer");
});

test("Noch keine Suche never shows when hits exist", async () => {
  const p = page({ liste: { treffer: [HIT], letzte_suche: null } });
  await settle();
  assert.equal(p.$("letzte").textContent, "1 Treffer, 1 neu");
  assert.equal(anzeige.letzteSuche(null, [HIT], String).includes("Noch keine Suche"), false);
});

test("Übernehmen becomes Merken, and the message reads Gemerkt. with a link to the new application", async () => {
  const p = page({ liste: { treffer: [HIT] } });
  await settle();
  const aktionen = p.$("detail").children.flat().filter(Boolean)
    .flatMap(function alle(n) { return [n, ...((n && n.children) || []).flat().flatMap(alle)]; });
  const merken = aktionen.find(n => n && n.tag === "button" && textOf(n) === "Merken");
  assert.ok(merken, "a button Merken");
  assert.ok(!aktionen.some(n => n && n.tag === "button" && /bernehmen/.test(textOf(n))));

  merken.fire("click");
  await settle();
  const gemerkt = p.messages.find(m => Array.isArray(m.inhalt) && m.inhalt[0] === "Gemerkt. ");
  assert.ok(gemerkt, "the message starts with Gemerkt.");
  assert.equal(gemerkt.inhalt[1].tag, "a");
  assert.equal(gemerkt.inhalt[1].attrs.href, "/bewerbung?id=b7");
  assert.equal(textOf(gemerkt.inhalt[1]), "Bewerbung öffnen");
  assert.match(HTML, /data-zustand="uebernommen" aria-pressed="false">Gemerkt </);
});

test("Register in user texts becomes Ihre Bewerbungen, in the Sie and the du form", () => {
  assert.equal(texte.text("suche.schon-titel", "stelle-sie"), "Schon in Ihren Bewerbungen");
  assert.equal(texte.text("suche.schon-titel", "stelle-du"), "Schon in deinen Bewerbungen");
  assert.equal(texte.text("suche.schon-marke", "lehrstelle-du"), "schon in deinen Bewerbungen");
  assert.doesNotMatch(CODE, /Register/);
  const routes = fs.readFileSync(path.join(ROOT, "routes_search.py"), "utf8");
  assert.match(routes, /"Dieser Treffer ist schon in Ihren Bewerbungen\."/);
  assert.match(routes, /"Dieser Treffer ist schon in deinen Bewerbungen\."/);
  assert.doesNotMatch(routes, /schon im Register/);
  assert.doesNotMatch(fs.readFileSync(path.join(ROOT, "hits.py"), "utf8"), /\) im Register\./);
});

test("Einstieg abschliessen becomes Meine Angaben abschliessen", () => {
  for (const datei of ["routes_search.py", "search_plan.py", "routes_career.py", path.join("ai", "tasks.py")]) {
    assert.doesNotMatch(fs.readFileSync(path.join(ROOT, datei), "utf8"), /Einstieg abschliessen/, datei);
  }
  assert.match(fs.readFileSync(path.join(ROOT, "search_plan.py"), "utf8"), /Zuerst Meine Angaben abschliessen\./);
});
