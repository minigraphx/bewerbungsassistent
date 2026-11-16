// Once the credit of the invitation code is used up (G80), „anfordern“ links to where a new code is requested: the
// contact on the help page of the website (#315), in the sidebar, Einstellungen, the window and page „KI“ and on
// „Alle prüfen“. Only invented amounts.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const texte = require("../seiten/texte.js");
const sidebarLogic = require("../seiten/sidebar-logic.js");
const trefferLogik = require("../seiten/treffer-logik.js");

const PAGES = path.join(__dirname, "..", "seiten");
const read = name => fs.readFileSync(path.join(PAGES, name), "utf8");
const CONTACT = "https://bewerbungsbegleiter.ch/hilfe.html#kontakt";
const USED_UP = { eingerichtet: true, vermittlung: true, waehrung: "CHF", guthaben_chf: 5, verbraucht_chf: 5 };
const settle = async () => { for (let i = 0; i < 8; i += 1) await new Promise(resolve => setImmediate(resolve)); };

/** A stand-in for App.el: a plain node with its attributes and children. */
const el = (tag, attrs = {}, ...children) => ({ tag, attrs, children });
const textOf = part => (typeof part === "string" ? part : part.children.map(textOf).join(""));
const linksIn = parts => parts.filter(part => typeof part === "object" && part.tag === "a");

const NEW_TAB = ", öffnet neuen Tab";
/** What a screen reader reads: the sentence with the hidden hint right after the link. */
const readAloud = sentence => sentence.replace(/anfordern(?![\p{L}])/u, `anfordern${NEW_TAB}`);

function assertLinked(sentence) {
  const parts = texte.withCodeRequestLink(sentence, el);
  assert.equal(parts.map(textOf).join(""), readAloud(sentence), "the words stay as they are");
  const links = linksIn(parts);
  assert.equal(links.length, 1, sentence);
  assert.deepEqual(links[0].children, ["anfordern", el("span", { class: "visually-hidden" }, NEW_TAB)],
    "the hint of the new tab is hidden from sight");
  assert.deepEqual(links[0].attrs, { href: CONTACT, target: "_blank", rel: "noopener" });
}

test("the contact of the help page is the one place a new code is requested", () => {
  assert.equal(texte.CODE_REQUEST_URL, CONTACT);
  const pages = fs.readdirSync(PAGES).filter(name => /\.(js|html)$/.test(name));
  const naming = pages.filter(name => read(name).includes("hilfe.html#kontakt"));
  assert.deepEqual(naming, ["texte.js"], "the address stands in one constant only");
});

test("every used-up sentence links „anfordern“, the rest stays text", () => {
  assertLinked(sidebarLogic.budgetView(USED_UP).warning);
  const estimate = { anzahl: 3, kosten: 0.12, dauer_minuten: 2, laden: [], nicht_ladbar: [], guthaben: 0, danach: 0,
                     reicht_fuer: 0, waehrung: "CHF" };
  assertLinked(trefferLogik.estimateLine(estimate));
  assertLinked("Das Guthaben des Einladungscodes ist aufgebraucht. Bitte einen neuen Code anfordern und unter "
    + "Einstellungen, KI und Guthaben einlösen. 2 von 5 Treffern bewertet.");
  assertLinked(/<p id="einladung-aufgebraucht" hidden>([^<]*)<\/p>/.exec(read("einstellungen.html"))[1]);
});

test("the link works in the Sie and in the du form", () => {
  assertLinked("Mit einem neuen Code geht es weiter: Sie können ihn anfordern.");
  assertLinked("Mit einem neuen Code geht es weiter: Du kannst ihn anfordern.");
});

test("only the whole word becomes a link, and a sentence without it stays one part", () => {
  for (const sentence of ["3 von 5 Anforderungen belegt.", "Der Code ist angefordert.", "Guthaben fast aufgebraucht", "anfordernd"]) {
    assert.deepEqual(texte.withCodeRequestLink(sentence, el), [sentence], sentence);
  }
  assert.deepEqual(texte.withCodeRequestLink("", el), []);
});

// ---------- The sidebar, run as written ----------

function fakeElement(tag = "div") {
  const node = {
    tag, hidden: false, textContent: "", dataset: {}, style: {}, attrs: {}, children: [],
    setAttribute(name, value) { node.attrs[name] = value; },
    getAttribute: name => node.attrs[name] ?? null,
    toggleAttribute() {}, contains: () => false, focus() {}, addEventListener() {},
    replaceChildren(...parts) { node.children = parts; node.textContent = parts.map(textOf).join(""); },
    querySelector: () => fakeElement(),
  };
  return node;
}

test("the sidebar warning links „anfordern“ once the credit is used up", async () => {
  const elements = new Map();
  const document = {
    hidden: false, documentElement: { dataset: {} },
    getElementById(id) { if (!elements.has(id)) elements.set(id, fakeElement()); return elements.get(id); },
    querySelector: selector => (selector === ".app-nav" ? fakeElement("nav") : null),
    addEventListener() {},
  };
  const holen = async pfad => {
    if (pfad === "/api/ki/status") return USED_UP;
    throw new Error(`not in this test: ${pfad}`);
  };
  const window = { App: { holen, el }, SidebarLogic: sidebarLogic, Texte: texte, addEventListener() {} };
  window.window = window;
  vm.runInNewContext(read("sidebar.js"), {
    window, document, location: { pathname: "/treffer", origin: "http://127.0.0.1:1" },
    sessionStorage: { getItem: () => null, setItem() {} }, setTimeout: () => 0, Promise, JSON, Date, Math, Number,
  });
  await settle();

  const warning = document.getElementById("nav-budget-warning");
  assert.equal(warning.hidden, false);
  assert.equal(warning.textContent, `Guthaben aufgebraucht: neuen Code anfordern${NEW_TAB}`);
  const links = linksIn(warning.children);
  assert.equal(links.length, 1);
  assert.equal(links[0].attrs.href, CONTACT);
});

test("the link in the sidebar warning keeps the colour of the warning", () => {
  assert.match(read("stil.css"), /\n\.app-nav__budget-warning a \{ color: inherit; \}\n/);
});

// ---------- Pages that show a used-up sentence put it through the same helper ----------

test("Einstellungen, the page „KI“ and „Alle prüfen“ draw their used-up words with the link", () => {
  assert.match(read("einstellungen.js"),
    /const usedUp = \$\("einladung-aufgebraucht"\);\s+usedUp\.replaceChildren\(\.\.\.window\.Texte\.withCodeRequestLink\(usedUp\.textContent, el\)\);/);
  assert.match(read("ki.js"), /\$\("ki-status"\)\.replaceChildren\(\.\.\.window\.Texte\.withCodeRequestLink\(statusText\(s\), el\)/);
  const hits = read("treffer.js");
  assert.match(hits, /\$\("kosten-hinweis"\)\.replaceChildren\(\.\.\.window\.Texte\.withCodeRequestLink\(logik\.estimateLine\(estimate, lehrstelle\), el\)\)/);
  assert.match(hits, /if \(stand\.fehler\) meldung\(window\.Texte\.withCodeRequestLink\(`\$\{stand\.fehler\} \$\{summary\}`, el\), "fehler"\)/);
  assert.doesNotMatch(hits, /\$\("kosten-hinweis"\)\.textContent = logik\.estimateLine/);
});
