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
const SET_UP = { eingerichtet: true, vermittlung: true, guthaben_chf: 5, verbraucht_chf: 0.4, einwilligung: { ...CONSENT, erteilt: true } };

const keep = item => item !== null && item !== undefined && item !== false;
const textOf = node => (node && typeof node === "object" ? node.children.map(textOf).join("") : String(node ?? ""));

// What has the focus; meldungen.js creates its elements through `ownerDocument`.
const focus = { active: null };
const fakeDocument = { createElement: tag => element(tag) };

/** A class list over the `className` string, as meldungen.js reads and changes it. */
function classListOf(node) {
  const names = () => String(node.className).split(/\s+/).filter(Boolean);
  const set = list => { node.className = list.join(" "); };
  return {
    contains: name => names().includes(name),
    add: (...added) => set([...names(), ...added.filter(name => !names().includes(name))]),
    remove: (...removed) => set(names().filter(name => !removed.includes(name))),
  };
}

/** A stand-in element that keeps what the page sets, its children and its listeners. */
function element(tag, attrs = {}) {
  const handlers = {};
  const node = {
    tag, attrs, children: [], hidden: false, disabled: false, checked: false, open: false, value: "", removed: false,
    dataset: {}, style: {}, className: "", ownerDocument: fakeDocument,
    get classList() { return classListOf(node); },
    get textContent() { return textOf(node); },
    set textContent(value) { node.children = [String(value)]; },
    setAttribute(name, value) { node.attrs[name] = value; },
    getAttribute(name) { return node.attrs[name]; },
    removeAttribute(name) { delete node.attrs[name]; },
    addEventListener(type, handler) { (handlers[type] ||= []).push(handler); },
    removeEventListener(type, handler) { handlers[type] = (handlers[type] || []).filter(h => h !== handler); },
    fire(type) { return [...(handlers[type] || [])].map(handler => handler({ target: node, currentTarget: node, preventDefault() {} })); },
    append(...items) { node.children.push(...items.flat().filter(keep)); },
    replaceChildren(...items) { node.children = items.flat().filter(keep); },
    contains: other => findAll(node, n => n === other).length > 0,
    remove() { node.removed = true; },
    focus() { focus.active = node; },
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
      status: (ort, text, art, optionen) => window.Meldungen.zeige(ort, text, art, optionen), textsatz: async () => "lehrstelle-du",
      fragenLink: (anker, text) => el("a", { href: `/fragen#${anker}` }, text),
    },
    Texte: texte,
  };
  const document = {
    body, documentElement: { dataset: { textsatz: "lehrstelle-du" } },
    addEventListener() {}, removeEventListener() {}, dispatchEvent: event => events.push(event),
  };
  class CustomEvent { constructor(type, init = {}) { this.type = type; this.detail = init.detail; } }
  const context = { window, document, CustomEvent, setTimeout: () => 0, clearTimeout: () => {} };
  vm.createContext(context);
  focus.active = null;
  for (const name of ["meldungen.js", "einwilligung.js", "ki-zugang.js", "ki-fenster.js"]) vm.runInContext(lies(name), context);
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

test("the window names the credit in CHF and, once it is used up, the way to a new code (G80)", async () => {
  const shows = async ki => {
    const w = windowWith({ "/api/ki/status": ki, "/api/claude/stand": new Error("none") });
    w.open();
    await settle();
    return textOf(w.dialog());
  };
  const running = await shows(SET_UP);
  assert.ok(running.includes("Guthaben: CHF\u00a00.40 von CHF\u00a05.00 verbraucht."));
  assert.ok(!running.includes("aufgebraucht"));
  const usedUp = await shows({ ...SET_UP, verbraucht_chf: 5 });
  assert.ok(usedUp.includes("Das Guthaben ist aufgebraucht: einen neuen Code anfordern, öffnet neuen Tab und unter Einstellungen, KI und Guthaben einlösen."));
});

// ---------- A used-up credit in the window (#315) ----------

const USED_UP_KI = { ...SET_UP, verbraucht_chf: 5 };
async function openDone(ki) {
  const w = windowWith({ "/api/ki/status": ki, "/api/claude/stand": new Error("none") });
  w.open();
  await settle();
  const dialog = w.dialog();
  return { dialog, done: findAll(dialog, n => String(n.className).includes("ki-fenster__fertig"))[0] };
}

test("once the credit is used up, „anfordern“ in the window links to the contact of the help page (#315)", async () => {
  const { dialog } = await openDone(USED_UP_KI);
  const links = visible(dialog, n => n.tag === "a" && textOf(n) === "anfordern, öffnet neuen Tab");
  assert.equal(links.length, 1);
  assert.deepEqual(plain(links[0].attrs), { href: "https://bewerbungsbegleiter.ch/hilfe.html#kontakt", target: "_blank", rel: "noopener" });
  const hint = links[0].children.find(child => typeof child === "object");
  assert.equal(hint.className, "visually-hidden", "the new tab is said to screen readers only");
});

test("the line of the set-up AI stays one text in the flex row of the notice, link included", async () => {
  for (const ki of [SET_UP, USED_UP_KI]) {
    const { done } = await openDone(ki);
    assert.equal(done.children.length, 1, "one child, so the row does not break around the link");
    assert.equal(done.children[0].tag, "span");
    assert.equal(done.children[0].className, "notice__body");
  }
});

test("a used-up credit is a warning in the window, a running one a success", async () => {
  const running = (await openDone(SET_UP)).done.className.split(" ");
  assert.ok(running.includes("notice--success") && !running.includes("notice--warning"));
  const usedUp = (await openDone(USED_UP_KI)).done.className.split(" ");
  assert.ok(usedUp.includes("notice--warning") && !usedUp.includes("notice--success"));
  assert.ok(usedUp.includes("notice") && usedUp.includes("ki-fenster__fertig"));
});

test("the window of a set-up AI focuses „Weiter“ first, not the link to the website", async () => {
  const { dialog } = await openDone(USED_UP_KI);
  assert.equal(button(dialog, "Weiter").autofocus, true);
  const choosing = windowWith({ "/api/ki/status": AGREED, "/api/claude/stand": new Error("none") });
  choosing.open();
  await settle();
  assert.equal(button(choosing.dialog(), "Schliessen").autofocus, false);
});

// ---------- A refused code or key clears on input (G97, #361) ----------

// The routes answer 400 only for a value wrong in itself (#350); anything else is no input error.
const refusal = (message, status) => Object.assign(new Error(message), { status });
const CODE_REFUSED = refusal("Der Code gilt nicht (falsch, schon benutzt oder abgelaufen). Bitte um einen neuen Code.", 400);
const KEY_REFUSED = refusal("Dieser Schlüssel gilt nicht. Bitte in der Anthropic Console prüfen. Gespeichert wurde nichts.", 400);
const UNREACHABLE = refusal("Keine Verbindung zur KI. Ist der Rechner mit dem Internet verbunden?", 502);

const typeInto = (field, text) => { field.value = text; field.fire("input"); };
const closeButtonOf = line => findAll(line, n => n.tag === "button" && n.attrs["aria-label"] === "Meldung schliessen")[0];
/** The line a field is described by, found through its aria-describedby. */
const lineOf = (dialog, field) => findAll(dialog, n => n.attrs.id && n.attrs.id === field.attrs["aria-describedby"])[0];

async function windowOn(way, answers) {
  const w = windowWith({ "/api/ki/status": AGREED, "/api/claude/stand": new Error("none"), ...answers });
  w.open();
  await settle();
  const dialog = w.dialog();
  choose(dialog, way);
  return { w, dialog };
}

async function redeemIn(failure) {
  const { w, dialog } = await windowOn("einladung", { "/api/ki/einladung": failure });
  const code = visible(dialog, n => n.attrs.id === "ki-fenster-code")[0];
  typeInto(code, "TEST-0000-TEST-0000");
  button(dialog, "Einladung einlösen").fire("click");
  await settle();
  return { w, dialog, code, redeem: button(dialog, "Einladung einlösen"), line: lineOf(dialog, code) };
}

async function saveKeyIn(failure) {
  const { w, dialog } = await windowOn("schluessel", { "/api/schluessel/speichern": failure });
  const key = visible(dialog, n => n.attrs.id === "ki-fenster-schluessel")[0];
  const tick = visible(dialog, n => n.tag === "input" && n.attrs.type === "checkbox")[0];
  tick.checked = true;
  tick.fire("change");
  typeInto(key, "erfundener-schluessel-0123456789");
  const save = button(dialog, "Prüfen und speichern");
  save.fire("click");
  await settle();
  return { w, dialog, key, save, line: lineOf(dialog, key) };
}

test("in the window the code and the key field are described by the status line that shows their errors", async () => {
  const { line: codeLine, code } = await redeemIn(CODE_REFUSED);
  assert.ok(codeLine, "the code field names its line");
  assert.equal(codeLine.attrs.role, "status");
  assert.ok(codeLine.textContent.startsWith(CODE_REFUSED.message), "the line it names is where its error shows");
  assert.ok(code.attrs["aria-describedby"]);
  const { line: keyLine } = await saveKeyIn(KEY_REFUSED);
  assert.ok(keyLine, "the key field names its line");
  assert.ok(keyLine.textContent.startsWith(KEY_REFUSED.message));
});

test("in the window a refused code marks its field and clears on the first input there", async () => {
  const { code, line } = await redeemIn(CODE_REFUSED);
  assert.equal(line.dataset.level, "danger");
  assert.equal(code.attrs["aria-invalid"], "true");

  typeInto(code, "TEST-0000-TEST-0001");

  assert.equal(line.textContent, "");
  assert.equal(code.attrs["aria-invalid"], undefined);
});

test("in the window an unreachable mediation is no input error and stays until «×»", async () => {
  const { code, line } = await redeemIn(UNREACHABLE);
  assert.equal(code.attrs["aria-invalid"], undefined);
  typeInto(code, "TEST-0000-TEST-0001");
  assert.match(line.textContent, /Keine Verbindung zur KI/);
  closeButtonOf(line).fire("click");
  assert.equal(line.textContent, "");
});

test("in the window a refused own key marks its field and clears on the first input there", async () => {
  const { key, line } = await saveKeyIn(KEY_REFUSED);
  assert.equal(key.value, "", "the key is never kept in the field");
  assert.equal(key.attrs["aria-invalid"], "true");

  typeInto(key, "e");

  assert.equal(line.textContent, "");
  assert.equal(key.attrs["aria-invalid"], undefined);
});

test("in the window an Anthropic that cannot check the key is no input error and stays until «×»", async () => {
  const { key, line } = await saveKeyIn(UNREACHABLE);
  assert.equal(key.attrs["aria-invalid"], undefined);
  typeInto(key, "e");
  assert.match(line.textContent, /Keine Verbindung zur KI/);
  closeButtonOf(line).fire("click");
  assert.equal(line.textContent, "");
});

test("in the window the focus is in the code field after a refused code", async () => {
  const { code } = await redeemIn(CODE_REFUSED);
  assert.equal(focus.active, code);
});

test("in the window an unreachable mediation with the code still typed leaves the focus on «Einladung einlösen»", async () => {
  const { code, redeem } = await redeemIn(UNREACHABLE);
  assert.equal(code.value, "TEST-0000-TEST-0000");
  assert.equal(redeem.disabled, false);
  assert.equal(focus.active, redeem);
});

for (const [what, failure] of [["refused", KEY_REFUSED], ["not checked", UNREACHABLE]]) {
  test(`in the window the focus is in the emptied key field after a key ${what}, and the button waits for a key`, async () => {
    const { key, save } = await saveKeyIn(failure);
    assert.equal(save.disabled, true, "nothing to send with an empty field");
    assert.equal(focus.active, key);
  });
}

test("in the window a code that works after a refused one clears the error, also without an input event", async () => {
  const answers = { "/api/ki/einladung": CODE_REFUSED };
  const w = windowWith({ "/api/ki/status": AGREED, "/api/claude/stand": new Error("none"),
    "/api/ki/einladung": () => answers["/api/ki/einladung"] });
  w.open();
  await settle();
  const dialog = w.dialog();
  choose(dialog, "einladung");
  const code = visible(dialog, n => n.attrs.id === "ki-fenster-code")[0];
  typeInto(code, "TEST-0000-TEST-0000");
  button(dialog, "Einladung einlösen").fire("click");
  await settle();
  const line = lineOf(dialog, code);
  assert.ok(line.textContent.startsWith(CODE_REFUSED.message));

  code.value = "TEST-0000-TEST-0001";  // filled without an input event, as a browser may on restore
  answers["/api/ki/einladung"] = SET_UP;
  findAll(dialog, n => n.tag === "button" && textOf(n) === "Einladung einlösen")[0].fire("click");
  await settle();

  assert.equal(line.textContent, "");
  assert.equal(code.attrs["aria-invalid"], undefined);
  assert.ok(textOf(dialog).includes("Die KI ist eingerichtet."));
});
