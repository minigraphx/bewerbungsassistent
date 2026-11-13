// Bewerbungen as its own page (#261, A5, G55, G27, G28, G29, G38): the list leaves Heute, keeps its views by stage
// with counts, discards the ticked ones in one step, takes a job by hand and starts the pass over saved jobs.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const L = require("../seiten/uebersicht-logik.js");
const A = require("../seiten/bewerbungen-logic.js");
const sidebar = require("../seiten/sidebar-logic.js");
const texte = require("../seiten/texte.js");

const PAGES = path.join(__dirname, "..", "seiten");
const read = name => fs.readFileSync(path.join(PAGES, name), "utf8");
const b = (id, status, fields = {}) => ({ id, firma: `Firma ${id}`, stelle: `Stelle ${id}`, status, eingetragen_am: "2026-11-01", ...fields });
const scriptsOf = html => [...html.matchAll(/<script src="([^"]+)"/g)].map(m => m[1]);

test("the app serves the page Bewerbungen at /bewerbungen with its script and logic", () => {
  const app = fs.readFileSync(path.join(__dirname, "..", "app.py"), "utf8");
  for (const [route, file] of [["/bewerbungen", "bewerbungen.html"], ["/bewerbungen.js", "bewerbungen.js"],
                               ["/bewerbungen-logic.js", "bewerbungen-logic.js"], ["/bewerbungen.css", "bewerbungen.css"]]) {
    assert.ok(app.includes(`"${route}": "${file}"`), route);
    assert.ok(fs.existsSync(path.join(PAGES, file)), file);
  }
  assert.equal(sidebar.activeTarget("/bewerbungen"), "bewerbungen");
  assert.equal(sidebar.activeTarget("/bewerbung"), "bewerbungen");
});

test("the sidebar leads to the page, not to a part of Heute", () => {
  for (const name of fs.readdirSync(PAGES).filter(file => file.endsWith(".html"))) {
    const nav = read(name).match(/<nav class="app-nav"[\s\S]*?<\/nav>/)[0];
    assert.match(nav, /<a class="app-nav__link" href="\/bewerbungen" data-target="bewerbungen">Bewerbungen<\/a>/, name);
    assert.doesNotMatch(read(name), /#liste-teil/, name);
  }
});

test("the page is laid out as A5: title, Stelle selbst erfassen, the four views with counts and the search", () => {
  const html = read("bewerbungen.html");
  assert.match(html, /<title>Bewerbungen<\/title>/);
  assert.match(html, /<h1 id="titel">Bewerbungen<\/h1>/);
  assert.match(html, /<button type="button" class="btn" id="von-hand" data-text="uebersicht.von-hand">Stelle selbst erfassen<\/button>/);
  const views = [...html.matchAll(/data-ansicht="(\w+)"/g)].map(m => m[1]);
  assert.deepEqual(views, ["gemerkt", "beworben", "abgeschlossen", "alle"]);
  for (const view of views) assert.match(html, new RegExp(`data-zahl="${view}"`));
  assert.match(html, /<label class="applications__search-label" for="suche">Suchen<\/label>/);
  const heads = [...html.matchAll(/<th[^>]*data-spalte="(\w+)"/g)].map(m => m[1]);
  assert.deepEqual(heads, ["stelle", "stand", "note", "schritt", "frist", "erfasst"]);
  assert.match(html, /data-spalte="frist"><button type="button" class="table__sort">Bis wann<\/button>/);
  assert.match(html, /<dialog class="dialog" id="neu-dialog"/);
  assert.match(html, /<dialog class="dialog pass" id="pass-dialog"/);
  const scripts = scriptsOf(html);
  for (const file of ["/uebersicht-logik.js", "/heute-logic.js", "/bewerbungen-logic.js"]) {
    assert.ok(scripts.indexOf(file) >= 0 && scripts.indexOf(file) < scripts.indexOf("/pass.js"), file);
  }
  assert.ok(scripts.indexOf("/pass.js") < scripts.indexOf("/bewerbungen.js"));
});

test("under the list: Angehakte verwerfen, what to tick first, and the pass over the saved jobs (G29, G38)", () => {
  const html = read("bewerbungen.html");
  const foot = html.slice(html.indexOf('class="applications__foot"'), html.indexOf("</main>"));
  assert.match(foot, /<button type="button" class="btn" id="verwerfen" disabled>Angehakte verwerfen<\/button>/);
  assert.match(foot, /id="auswahl-zahl"[^>]*>Zuerst Bewerbungen anhaken\.<\/span>/);
  assert.match(foot, /<button type="button" class="link" id="durchgang" hidden>Gemerkte in einem Durchgang bewerten<\/button>/);
  assert.match(foot, /id="auswahl-leiste"[^>]*hidden/);
  assert.ok(foot.indexOf('id="verwerfen"') < foot.indexOf('id="stand-setzen"'), "discard first, then any other stage");
  const code = read("bewerbungen.js");
  assert.match(code, /window\.Pass\.start\(H\.passQueue\(zeilen\), durchgangFertig\)/);
  assert.match(code, /A\.discardPlan\(/);
});

test("discarding the ticked ones ends each by its stage: before sending Verworfen, after it Zurückgezogen (G29)", () => {
  const rows = L.mitSchritten([b("m", "Gemerkt"), b("x", "Bewerben"), b("w", "Beworben"), b("g", "Gespräch"), b("z", "Zusage")]);
  const plan = A.discardPlan(rows, ["z", "g", "w", "x", "m"]);
  const inRowOrder = ids => rows.map(row => row.bewerbung.id).filter(id => ids.includes(id));
  assert.deepEqual(plan, { Verworfen: inRowOrder(["m", "x"]), "Zurückgezogen": inRowOrder(["w", "g"]), kept: ["z"] });
  assert.equal(A.discardCount(plan), 4);
  assert.deepEqual(A.discardPlan(rows, []), { Verworfen: [], "Zurückgezogen": [], kept: [] });
  assert.deepEqual(A.discardPlan(rows, ["unknown"]), { Verworfen: [], "Zurückgezogen": [], kept: [] });
});

test("the question and the result of discarding name what happens to each", () => {
  const only = { Verworfen: ["a"], "Zurückgezogen": [], kept: [] };
  assert.equal(A.discardQuestion(only), "1 Bewerbung verwerfen?");
  assert.deepEqual(A.discardNotes(only), []);
  assert.equal(A.discardDone(only), "1 Bewerbung verworfen.");
  const mixed = { Verworfen: ["a", "b"], "Zurückgezogen": ["c"], kept: ["d", "e"] };
  assert.equal(A.discardQuestion(mixed), "3 Bewerbungen verwerfen?");
  assert.deepEqual(A.discardNotes(mixed), ["1 schon verschickte wird zurückgezogen.", "2 abgeschlossene bleiben, wie sie sind."]);
  assert.equal(A.discardDone(mixed), "2 Bewerbungen verworfen, 1 zurückgezogen.");
  assert.equal(A.discardDone({ Verworfen: [], "Zurückgezogen": ["c", "d"], kept: [] }), "2 Bewerbungen zurückgezogen.");
});

test("the line next to the button says to tick first, then how many are ticked", () => {
  assert.equal(A.selectionHint(0), "Zuerst Bewerbungen anhaken.");
  assert.equal(A.selectionHint(1), "1 angehakt");
  assert.equal(A.selectionHint(3), "3 angehakt");
});

test("Bis wann shows the deadline, the follow-up date or a dash", () => {
  const rows = L.mitSchritten([
    b("m", "Gemerkt", { frist: "2026-11-20" }), b("w", "Beworben", { beworben_am: "2026-11-10" }),
    b("g", "Gespräch"), b("z", "Zusage"), b("i", "Beworben", { beworben_am: "2026-11-02", gespraech_am: "2026-11-19" }),
  ]);
  const due = Object.fromEntries(rows.map(row => [row.bewerbung.id, A.dueText(row)]));
  assert.deepEqual(due, { m: "20.11.2026", w: "nachfragen ab 24.11.2026", g: "offen", z: "–", i: "19.11.2026" });
});

test("a view comes from the address, so Heute can open the list at Gemerkt", () => {
  assert.equal(A.viewFromHash("#gemerkt"), "gemerkt");
  assert.equal(A.viewFromHash("#abgeschlossen"), "abgeschlossen");
  assert.equal(A.viewFromHash("#alle"), "alle");
  assert.equal(A.viewFromHash(""), null);
  assert.equal(A.viewFromHash("#etwas"), null);
  assert.equal(A.viewFromHash(undefined), null);
  const heute = read("uebersicht.html");
  for (const view of ["gemerkt", "beworben", "abgeschlossen"]) {
    assert.match(heute, new RegExp(`<a class="tile" href="/bewerbungen#${view}" data-stand="${view}">`));
  }
});

test("Heute no longer holds the list, the bulk change or the dialog to enter a job", () => {
  const html = read("uebersicht.html");
  for (const id of ["liste-teil", "auswahl-leiste", "neu-dialog", "stand-dialog", "von-hand", "ansichten"]) {
    assert.doesNotMatch(html, new RegExp(`id="${id}"`), id);
  }
  assert.match(html, /<dialog class="dialog pass" id="pass-dialog"/);
  assert.doesNotMatch(read("uebersicht.js"), /zeigeListe|setzeStand/);
});

test("the application leads back to Bewerbungen by a path, not to the overview", () => {
  const html = read("bewerbung.html");
  assert.doesNotMatch(html, /Zurück zur Übersicht/);
  assert.match(html, /<nav class="crumbs" aria-label="Pfad"><a href="\/bewerbungen">Bewerbungen<\/a> › <span id="pfad-stelle" aria-current="page">Bewerbung<\/span><\/nav>/);
  const code = read("bewerbung.js");
  assert.doesNotMatch(code, /Zur Übersicht/);
  assert.match(code, /\$\("pfad-stelle"\)\.textContent = b\.stelle \|\| "Bewerbung";/);
});

test("every text the page speaks to the person with exists in all forms", () => {
  const html = read("bewerbungen.html");
  for (const [, key] of html.matchAll(/data-text="([^"]+)"/g)) assert.ok(texte.TEXTE[key], key);
  assert.equal(texte.text("uebersicht.von-hand", "stelle-sie"), "Stelle selbst erfassen");
  assert.equal(texte.text("uebersicht.von-hand", "lehrstelle-du"), "Lehrstelle selbst erfassen");
});
