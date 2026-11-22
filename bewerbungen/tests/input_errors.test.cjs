// An error about the person's own input clears once the input fits or the action worked (G97, #341); every other
// error still stays until «×» (#215). The shared helper first, then /suchbegriffe with a stand-in DOM, then each
// other input error of the app.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const meldungen = require("../seiten/meldungen.js");
const Texte = require("../seiten/texte.js");
const DotLine = require("../seiten/dot-line.js");

const SEITEN = path.join(__dirname, "..", "seiten");
const source = name => fs.readFileSync(path.join(SEITEN, name), "utf8");

// A small stand-in DOM: what meldungen.js and suchbegriffe.js use, and events that bubble.
class FakeText {
  constructor(text) { this.data = String(text); this.parentNode = null; }
  get textContent() { return this.data; }
}

class FakeElement {
  constructor(document, tag) {
    Object.assign(this, { ownerDocument: document, tagName: tag.toUpperCase(), childNodes: [], parentNode: null,
      dataset: {}, attrs: new Map(), listeners: {}, classes: new Set(), value: "", checked: false });
    this.classList = {
      add: (...names) => names.forEach(n => this.classes.add(n)),
      remove: (...names) => names.forEach(n => this.classes.delete(n)),
      contains: name => this.classes.has(name),
      toggle: (name, on) => (on ? this.classes.add(name) : this.classes.delete(name)),
    };
  }
  get children() { return this.childNodes.filter(n => n instanceof FakeElement); }
  get className() { return [...this.classes].join(" "); }
  set className(value) { this.classes = new Set(String(value).split(/\s+/).filter(Boolean)); }
  get textContent() { return this.childNodes.map(n => n.textContent).join(""); }
  set textContent(value) { this.replaceChildren(...(value === "" ? [] : [String(value)])); }
  get hidden() { return this.attrs.has("hidden"); }
  set hidden(value) { if (value) this.attrs.set("hidden", ""); else this.attrs.delete("hidden"); }
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
  replaceChildren(...nodes) { this.childNodes = []; this.append(...nodes); }
  contains(node) {
    for (let n = node; n; n = n.parentNode) if (n === this) return true;
    return false;
  }
  addEventListener(type, handler) { (this.listeners[type] ||= []).push(handler); }
  removeEventListener(type, handler) { this.listeners[type] = (this.listeners[type] || []).filter(h => h !== handler); }
  listenerCount() { return Object.values(this.listeners).reduce((sum, list) => sum + list.length, 0); }
  dispatch(type, init = {}) {
    for (let n = this; n; n = n.parentNode) for (const h of [...(n.listeners[type] || [])]) h({ type, target: this, ...init });
  }
  focus() { this.ownerDocument.activeElement = this; }
  querySelector() { return null; }
  querySelectorAll() { return []; }
  find(tag) {
    for (const child of this.children) {
      if (child.tagName === tag) return child;
      const inner = child.find(tag);
      if (inner) return inner;
    }
    return null;
  }
}

function fakeDocument() {
  const document = { activeElement: null };
  document.createElement = tag => new FakeElement(document, tag);
  return document;
}

const closeButton = line => line.find("BUTTON");
const type = (field, text) => { field.value = text; field.dispatch("input"); };

// The shared helper

function setup() {
  const document = fakeDocument();
  const line = document.createElement("p");
  line.className = "status-line";
  const field = document.createElement("textarea");
  return { document, line, field };
}

test("an input error clears on the first input in its field, and the focus stays in the field", () => {
  const { document, line, field } = setup();
  field.setAttribute("aria-invalid", "true");
  meldungen.zeige(line, "Bitte schreiben, was anders sein soll.", "fehler", { input: field });
  field.focus();
  assert.equal(line.dataset.level, "danger");
  assert.ok(closeButton(line), "it can still be closed with «×» before");

  type(field, "T");

  assert.equal(line.textContent, "");
  assert.equal(line.dataset.level, undefined);
  assert.ok(!line.classList.contains("status--closable"));
  assert.equal(field.getAttribute("aria-invalid"), null, "the field is no longer marked invalid");
  assert.equal(document.activeElement, field);
  assert.equal(field.listenerCount(), 0, "the watch ends with the message");

  meldungen.zeige(line, "Die App antwortet nicht.", "fehler");
  type(field, "x");
  assert.match(line.textContent, /Die App antwortet nicht/, "an error without a field stays on input");
  closeButton(line).dispatch("click");
  assert.equal(line.textContent, "", "until «×»");
});

test("a change in a box or a radio clears it as well, also from inside an element around the fields", () => {
  const { document, line } = setup();
  const group = document.createElement("fieldset");
  const box = document.createElement("input");
  group.append(box);
  meldungen.zeige(line, "Bitte mindestens eine Kürzung anhaken.", "fehler", { input: group });

  box.checked = true;
  box.dispatch("change");

  assert.equal(line.textContent, "");
});

test("clearing an error watched through a container drops aria-invalid of the fields inside it", () => {
  const { document, line } = setup();
  const group = document.createElement("div");
  const first = document.createElement("textarea");
  const second = document.createElement("textarea");
  group.append(first, second);
  group.querySelectorAll = selector => (selector === "[aria-invalid]"
    ? group.children.filter(child => child.hasAttribute("aria-invalid")) : []);
  first.setAttribute("aria-invalid", "true");
  meldungen.zeige(line, "Das Anschreiben braucht mindestens einen Absatz mit Text.", "fehler", { input: group });

  type(second, "Neuer Absatz");

  assert.equal(line.textContent, "");
  assert.equal(first.getAttribute("aria-invalid"), null, "the field marked inside the container is valid again");
});

test("any of several fields clears it", () => {
  const { document, line, field } = setup();
  const other = document.createElement("input");
  meldungen.zeige(line, "Bitte ausfüllen.", "hinweis", { input: [field, other] });

  type(other, "x");

  assert.equal(line.textContent, "");
  assert.equal(field.listenerCount(), 0);
});

test("a newer message ends the watch: input then leaves the newer error alone", () => {
  const { line, field } = setup();
  meldungen.zeige(line, "Bitte schreiben, was anders sein soll.", "fehler", { input: field });
  assert.ok(field.listenerCount() > 0, "the field is watched while its error shows");
  meldungen.zeige(line, "Kein Vorschlag: Die KI antwortet nicht.", "fehler");
  assert.equal(field.listenerCount(), 0);

  type(field, "x");

  assert.match(line.textContent, /Die KI antwortet nicht/);
});

test("clearInputError clears an input error once the action worked, and nothing else", () => {
  const { line, field } = setup();
  meldungen.zeige(line, "Bitte schreiben, was anders sein soll.", "fehler", { input: field });
  meldungen.clearInputError(line);
  assert.equal(line.textContent, "");
  assert.equal(field.listenerCount(), 0);

  meldungen.zeige(line, "Kein Vorschlag: Die KI antwortet nicht.", "fehler");
  meldungen.clearInputError(line);
  assert.match(line.textContent, /Die KI antwortet nicht/);
});

test("clearOnInput watches a line the page writes itself, as long as it still says the same", () => {
  const { line, field } = setup();
  line.textContent = "Bitte mindestens eine Kürzung anhaken oder drei Seiten erlauben.";
  meldungen.clearOnInput(line, field);
  type(field, "x");
  assert.equal(line.textContent, "");

  line.textContent = "Bitte mindestens eine Kürzung anhaken oder drei Seiten erlauben.";
  meldungen.clearOnInput(line, field);
  line.textContent = "Wird gekürzt und neu erstellt …";
  type(field, "x");
  assert.equal(line.textContent, "Wird gekürzt und neu erstellt …", "a text the page wrote since stays");
  assert.equal(field.listenerCount(), 0);
});

test("only a refusal of the values counts as an input error; a failure to reach the app does not", () => {
  assert.equal(meldungen.isInputRejection(Object.assign(new Error("Begriff schon gesucht."), { status: 400 })), true);
  assert.equal(meldungen.isInputRejection(Object.assign(new Error("Interner Fehler"), { status: 500 })), false);
  assert.equal(meldungen.isInputRejection(new Error("Failed to fetch")), false);
});

// The failure of an action on one field (#361): shared by Einstellungen and the window „KI einrichten“

test("showFailure ties a refused value to its field: marked invalid, cleared on the first input there", () => {
  const { line, field } = setup();
  const refused = Object.assign(new Error("Der Code gilt nicht."), { status: 400 });

  assert.equal(meldungen.showFailure(line, field, refused), true, "it says it was a refusal");

  assert.equal(line.textContent.startsWith("Der Code gilt nicht."), true);
  assert.equal(line.dataset.level, "danger");
  assert.equal(field.getAttribute("aria-invalid"), "true");
  type(field, "x");
  assert.equal(line.textContent, "");
  assert.equal(field.getAttribute("aria-invalid"), null);
});

test("showFailure leaves any other failure until «×» and the field valid, also after an earlier refusal", () => {
  const { line, field } = setup();
  meldungen.showFailure(line, field, Object.assign(new Error("Der Code gilt nicht."), { status: 400 }));
  const unreachable = Object.assign(new Error("Keine Verbindung zur KI."), { status: 502 });

  assert.equal(meldungen.showFailure(line, field, unreachable), false);

  assert.equal(field.getAttribute("aria-invalid"), null, "the field is not what failed");
  type(field, "x");
  assert.match(line.textContent, /Keine Verbindung zur KI/);
  closeButton(line).dispatch("click");
  assert.equal(line.textContent, "");
});

test("focusAfterFailure: a refused value goes back to its field, any other failure to the button while it can try again", () => {
  const { document, field } = setup();
  const retry = document.createElement("button");
  const refused = Object.assign(new Error("Der Code gilt nicht."), { status: 400 });
  const unreachable = Object.assign(new Error("Keine Verbindung zur KI."), { status: 502 });

  meldungen.focusAfterFailure(refused, field, retry);
  assert.equal(document.activeElement, field);

  meldungen.focusAfterFailure(unreachable, field, retry);
  assert.equal(document.activeElement, retry);

  retry.disabled = true;  // the field is empty again: the next try starts there
  meldungen.focusAfterFailure(unreachable, field, retry);
  assert.equal(document.activeElement, field);
});

test("Einstellungen and the window „KI einrichten“ show a failed code or key through the shared helper", () => {
  for (const name of ["einstellungen.js", "ki-fenster.js"]) {
    assert.match(source(name), /window\.Meldungen\.showFailure\(/, `${name} uses Meldungen.showFailure`);
    assert.match(source(name), /window\.Meldungen\.focusAfterFailure\(/, `${name} uses Meldungen.focusAfterFailure`);
    assert.doesNotMatch(source(name), /function showFailure\(/, `${name} keeps no copy of its own`);
  }
});

// /suchbegriffe: „Neu vorschlagen“ without a text

const ESTIMATE = "/api/suchbegriffe/schaetzung";
const HINT = { verfuegbar: true, hinweis: null, treffer: 40, seit: "2026-11-01" };
const FITS = { aenderungen: [], treffer: 40, seit: "2026-11-01", runde: 1 };
const TERMS = { suchbegriffe: ["Python"], positiv: [], ausschluss: [] };
const CHANGE = { nummer: 1, bereich: "keywords", bereich_name: "Suchbegriffe", zu_allgemein: false, satz: "«Trainer» aufnehmen",
  entfaellt: [], neu: ["Trainer"], grund: "Steht im Lebenslauf.", beleg: null };
const PROPOSAL = { vorschlag: "v1", aenderungen: [CHANGE], zusammenfassung: "Eine Änderung.", treffer: 40,
  seit: "2026-11-01", jetzt: TERMS, bisherige: TERMS, endstand: { ...TERMS, suchbegriffe: ["Python", "Trainer"] }, entfaellt: [],
  grenzen: { teile: ["Danach: 2 von 15 Suchbegriffen"], gesperrt: null, zu_viel: { suchbegriffe: 0, positiv: 0, ausschluss: 0 },
    erlaubt: { suchbegriffe: 15, positiv: 30, ausschluss: 30 } }, modell: "claude-sonnet-5-5", kosten_usd: 0.03,
  waehrung: "USD", datum: "2026-11-16", runde: 1 };
const ASK = "Bitte schreiben, was anders sein soll.";

const settled = async () => {
  for (let i = 0; i < 10; i += 1) await new Promise(resolve => setImmediate(resolve));
};

/** Runs suchbegriffe.js with the real meldungen.js; `answers` stays live, `sent` lists each POST. */
async function termsPage(answers) {
  const document = fakeDocument();
  const elements = new Map();
  document.getElementById = id => {
    if (!elements.has(id)) elements.set(id, document.createElement(id === "anders-text" ? "textarea" : "div"));
    return elements.get(id);
  };
  document.addEventListener = () => {};
  const el = (tag, attributes = {}, ...children) => {
    const element = document.createElement(tag);
    for (const [name, value] of Object.entries(attributes)) {
      if (name === "class") element.className = value;
      else if (name.startsWith("on") && typeof value === "function") element.addEventListener(name.slice(2), value);
      else element.setAttribute(name, value);
    }
    for (const child of children.flat()) if (child !== null && child !== undefined && child !== false) element.append(child);
    return element;
  };
  const sent = [];
  const answer = async (route, body) => {
    if (body) sent.push({ route, body });
    if (!(route in answers)) throw new Error(`unexpected route ${route}`);
    if (answers[route] instanceof Error) throw answers[route];
    return answers[route];
  };
  const window = { Texte, DotLine };
  const context = { window, document, console, setTimeout: () => 0, clearTimeout: () => {}, CustomEvent: class {} };
  vm.createContext(context);
  vm.runInContext(source("meldungen.js"), context);
  window.App = { el, holen: route => answer(route), senden: answer, textsatz: async () => "stelle-sie",
    status: (element, text, art, optionen) => window.Meldungen.zeige(element, text, art, optionen) };
  for (const name of ["treffer-logik.js", "suchbegriffe-logik.js", "suchbegriffe-schalter.js", "suchbegriffe-gezaehlt.js", "suchbegriffe.js"]) {
    vm.runInContext(source(name), context);
  }
  await settled();
  const $ = id => document.getElementById(id);
  const ask = async () => {
    $("neu-vorschlagen").dispatch("click");
    await settled();
  };
  return { $, document, sent, ask };
}

const termsAnswers = proposal => ({ "/api/suchbegriffe/hinweis": HINT, "/api/ki/status": { einwilligung: null },
  "/api/suchbegriffe/vorschlag": proposal, [ESTIMATE]: { verfuegbar: true, anzahl: 1, kosten: 0.03, waehrung: "USD",
    guthaben: null, danach: null, dauer_minuten: 1, reicht_fuer: null } });

test("on /suchbegriffe the error shows beside the field, also when the proposal is hidden, and the focus is in the field", async () => {
  const page = await termsPage(termsAnswers(FITS));
  assert.equal(page.$("vorschlag").hidden, true, "nothing to change: the proposal is hidden, the field stays");
  page.sent.length = 0;

  await page.ask();

  assert.match(page.$("anders-status").textContent, new RegExp(ASK));
  assert.equal(page.$("anders-status").dataset.level, "danger");
  assert.equal(page.$("status").textContent, "", "not in the line of the hidden proposal");
  assert.equal(page.document.activeElement, page.$("anders-text"));
  assert.equal(page.sent.filter(s => s.route === "/api/suchbegriffe/vorschlag").length, 0, "nothing goes to the AI");
});

test("on /suchbegriffe the first input in the field clears it, the focus stays, another error stays until «×»", async () => {
  const answers = { ...termsAnswers(PROPOSAL), "/api/suchbegriffe/endstand": new Error("Die App antwortet nicht.") };
  const page = await termsPage(answers);
  const box = page.$("aenderungen").find("INPUT");
  box.checked = false;
  box.dispatch("change");
  await settled();
  assert.match(page.$("status").textContent, /Die App antwortet nicht/);
  await page.ask();
  assert.match(page.$("anders-status").textContent, new RegExp(ASK));

  page.$("anders-text").focus();
  type(page.$("anders-text"), "T");

  assert.equal(page.$("anders-status").textContent, "");
  assert.equal(page.document.activeElement, page.$("anders-text"));
  assert.match(page.$("status").textContent, /Die App antwortet nicht/, "an error that is not about the field stays");
  assert.ok(closeButton(page.$("status")));
});

test("on /suchbegriffe a successful „Neu vorschlagen“ clears it", async () => {
  const answers = termsAnswers(PROPOSAL);
  const page = await termsPage(answers);
  await page.ask();
  assert.match(page.$("anders-status").textContent, new RegExp(ASK));

  page.$("anders-text").value = "«Trainer» behalten";  // filled without an input event, as a browser may on restore
  answers["/api/suchbegriffe/vorschlag"] = { ...PROPOSAL, vorschlag: "v2", runde: 2, hinweis: "«Trainer» behalten" };
  await page.ask();

  assert.equal(page.$("anders-status").textContent, "");
  // The page's objects come from another realm, so compare their JSON.
  assert.equal(JSON.stringify(page.sent.at(-1).body), JSON.stringify({ vorher: "v1", hinweis: "«Trainer» behalten" }));
});

test("on /suchbegriffe the field is marked invalid with its error and valid again after one input", async () => {
  const page = await termsPage(termsAnswers(PROPOSAL));
  await page.ask();
  assert.equal(page.$("anders-text").getAttribute("aria-invalid"), "true");

  type(page.$("anders-text"), "T");

  assert.equal(page.$("anders-text").getAttribute("aria-invalid"), null);
  assert.equal(page.$("anders-status").textContent, "");
});

test("on /suchbegriffe the field is described by its hint and its error line", () => {
  const html = source("suchbegriffe.html");
  const field = html.match(/<textarea [^>]*id="anders-text"[^>]*>/)[0];
  assert.match(field, /aria-describedby="anders-hilfe anders-status"/);
  assert.match(html, /id="anders-hilfe"/);
  assert.match(html, /id="anders-status"/);
});

test("on /suchbegriffe the line for the field is a live region inside the revise section, after the button", () => {
  const html = source("suchbegriffe.html");
  const section = html.slice(html.indexOf('<section id="anders"'), html.indexOf("</section>", html.indexOf('<section id="anders"')));
  assert.match(section, /id="neu-vorschlagen"[\s\S]*<p class="status-line" id="anders-status" role="status" aria-live="polite"><\/p>/);
});

// The other input errors of the app use the same helper (inventory of #341)

const WIRED = [
  ["fragen.js", "an empty question", /status\(\$\("fragen-meldung"\), texte\.leer, "hinweis", \{ input: \$\("fragen-text"\) \}\)/],
  ["firmen.js", "no company chosen", /meldung\("Bitte eine Firma wählen oder «Keine davon passt»\.", "warning",\s*\{ input: document\.getElementById\(`wahl-\$\{firma\.schluessel\}`\) \}\)/],
  ["firmen.js", "a kununu value or count by hand that does not fit", /if \(falsch\) window\.Meldungen\.clearOnInput\(\$\(`hand-\$\{feld\}-fehler`\), \$\(`hand-\$\{feld\}`\)\)/],
  ["firmen.js", "a kununu link refused", /if \(abgelehnt\) window\.Meldungen\.clearOnInput\(\$\("zuordnen-fehler"\), \$\("zuordnen-link"\)\)/],
  ["kuerzen.js", "no cut ticked", /status\.textContent = NOTHING_TICKED;\s*window\.Meldungen\.clearOnInput\(status, fieldset\)/],
  ["lebenslauf-erstellen.js", "no station chosen", /error\.message === Logic\.NOTHING_CHOSEN \? \$\("cv-erstellen-stationen"\) : null/],
  ["letter-editor.js", "a letter without a paragraph", /say\(NO_TEXT, "fehler", \{ input: \$\("brief-absaetze"\) \}\)/],
  ["beruf-vorschlag.js", "an own search term refused", /meldeListe\(fehler\.message, "fehler", \{ input: window\.Meldungen\.isInputRejection\(fehler\) \? feld : null \}\)/],
  ["suche-rahmen.js", "a value of Region, Was nicht or Titelfilter refused", /\{ input: window\.Meldungen\.isInputRejection\(fehler\) \? \$\(`\$\{karte\}-form`\) : null \}/],
  ["weitere-seiten.js", "an address refused", /meldung\(fehler\.message, "fehler", \{ input: window\.Meldungen\.isInputRejection\(fehler\) \? \$\("seiten"\) : null \}\)/],
  ["haken-ausschluss.js", "an exclusion entry refused", /if \(window\.Meldungen\.isInputRejection\(fehler\)\) window\.Meldungen\.clearOnInput\(teile\.fehler, teile\.feld\)/],
  ["zeichen.js", "initials refused", /speichere\("\/api\/dossier\/zeichen", \{ initialen: event\.target\.value\.trim\(\) \}, \$\("d-initialen"\)\)/],
];

for (const [name, what, wiring] of WIRED) {
  test(`${name}: ${what} clears on the first input in its field`, () => {
    assert.ok(wiring.test(source(name)), `${name} does not arm ${wiring}`);
  });
}

test("lebenslauf-erstellen-logik.js names the error of no station, so the page knows it is about the choice", () => {
  const logic = require("../seiten/lebenslauf-erstellen-logik.js");
  assert.equal(logic.NOTHING_CHOSEN, "Bitte mindestens eine Station wählen.");
});

test("zeichen.js passes the field of a refused value on to its message", () => {
  const wiring = /meldung\(`Nicht gespeichert\. \$\{fehler\.message\}`, "fehler", \{ input: window\.Meldungen\.isInputRejection\(fehler\) \? feld : null \}\)/;
  assert.ok(wiring.test(source("zeichen.js")), `zeichen.js does not arm ${wiring}`);
});

// Einstellungen: the invitation code and the own key (#350). The routes answer 400 only for a value wrong in itself.

const refusal = (message, status) => Object.assign(new Error(message), { status });
const CODE_REFUSED = refusal("Der Code gilt nicht (falsch, schon benutzt oder abgelaufen). Bitte um einen neuen Code.", 400);
const MEDIATION_DOWN = refusal("Keine Verbindung zur KI. Ist der Rechner mit dem Internet verbunden?", 502);
const KEY_REFUSED = refusal("Dieser Schlüssel gilt nicht. Bitte in der Anthropic Console prüfen. Gespeichert wurde nichts.", 400);
const SETTINGS_ANSWERS = {
  "/api/schluessel": { gesetzt: false, kosten: { monat_usd: 0, gesamt_usd: 0, aufrufe: 0, aufgaben: {} } },
  "/api/ki/status": { monat: "2026-11", eingerichtet: false, einladung: true, kosten_usd: 0, einwilligung: { erteilt: true } },
  "/api/claude/stand": new Error("none"),
  "/api/einrichtung/wahl": { gesucht: "stelle", anrede: "sie", rav: false },
};

/** Runs einstellungen.js with the real meldungen.js; `answers` stays live. */
async function settingsPage(answers) {
  const document = fakeDocument();
  const elements = new Map();
  const make = tag => Object.assign(document.createElement(tag), { style: {}, scrollIntoView: () => {} });
  document.getElementById = id => {
    if (!elements.has(id)) elements.set(id, make(["einladung-code", "schluessel", "bestaetigt"].includes(id) ? "input" : "div"));
    return elements.get(id);
  };
  document.querySelector = () => make("div");
  document.querySelectorAll = () => [];
  document.documentElement = { dataset: {} };
  const el = (tag, attributes = {}, ...children) => {
    const element = document.createElement(tag);
    for (const [name, value] of Object.entries(attributes)) element.setAttribute(name, value);
    for (const child of children.flat()) if (child !== null && child !== undefined && child !== false) element.append(child);
    return element;
  };
  const answer = async route => {
    if (!(route in answers)) throw new Error(`unexpected route ${route}`);
    if (answers[route] instanceof Error) throw answers[route];
    return answers[route];
  };
  const window = {
    Texte, EinstellungenLogik: require("../seiten/einstellungen-logik.js"),
    KiZugang: { options: () => [], render: () => ({ choose: () => {}, setCurrent: () => {} }) },
    Einwilligung: { link: () => null, zeile: () => {} },
    addEventListener: () => {}, postMessage: () => {},
  };
  const context = { window, document, console, location: { hash: "", origin: "http://127.0.0.1" },
    setTimeout: () => 0, clearTimeout: () => {}, MutationObserver: class { observe() {} } };
  vm.createContext(context);
  vm.runInContext(source("meldungen.js"), context);
  window.App = { el, holen: route => answer(route), senden: answer, bestaetigen: () => {},
    status: (element, text, art, optionen) => window.Meldungen.zeige(element, text, art, optionen) };
  vm.runInContext(source("einstellungen.js"), context);
  await settled();
  const $ = id => document.getElementById(id);
  return { $, document };
}

async function redeemWith(failure) {
  const page = await settingsPage({ ...SETTINGS_ANSWERS, "/api/ki/einladung": failure });
  type(page.$("einladung-code"), "TEST-0000-TEST-0000");
  page.$("einladung-einloesen").dispatch("click");
  await settled();
  return page;
}

async function saveKeyWith(failure) {
  const page = await settingsPage({ ...SETTINGS_ANSWERS, "/api/schluessel/speichern": failure });
  page.$("bestaetigt").checked = true;
  type(page.$("schluessel"), "erfundener-schluessel-0123456789");
  page.$("speichern").dispatch("click");
  await settled();
  return page;
}

test("Einstellungen: a refused invitation code clears on the first input in the code field", async () => {
  const { $ } = await redeemWith(CODE_REFUSED);
  assert.equal($("einladung-status").textContent.startsWith(CODE_REFUSED.message), true);
  assert.equal($("einladung-code").getAttribute("aria-invalid"), "true");

  type($("einladung-code"), "TEST-0000-TEST-0001");

  assert.equal($("einladung-status").textContent, "");
  assert.equal($("einladung-code").getAttribute("aria-invalid"), null);
});

test("Einstellungen: an unreachable mediation is no input error and stays until «×»", async () => {
  const { $ } = await redeemWith(MEDIATION_DOWN);
  type($("einladung-code"), "TEST-0000-TEST-0001");
  assert.match($("einladung-status").textContent, /Keine Verbindung zur KI/);
  assert.equal($("einladung-code").getAttribute("aria-invalid"), null);
  closeButton($("einladung-status")).dispatch("click");
  assert.equal($("einladung-status").textContent, "");
});

test("Einstellungen: a refused own key clears on the first input in the key field", async () => {
  const { $ } = await saveKeyWith(KEY_REFUSED);
  assert.equal($("meldung").textContent.startsWith(KEY_REFUSED.message), true);
  assert.equal($("schluessel").getAttribute("aria-invalid"), "true");

  type($("schluessel"), "s");

  assert.equal($("meldung").textContent, "");
  assert.equal($("schluessel").getAttribute("aria-invalid"), null);
});

test("Einstellungen: after a refused code the focus is in the code field", async () => {
  const { $, document } = await redeemWith(CODE_REFUSED);
  assert.equal(document.activeElement, $("einladung-code"));
});

test("Einstellungen: after an unreachable mediation with a code still typed the focus is on «Einladung einlösen»", async () => {
  const { $, document } = await redeemWith(MEDIATION_DOWN);
  assert.equal($("einladung-code").value, "TEST-0000-TEST-0000");
  assert.equal(document.activeElement, $("einladung-einloesen"));
});

for (const [what, failure] of [["refused", KEY_REFUSED], ["not checked", MEDIATION_DOWN]]) {
  test(`Einstellungen: after a key ${what} the focus is in the key field`, async () => {
    const { $, document } = await saveKeyWith(failure);
    assert.equal(document.activeElement, $("schluessel"));
  });
}

test("Einstellungen: the code and the key field are described by the line of their message", () => {
  const html = source("einstellungen.html");
  assert.match(html, /<input class="input" id="einladung-code" [^>]*aria-describedby="einladung-status"[^>]*>/);
  assert.match(html, /<input class="input" id="schluessel" [^>]*aria-describedby="meldung"[^>]*>/);
});

test("Einstellungen: an Anthropic that cannot check the key is no input error and stays until «×»", async () => {
  const { $ } = await saveKeyWith(MEDIATION_DOWN);
  type($("schluessel"), "s");
  assert.match($("meldung").textContent, /Keine Verbindung zur KI/);
  closeButton($("meldung")).dispatch("click");
  assert.equal($("meldung").textContent, "");
});
