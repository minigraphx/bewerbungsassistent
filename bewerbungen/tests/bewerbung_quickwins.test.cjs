// Application page and overview show only what is due (#222, UX findings 3, 5, 11, 12 and 15): „Erneut prüfen“ after
// a first check, the AI consent as one line with a dialog outside the setup, the dispatch without folder words, the
// PDF link to the upload in Meine Angaben, the bulk bar only with a selection and Einrichtung next to the settings.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const bewerbungLogik = require("../seiten/bewerbung-logik.js");
const uebersichtLogik = require("../seiten/uebersicht-logik.js");
const texte = require("../seiten/texte.js");

const SEITEN = path.join(__dirname, "..", "seiten");
const ONBOARDING = path.join(__dirname, "..", "..", "onboarding", "src");
const lies = name => fs.readFileSync(path.join(SEITEN, name), "utf8");
const CONSENT_TEXT = "Ich willige ein, dass Texte pseudonymisiert an die KI gehen.";
const STAND = { erteilt: false, fassung: "2026-11 stelle", text: CONSENT_TEXT, link: "https://example.ch/datenschutz" };

/** A stand-in element that keeps what the page sets, its children and its listeners. */
function element(tag, attrs = {}, children = []) {
  const handlers = {};
  const node = {
    tag, attrs, children: children.flat().filter(c => c !== null && c !== undefined && c !== false),
    hidden: false, disabled: false, checked: false, open: false, id: attrs.id || "",
    addEventListener(type, handler) { handlers[type] = handler; },
    fire(type) { return handlers[type] && handlers[type]({ target: node }); },
    replaceChildren(...items) { node.children = items; },
    showModal() { node.open = true; },
    close() { node.open = false; },
  };
  return node;
}

const textOf = node => (node && typeof node === "object" ? node.children.map(textOf).join("") : String(node ?? ""));
const findAll = (node, match) => (node && typeof node === "object"
  ? [...(match(node) ? [node] : []), ...node.children.flatMap(child => findAll(child, match))] : []);
const button = (node, text) => findAll(node, n => n.tag === "button" && textOf(n) === text)[0];

/** einwilligung.js in a sandbox; `senden` answers the consent route. */
function consent(senden = async () => ({ einwilligung: { ...STAND, erteilt: true } })) {
  const window = {
    App: { senden, el: (tag, attrs, ...kids) => element(tag, attrs || {}, kids), fragenLink: (anker, text) => element("a", { href: `/fragen#${anker}` }, [text]), textsatz: async () => "stelle-sie" },
    Texte: texte,
    Meldungen: { zeige() {} },
  };
  vm.runInNewContext(lies("einwilligung.js"), { window, document: { documentElement: { dataset: { textsatz: "stelle-sie" } } } });
  return window.Einwilligung;
}

const settle = async () => { for (let i = 0; i < 5; i += 1) await new Promise(resolve => setImmediate(resolve)); };

test("Erneut prüfen is hidden until a first check, and the page asks the rule each time it draws", () => {
  assert.equal(bewerbungLogik.erneutPruefen(null), false);
  assert.equal(bewerbungLogik.erneutPruefen([]), true);
  assert.equal(bewerbungLogik.erneutPruefen([{ stufe: "fehler", text: "x" }]), true);
  assert.match(lies("bewerbung.html"), /<button type="button" class="btn btn--quiet" id="pruefen" hidden>Erneut prüfen<\/button>/);
  assert.match(lies("bewerbung.js"), /\$\("pruefen"\)\.hidden = !L\.erneutPruefen\(befunde\);/);
});

test("outside the setup the consent is one line: Die KI ist noch aus. KI einschalten", () => {
  const ort = element("div", { id: "ki-einwilligung" });
  ort.hidden = true;
  consent().zeile(ort, STAND, () => {});
  const zeile = ort.children[0];
  assert.equal(ort.hidden, false);
  assert.equal(textOf(zeile), "Die KI ist noch aus. KI einschalten");
  const dialog = findAll(ort, n => n.tag === "dialog")[0];
  assert.ok(dialog, "the text waits in a dialog");
  assert.equal(dialog.open, false);
  assert.equal(findAll(zeile, n => n.tag === "input").length, 0, "no tick in the line itself");
});

test("KI einschalten shows the unchanged consent text in a dialog, and agreeing closes it", async () => {
  const sent = [];
  const done = [];
  const ort = element("div", { id: "ki-einwilligung" });
  consent(async (pfad, daten) => { sent.push({ pfad, daten }); return { einwilligung: { ...STAND, erteilt: true } }; })
    .zeile(ort, STAND, neu => done.push(neu));
  const dialog = findAll(ort, n => n.tag === "dialog")[0];
  button(ort, "KI einschalten").fire("click");
  assert.equal(dialog.open, true);
  assert.ok(textOf(dialog).includes(CONSENT_TEXT), "the text of G14, word for word");
  assert.ok(textOf(dialog).includes("Datenschutzerklärung lesen"));
  assert.ok(textOf(dialog).includes(texte.text("einwilligung.ersetzt", "stelle-sie")));

  const tick = findAll(dialog, n => n.tag === "input" && n.attrs.type === "checkbox")[0];
  const agree = button(dialog, "Einwilligen");
  assert.equal(agree.disabled, true);
  tick.checked = true;
  tick.fire("change");
  agree.fire("click");
  await settle();
  assert.deepEqual(JSON.parse(JSON.stringify(sent)),  // made in the sandbox, so compared as plain data
    [{ pfad: "/api/ki/einwilligung", daten: { fassung: STAND.fassung, zustimmung: true } }]);
  assert.equal(dialog.open, false);
  assert.equal(done.length, 1);
});

test("Abbrechen closes the dialog without agreeing", () => {
  const sent = [];
  const ort = element("div", { id: "einwilligung-offen" });
  consent(async pfad => { sent.push(pfad); return {}; }).zeile(ort, STAND, () => {});
  const dialog = findAll(ort, n => n.tag === "dialog")[0];
  button(ort, "KI einschalten").fire("click");
  button(dialog, "Abbrechen").fire("click");
  assert.equal(dialog.open, false);
  assert.deepEqual(sent, []);
});

test("application, search and settings use the line; only the window KI einrichten keeps the full block", () => {
  for (const [name, ort] of [["ki.js", "ki-einwilligung"], ["beruf-vorschlag.js", "vorschlag-einwilligung"], ["einstellungen.js", "einwilligung-offen"]]) {
    const code = lies(name);
    assert.match(code, new RegExp(`Einwilligung\\.zeile\\(\\$\\("${ort}"\\)`), name);
    assert.doesNotMatch(code, /Einwilligung\.zeige\(/, name);
  }
  assert.match(lies("ki-fenster.js"), /Einwilligung\.zeige\(parts\.consent,/);
});

test("Versand erfassen names neither the folder versendet/ nor eingefroren and says the sent version stays", () => {
  const html = lies("bewerbung.html");
  const form = html.slice(html.indexOf('<div id="versand-form">'), html.indexOf('id="versenden"'));
  assert.ok(form.includes("Die verschickte Fassung bleibt gespeichert."));
  assert.doesNotMatch(form, /versendet\/|eingefroren/);
  const code = lies("bewerbung.js");
  const nachVersand = code.slice(code.indexOf('bestaetigen($("versenden")'), code.indexOf('bestaetigen($("versenden")') + 700);
  assert.doesNotMatch(nachVersand, /eingefroren/);
  assert.match(code, /Die verschickte Fassung bleibt gespeichert\./);
});

test("on the first start the CV upload leads to the upload in Meine Angaben (#260, A2)", () => {
  const html = lies("uebersicht.html");
  assert.match(html, /<a class="btn btn--primary" href="\/angaben#feld=unterlagen">Lebenslauf hochladen und vorbefüllen<\/a>/);
  assert.doesNotMatch(html, /href="\/dateien">[^<]*Lebenslauf/);
  const app = fs.readFileSync(path.join(ONBOARDING, "app.js"), "utf8");
  assert.match(app, /const UPLOAD_TARGET = "unterlagen";/);
  assert.match(app, /if \(wanted === UPLOAD_TARGET\) return openUploads\(\);/);
  const angaben = lies("angaben.html");
  assert.ok(angaben.includes("function openUploads()"), "angaben.html is built from the changed source");
});

test("the other stages appear only once a row is ticked, after the count and Angehakte verwerfen (#170, #261)", () => {
  assert.equal(uebersichtLogik.showBulkBar(0), false);
  assert.equal(uebersichtLogik.showBulkBar(1), true);
  const html = lies("bewerbungen.html");
  const bar = html.slice(html.indexOf('id="auswahl-leiste"'), html.indexOf("</span>\n", html.indexOf('id="auswahl-leiste"')));
  assert.match(bar, /^id="auswahl-leiste"[^>]*hidden>/);
  assert.ok(html.indexOf('id="auswahl-zahl"') < html.indexOf('id="stand-setzen"'), "count first, then Stand setzen");
  assert.doesNotMatch(html, /Keine ausgewählt/);
  assert.match(html, /<th class="table__pick"><input type="checkbox" id="alle-kopf" aria-label="Alle in dieser Ansicht auswählen"><\/th>/);
  const code = lies("bewerbungen.js");
  assert.match(code, /\$\("auswahl-leiste"\)\.hidden = !L\.showBulkBar\(ids\.length\);/);
  assert.doesNotMatch(code, /\$\("auswahl-leiste"\)\.hidden = gezeigte\.length === 0/);
});

test("Einrichtung is reached from the settings, never from Hilfe in the sidebar (G54)", () => {
  const pages = fs.readdirSync(SEITEN).filter(name => name.endsWith(".html"));
  assert.ok(pages.length >= 12);
  for (const name of pages) {
    const nav = lies(name).match(/<nav class="app-nav"[\s\S]*?<\/nav>/)[0];
    assert.doesNotMatch(nav, /href="\/einrichtung"/, name);
  }
  assert.match(lies("einstellungen.html"), /<a href="\/einrichtung">Einrichtung: Datenordner, Erweiterung und KI<\/a>/);
});
