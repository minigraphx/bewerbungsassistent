// The page Suche with a stand-in extension (#142): it never stays on „Suche startet …“ while no search runs.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const logik = require("../seiten/treffer-logik.js");

const CODE = fs.readFileSync(path.join(__dirname, "..", "seiten", "treffer.js"), "utf8");
const ORIGIN = "http://127.0.0.1:1";

/** An element that takes whatever the page does with it; only what the tests read is kept. */
function element() {
  const handlers = {};
  const store = { hidden: false, disabled: false, textContent: "", dataset: {}, attributes: {}, value: "" };
  const target = function () {};
  return new Proxy(target, {
    get(_, name) {
      if (name in store) return store[name];
      if (name === "addEventListener") return (type, handler) => { handlers[type] = handler; };
      if (name === "fire") return type => handlers[type]({ target: { checked: false } });
      if (name === "setAttribute") return (key, value) => { store.attributes[key] = value; };
      if (name === "then" || typeof name === "symbol") return undefined;
      return () => element();
    },
    set(_, name, value) { store[name] = value; return true; },
  });
}

function page() {
  const elements = new Map();
  const $ = id => { if (!elements.has(id)) elements.set(id, element()); return elements.get(id); };
  const posted = [];
  const timers = [];
  let listener = null;
  let loads = 0;
  const window = {
    App: {
      holen: async pfad => { if (pfad === "/api/suche/liste") loads += 1; throw new Error("nicht in diesem Test"); },
      senden: async () => ({}), el: () => element(), status() {}, datum: String, beobachten() {}, textsatz: async () => "stelle-sie",
    },
    TrefferLogik: logik,
    Meldungen: { zeige() {}, leere() {} },  // messages have their own tests (meldungen.test.cjs)
    Texte: { text: key => key, anwenden() {} },
    PortalWahl: { zeige() {} },
    Suchbegriffe: { zeige() {} },
    addEventListener: (type, handler) => { if (type === "message") listener = handler; },
    postMessage: message => posted.push(message),
  };
  const context = {
    window,
    document: {
      getElementById: $, querySelectorAll: () => [], addEventListener() {},
      documentElement: { dataset: { bewerbungsbegleiterErweiterung: "1" } },
    },
    localStorage: { getItem: () => null, setItem() {} },
    location: { origin: ORIGIN },
    setTimeout: (f, ms) => { timers.push({ f, ms }); return timers.length; },
    clearTimeout: id => { if (timers[id - 1]) timers[id - 1].f = null; },
    console,
  };
  vm.runInNewContext(CODE, context);
  const fromExtension = data => listener({ source: window, origin: ORIGIN, data: { quelle: "bewerbungsbegleiter-erweiterung", ...data } });
  const quiet = () => timers.filter(t => t.f && t.ms === logik.STILLE_MS);
  return { $, posted, quiet, fromExtension, loads: () => loads };
}

const settle = () => new Promise(resolve => setImmediate(resolve));

test("a start the extension does not take ends the wait with the message, Jetzt suchen and a fresh list", async () => {
  const p = page();
  await settle();
  const before = p.loads();
  p.$("suchen").fire("click");
  assert.equal(p.$("suchen").disabled, true);

  p.fromExtension({ art: "antwort", frage: "suche-starten", antwort: { fehler: "Die Erweiterung antwortet nicht. Bitte die Seite neu laden." } });

  assert.equal(p.$("suchen").disabled, false);
  assert.equal(p.$("suchen").textContent, "Jetzt suchen");
  assert.equal(p.$("lauf-box").hidden, true);
  assert.ok(p.loads() > before, "the list and its hints are loaded again");
});

test("without progress for a while the page asks for the status and follows the run that ended", async () => {
  const p = page();
  await settle();
  p.$("suchen").fire("click");
  p.fromExtension({ art: "lauf", lauf: { zustand: "laeuft", beginn: new Date().toISOString(), schritt: { phase: "start" } } });
  const waiting = p.quiet();
  assert.equal(waiting.length, 1, "a timer waits for the next word");

  waiting[0].f();
  assert.deepEqual({ ...p.posted.at(-1) }, { quelle: "bewerbungsbegleiter-seite", art: "status" }); // from the sandbox's realm
  const before = p.loads();
  p.fromExtension({ art: "antwort", frage: "status",
    antwort: { verbunden: true, lauf: { zustand: "fertig", beginn: new Date().toISOString(), ergebnis: { abgebrochen: true } } } });

  assert.equal(p.$("suchen").disabled, false);
  assert.equal(p.$("lauf-box").hidden, true);
  assert.ok(p.loads() > before);
  assert.equal(p.quiet().length, 0, "no more asking once the run is over");
});

test("a status without a run of this page ends the wait too", async () => {
  const p = page();
  await settle();
  p.$("suchen").fire("click");
  p.quiet()[0].f();

  p.fromExtension({ art: "antwort", frage: "status", antwort: { verbunden: true, lauf: null } });

  assert.equal(p.$("suchen").disabled, false);
  assert.equal(p.$("lauf-box").hidden, true);
});

test("a status while nobody waits changes nothing", async () => {
  const p = page();
  await settle();
  const before = p.loads();
  p.fromExtension({ art: "antwort", frage: "status", antwort: { verbunden: false, fehler: "Die App läuft nicht." } });
  assert.equal(p.loads(), before);
});
