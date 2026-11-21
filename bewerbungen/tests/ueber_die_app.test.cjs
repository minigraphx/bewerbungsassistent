// Über die App in the Store package (#344, G6): its last line says that the Store brings the updates (#370);
// the installer build shows the card as before.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const SEITEN = path.join(__dirname, "..", "seiten");
const STORE_NOTE = "Updates kommen über den Microsoft Store.";

const textOf = node => (node && typeof node === "object" ? node.children.map(textOf).join("") : String(node ?? ""));
const paragraphs = node => (node && typeof node === "object"
  ? [...(node.tag === "p" ? [node] : []), ...node.children.flatMap(paragraphs)] : []);
const settle = async () => { for (let i = 0; i < 8; i += 1) await new Promise(resolve => setImmediate(resolve)); };

/** A stand-in element that keeps its tag, class, attributes and children. */
function element(tag) {
  const node = {
    tag, attrs: {}, children: [], hidden: false, className: "",
    get textContent() { return textOf(node); },
    set textContent(value) { node.children = [String(value)]; },
    setAttribute(name, value) { node.attrs[name] = value; },
    removeAttribute(name) { delete node.attrs[name]; },
    addEventListener() {},
    append(...items) { node.children.push(...items); },
    replaceChildren(...items) { node.children = items; },
    prepend(...items) { node.children.unshift(...items); },
  };
  return node;
}

/** app.js in a sandbox on the settings page; `version` is what /api/app/version answers. */
async function aboutWith(version) {
  const card = element("section");
  card.hidden = true;
  const answers = { "/api/app/version": version, "/api/app/einrichtung": { eingerichtet: true } };
  const fetch = async url => {
    const found = answers[String(url).split("?")[0]];
    return { ok: Boolean(found), status: found ? 200 : 404, statusText: "", headers: { get: () => "application/json" },
             json: async () => found || { fehler: "Nicht gefunden" } };
  };
  const document = {
    querySelector: selector => (selector.startsWith("meta") ? { content: "token" } : null),
    getElementById: id => (id === "ueber-die-app" ? card : null),
    addEventListener() {}, hidden: false, documentElement: { dataset: {} },
    head: element("head"), body: element("body"), createElement: tag => element(tag), createTextNode: text => text,
  };
  const Node = { [Symbol.hasInstance]: value => typeof value === "object" && value !== null };
  const location = { pathname: "/einstellungen", search: "", hash: "", origin: "http://127.0.0.1:1", replace() {}, reload() {} };
  const window = { addEventListener() {} };
  vm.runInNewContext(fs.readFileSync(path.join(SEITEN, "app.js"), "utf8"), {
    window, document, location, history: { state: null, length: 1, replaceState() {} }, fetch, URLSearchParams, Node,
    setInterval() {}, setTimeout, Promise, crypto: { randomUUID: () => "x" },
  });
  await settle();
  return card;
}

test("in the Store package the note stands on its own line last, where the update check stands elsewhere", async () => {
  const card = await aboutWith({ version: "9.2.0", update: null, store: true });

  assert.equal(card.hidden, false);
  const lines = paragraphs(card).map(textOf);
  assert.deepEqual(lines, ["Bewerbungsbegleiter", "Version 9.2.0", "von Andreas Schmidt", STORE_NOTE]);
  const note = paragraphs(card)[3];
  assert.equal(note.className, "about__meta");
});

test("outside the Store package the card shows no note", async () => {
  const card = await aboutWith({ version: "9.2.0", update: null });

  const lines = paragraphs(card).map(textOf);
  assert.ok(lines.includes("Version 9.2.0"));
  assert.ok(!lines.includes(STORE_NOTE));
});
