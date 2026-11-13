// The window „KI einrichten“ (G60, #272): the setup has no AI step any more; the window opens over the page from the
// text „KI einrichten“ in the setup, when a feature needs the AI and none is set up, and from an invitation link. It
// asks for the consent first, then for the way to the AI, and closes back to the page it opened on.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const texte = require("../seiten/texte.js");
const einrichtung = require("../seiten/einrichtung-logik.js");

const SEITEN = path.join(__dirname, "..", "seiten");
const lies = name => fs.readFileSync(path.join(SEITEN, name), "utf8");
const PARENT_TEXT = "Ich bin Elternteil oder gesetzliche Vertretung und mindestens 18 Jahre alt.";
const CONSENT = { erteilt: false, fassung: "2026-11", text: PARENT_TEXT, link: "https://example.ch/datenschutz" };
const NOT_SET_UP = { eingerichtet: false, einladung: true, hinweis: "Die KI ist noch nicht eingerichtet.", einwilligung: CONSENT };
const AGREED = { ...NOT_SET_UP, einwilligung: { ...CONSENT, erteilt: true } };
const SET_UP = { eingerichtet: true, vermittlung: true, budget_usd: 5, verbraucht_usd: 0.4, einwilligung: { ...CONSENT, erteilt: true } };

const keep = item => item !== null && item !== undefined && item !== false;
const textOf = node => (node && typeof node === "object" ? node.children.map(textOf).join("") : String(node ?? ""));

/** A stand-in element that keeps what the page sets, its children and its listeners. */
function element(tag, attrs = {}) {
  const handlers = {};
  const node = {
    tag, attrs, children: [], hidden: false, disabled: false, checked: false, open: false, value: "", removed: false,
    dataset: {}, style: {}, className: "",
    get textContent() { return textOf(node); },
    set textContent(value) { node.children = [String(value)]; },
    setAttribute(name, value) { node.attrs[name] = value; },
    getAttribute(name) { return node.attrs[name]; },
    removeAttribute(name) { delete node.attrs[name]; },
    addEventListener(type, handler) { (handlers[type] ||= []).push(handler); },
    fire(type) { return (handlers[type] || []).map(handler => handler({ target: node, currentTarget: node, preventDefault() {} })); },
    append(...items) { node.children.push(...items.flat().filter(keep)); },
    replaceChildren(...items) { node.children = items.flat().filter(keep); },
    remove() { node.removed = true; },
    focus() {},
    showModal() { node.open = true; },
    close() {
      if (!node.open) return;
      node.open = false;
      node.fire("close");
    },
  };
  return node;
}

function el(tag, attrs = {}, ...kids) {
  const node = element(tag, {});
  for (const [name, value] of Object.entries(attrs || {})) {
    if (value === false || value === null || value === undefined) continue;
    if (name.startsWith("on")) node.addEventListener(name.slice(2), value);
    else if (name === "hidden") node.hidden = true;
    else if (name === "disabled") node.disabled = true;
    else if (name === "class") node.className = value;
    else node.attrs[name] = value === true ? "" : value;
  }
  node.append(...kids);
  return node;
}

const findAll = (node, match) => (node && typeof node === "object"
  ? [...(match(node) ? [node] : []), ...node.children.flatMap(child => findAll(child, match))] : []);
/** Visible means: neither the node nor one of its parents is hidden. */
const visible = (node, match) => (node && typeof node === "object" && !node.hidden
  ? [...(match(node) ? [node] : []), ...node.children.flatMap(child => visible(child, match))] : []);
const button = (node, text) => visible(node, n => n.tag === "button" && textOf(n) === text)[0];
const radios = node => visible(node, n => n.tag === "input" && n.attrs.type === "radio");
const plain = value => JSON.parse(JSON.stringify(value));  // made in the sandbox, so compared as plain data
const settle = async () => { for (let i = 0; i < 8; i += 1) await new Promise(resolve => setImmediate(resolve)); };

/**
 * ki-fenster.js with the real consent and choice of the way, in a sandbox. `answers` maps a path to what the app
 * answers (a function of the body for POST); an Error rejects.
 */
function windowWith(answers) {
  const sent = [];
  const events = [];
  const body = element("body");
  const answer = async (pfad, daten) => {
    const value = typeof answers[pfad] === "function" ? answers[pfad](daten) : answers[pfad];
    if (value === undefined || value instanceof Error) throw value || new Error(`no answer for ${pfad}`);
    return JSON.parse(JSON.stringify(value));
  };
  const window = {
    App: {
      el, holen: pfad => answer(pfad), senden: (pfad, daten) => { sent.push({ pfad, daten }); return answer(pfad, daten); },
      status: (ort, text) => { ort.textContent = text; }, textsatz: async () => "lehrstelle-du",
      fragenLink: (anker, text) => el("a", { href: `/fragen#${anker}` }, text),
    },
    Texte: texte,
    Meldungen: { zeige: (ort, text) => { ort.textContent = text; } },
  };
  const document = {
    body, documentElement: { dataset: { textsatz: "lehrstelle-du" } },
    addEventListener() {}, removeEventListener() {}, dispatchEvent: event => events.push(event),
  };
  class CustomEvent { constructor(type, init = {}) { this.type = type; this.detail = init.detail; } }
  const context = { window, document, CustomEvent };
  for (const name of ["einwilligung.js", "ki-zugang.js", "ki-fenster.js"]) vm.runInNewContext(lies(name), context);
  return { open: () => window.KiFenster.oeffnen(), body, sent, events, dialog: () => body.children.find(n => n.tag === "dialog") };
}

async function agree(dialog) {
  const tick = visible(dialog, n => n.tag === "input" && n.attrs.type === "checkbox")[0];
  tick.checked = true;
  tick.fire("change");
  button(dialog, "Einwilligen").fire("click");
  await settle();
}

function choose(dialog, way) {
  const radio = radios(dialog).find(n => n.attrs.value === way);
  assert.ok(radio, `the way ${way} is offered`);
  radio.checked = true;
  radio.fire("change");
}

// ---------- The setup has no step KI ----------

test("the setup has no step KI, whatever it finds", () => {
  for (const einstiegDatei of [null, "/Users/x/Downloads/einstieg.zip"]) {
    for (const jetzt of ["", "ki", "vorlage"]) {
      assert.ok(!einrichtung.schritte({ installiert: true, einstiegDatei, jetzt }).includes("ki"), `${einstiegDatei} ${jetzt}`);
    }
  }
  const html = lies("einrichtung.html");
  assert.doesNotMatch(html, /data-schritt="ki"/);
  assert.doesNotMatch(html, /Ohne KI weiter/);
  assert.doesNotMatch(lies("einrichtung.js"), /\bki: "KI"/, "no step title for KI");
});

test("the setup window has a clickable text KI einrichten that opens the window", () => {
  const html = lies("einrichtung.html");
  const head = html.slice(html.indexOf('<header class="setup__head">'), html.indexOf('<ol id="schritte"'));
  assert.match(head, /<button type="button" class="btn btn--quiet btn--sm" id="ki-einrichten">KI einrichten<\/button>/);
  assert.match(lies("einrichtung.js"), /\$\("ki-einrichten"\)\.addEventListener\("click", oeffneKi\)/);
  assert.match(lies("einrichtung.js"), /window\.App\.kiEinrichten\(\)/);
});

test("the end of the setup opens the window for an open AI instead of a step", () => {
  const offen = einrichtung.offenePunkte({ kiVerbunden: false, erweiterungMoeglich: false, erweiterungGeladen: "" });
  assert.deepEqual(offen.map(p => [p.id, p.knopf, p.aktion]), [["ki", "KI einrichten", "ki-einrichten"]]);
});

// ---------- The window ----------

test("the window asks for the consent first, with the parent's confirmation for apprenticeships", async () => {
  const w = windowWith({ "/api/ki/status": NOT_SET_UP, "/api/claude/stand": new Error("no subscription") });
  w.open();
  await settle();
  const dialog = w.dialog();
  assert.ok(dialog && dialog.open, "the window is open over the page");
  assert.equal(textOf(visible(dialog, n => n.tag === "h2")[0]), "KI einrichten");
  assert.ok(textOf(dialog).includes(PARENT_TEXT), "the consent text of the server, word for word");
  assert.equal(radios(dialog).length, 0, "the way comes after the consent");
  assert.deepEqual(w.sent, []);
});

test("after the consent the window offers invitation code and own key, and the subscription where the app has it", async () => {
  const without = windowWith({ "/api/ki/status": NOT_SET_UP, "/api/claude/stand": new Error("none"), "/api/ki/einwilligung": AGREED });
  without.open();
  await settle();
  await agree(without.dialog());
  assert.deepEqual(without.sent.map(s => s.pfad), ["/api/ki/einwilligung"]);
  assert.deepEqual(radios(without.dialog()).map(n => n.attrs.value), ["einladung", "schluessel"]);

  const withAbo = windowWith({ "/api/ki/status": AGREED, "/api/claude/stand": { zugang: false } });
  withAbo.open();
  await settle();
  assert.deepEqual(radios(withAbo.dialog()).map(n => n.attrs.value), ["einladung", "abo", "schluessel"]);
  const titles = visible(withAbo.dialog(), n => n.className === "access-choice__title").map(textOf);
  assert.deepEqual(titles, ["Einladungscode", "Eigenes Claude-Abo", "Eigener Schlüssel von Anthropic"]);
});

test("an invitation code sets the AI up, and Weiter closes the window back to the page", async () => {
  const w = windowWith({ "/api/ki/status": AGREED, "/api/claude/stand": new Error("none"), "/api/ki/einladung": SET_UP });
  const closed = w.open();
  await settle();
  const dialog = w.dialog();
  choose(dialog, "einladung");
  const code = visible(dialog, n => n.tag === "input" && n.attrs.id === "ki-fenster-code")[0];
  code.value = "TEST-0000-TEST-0000";
  code.fire("input");
  button(dialog, "Einladung einlösen").fire("click");
  await settle();
  assert.deepEqual(plain(w.sent), [{ pfad: "/api/ki/einladung", daten: { code: "TEST-0000-TEST-0000" } }]);
  assert.ok(textOf(dialog).includes("Die KI ist eingerichtet."));

  button(dialog, "Weiter").fire("click");
  const status = await closed;
  assert.equal(dialog.open, false);
  assert.equal(dialog.removed, true, "nothing of the window stays on the page");
  assert.equal(status.eingerichtet, true);
  assert.deepEqual(w.events.map(e => e.type), ["ki-fenster-geschlossen"]);
});

test("an own key is checked and stored from the window after the tick, and the field is emptied", async () => {
  let saved = false;
  const w = windowWith({ "/api/ki/status": () => (saved ? { ...SET_UP, vermittlung: false, eigener_schluessel: true } : AGREED),
    "/api/claude/stand": new Error("none"),
    "/api/schluessel/speichern": () => { saved = true; return { gesetzt: true }; } });
  w.open();
  await settle();
  const dialog = w.dialog();
  choose(dialog, "schluessel");
  const save = button(dialog, "Prüfen und speichern");
  const key = visible(dialog, n => n.tag === "input" && n.attrs.type === "password")[0];
  assert.equal(save.disabled, true);
  key.value = "sk-test-erfunden";
  key.fire("input");
  assert.equal(save.disabled, true, "not without the tick");
  const tick = visible(dialog, n => n.tag === "input" && n.attrs.type === "checkbox")[0];
  tick.checked = true;
  tick.fire("change");
  assert.equal(save.disabled, false);
  save.fire("click");
  await settle();
  assert.deepEqual(plain(w.sent), [{ pfad: "/api/schluessel/speichern", daten: { schluessel: "sk-test-erfunden", bestaetigt: true } }]);
  assert.equal(key.value, "");
  assert.ok(textOf(dialog).includes("Die KI ist eingerichtet."));
});

test("closing without a setup sends nothing and leaves the person where they were", async () => {
  const w = windowWith({ "/api/ki/status": AGREED, "/api/claude/stand": new Error("none") });
  const closed = w.open();
  await settle();
  const dialog = w.dialog();
  button(dialog, "Schliessen").fire("click");
  const status = await closed;
  assert.equal(dialog.open, false);
  assert.equal(status.eingerichtet, false);
  assert.deepEqual(w.sent, []);
});

test("the window opens once, however many features ask for it at the same time", async () => {
  const w = windowWith({ "/api/ki/status": AGREED, "/api/claude/stand": new Error("none") });
  const first = w.open();
  const second = w.open();
  await settle();
  assert.equal(w.body.children.filter(n => n.tag === "dialog").length, 1);
  assert.equal(first, second);
});

// ---------- app.js: a feature without AI and an invitation link open it ----------

/** app.js in a sandbox: `answers` maps a path to [status, body]; the window is a spy. */
function appWith({ pfad = "/bewerbungen", search = "", answers = {} }) {
  const opened = [];
  const replaced = [];
  const navigated = [];
  const response = ([status, body]) => ({ ok: status < 400, status, statusText: "", headers: { get: () => "application/json" },
    json: async () => body });
  const fetch = async url => response(answers[String(url).split("?")[0]] || [404, { fehler: "Nicht gefunden" }]);
  const location = { pathname: pfad, search, hash: "", origin: "http://127.0.0.1:1", replace: ziel => navigated.push(ziel), reload() {} };
  const document = {
    querySelector: () => ({ content: "token" }), getElementById: () => null, addEventListener() {}, hidden: false,
    documentElement: { dataset: {} }, head: element("head"), body: element("body"), createElement: tag => element(tag),
  };
  // The scripts of the window are there already; the window itself is a spy.
  const window = { Texte: { anwenden() {} }, Einwilligung: {}, KiZugang: {}, addEventListener() {},
                   KiFenster: { oeffnen: async () => { opened.push(location.pathname); return { eingerichtet: true }; } } };
  const history = { state: null, length: 1, replaceState: (state, title, ziel) => replaced.push(ziel) };
  vm.runInNewContext(lies("app.js"), { window, document, location, history, fetch, URLSearchParams, setInterval() {}, setTimeout,
    Promise, crypto: { randomUUID: () => "x" } });
  return { App: window.App, opened, replaced, navigated };
}

test("a feature that needs the AI while none is set up opens the window", async () => {
  const answer = [400, { fehler: "Die KI ist noch nicht eingerichtet.", aktion: "ki-einrichten" }];
  const app = appWith({ answers: { "/api/ki/bewerten": answer } });
  await settle();
  await assert.rejects(app.App.senden("/api/ki/bewerten", {}), /noch nicht eingerichtet/);
  await settle();
  assert.deepEqual(app.opened, ["/bewerbungen"]);
});

test("another error opens no window", async () => {
  const app = appWith({ answers: { "/api/ki/bewerten": [400, { fehler: "Zuerst den Stellentext einfügen und speichern." }] } });
  await settle();
  await assert.rejects(app.App.senden("/api/ki/bewerten", {}));
  await settle();
  assert.deepEqual(app.opened, []);
});

test("an invitation link opens the window on the page it lands on, and the request leaves the address", async () => {
  const app = appWith({ pfad: "/", search: "?ki=einrichten" });
  await settle();
  assert.deepEqual(app.opened, ["/"]);
  assert.deepEqual(app.replaced, ["/"]);
});

test("before the data folder the invitation link goes to the setup with its request", async () => {
  const app = appWith({ pfad: "/", search: "?ki=einrichten",
    answers: { "/api/app/version": [200, { version: "0.0.0" }], "/api/app/einrichtung": [200, { eingerichtet: false }] } });
  await settle();
  assert.deepEqual(app.navigated, ["/einrichtung?ki=einrichten"]);
  assert.deepEqual(app.opened, [], "the setup opens it once the folder is there");
});

test("the setup page takes the request itself", async () => {
  const app = appWith({ pfad: "/einrichtung", search: "?ki=einrichten" });
  await settle();
  assert.deepEqual(app.opened, []);
  assert.match(lies("einrichtung.js"), /window\.App\.kiAnfrageNehmen\(\)/);
});

// ---------- Pages that pointed to the step KI ----------

test("the application page opens the window instead of linking to the setup", () => {
  assert.doesNotMatch(lies("bewerbung.js"), /\/einrichtung#ki/);
  assert.match(lies("bewerbung.js"), /"KI einrichten"/);
  assert.match(lies("bewerbung.js"), /App\.kiEinrichten\(\)/);
  assert.match(lies("ki.js"), /App\.kiEinrichten\(\)/);
  assert.doesNotMatch(lies("bewerbung.html"), /id="ki-einladung"/, "no second field for the code on the page");
});

test("the window uses the tokens of the design system only", () => {
  const css = lies("stil.css");
  const rules = css.slice(css.indexOf("/* The window „KI einrichten“"));
  assert.ok(rules.length > 100, "rules for the window in stil.css");
  assert.doesNotMatch(rules.slice(0, rules.indexOf("\n\n")), /#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(/);
  assert.match(css, /label\.access-choice__option \{/, "the choice is styled on every page, not only in the settings");
});
