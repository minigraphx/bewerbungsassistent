// Stellen suchen quick wins (#220, UX findings 8 and 9, quick win 13): clearer words, closed settings with a summary,
// the reason under a disabled „Jetzt suchen“, the right empty texts and one name for tab and page.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const anzeige = require("../seiten/suche-anzeige.js");
const logik = require("../seiten/treffer-logik.js");
const texte = require("../seiten/texte.js");
const DotLine = require("../seiten/dot-line.js");
const { shown, heard, wholeParts, seenLine } = require("./dot_line_text.cjs");

const SEITEN = path.join(__dirname, "..", "seiten");
const ROOT = path.join(__dirname, "..");
const HTML = fs.readFileSync(path.join(SEITEN, "treffer.html"), "utf8");
const CODE = fs.readFileSync(path.join(SEITEN, "treffer.js"), "utf8");
const ORIGIN = "http://127.0.0.1:1";
const HIT = { id: "h1", stelle: "Data Engineer", firma: "Muster AG", portal: "jobs.ch", link: "https://www.jobs.ch/x", zustand: "neu", gefunden_am: "2026-11-01" };

/** A stand-in element that keeps what the page sets, and the children it gets as plain values. */
function element(tag = "div", attrs = {}, children = []) {
  const handlers = {};
  return {
    tag, attrs, children, hidden: false, disabled: false, textContent: "", value: "", dataset: {}, attributes: {},
    addEventListener(type, handler) { handlers[type] = handler; },
    fire(type) { return handlers[type]({ target: { checked: false } }); },
    setAttribute(key, value) { this.attributes[key] = value; },
    replaceChildren(...items) { this.children = items; },
    scrollIntoView() {}, focus() {},
    classList: { toggle() {}, add() {}, remove() {} },
  };
}

/** Text of an element made with App.el, children included. */
const textOf = node => (node && typeof node === "object" ? (node.children || []).flat().map(textOf).join("") : String(node ?? ""));

function page({ liste = {}, uebernehmen = {}, erweiterung = true, hash = "" } = {}) {
  const elements = new Map();
  const $ = id => { if (!elements.has(id)) elements.set(id, element()); return elements.get(id); };
  for (const id of ["lauf-box", "bewerten-box"]) $(id).hidden = true;  // hidden in treffer.html
  const messages = [];
  const posted = [];
  const replaced = [];
  const timers = [];
  const daten = {
    treffer: [], einstellungen: { auto_bewerten: false, zuschauen: false, beruf_sterne: {}, sortierung: "note" },
    paket: 10, grenze: 30, art: "stelle", portale: ["job-room", "jobs.ch", "jobscout24", "ictjobs"], portale_wahl: [],
    gesuchte_berufe: ["Data Engineer", "Analyst"], gesuchte_schluessel: [], hinweise: [], hinweis_ziele: {},
    letzte_suche: null, region: { kantone: [], orte: ["Bern"], umkreis_km: 25, schweizweit: false }, sperrgrund: "", ...liste,
  };
  const document = {
    title: "", getElementById: $, querySelectorAll: () => [], querySelector: () => element(), addEventListener() {},
    documentElement: { dataset: erweiterung ? { bewerbungsbegleiterErweiterung: "1" } : {} },
  };
  const window = {
    App: {
      holen: async pfad => {
        if (pfad === "/api/suche/liste") return structuredClone(daten);
        if (pfad === "/api/firmen") return { firmen: [], heute: "2026-11-02" };
        if (pfad === "/api/angaben/offen") return { offen: false };
        throw new Error(`unexpected ${pfad}`);
      },
      senden: async pfad => (pfad === "/api/suche/uebernehmen" ? { ...HIT, zustand: "uebernommen", bewerbung_id: "b7", ...uebernehmen } : {}),
      el: (tag, attrs, ...children) => element(tag, attrs || {}, children),
      status() {}, datum: String, beobachten() {}, textsatz: async () => "stelle-sie",
    },
    TrefferLogik: logik,
    SuchlaufLogik: require("../seiten/suchlauf-logik.js"),
    SucheAnzeige: anzeige,
    DotLine,
    Texte: texte,
    Meldungen: { zeige: (el, inhalt, stufe) => messages.push({ el, inhalt, stufe }), leere() {} },
    FirmenLogik: { nachTreffer: () => new Map() },
    TrefferFirma: { zeile: () => null, marke: () => null },
    WiederLogik: require("../seiten/wieder-logik.js"),
    TrefferWieder: { zeile: () => null, vermittler: () => null, marke: () => "", gleicheInserate: () => null },
    PortalWahl: { zeige() {} },
    Suchbegriffe: { zeige() {} },
    SuchbegriffeStart: { zeige() {}, ids: () => null },
    addEventListener() {},
    postMessage(nachricht) { posted.push(nachricht); },
    matchMedia: () => ({ matches: false }),
  };
  const context = {
    window, document, URLSearchParams, console,
    localStorage: { getItem: () => "1", setItem() {} },  // an old „keep open“ must not open the settings any more
    location: { origin: ORIGIN, hash, pathname: "/treffer", search: "" },
    history: { replaceState: (...args) => replaced.push(args) },
    setTimeout: (f, ms) => { timers.push({ f, ms }); return timers.length; },
    clearTimeout() {},
  };
  vm.runInNewContext(CODE, context);
  return { $, messages, document, timers, posted, replaced };
}

const settle = async () => { for (let i = 0; i < 5; i += 1) await new Promise(resolve => setImmediate(resolve)); };

test("the browser tab and the page both say Stellen (G55, #262)", async () => {
  assert.match(HTML, /<title>Stellen<\/title>/);
  assert.match(HTML, /<h1 id="titel" data-text="nav.stellen">Stellen<\/h1>/);
  const p = page();
  await settle();
  assert.equal(p.document.title, "Stellen");
});

test("the settings sum themselves up in one line, and Ändern leads to Suche einstellen (#263)", async () => {
  const p = page({ liste: { treffer: [] } });
  await settle();
  assert.equal(p.$("einstellen-zeile").hidden, false);
  // #342: a «·» line of whole parts, so no line starts with «·»; a screen reader hears commas
  const summary = ["Sucht nach Data Engineer, Analyst", "ganze Schweiz, nahe Bern zuerst", "4 Portale"];
  assert.deepEqual(wholeParts(p.$("einstellen-text")), summary);
  assert.equal(shown(p.$("einstellen-text")), seenLine(summary));
  assert.equal(heard(p.$("einstellen-text")), summary.join(", "));
  assert.match(HTML, /id="einstellen-zeile"[^>]*hidden><span id="einstellen-text"><\/span> <a [^>]*id="einstellen-aendern" href="\/suche-einstellen">Ändern<\/a>/);
  assert.match(HTML, /<a class="btn" id="einstellen-knopf" href="\/suche-einstellen">Suche einstellen<\/a>/);
  assert.match(HTML, /<a class="btn" id="leer-einstellen" href="\/suche-einstellen">Suche einstellen<\/a>/);
});

test("Jetzt suchen on Suche einstellen starts the search once Stellen can (#263)", async () => {
  const p = page({ hash: "#jetzt-suchen" });
  await settle();
  assert.deepEqual(p.posted.map(n => n.art), ["suche-starten"]);
  assert.equal(p.replaced.length, 1);  // the address loses #jetzt-suchen, so reloading does not search again
  const ohne = page({ hash: "#jetzt-suchen", liste: { sperrgrund: "Zuerst Meine Angaben abschliessen." } });
  await settle();
  assert.deepEqual(ohne.posted, []);
  assert.equal(ohne.$("suchen-grund").textContent, "Zuerst Meine Angaben abschliessen.");
  const gewoehnlich = page();
  await settle();
  assert.deepEqual(gewoehnlich.posted, []);
});


/** The first element below `node` with `className` in its class, depth first. */
function find(node, className) {
  if (!node || typeof node !== "object") return null;
  if (String((node.attrs || {}).class || "").split(" ").includes(className)) return node;
  for (const child of (node.children || []).flat()) {
    const found = find(child, className);
    if (found) return found;
  }
  return null;
}

test("the hit row and the detail join their «·» lines as whole parts (#342)", async () => {
  const hit = { ...HIT, ort: "Bern", pensum: "80–100%", alter_tage: 3, eigene_sterne: 2 };
  const p = page({ liste: { treffer: [hit] } });
  await settle();
  const row = p.$("liste").children[0];
  assert.deepEqual(wholeParts(find(row, "hit__where")), ["Muster AG", "Bern", "80–100%"]);
  assert.deepEqual(wholeParts(find(row, "hit__meta")), ["jobs.ch", "2026-11-01", "Eigene: ★★"]);
  assert.equal(heard(find(row, "hit__meta")), "jobs.ch, 2026-11-01, Eigene: ★★");
  row.fire("click");
  const head = find(p.$("detail").children[0], "search__detail-head");
  assert.deepEqual(wholeParts(head.children[1]), ["Muster AG, Bern", "80–100%"]);
  assert.deepEqual(wholeParts(find(head, "search__hint")), ["Inserat auf jobs.ch öffnen", "gefunden 2026-11-01", "3 Tage online"]);
});

test("the summary names cantons, a radius for apprenticeships, a missing term and caps a long list", () => {
  assert.deepEqual(anzeige.zusammenfassung({ begriffe: ["A"], region: { kantone: ["BE", "SO"], orte: ["Bern"] }, portale: 1 }),
    ["Sucht nach A", "Kantone BE und SO", "1 Portal"]);
  assert.deepEqual(anzeige.zusammenfassung({ begriffe: ["Koch EFZ"], region: { orte: ["Thun"], umkreis_km: 25 }, portale: 2, lehrstelle: true }),
    ["Sucht nach Koch EFZ", "25 km um Thun", "2 Portale"]);
  assert.deepEqual(anzeige.zusammenfassung({ begriffe: [], region: null, portale: 4 }), ["Noch keine Suchbegriffe", "4 Portale"]);
  assert.deepEqual(anzeige.zusammenfassung({ begriffe: ["A", "B", "C", "D", "E"], portale: 4 }), ["Sucht nach A, B, C und 2 weiteren", "4 Portale"]);
});

test("the reason a disabled Jetzt suchen is disabled stands directly under it", async () => {
  assert.match(HTML, /<button type="button" class="btn btn--primary" id="suchen" aria-describedby="suchen-grund" disabled>Jetzt suchen<\/button>\s*<p id="suchen-grund" class="btn-reason"><\/p>/);

  const ohneProfil = page({ liste: { sperrgrund: "Zuerst Meine Angaben abschliessen." } });
  await settle();
  assert.equal(ohneProfil.$("suchen").disabled, true);
  assert.equal(ohneProfil.$("suchen-grund").textContent, "Zuerst Meine Angaben abschliessen.");

  const ohneErweiterung = page({ erweiterung: false });
  await settle();
  assert.equal(ohneErweiterung.$("suchen-grund").textContent, "", "no reason while the page still waits for the extension");
  ohneErweiterung.timers.find(t => t.ms === 1500).f();
  assert.equal(ohneErweiterung.$("suchen").disabled, true);
  assert.equal(ohneErweiterung.$("suchen-grund").textContent, "Zuerst die Erweiterung einrichten.");

  const bereit = page();
  await settle();
  assert.equal(bereit.$("suchen").disabled, false);
  assert.equal(bereit.$("suchen-grund").textContent, "");
});

test("before a long run the page says under Jetzt suchen how many searches and stages and how long (G43)", async () => {
  assert.match(HTML, /<p id="suchen-grund" class="btn-reason"><\/p>\s*<p id="suchen-umfang" class="btn-reason" hidden><\/p>/);
  const text = "Diese Suche dauert etwa 23 Minuten: 193 Suchen in 7 Etappen, mit je einer Minute Pause dazwischen.";
  const lang = page({ liste: { umfang: { lang: true, text, suchen: 193, etappen: 7, minuten: 23 } } });
  await settle();
  assert.equal(lang.$("suchen-umfang").textContent, text);
  assert.equal(lang.$("suchen-umfang").hidden, false);

  const kurz = page({ liste: { umfang: { lang: false, text: "", suchen: 12, etappen: 4, minuten: 1 } } });
  await settle();
  assert.equal(kurz.$("suchen-umfang").hidden, true);
});

test("without a search profile the app gives the short reason and keeps it out of the hints", () => {
  const routes = fs.readFileSync(path.join(ROOT, "routes_search.py"), "utf8");
  assert.match(routes, /BLOCKED_WITHOUT_PROFILE = "Zuerst Meine Angaben abschliessen\."/);
  assert.match(routes, /"sperrgrund": blocked/);
});

test("before the first search the list says Noch nicht gesucht, not Keine neuen Treffer", async () => {
  const p = page({ liste: { treffer: [], letzte_suche: null } });
  await settle();
  assert.equal(p.$("leer-titel").textContent, "Noch nicht gesucht.");
  assert.equal(p.$("leer-text").textContent, "Die erste Suche dauert einige Minuten.");
  assert.notEqual(shown(p.$("letzte")), "Noch keine Suche.");

  const danach = page({ liste: { treffer: [], letzte_suche: { datum: "2026-11-01", portale: { "jobs.ch": {} } } } });
  await settle();
  assert.equal(danach.$("leer-titel").textContent, "Keine neuen Treffer");
});

test("Noch keine Suche never shows when hits exist", async () => {
  const p = page({ liste: { treffer: [HIT], letzte_suche: null } });
  await settle();
  assert.equal(shown(p.$("letzte")), "1 Treffer, 1 neu");
  assert.deepEqual(anzeige.letzteSuche(null, [HIT], String), ["1 Treffer, 1 neu"]);
});

test("Übernehmen becomes Merken, and the message says where the application stands, with a link to it (#374)", async () => {
  const p = page({ liste: { treffer: [HIT] } });
  await settle();
  const aktionen = p.$("detail").children.flat().filter(Boolean)
    .flatMap(function alle(n) { return [n, ...((n && n.children) || []).flat().flatMap(alle)]; });
  const merken = aktionen.find(n => n && n.tag === "button" && textOf(n) === "Merken");
  assert.ok(merken, "a button Merken");
  assert.ok(!aktionen.some(n => n && n.tag === "button" && /bernehmen/.test(textOf(n))));

  merken.fire("click");
  await settle();
  const gemerkt = p.messages.find(m => Array.isArray(m.inhalt) && m.inhalt[0] === "Gemerkt. Die Bewerbung steht jetzt unter Bewerbungen. ");
  assert.ok(gemerkt, "the message reads Gemerkt. Die Bewerbung steht jetzt unter Bewerbungen.");
  assert.equal(gemerkt.inhalt[1].tag, "a");
  assert.equal(gemerkt.inhalt[1].attrs.href, "/bewerbung?id=b7");
  assert.equal(textOf(gemerkt.inhalt[1]), "Bewerbung öffnen");
  assert.match(HTML, /data-zustand="uebernommen">In Bewerbungen </);
});

test("Register in user texts becomes Ihre Bewerbungen, in the Sie and the du form", () => {
  assert.equal(texte.text("suche.schon-titel", "stelle-sie"), "Schon in Ihren Bewerbungen");
  assert.equal(texte.text("suche.schon-titel", "stelle-du"), "Schon in deinen Bewerbungen");
  assert.equal(texte.text("suche.schon-marke", "lehrstelle-du"), "schon in deinen Bewerbungen");
  assert.doesNotMatch(CODE, /Register/);
  const routes = fs.readFileSync(path.join(ROOT, "routes_search.py"), "utf8");
  const preferences = fs.readFileSync(path.join(ROOT, "preferences.py"), "utf8");
  assert.match(routes, /"Dieser Treffer ist schon \{saved_in\}\."/);
  assert.match(preferences, /SAVED_IN = \{SIE: "in Ihren Bewerbungen", DU: "in deinen Bewerbungen"\}/);
  assert.doesNotMatch(routes, /schon im Register/);
  assert.doesNotMatch(fs.readFileSync(path.join(ROOT, "hits.py"), "utf8"), /\) im Register\./);
});

test("Einstieg abschliessen becomes Meine Angaben abschliessen", () => {
  for (const datei of ["routes_search.py", "search_plan.py", "routes_career.py", path.join("ai", "tasks.py")]) {
    assert.doesNotMatch(fs.readFileSync(path.join(ROOT, datei), "utf8"), /Einstieg abschliessen/, datei);
  }
  assert.match(fs.readFileSync(path.join(ROOT, "search_plan.py"), "utf8"), /Zuerst Meine Angaben abschliessen\./);
});

test("the last search names its day, and a catching up portal says from when (#208)", () => {
  const lauf = { datum: "2026-11-09", portale: { "job-room": {}, "jobs.ch": {}, jobscout24: {} } };
  assert.deepEqual(anzeige.letzteSuche(lauf, [HIT], String, "gestern"), ["Letzte Suche gestern", "3 Portale", "1 Treffer, 1 neu"]);
  assert.deepEqual(anzeige.letzteSuche(lauf, [HIT], d => `x${d}`), ["Letzte Suche am x2026-11-09", "3 Portale", "1 Treffer, 1 neu"]);
  assert.deepEqual(anzeige.letzteSuche(null, [], String), [], "nothing to say before the first search");
  assert.equal(anzeige.problemZeile("Seite verändert.", "Sobald die Suche dort wieder geht, holt sie die Inserate ab 06.11.2026 nach."),
    "Seite verändert. Sobald die Suche dort wieder geht, holt sie die Inserate ab 06.11.2026 nach.");
  assert.equal(anzeige.problemZeile("Seite verändert."), "Seite verändert.");
});

test("the window choices keep a value of the profile, and each portal reads as a sentence (#208)", () => {
  assert.deepEqual(anzeige.zeitfensterWahl(21).map(w => w.text),
    ["7 Tage", "14 Tage", "21 Tage (Vorgabe)", "30 Tage", "45 Tage", "60 Tage"]);
  assert.deepEqual(anzeige.zeitfensterWahl(10).map(w => w.wert), [7, 10, 14, 21, 30, 45, 60]);
  assert.deepEqual(anzeige.portalStand({ portal: "job-room", zuletzt: "gestern", ab: "09.11.2026", problem: false }),
    ["job-room: zuletzt gestern", "nächste Suche ab 09.11.2026"]);
  assert.deepEqual(anzeige.portalStand({ portal: "jobs.ch", zuletzt: "am 06.11.2026", ab: "06.11.2026", problem: true }),
    ["jobs.ch: Problem bei der letzten Suche", "nächste Suche ab 06.11.2026"]);
  assert.deepEqual(anzeige.portalStand({ portal: "ictjobs", zuletzt: "", ab: "21.10.2026", problem: false }),
    ["ictjobs: noch nie gesucht", "nächste Suche ab 21.10.2026"]);
});

test("the second line shows only with a sentence, the link only when it helps (#208)", async () => {
  const p = page({ liste: { treffer: [HIT], letzte_suche: { datum: "2026-10-24", portale: { "jobs.ch": {} } },
    zeitraum: { letzte: "am 24.10.2026", zeile: "Die nächste Suche nimmt nur die letzten 14 Tage, ab 28.10.2026.", zeitfenster_aendern: true, nachholen: {} } } });
  await settle();
  assert.equal(p.$("zeitraum").hidden, false);
  assert.equal(p.$("zeitraum-text").textContent, "Die nächste Suche nimmt nur die letzten 14 Tage, ab 28.10.2026.");
  assert.equal(p.$("zeitraum-aendern").hidden, false);
  assert.match(shown(p.$("letzte")), /^Letzte Suche am 24\.10\.2026/);
  const ruhig = page({ liste: { treffer: [HIT], letzte_suche: { datum: "2026-11-09", portale: { "jobs.ch": {} } },
    zeitraum: { letzte: "gestern", zeile: "", zeitfenster_aendern: false, nachholen: {} } } });
  await settle();
  assert.equal(ruhig.$("zeitraum").hidden, true);
});
