// Where the language switch stands (#435, G10, UI/UX design before building): at the bottom of the sidebar below the
// status box, inside «Menü» below 900 px, and in the header of Einrichtung; loaded on every page; the guide says so.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const SEITEN = path.join(__dirname, "..", "seiten");
const ROOT = path.join(__dirname, "..", "..");
const read = name => fs.readFileSync(path.join(SEITEN, name), "utf8");
const htmlPages = () => fs.readdirSync(SEITEN).filter(name => name.endsWith(".html"));
const navOf = html => html.match(/<nav class="app-nav"[\s\S]*?<\/nav>/)[0];
const GLOBE = /<svg class="language-switch__icon" aria-hidden="true" width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">/;

test("the sidebar's switch follows the status box inside the part «Menü» opens below 900 px", () => {
  const nav = navOf(read("uebersicht.html"));
  const more = nav.slice(nav.indexOf('<div class="app-nav__more" id="nav-more">'));
  const status = more.indexOf('<div class="app-nav__status">');
  const group = more.indexOf('<div class="app-nav__language language-switch" id="nav-language" role="group" hidden>');
  assert.ok(status >= 0 && group > status, "after the status box, inside #nav-more");
  assert.ok(more.indexOf('id="nav-extension"') < group, "not inside the status box");
  assert.match(more, /<div class="status language-switch__status" id="nav-language-status" role="status" aria-live="polite"><\/div><\/div><\/nav>$/);
  assert.match(more.slice(group), GLOBE);
});

test("the group's label is set by the script, so no page carries it for the translation", () => {
  for (const name of htmlPages()) {
    assert.doesNotMatch(read(name), /Langue|aria-label="Sprache/, name);
    assert.doesNotMatch(read(name), />(Deutsch|Français|English)</, name);
  }
});

test("Einrichtung has its own copy on the line of its heading, with its status line", () => {
  const html = read("einrichtung.html");
  const head = html.slice(html.indexOf('<header class="setup__head">'), html.indexOf("</header>"));
  assert.match(head, /<div class="setup__title"><h1>Einrichtung<\/h1><div class="setup__language"><div class="language-switch" id="setup-language" role="group" hidden><svg/);
  assert.match(head, /<div class="status language-switch__status" id="setup-language-status" role="status" aria-live="polite"><\/div><\/div><\/div>/);
  assert.match(head, GLOBE);
});

test("every page loads the logic and the switch after the sidebar, each once", () => {
  for (const name of htmlPages()) {
    const scripts = [...read(name).matchAll(/<script src="([^"]+)"/g)].map(m => m[1]);
    const at = file => scripts.indexOf(file);
    assert.ok(at("/sprache-logik.js") > at("/sidebar.js") && at("/sidebar.js") >= 0, name);
    assert.equal(at("/sprachwahl.js"), at("/sprache-logik.js") + 1, name);
    assert.ok(at("/meldungen.js") >= 0 && at("/meldungen.js") < at("/sprachwahl.js"), name);
    assert.equal(scripts.length, new Set(scripts).size, `${name} loads a script twice`);
  }
});

test("the app serves the switch's script", () => {
  assert.match(fs.readFileSync(path.join(ROOT, "bewerbungen", "app.py"), "utf8"), /"\/sprachwahl\.js": "sprachwahl\.js"/);
});

test("the buttons are tall enough to tap, wrap rather than shrink and show focus", () => {
  for (const css of [read("stil.css"), fs.readFileSync(path.join(ROOT, "onboarding", "src", "appnav.css"), "utf8")]) {
    const rule = selector => {
      const at = css.indexOf(`${selector} {`);
      assert.ok(at >= 0, selector);
      return css.slice(at, css.indexOf("}", at));
    };
    assert.match(rule(".language-switch"), /flex-wrap: wrap/);
    assert.match(rule(".language-switch__option"), /min-height: 44px/);
    assert.match(rule(".language-switch__option"), /flex: none/);
    assert.match(rule(".language-switch__option"), /white-space: nowrap/);
    assert.match(css, /\.language-switch__option\[aria-pressed="true"\] \{[^}]*font-weight: 500[^}]*cursor: default/);
    assert.match(css, /\.language-switch__option:focus-visible \{[^}]*outline: 2px solid var\(--focus\)/);
    assert.match(css, /\.language-switch__status:empty \{ display: none; \}/);
  }
});

test("on Einrichtung the switch stands right of the heading and wraps under it below 600 px", () => {
  const css = read("stil.css");
  assert.match(css, /\.setup__title \{[^}]*display: flex;[^}]*flex-wrap: wrap;[^}]*justify-content: space-between/);
  assert.match(css, /@media \(max-width: 599px\) \{ \.setup__title \{ flex-direction: column; align-items: flex-start; \}/);
});

test("the guide names the switch in the sidebar, in Einrichtung and for sprachen.yaml", () => {
  const guide = fs.readFileSync(path.join(ROOT, "docs", "installation.md"), "utf8");
  assert.ok(guide.includes("ganz unten **Einstellungen**. Darunter wechseln Sie die Sprache der App: **Deutsch**, **Français** oder **English**; im schmalen Fenster steht die Wahl unter **Menü**."));
  assert.ok(guide.includes("**Sprachen:** Die **Sprache der App** wählen Sie unten in der Seitenleiste, oben auf der Seite **Einrichtung** oder unter **Einstellungen**, **KI, Budget und Sprache**, bei **Sprache**. Dort wählen Sie unter **Ich bewerbe mich auf** auch die Sprachen, in denen Sie sich bewerben."));
  assert.ok(guide.includes("Wählen Sie die Sprache in der Einrichtung, bevor der Datenordner feststeht, übernimmt die App sie in diesen Ordner; ist dort schon eine Sprache der App gespeichert, gilt diese, und die Einrichtung sagt es. Solange Sie nichts gewählt haben"));
  assert.ok(guide.includes("Die App selbst gibt es vorerst nur auf Deutsch; Französisch und Englisch folgen."));
  assert.ok(guide.includes("bei **Sprache**, oder mit der Sprachwahl in der Seitenleiste oder auf der Seite **Einrichtung**."));
  assert.equal(guide.split("oben rechts die Sprachwahl Deutsch, Français, English](bilder/einrichtung-start.jpg)").length, 3,
               "both pictures of Einrichtung name the switch");
});

test("the README picture of Heute names the switch below the budget", () => {
  const readme = fs.readFileSync(path.join(ROOT, "README.md"), "utf8");
  assert.ok(readme.includes("; links die Seitenleiste mit dem KI-Budget des Monats und darunter der Sprachwahl Deutsch, Français, English](docs/bilder/uebersicht.jpg)"));
});
