// The switches of /suchbegriffe on the page (#371, G102), with a small stand-in DOM: one switch per term, updated in
// place so the focus stays, totals at once, requests after a pause with old answers dropped, a polite announcement only
// when the choice becomes blocked or free. All terms are invented.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const Texte = require("../seiten/texte.js");
const DotLine = require("../seiten/dot-line.js");

const SEITEN = path.join(__dirname, "..", "seiten");
const source = name => fs.readFileSync(path.join(SEITEN, name), "utf8");

class FakeText {
  constructor(text) { this.data = String(text); this.parentNode = null; }
  get textContent() { return this.data; }
}

class FakeElement {
  constructor(document, tag) {
    Object.assign(this, { ownerDocument: document, tagName: tag.toUpperCase(), childNodes: [], parentNode: null,
      dataset: {}, attrs: new Map(), listeners: {}, className: "", value: "", checked: false });
  }
  get children() { return this.childNodes.filter(n => n instanceof FakeElement); }
  get textContent() { return this.childNodes.map(n => n.textContent).join(""); }
  set textContent(value) { this.replaceChildren(...(value === "" ? [] : [String(value)])); }
  get hidden() { return this.attrs.has("hidden"); }
  set hidden(value) { if (value) this.attrs.set("hidden", ""); else this.attrs.delete("hidden"); }
  get id() { return this.getAttribute("id") || ""; }
  setAttribute(name, value) { this.attrs.set(name, String(value)); }
  getAttribute(name) { return this.attrs.has(name) ? this.attrs.get(name) : null; }
  hasAttribute(name) { return this.attrs.has(name); }
  removeAttribute(name) { this.attrs.delete(name); }
  append(...nodes) {
    for (const node of nodes) {
      const child = node instanceof FakeElement || node instanceof FakeText ? node : new FakeText(node);
      child.parentNode = this;
      this.childNodes.push(child);
    }
  }
  replaceChildren(...nodes) {
    this.ownerDocument.replaced.add(this);
    this.childNodes = [];
    this.append(...nodes);
  }
  contains(node) {
    for (let n = node; n; n = n.parentNode) if (n === this) return true;
    return false;
  }
  addEventListener(type, handler) { (this.listeners[type] ||= []).push(handler); }
  removeEventListener(type, handler) { this.listeners[type] = (this.listeners[type] || []).filter(h => h !== handler); }
  dispatch(type, init = {}) {
    const event = { type, target: this, defaultPrevented: false, preventDefault() { this.defaultPrevented = true; }, ...init };
    for (let n = this; n; n = n.parentNode) for (const h of [...(n.listeners[type] || [])]) h(event);
    return event;
  }
  focus() { this.ownerDocument.activeElement = this; }
  querySelector() { return null; }
  querySelectorAll() { return []; }
}

function* below(node) {
  for (const child of node.children) {
    yield child;
    yield* below(child);
  }
}

const settled = async () => {
  for (let i = 0; i < 10; i += 1) await new Promise(resolve => setImmediate(resolve));
};

const LIMITS = { teile: ["Danach: 3 von 15 Suchbegriffen", "bis 6 Suchen pro Portal"], gesperrt: null,
  zu_viel: { suchbegriffe: 0, positiv: 0, ausschluss: 0 }, erlaubt: { suchbegriffe: 15, positiv: 30, ausschluss: 30 } };
const REPLACE = { nummer: 0, bereich: "positive", bereich_name: "Titel enthält eines davon", zu_allgemein: false,
  satz: "«Engineer» ersetzen durch Backend und Frontend", entfaellt: ["Engineer"], neu: ["Backend", "Frontend"],
  grund: "Bringt viele Industriestellen.", beleg: null };
const ADD = { nummer: 1, bereich: "keywords", bereich_name: "Suchbegriffe", zu_allgemein: false,
  satz: "Suchbegriff «Datenanalyst» aufnehmen", entfaellt: [], neu: ["Datenanalyst"], grund: "Steht im Lebenslauf.", beleg: null };
const PROPOSAL = { vorschlag: "v1", runde: 1, aenderungen: [REPLACE, ADD], zusammenfassung: "Zwei Änderungen.",
  treffer: 40, seit: "2026-11-01", modell: "claude-sonnet-5-5", kosten_usd: 0.03, waehrung: "CHF", datum: "2026-11-21",
  jetzt: { suchbegriffe: ["Python", "TypeScript"], positiv: ["Web", "Engineer"], ausschluss: [] },
  bisherige: { suchbegriffe: ["Python", "TypeScript"], positiv: ["Web"], ausschluss: [] },
  endstand: { suchbegriffe: ["Python", "TypeScript", "Datenanalyst"], positiv: ["Web", "Backend", "Frontend"], ausschluss: [] },
  entfaellt: ["Engineer"], grenzen: LIMITS };
const ESTIMATE = { verfuegbar: true, anzahl: 1, kosten: 0.03, waehrung: "CHF", guthaben: 4, danach: 3.97,
  dauer_minuten: 1, reicht_fuer: null };
const SCRIPTS = ["treffer-logik.js", "suchbegriffe-logik.js", "suchbegriffe-schalter.js", "suchbegriffe-gezaehlt.js", "suchbegriffe.js"];

/** Runs the page; an answer to „endstand“ waits until the test gives it with `answer(body)`. Timers run on `pause()`. */
async function page(proposal = PROPOSAL, more = {}) {
  const document = { activeElement: null, replaced: new Set() };
  document.createElement = tag => new FakeElement(document, tag);
  const elements = new Map();
  document.getElementById = id => {
    if (!elements.has(id)) {
      const element = document.createElement("div");
      element.setAttribute("id", id);
      elements.set(id, element);
    }
    return elements.get(id);
  };
  document.addEventListener = () => {};
  const el = (tag, attributes = {}, ...children) => {
    const element = document.createElement(tag);
    for (const [name, value] of Object.entries(attributes)) {
      if (value === false || value === null || value === undefined) continue;
      if (name === "class") element.className = value;
      else if (name.startsWith("on") && typeof value === "function") element.addEventListener(name.slice(2), value);
      else element.setAttribute(name, value);
    }
    for (const child of children.flat()) if (child !== null && child !== undefined && child !== false) element.append(child);
    return element;
  };
  const sent = [];
  const waiting = [];
  const statuses = [];
  const fixed = { "/api/suchbegriffe/hinweis": { verfuegbar: true, treffer: 40, seit: "2026-11-01" },
    "/api/ki/status": { einwilligung: null }, "/api/suchbegriffe/vorschlag": proposal,
    "/api/suchbegriffe/schaetzung": ESTIMATE,
    "/api/suchbegriffe/uebernehmen": { neu: 3, entfallen: 1, vorher: "a".repeat(64), nachher: "b".repeat(64) }, ...more };
  const answer = (route, body) => {
    if (body) sent.push({ route, body: JSON.parse(JSON.stringify(body)) });
    if (route === "/api/suchbegriffe/endstand") return new Promise(resolve => waiting.push({ body, resolve }));
    if (!(route in fixed)) return Promise.reject(new Error(`unexpected route ${route}`));
    return Promise.resolve(fixed[route]);
  };
  const timers = [];
  const window = { Texte, DotLine, Meldungen: { clearInputError() {} }, Einwilligung: { zeile() {} } };
  const context = { window, document, console, CustomEvent: class {},
    setTimeout: fn => { timers.push(fn); return timers.length; }, clearTimeout: () => {} };
  vm.createContext(context);
  window.App = { el, holen: route => answer(route), senden: answer, textsatz: async () => "stelle-sie",
    status: (element, text) => statuses.push({ id: element.id, text }) };
  for (const name of SCRIPTS) vm.runInContext(source(name), context);
  await settled();
  const $ = id => document.getElementById(id);
  // The stand-in has no HTML around the containers the script fills, so it looks in each of them.
  const drawn = () => [...below($("aenderungen")), ...below($("bisherige-bereiche"))];
  const byId = id => drawn().find(n => n.id === id);
  const boxes = () => drawn().filter(n => n.tagName === "INPUT" && n.className === "term__box");
  const chip = term => boxes().find(box => box.parentNode.textContent.startsWith(term));
  const flip = async (box, on) => {
    box.focus();
    box.checked = on;
    box.dispatch("change");
    await settled();
  };
  const pause = async () => {
    const due = timers.splice(0);
    for (const fn of due) fn();
    await settled();
  };
  const reply = async (index, grenzen = LIMITS) => {
    const { body, resolve } = waiting[index];
    const endstand = body.danach;
    resolve({ endstand, entfaellt: PROPOSAL.jetzt.positiv.filter(t => !endstand.positiv.includes(t)), grenzen });
    await settled();
  };
  return { $, byId, document, sent, waiting, statuses, boxes, chip, flip, pause, reply };
}

const ends = sent => sent.filter(s => s.route === "/api/suchbegriffe/endstand");
const heard = n => (n instanceof FakeElement
  ? (n.hidden || n.getAttribute("aria-hidden") === "true" ? "" : n.childNodes.map(heard).join("")) : n.data);

test("every term has exactly one switch: the terms of a change in its card, the other current terms below", async () => {
  const p = await page();
  const names = p.boxes().map(box => heard(box.parentNode).split(",")[0]);
  assert.deepEqual([...names].sort(), ["Backend", "Datenanalyst", "Engineer", "Frontend", "Python", "TypeScript", "Web"]);
  const below = p.$("bisherige-bereiche").children;
  assert.deepEqual(below.map(set => set.tagName), ["FIELDSET", "FIELDSET"], "an empty area is left out");
  assert.equal(heard(below[0].children[0]), "Suchbegriffe, danach 3 eingeschaltet");
  assert.equal(p.$("bisherige-satz").textContent, "Alle sind eingeschaltet. Was Sie ausschalten, entfällt beim Übernehmen.");
  assert.equal(p.$("bisherige-oben").hidden, false, "some current terms stand in a card");
  assert.equal(p.$("uebernehmen").textContent, "Auswahl übernehmen");
});

test("«So sucht die App danach» only shows the result, with «Entfällt: …» at the end", async () => {
  const p = await page();
  assert.equal([...below(p.$("endstand"))].filter(n => n.tagName === "INPUT").length, 0);
  assert.equal(p.$("faellt-weg").textContent, "Entfällt: Engineer");
});

test("a switched chip changes in place, the focus stays on it, and the total follows at once", async () => {
  const p = await page();
  const web = p.chip("Web");
  const before = p.boxes();
  p.document.replaced.clear();

  await p.flip(web, false);

  assert.equal(p.document.activeElement, web);
  assert.deepEqual(p.boxes(), before, "the same chips, none drawn anew");
  assert.ok(!p.document.replaced.has(p.$("aenderungen")) && !p.document.replaced.has(p.$("bisherige-bereiche")));
  assert.equal(heard(web.parentNode), "Web, entfällt");
  assert.match(web.parentNode.className, /is-off/);
  assert.equal(heard(p.$("bisherige-bereiche").children[1].children[0]), "Titel enthält eines davon, danach 2 eingeschaltet",
    "before the app answers");
});

test("a removed term switched off stays, and the change shows it is taken over only partly", async () => {
  const p = await page();
  const card = p.byId("aenderung-0");
  await p.flip(p.chip("Engineer"), false);
  assert.equal(heard(p.chip("Engineer").parentNode), "Engineer, bleibt");
  assert.equal(card.indeterminate, true);
  assert.equal(card.checked, false);
  assert.equal(p.byId("aenderung-0-teilweise").hidden, false);
  assert.equal(p.byId("aenderung-0-teilweise").textContent, "Teilweise übernommen");

  card.checked = true;
  card.dispatch("change");
  await settled();

  assert.equal(card.indeterminate, false);
  assert.equal(p.byId("aenderung-0-teilweise").hidden, true);
  assert.ok(["Engineer", "Backend", "Frontend"].every(term => p.chip(term).checked), "the checkbox switched them together");
});

test("requests wait for a pause, and an older answer that comes last is dropped", async () => {
  const p = await page();
  await p.flip(p.chip("Python"), false);
  assert.equal(ends(p.sent).length, 1, "the first switch asks at once");
  await p.flip(p.chip("TypeScript"), false);
  await p.flip(p.chip("Web"), false);
  assert.equal(ends(p.sent).length, 1, "more switches wait for the pause");

  await p.pause();

  assert.equal(ends(p.sent).length, 2);
  assert.deepEqual(ends(p.sent)[1].body.danach.suchbegriffe, ["Datenanalyst"]);
  await p.reply(1, { ...LIMITS, teile: ["Danach: 1 von 15 Suchbegriffen", "bis 2 Suchen pro Portal"] });
  await p.reply(0, { ...LIMITS, teile: ["Danach: 2 von 15 Suchbegriffen", "bis 4 Suchen pro Portal"] });
  assert.match(heard(p.$("grenzen")), /^Danach: 1 von 15/);
});

const OVER = n => ({ ...LIMITS, teile: [`Danach: ${31 + n} Suchbegriffe, erlaubt sind 31`, "bis 34 Suchen pro Portal"],
  gesperrt: `Mit dieser Auswahl wären es ${31 + n} Suchbegriffe. Höchstens 15 gehen; da es schon 31 sind, dürfen es nicht `
    + `mehr werden. Bitte noch ${n} ausschalten, unter «Bisherige Begriffe» oder bei den Vorschlägen.`,
  zu_viel: { suchbegriffe: n, positiv: 0, ausschluss: 0 }, erlaubt: { suchbegriffe: 31, positiv: 30, ausschluss: 30 } });

test("over the limit the reason links to the current terms and the page says how many are still too many", async () => {
  const p = await page({ ...PROPOSAL, grenzen: OVER(3) });
  assert.equal(p.$("uebernehmen").disabled, true);
  assert.equal(p.$("auswahl-ansage").textContent, "", "nothing announced on opening");
  const link = [...below(p.$("uebernehmen-grund"))].find(n => n.tagName === "A");
  assert.equal(link.textContent, "Zu den bisherigen Begriffen");
  assert.match(p.$("uebernehmen-grund").textContent, /Bitte noch 3 ausschalten/);
  link.dispatch("click");
  const legend = p.$("bisherige-bereiche").children[0].children[0];
  assert.equal(p.document.activeElement, legend);
  assert.equal(legend.getAttribute("tabindex"), "-1");

  await p.flip(p.chip("Python"), false);
  await p.reply(0, OVER(2));
  assert.equal(p.$("auswahl-ansage").textContent, "Noch 2 Suchbegriffe zu viel");

  await p.flip(p.chip("TypeScript"), false);
  await p.pause();
  await p.reply(1, LIMITS);
  assert.equal(p.$("auswahl-ansage").textContent, "Die Auswahl lässt sich übernehmen.");
  assert.equal(p.$("uebernehmen").disabled, false);
});

test("Tab reaches every chip of a group, and the arrow keys stay with the browser", async () => {
  const p = await page();
  const boxes = p.boxes();
  assert.equal(boxes.length, 7);
  for (const box of boxes) {
    assert.equal(box.hasAttribute("tabindex"), false, `${heard(box.parentNode)} keeps its place in the tab order`);
    assert.deepEqual(Object.keys(box.listeners).sort(), ["change"], "no focus or key handlers of its own");
    assert.equal(box.dispatch("keydown", { key: "ArrowRight" }).defaultPrevented, false);
  }
  const area = [p.chip("Python"), p.chip("TypeScript")];
  area[1].focus();
  area[1].dispatch("focus");
  assert.equal(area[0].hasAttribute("tabindex"), false, "focusing one chip leaves the others reachable");
});

test("«Auswahl übernehmen» sends exactly the switched-on terms and says what is new and what goes", async () => {
  const p = await page();
  await p.flip(p.chip("Frontend"), false);
  p.$("uebernehmen").dispatch("click");
  await settled();
  const adopted = p.sent.find(s => s.route === "/api/suchbegriffe/uebernehmen").body;
  assert.equal(adopted.vorschlag, "v1");
  assert.deepEqual(adopted.danach, { suchbegriffe: ["Python", "TypeScript", "Datenanalyst"], positiv: ["Web", "Backend"],
    ausschluss: [], verschoben: [] }, "G108: the moves switched on go along, none in this proposal");
  assert.ok(!("gewaehlt" in adopted));
  assert.match(p.statuses.at(-1).text, /^Übernommen: 3 Begriffe neu, 1 entfällt\./);
});

// G108, #383: what the app counted, and the one switch of a move. Invented keywords only.
const COUNT = (begriff, fields) => ({ begriff, suchen: 9, suchen_pro_lauf: 3, treffer_portale: 4, aussortiert: 0, treffer: 4,
  nur_hier: 4, ab_note_4: 1, laeufe: 3, laeufe_ohne_treffer: 0, auch_ueber: null, alle_ueber: false, marke: null, ...fields });
const COUNTED = { verfuegbar: true, laeufe: 3, noetig: 3, genug: true, begriffe: [
  COUNT("Python", {}), COUNT("TypeScript", { treffer_portale: 0, treffer: 0, nur_hier: 0, ab_note_4: 0, marke: "ohne_ertrag" })] };

test("«Was die App gezählt hat» shows at once while the AI works, flagged keywords with a chip and every one in the table", async () => {
  const p = await page(new Promise(() => {}), { "/api/suchbegriffe/gezaehlt": COUNTED });
  assert.equal(p.$("gezaehlt").hidden, false);
  assert.equal(p.$("warten").hidden, false, "the AI is still working");
  assert.equal(p.$("gezaehlt-unterzeile").textContent, "Aus den letzten 3 Suchläufen, gezählt von der App, nicht von der KI. "
    + "Treffer zählt sie bei jeder Suche, Stellen nur einmal.");
  const [row] = p.$("gezaehlt-liste").children;
  assert.equal(heard(row), "„TypeScript“ ohne Ertrag: 9 Suchen, kein Treffer.");
  assert.ok(below(row).some(n => n.className === "term term--flag"));
  assert.equal(p.$("gezaehlt-nichts").hidden, true);
  const rows = [...below(p.$("gezaehlt-tabelle"))].filter(n => n.tagName === "TR").map(heard);
  assert.deepEqual(rows, ["BegriffSuchenTrefferaussortiertnur über diesen Begriffab Note 4", "Python94041",
    "TypeScript ohne Ertrag90000"]);
});

test("with too few runs the section names them and marks nothing", async () => {
  const p = await page(new Promise(() => {}), { "/api/suchbegriffe/gezaehlt": { ...COUNTED, laeufe: 1, genug: false } });
  assert.equal(p.$("gezaehlt-unterzeile").textContent,
    "Für diese Zahlen braucht die App 3 Suchläufe seit Version 0.3.3, bisher sind es 1.");
  assert.equal(p.$("gezaehlt-liste").hidden, true);
  assert.equal(p.$("gezaehlt-alle").hidden, true);
});

test("when the counts cannot be read, the section says so and the AI still proposes", async () => {
  const failed = Promise.reject(new Error("Der Suchverlauf liess sich nicht lesen."));
  failed.catch(() => {});
  const p = await page(PROPOSAL, { "/api/suchbegriffe/gezaehlt": failed });
  assert.equal(p.$("gezaehlt").hidden, false);
  assert.equal(p.$("gezaehlt-unterzeile").textContent,
    "Die Zahlen der App liessen sich nicht laden: Der Suchverlauf liess sich nicht lesen. Die KI schlägt darum ohne diese Zahlen vor.");
  assert.equal(p.$("gezaehlt-liste").hidden, true);
  assert.equal(p.$("gezaehlt-alle").hidden, true);
  assert.equal(p.$("vorschlag").hidden, false, "the proposal does not depend on the counts");
});

const NICHE = { nummer: 0, bereich: "keywords", bereich_name: "Suchbegriffe", zu_allgemein: false, art: "niche",
  satz: "„TypeScript“ zu den Nischen verschieben (ohne Ort suchen)", entfaellt: [], neu: [], verschoben: "TypeScript",
  verschoben_wort: "zu den Nischen", marke: "ohne_ertrag", grund: "Findet ohne Ort mehr.", beleg: null };
const MOVING = { ...PROPOSAL, aenderungen: [NICHE], verschoben: ["TypeScript"],
  bisherige: { suchbegriffe: ["Python"], positiv: ["Web", "Engineer"], ausschluss: [] },
  endstand: { suchbegriffe: ["Python"], positiv: ["Web", "Engineer"], ausschluss: [] }, entfaellt: [],
  nischen: [{ begriff: "TypeScript", neu: true }], nur_zeilen: [] };

test("a move has one chip with its mark on the card; switching it off sends the move off and the keyword stays", async () => {
  const p = await page(MOVING);
  const card = p.$("aenderungen").children[0];
  assert.match(heard(card.children[0]), /^Suchbegriffe.*ohne Ertrag/);
  assert.equal(p.$("bisherige-oben").hidden, false, "a moved keyword stands in its card, not below");
  const box = p.chip("TypeScript");
  assert.equal(heard(box.parentNode), "TypeScript, zu den Nischen");
  assert.equal(box.checked, true);
  await p.flip(box, false);
  assert.equal(heard(box.parentNode), "TypeScript, bleibt");
  assert.deepEqual(ends(p.sent).at(-1).body.danach.verschoben, []);
  assert.deepEqual(ends(p.sent).at(-1).body.danach.suchbegriffe, ["Python"], "the app keeps a moved keyword by itself");
  assert.ok([...below(p.$("endstand"))].some(n => n.tagName === "H3" && heard(n) === "Nischen (ohne Ort suchen)"));
});

test("a keyword limited to portals shows only in its «Nur» block of the result", async () => {
  const limited = { ...MOVING, aenderungen: [{ ...NICHE, art: "portals", satz: "„TypeScript“ nur auf jobs.ch suchen",
    verschoben_wort: "nur jobs.ch" }], endstand: { ...MOVING.endstand, suchbegriffe: ["Python", "TypeScript"] }, nischen: [],
    nur_zeilen: [{ portale: ["jobs.ch"], begriffe: [{ begriff: "TypeScript", neu: true }] }] };
  const p = await page(limited);
  const blocks = Object.fromEntries(p.$("endstand").children.map(block => [heard(block.children[0]), heard(block.children[1])]));
  assert.equal(blocks.Suchbegriffe, "Python");
  assert.equal(blocks["Nur jobs.ch"], "TypeScriptneu", "marked «neu» there");
});
