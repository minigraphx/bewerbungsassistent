// The browser the app opens in (G99, #369): the card «Browser der App» under «Browser und Erweiterung», its radio
// group with the browsers this computer has, the lines after saving, and the notice after a fallback.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const logic = require("../seiten/browser-wahl-logik.js");
const settings = require("../seiten/einstellungen-logik.js");

const PAGES = path.join(__dirname, "..", "seiten");
const read = name => fs.readFileSync(path.join(PAGES, name), "utf8");

const ALL_FOUND = [{ wert: "standard", gefunden: true }, { wert: "chrome", gefunden: true }, { wert: "edge", gefunden: true }];
const NO_CHROME = [{ wert: "standard", gefunden: true }, { wert: "chrome", gefunden: false }, { wert: "edge", gefunden: true }];

// ---------- the page ----------

test("the panel is called «Browser und Erweiterung» and keeps its anchor", () => {
  const html = read("einstellungen.html");
  assert.ok(html.includes('<a href="#erweiterung">Browser und Erweiterung</a>'));
  assert.ok(html.includes('id="bereich-erweiterung" aria-label="Browser und Erweiterung"'));
  assert.equal(settings.SECTIONS.find(section => section.id === "erweiterung").label, "Browser und Erweiterung");
});

test("the card «Browser der App» stands in that panel, hidden until the installed app answers", () => {
  const html = read("einstellungen.html");
  const start = html.indexOf('id="bereich-erweiterung"');
  const panel = html.slice(start, html.indexOf('class="settings__panel"', start));
  const card = panel.slice(panel.indexOf('<section class="card" id="browser"'));
  assert.ok(card.startsWith('<section class="card" id="browser" aria-labelledby="browser-titel" hidden>'));
  assert.ok(card.includes('<h2 id="browser-titel">Browser der App</h2>'));
  assert.ok(card.includes("<legend"));
  assert.ok(card.includes(logic.LEGEND));
  assert.ok(card.includes(logic.HINT));
  assert.ok(card.includes('role="status"'));
  assert.ok(panel.indexOf('id="erweiterung-titel"') < panel.indexOf('id="browser"'), "the extension card comes first");
  assert.ok(html.includes('<script src="/browser-wahl-logik.js"></script>'));
  assert.ok(html.includes('<script src="/browser-wahl.js"></script>'));
});

test("the anchor #browser opens the panel «Browser und Erweiterung»", () => {
  assert.equal(settings.sectionOf("#browser"), "erweiterung");
  assert.equal(settings.sectionOf("#erweiterung"), "erweiterung");
});

test("the texts are the ones of the UI/UX review", () => {
  assert.equal(logic.LEGEND, "Die App öffnet sich in");
  assert.equal(logic.HINT, "Die Browser-Erweiterung läuft in Chrome und Edge. Ist ein anderer Browser der Standard, "
    + "öffnet sich die App besser gleich in Chrome oder Edge.");
  assert.equal(logic.NOT_FOUND, "auf diesem Computer nicht gefunden");
});

// ---------- the radio group ----------

test("three options in order, the default browser preset", () => {
  const options = logic.options({ gewaehlt: "standard", plattform: "windows", browser: ALL_FOUND });
  assert.deepEqual(options.map(option => option.label),
    ["Standardbrowser des Computers (Voreinstellung)", "Google Chrome", "Microsoft Edge"]);
  assert.deepEqual(options.map(option => option.checked), [true, false, false]);
  assert.ok(options.every(option => !option.disabled && option.note === null));
});

test("on Linux Chromium counts for Chrome, and the label says so", () => {
  const options = logic.options({ gewaehlt: "chrome", plattform: "linux", browser: ALL_FOUND });
  assert.equal(options[1].label, "Google Chrome oder Chromium");
  assert.equal(options[1].checked, true);
});

test("a browser not found is disabled and says why in words, not only greyed", () => {
  const chrome = logic.options({ gewaehlt: "standard", plattform: "macos", browser: NO_CHROME })[1];
  assert.equal(chrome.disabled, true);
  assert.equal(chrome.note, "auf diesem Computer nicht gefunden");
});

test("a saved choice that is gone stays checked and says the default browser steps in", () => {
  const chrome = logic.options({ gewaehlt: "chrome", plattform: "windows", browser: NO_CHROME })[1];
  assert.equal(chrome.checked, true);
  assert.equal(chrome.disabled, true);
  assert.equal(chrome.note, "auf diesem Computer nicht gefunden; bis dahin öffnet sich die App im Standardbrowser");
});

test("a browser not found and not chosen keeps the plain note", () => {
  const chrome = logic.options({ gewaehlt: "edge", plattform: "windows", browser: NO_CHROME })[1];
  assert.equal(chrome.checked, false);
  assert.equal(chrome.note, "auf diesem Computer nicht gefunden");
});

test("an unknown choice checks the default browser", () => {
  const options = logic.options({ gewaehlt: "netscape", plattform: "windows", browser: ALL_FOUND });
  assert.deepEqual(options.map(option => option.checked), [true, false, false]);
});

test("after saving the line says where the app appears from the next opening", () => {
  assert.equal(logic.savedText("chrome", "windows"), "Gespeichert. Ab dem nächsten Öffnen erscheint die App in Google Chrome.");
  assert.equal(logic.savedText("edge", "macos"), "Gespeichert. Ab dem nächsten Öffnen erscheint die App in Microsoft Edge.");
  assert.equal(logic.savedText("standard", "linux"), "Gespeichert. Ab dem nächsten Öffnen erscheint die App im Standardbrowser.");
  assert.equal(logic.savedText("chrome", "linux"),
    "Gespeichert. Ab dem nächsten Öffnen erscheint die App in Google Chrome oder Chromium.");
});

test("a failed save names the reason", () => {
  assert.equal(logic.failedText("Die App antwortet nicht."), "Nicht gespeichert: Die App antwortet nicht.");
});

// ---------- saving on change (browser-wahl.js) ----------

/** browser-wahl.js in a sandbox; every POST waits until the test settles it. */
async function card(state) {
  const nodes = {};
  const posts = [];
  const lines = [];
  const make = tag => ({ tag, attrs: {}, children: [], listeners: {}, hidden: true, checked: false,
    setAttribute(name, value) { this.attrs[name] = value; },
    addEventListener(type, listener) { this.listeners[type] = listener; },
    append(...items) { this.children.push(...items); },
    replaceChildren(...items) { this.children = items; },
    scrollIntoView() {} });
  for (const id of ["browser", "browser-optionen", "browser-meldung"]) nodes[id] = make("div");
  const el = (tag, attrs = {}, ...children) => {
    const node = make(tag);
    for (const [name, value] of Object.entries(attrs)) if (value !== null && value !== false) node.setAttribute(name, value);
    node.value = attrs.value;
    node.append(...children.filter(child => child !== null));
    return node;
  };
  const inputs = () => {
    const walk = node => (typeof node === "object" ? [...(node.tag === "input" ? [node] : []), ...node.children.flatMap(walk)] : []);
    return walk(nodes["browser-optionen"]);
  };
  const App = {
    holen: async () => state,
    senden: (route, body) => new Promise((resolve, reject) => posts.push({ body, resolve, reject })),
    status: (element, text, level) => lines.push({ element, text, level }),
    el,
  };
  vm.runInNewContext(fs.readFileSync(path.join(PAGES, "browser-wahl.js"), "utf8"), {
    window: { App, BrowserWahlLogik: logic }, location: { hash: "" }, Promise,
    document: { getElementById: id => nodes[id], querySelectorAll: () => inputs() },
  });
  await settle();
  const pick = value => {
    for (const input of inputs()) input.checked = input.value === value;
    inputs().find(input => input.value === value).listeners.change();
  };
  const checked = () => inputs().find(input => input.checked)?.value;
  return { nodes, posts, lines, pick, checked };
}

test("a choice that cannot be saved puts the previous one back and says why", async () => {
  const page = await card({ gewaehlt: "standard", plattform: "windows", browser: ALL_FOUND });
  assert.equal(page.nodes.browser.hidden, false);

  page.pick("chrome");
  page.posts[0].reject(new Error("Die App antwortet nicht."));
  await settle();

  assert.equal(page.checked(), "standard");
  assert.deepEqual(page.lines.map(line => [line.text, line.level]), [["Nicht gespeichert: Die App antwortet nicht.", "fehler"]]);
});

test("the answer to an older click says nothing once a newer choice is on its way", async () => {
  const page = await card({ gewaehlt: "standard", plattform: "windows", browser: ALL_FOUND });

  page.pick("chrome");
  page.pick("edge");
  page.posts[1].resolve({ gewaehlt: "edge", plattform: "windows", browser: ALL_FOUND });
  await settle();
  page.posts[0].reject(new Error("zu spät"));
  await settle();

  assert.equal(page.checked(), "edge");
  assert.deepEqual(page.lines.map(line => line.text),
    ["Gespeichert. Ab dem nächsten Öffnen erscheint die App in Microsoft Edge."]);
});

// ---------- the notice after a fallback, on the first page ----------

const textOf = node => (node && typeof node === "object" ? node.children.map(textOf).join("") : String(node ?? ""));
const settle = async () => { for (let i = 0; i < 8; i += 1) await new Promise(resolve => setImmediate(resolve)); };
const find = (node, test) => (node && typeof node === "object"
  ? (test(node) ? node : node.children.map(child => find(child, test)).find(Boolean)) : undefined);

function element(tag) {
  const node = {
    tag, attrs: {}, children: [], hidden: false, className: "", listeners: {}, parent: null,
    get textContent() { return textOf(node); },
    set textContent(value) { node.children = [String(value)]; },
    setAttribute(name, value) { node.attrs[name] = value; },
    getAttribute(name) { return node.attrs[name]; },
    removeAttribute(name) { delete node.attrs[name]; },
    addEventListener(type, listener) { node.listeners[type] = listener; },
    append(...items) { items.forEach(item => { if (typeof item === "object") item.parent = node; }); node.children.push(...items); },
    replaceChildren(...items) { node.children = items; },
    prepend(...items) { items.forEach(item => { if (typeof item === "object") item.parent = node; }); node.children.unshift(...items); },
    remove() { if (node.parent) node.parent.children = node.parent.children.filter(child => child !== node); },
  };
  return node;
}

/** app.js in a sandbox on the first page of the installed app, opened with `search`. */
async function firstPage(search, { installed = true } = {}) {
  const main = element("main");
  const answers = installed ? { "/api/app/version": { version: "9.2.0", update: null }, "/api/app/einrichtung": { eingerichtet: true } } : {};
  const fetch = async url => {
    const found = answers[String(url).split("?")[0]];
    return { ok: Boolean(found), status: found ? 200 : 404, statusText: "", headers: { get: () => "application/json" },
             json: async () => found || { fehler: "Nicht gefunden" } };
  };
  const document = {
    querySelector: selector => (selector.startsWith("meta") ? { content: "token" } : selector === "main" ? main : null),
    getElementById: () => null,
    addEventListener() {}, hidden: false, documentElement: { dataset: {} },
    head: element("head"), body: element("body"), createElement: tag => element(tag), createTextNode: text => text,
  };
  const Node = { [Symbol.hasInstance]: value => typeof value === "object" && value !== null };
  const location = { pathname: "/", search, hash: "", origin: "http://127.0.0.1:1", replace() {}, reload() {} };
  const addresses = [];
  const history = { state: null, length: 1, replaceState(state, title, address) { addresses.push(address); } };
  vm.runInNewContext(fs.readFileSync(path.join(PAGES, "app.js"), "utf8"), {
    window: { addEventListener() {} }, document, location, history, fetch, URLSearchParams, Node,
    setInterval() {}, setTimeout, Promise, crypto: { randomUUID: () => "x" },
  });
  await settle();
  return { main, addresses };
}

const FALLBACK = "Google Chrome liess sich nicht starten, darum ist die App im Standardbrowser offen. "
  + "Der Browser für die App lässt sich unter Einstellungen, Browser und Erweiterung wählen.";

test("after a fallback the first page says so in a warning with the way to the settings", async () => {
  const { main } = await firstPage("?browser-fehlt=chrome");

  const notice = main.children[0];
  assert.equal(notice.className, "notice notice--warning");
  assert.equal(textOf(find(notice, node => node.className === "notice__body")), FALLBACK);
  const link = find(notice, node => node.tag === "a");
  assert.equal(link.attrs.href, "/einstellungen#browser");
  assert.equal(textOf(link), "Zu den Einstellungen");
});

test("the notice names Edge when Edge did not start", async () => {
  const { main } = await firstPage("?browser-fehlt=edge");

  assert.ok(textOf(main.children[0]).startsWith("Microsoft Edge liess sich nicht starten, "));
});

test("the notice can be closed", async () => {
  const { main } = await firstPage("?browser-fehlt=chrome");

  const close = find(main.children[0], node => node.tag === "button");
  assert.equal(close.attrs["aria-label"], "Meldung schliessen");
  close.listeners.click();
  assert.equal(main.children.length, 0);
});

test("the request leaves the address, so a reload shows no notice again", async () => {
  const { addresses } = await firstPage("?id=7&browser-fehlt=chrome");

  assert.deepEqual(addresses, ["/?id=7"]);
});

test("without a fallback, with an unknown browser or outside the installed app there is no notice", async () => {
  assert.equal((await firstPage("")).main.children.length, 0);
  assert.equal((await firstPage("?browser-fehlt=netscape")).main.children.length, 0);
  assert.equal((await firstPage("?browser-fehlt=chrome", { installed: false })).main.children.length, 0);
});
