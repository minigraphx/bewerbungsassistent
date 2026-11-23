// «Nach Updates suchen» under «Über die App» (#370, G100): the button asks the update server at once and the line
// below it says what came back. No test reaches a server: every answer here is invented.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const Texte = require("../seiten/texte.js");

const SEITEN = path.join(__dirname, "..", "seiten");
const ROUTE = "/api/app/updates-suchen";
const FAILED = "Die Suche nach Updates hat nicht geklappt. Vielleicht fehlt die Internetverbindung; bitte später nochmals versuchen.";
const STORE_NOTE = "Updates kommen über den Microsoft Store.";
const TIMEOUT_MS = 10000;
const PRESENCE = ["/api/app/da", "/api/app/weg"];  // the heartbeat of every page, not part of the check

/** A stand-in DOM element: tree, attributes, classes, listeners, click and focus. */
function element(document, tag) {
  const node = {
    tag, attrs: {}, children: [], parentNode: null, hidden: false, disabled: false, listeners: {}, classes: new Set(),
    get className() { return [...node.classes].join(" "); },
    set className(value) { node.classes = new Set(String(value).split(/\s+/).filter(Boolean)); },
    classList: {
      add: (...names) => names.forEach(name => node.classes.add(name)),
      remove: (...names) => names.forEach(name => node.classes.delete(name)),
      contains: name => node.classes.has(name),
      toggle: (name, on) => { if (on ?? !node.classes.has(name)) node.classes.add(name); else node.classes.delete(name); },
    },
    get textContent() { return node.children.map(child => (typeof child === "string" ? child : child.textContent)).join(""); },
    set textContent(value) { node.replaceChildren(...(value === "" ? [] : [String(value)])); },
    get href() { return node.attrs.href; },
    setAttribute(name, value) { node.attrs[name] = String(value); },
    getAttribute(name) { return name in node.attrs ? node.attrs[name] : null; },
    removeAttribute(name) { delete node.attrs[name]; },
    hasAttribute(name) { return name in node.attrs; },
    append(...items) {
      for (const item of items) {
        if (typeof item === "object") { item.parentNode?.children.splice(item.parentNode.children.indexOf(item), 1); item.parentNode = node; }
        node.children.push(item);
      }
    },
    prepend(...items) { for (const item of items.reverse()) { if (typeof item === "object") item.parentNode = node; node.children.unshift(item); } },
    replaceChildren(...items) {
      node.children.forEach(child => { if (typeof child === "object") child.parentNode = null; });
      node.children = [];
      node.append(...items);
      document.mutations.push(node);
    },
    remove() {
      if (!node.parentNode) return;
      node.parentNode.children.splice(node.parentNode.children.indexOf(node), 1);
      node.parentNode = null;
    },
    contains(other) { for (let n = other; n; n = n.parentNode) if (n === node) return true; return false; },
    addEventListener(type, handler) { (node.listeners[type] ||= []).push(handler); },
    click() { for (const handler of node.listeners.click || []) handler({ type: "click", target: node, preventDefault() {} }); },
    focus() { document.activeElement = node; },
    showModal() {}, close() {},
  };
  return node;
}

const all = node => (typeof node === "object" ? [node, ...node.children.flatMap(all)] : []);

/** app.js on the settings page; `answers` maps a path to its answer or to a function giving a promise of one. */
async function settingsPage(answers) {
  const timers = [];
  const sent = [];
  const document = {
    mutations: [], activeElement: null, hidden: false, documentElement: { dataset: {} },
    addEventListener() {}, createTextNode: text => text, querySelectorAll: () => [],
  };
  document.createElement = tag => element(document, tag);
  document.head = element(document, "head");
  document.body = element(document, "body");
  const main = element(document, "main");
  const card = element(document, "section");
  card.attrs.id = "ueber-die-app";
  card.hidden = true;
  document.body.append(main);
  main.append(card);
  document.activeElement = document.body;
  document.getElementById = id => all(document.body).find(node => node.attrs.id === id) || null;
  document.querySelector = selector => (selector.startsWith("meta") ? { content: "token" } : selector === "main" ? main : null);
  const respond = (status, data) => ({ ok: status < 400, status, statusText: "", headers: { get: () => "application/json" },
                                       json: async () => data });
  const fetch = async (url, options = {}) => {
    const route = String(url).split("?")[0];
    if (options.method === "POST" && !PRESENCE.includes(route)) sent.push(route);
    const found = answers[route];
    if (found === undefined) return respond(404, { fehler: "Nicht gefunden" });
    const answer = typeof found === "function" ? await found() : found;
    return answer.status ? respond(answer.status, answer.data) : respond(200, answer);
  };
  const Node = { [Symbol.hasInstance]: value => typeof value === "object" && value !== null };
  const location = { pathname: "/einstellungen", search: "", hash: "", origin: "http://127.0.0.1:1", replace() {}, reload() {} };
  vm.runInNewContext(fs.readFileSync(path.join(SEITEN, "app.js"), "utf8"), {
    window: { addEventListener() {}, Texte }, document, location, history: { state: null, length: 1, replaceState() {} },
    fetch, URLSearchParams, Node, Promise, Date, Intl, Set, Map, Error, crypto: { randomUUID: () => "x" },
    setInterval() {}, setTimeout: (run, ms = 0) => timers.push({ run, ms }) && timers.length,
    clearTimeout: id => { if (timers[id - 1]) timers[id - 1].run = null; },
  });
  /** Let promises settle and run every timer shorter than `upTo` ms, as often as new ones appear. */
  const settle = async (upTo = TIMEOUT_MS - 1) => {
    for (let round = 0; round < 20; round += 1) {
      for (let i = 0; i < 6; i += 1) await new Promise(resolve => setImmediate(resolve));
      const due = timers.filter(timer => timer.run && timer.ms <= upTo);
      if (!due.length) continue;
      for (const timer of due) { const run = timer.run; timer.run = null; run(); }
    }
  };
  await settle();
  const button = () => all(card).find(node => node.tag === "button" && node.textContent === "Nach Updates suchen");
  const line = () => document.getElementById("update-suche");
  return { document, card, main, sent, settle, button, line };
}

const version = (extra = {}) => ({ version: "9.2.0", update: null, ...extra });
const newer = (extra = {}) => ({ version: "9.3.0", seite: "https://example.ch/releases", automatisch: true, beimBeenden: true,
                                 hinweis: "", fragen: true, ...extra });
const later = () => { let release; const promise = new Promise(resolve => { release = resolve; }); return { promise, release }; };

test("name, version and author come first, then the button with the live line below it", async () => {
  const page = await settingsPage({ "/api/app/version": version() });

  const knopf = page.button();
  assert.ok(knopf, "button missing");
  assert.ok(knopf.classes.has("btn") && !knopf.classes.has("btn--primary"));
  assert.equal(knopf.getAttribute("aria-describedby"), "update-suche");
  const zeile = page.line();
  assert.equal(zeile.tag, "p");
  assert.equal(zeile.getAttribute("role"), "status");
  assert.equal(zeile.getAttribute("aria-live"), "polite");
  const block = knopf.parentNode.parentNode;
  const order = block.children.filter(child => typeof child === "object");
  assert.equal(order.length, 4);
  assert.equal(order[0].textContent, "Bewerbungsbegleiter");
  assert.equal(order[1].textContent, "Version 9.2.0");
  assert.equal(order[2].textContent, "von Andreas Schmidt");
  assert.ok(order[3].contains(knopf) && order[3].contains(zeile));
  assert.ok(all(page.card).some(node => node.tag === "button" && node.textContent === "Beenden" && !block.contains(node)));
});

test("up to date: the line names the version and the time of the check", async () => {
  const page = await settingsPage({ "/api/app/version": version(), [ROUTE]: { version: "9.2.0", update: null, vorabversionen: false } });

  page.button().click();
  await page.settle();

  assert.match(page.line().textContent, /^Version 9\.2\.0 ist die neueste\. Geprüft um \d{2}:\d{2}\.$/);
  assert.deepEqual(page.sent, [ROUTE]);
});

test("with pre-releases on, the line says they were included", async () => {
  const page = await settingsPage({ "/api/app/version": version(), [ROUTE]: { version: "9.2.0", update: null, vorabversionen: true } });

  page.button().click();
  await page.settle();

  assert.match(page.line().textContent, /^Version 9\.2\.0 ist die neueste\. Geprüft um \d{2}:\d{2}\. Vorabversionen eingeschlossen\.$/);
});

test("while checking the button says so with aria-disabled, ignores clicks and keeps the focus", async () => {
  const answer = later();
  const page = await settingsPage({ "/api/app/version": version(), [ROUTE]: () => answer.promise });
  const knopf = page.button();
  knopf.focus();

  knopf.click();
  await page.settle();
  knopf.click();
  await page.settle();

  assert.equal(page.line().textContent, "Sucht nach Updates …");
  assert.equal(knopf.getAttribute("aria-disabled"), "true");
  assert.equal(knopf.disabled, false);
  assert.equal(page.document.activeElement, knopf);
  assert.deepEqual(page.sent, [ROUTE]);
  answer.release({ version: "9.2.0", update: null, vorabversionen: false });
  await page.settle();
  assert.equal(knopf.hasAttribute("aria-disabled"), false);
  assert.equal(page.document.activeElement, knopf);
});

test("a newer version is offered as the automatic check offers it, without a dialog", async () => {
  const page = await settingsPage({ "/api/app/version": version(), [ROUTE]: { version: "9.2.0", update: newer(), vorabversionen: false },
                                    "/api/app/aktualisieren": { ok: true, version: "9.3.0" } });

  page.button().click();
  await page.settle();

  const zeile = page.line();
  assert.equal(zeile.textContent, "Version 9.3.0 ist verfügbar. Sie wird beim Beenden installiert, oder gleich hier. Jetzt aktualisieren");
  assert.ok(!all(page.document.body).some(node => node.tag === "dialog"));
  all(zeile).find(node => node.tag === "button").click();
  await page.settle();
  assert.deepEqual(page.sent, [ROUTE, "/api/app/aktualisieren"]);
  assert.match(zeile.textContent, /^Die neue Version wird installiert/);
});

test("without a self-update the newer version comes as the download link (Linux)", async () => {
  const offer = newer({ automatisch: false, beimBeenden: false, seite: "https://updates.example.ch/app/9.3.0/x.AppImage" });
  const page = await settingsPage({ "/api/app/version": version(), [ROUTE]: { version: "9.2.0", update: offer, vorabversionen: false } });

  page.button().click();
  await page.settle();

  const link = all(page.line()).find(node => node.tag === "a");
  assert.equal(link.textContent, "Neue Version herunterladen");
  assert.equal(link.href, offer.seite);
});

test("a failed check says so as a warning line, and the button works again with the focus on it", async () => {
  const page = await settingsPage({ "/api/app/version": version(), [ROUTE]: { status: 502, data: { fehler: "anders" } } });
  const knopf = page.button();
  knopf.focus();

  knopf.click();
  await page.settle();

  const zeile = page.line();
  assert.equal(zeile.textContent, FAILED);
  assert.equal(zeile.className, "status-line");
  assert.equal(zeile.getAttribute("data-level"), "warning");
  assert.equal(knopf.hasAttribute("aria-disabled"), false);
  assert.equal(page.document.activeElement, knopf);
});

test("a check without an answer after ten seconds failed, and a late answer changes nothing", async () => {
  const answer = later();
  const page = await settingsPage({ "/api/app/version": version(), [ROUTE]: () => answer.promise });
  const knopf = page.button();

  knopf.click();
  await page.settle();
  assert.equal(page.line().textContent, "Sucht nach Updates …");
  await page.settle(TIMEOUT_MS);

  assert.equal(page.line().textContent, FAILED);
  assert.equal(knopf.hasAttribute("aria-disabled"), false);
  answer.release({ version: "9.2.0", update: null, vorabversionen: false });
  await page.settle(TIMEOUT_MS);
  assert.equal(page.line().textContent, FAILED);
});

test("after a failure the next check and its result are plain again", async () => {
  const second = later();
  let fails = true;
  const page = await settingsPage({ "/api/app/version": version(),
    [ROUTE]: () => (fails ? Promise.resolve({ status: 502, data: {} }) : second.promise) });

  page.button().click();
  await page.settle();
  assert.equal(page.line().getAttribute("data-level"), "warning");
  fails = false;
  page.button().click();
  await page.settle();

  assert.equal(page.line().textContent, "Sucht nach Updates …");
  assert.equal(page.line().getAttribute("data-level"), null);
  second.release({ version: "9.2.0", update: null, vorabversionen: false });
  await page.settle();
  assert.equal(page.line().getAttribute("data-level"), null);
  assert.equal(page.line().className, "status-line");
  assert.match(page.line().textContent, /ist die neueste/);
});

test("a repeated check empties the line first, so the same result is announced again", async () => {
  const page = await settingsPage({ "/api/app/version": version(), [ROUTE]: { version: "9.2.0", update: null, vorabversionen: false } });
  page.button().click();
  await page.settle();
  const first = page.line().textContent;

  page.button().click();
  assert.equal(page.line().textContent, "");
  await page.settle();

  assert.equal(page.line().textContent, first);
});

test("only one install runs even when the start banner offers the same update", async () => {
  const install = later();
  const page = await settingsPage({ "/api/app/version": version({ update: newer({ fragen: false }) }),
                                    [ROUTE]: { version: "9.2.0", update: newer(), vorabversionen: false },
                                    "/api/app/aktualisieren": () => install.promise });
  const banner = all(page.main).find(node => node.classes.has("banner"));
  assert.ok(banner, "banner missing");

  page.button().click();
  await page.settle();
  const fromBanner = all(banner).find(node => node.tag === "button");
  const fromLine = all(page.line()).find(node => node.tag === "button");
  fromBanner.click();
  fromLine.click();
  await page.settle();

  assert.deepEqual(page.sent.filter(route => route === "/api/app/aktualisieren"), ["/api/app/aktualisieren"]);
  assert.equal(fromLine.disabled, true);
  install.release({ ok: true, version: "9.3.0" });
  await page.settle();
  assert.equal(fromLine.parentNode, null);
  assert.equal(fromBanner.parentNode, null);
});

test("a button offered while an install runs starts disabled like the others", async () => {
  const install = later();
  const page = await settingsPage({ "/api/app/version": version({ update: newer({ fragen: false }) }),
                                    [ROUTE]: { version: "9.2.0", update: newer(), vorabversionen: false },
                                    "/api/app/aktualisieren": () => install.promise });
  const banner = all(page.main).find(node => node.classes.has("banner"));

  all(banner).find(node => node.tag === "button").click();
  await page.settle();
  page.button().click();
  await page.settle();

  const fromLine = all(page.line()).find(node => node.tag === "button");
  assert.equal(fromLine.textContent, "Jetzt aktualisieren");
  assert.equal(fromLine.disabled, true);
});

test("in the Store package there is no button and the note stays", async () => {
  const page = await settingsPage({ "/api/app/version": version({ store: true }) });

  assert.equal(page.button(), undefined);
  assert.equal(page.line(), null);
  assert.ok(all(page.card).some(node => node.tag === "p" && node.textContent === STORE_NOTE));
});
