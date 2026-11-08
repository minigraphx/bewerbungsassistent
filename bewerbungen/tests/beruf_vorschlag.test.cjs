// Suggestions on the page Suche (MIN-375) ask for the AI consent in place (#140): nothing typed leaves before it.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const seite = name => fs.readFileSync(path.join(__dirname, "..", "seiten", name), "utf8");
const OPEN = { erteilt: false, fassung: "1", text: "Ich bin einverstanden …", link: null };

function element() {
  const handlers = {};
  return {
    value: "", hidden: false, disabled: false, textContent: "", open: false, children: [],
    addEventListener(type, handler) { handlers[type] = handler; },
    replaceChildren(...children) { this.children = children; },
    focus() {},
    fire(type) { return handlers[type](); },
  };
}

/** The page script in a sandbox: elements by id, a fake App that records what it sends, and a fake consent block. */
function page({ status = { einwilligung: OPEN } } = {}) {
  const elements = new Map();
  const byId = id => {
    if (!elements.has(id)) elements.set(id, element());
    return elements.get(id);
  };
  const sent = [];
  const consent = [];
  const App = {
    el: () => element(),
    status: (target, text) => { target.textContent = text; },
    textsatz: async () => "lehrstelle-du",
    holen: async pfad => {
      assert.equal(pfad, "/api/ki/status");
      return status;
    },
    senden: async (pfad, body) => {
      sent.push({ pfad, body });
      return { vorschlaege: [] };
    },
  };
  const Einwilligung = { zeige: (ort, stand, fertig) => { ort.hidden = false; consent.push({ ort, stand, fertig }); } };
  const context = {
    window: { App, Einwilligung },
    document: { getElementById: byId, dispatchEvent() {} },
    CustomEvent: class {},
  };
  vm.runInNewContext(seite("beruf-vorschlag.js"), context);
  return { byId, sent, consent, suchbegriffe: context.window.Suchbegriffe };
}

async function typeAndAsk(p) {
  await p.suchbegriffe.zeige("lehrstelle", [], []);
  p.byId("vorschlag-interessen").value = "Tiere, draussen sein";
  p.byId("vorschlag-staerken").value = "geduldig, genau";
  p.byId("vorschlag-vermeiden").value = "Büro";
  await p.byId("vorschlag-holen").fire("click");
}

test("without consent, Vorschlagen shows the consent in the suggestion box and sends nothing typed", async () => {
  const p = page();
  await typeAndAsk(p);

  assert.deepEqual(p.sent, [], "nothing typed goes out before the consent");
  assert.equal(p.consent.length, 1);
  assert.equal(p.consent[0].ort, p.byId("vorschlag-einwilligung"));
  assert.equal(p.consent[0].stand, OPEN);
  assert.doesNotMatch(p.byId("vorschlag-status").textContent, /Erweiterte Einstellungen/);
  assert.equal(p.byId("vorschlag-holen").disabled, false);
});

test("after the consent is given there, the typed answers stay and the suggestion runs", async () => {
  const p = page();
  await typeAndAsk(p);
  await p.consent[0].fertig({ einwilligung: { ...OPEN, erteilt: true } });

  assert.equal(p.byId("vorschlag-einwilligung").hidden, true);
  assert.equal(p.byId("vorschlag-interessen").value, "Tiere, draussen sein");
  assert.equal(p.byId("vorschlag-staerken").value, "geduldig, genau");
  assert.equal(p.byId("vorschlag-vermeiden").value, "Büro");
  // the body comes from the sandbox's realm, so compare it as JSON
  assert.deepEqual(JSON.parse(JSON.stringify(p.sent)), [{ pfad: "/api/beruf/vorschlag",
    body: { interessen: "Tiere, draussen sein", staerken: "geduldig, genau", vermeiden: "Büro" } }]);
});

test("with consent given, Vorschlagen asks the AI right away", async () => {
  const p = page({ status: { einwilligung: { ...OPEN, erteilt: true } } });
  await typeAndAsk(p);

  assert.equal(p.consent.length, 0);
  assert.equal(p.sent.length, 1);
  assert.equal(p.sent[0].pfad, "/api/beruf/vorschlag");
});

test("the page Suche has a place for the consent inside the suggestion box and loads its script", () => {
  const html = seite("treffer.html");
  const box = html.slice(html.indexOf('<details id="vorschlag"'), html.indexOf("</details>", html.indexOf('<details id="vorschlag"')));
  assert.match(box, /id="vorschlag-einwilligung"/);
  assert.ok(html.indexOf('src="/einwilligung.js"') > 0, "einwilligung.js is loaded");
  assert.ok(html.indexOf('src="/einwilligung.js"') < html.indexOf('src="/beruf-vorschlag.js"'));
});
