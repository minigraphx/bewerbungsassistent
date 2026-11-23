// «·» lines app-wide (#342): every page joins a visible line through dot-line.js, so no line starts with «·» and
// screen readers hear commas. Read from the pages as written; the helper itself has its tests in dot_line.test.cjs.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const SEITEN = path.join(__dirname, "..", "seiten");
const read = name => fs.readFileSync(path.join(SEITEN, name), "utf8");
const files = ext => fs.readdirSync(SEITEN).filter(name => name.endsWith(ext));

/**
 * The «·» joins that stay plain strings, each with why: none is a line of parts that the eye reads and that wraps.
 * Each entry names a piece of the line and how many lines have it, so a fixed or moved join is noticed here.
 */
const LEFT_ALONE = {
  // The narrow sidebar shows a short label beside an icon that never wraps.
  "sidebar-logic.js": [["narrow: warning ? `${short} · ${warning.short}`", 1], ["narrow: `${short} · ${none.short}`", 1],
                       ["low: `${short} · ${Texte.t(\"fast aufgebraucht\")}`", 1]],
  // Error and warning texts joined from reasons or suspicious lines: a message, not a line of parts.
  "bewerbung.js": [["antwortDaten.abgelehnt.map(a => a.grund).join(\" · \")", 1], ["ergebnis.hinweise.join(\" · \")", 1]],
  "dossier-texte.js": [["ergebnis.suspicious_lines.join(\" · \")", 1]],
  // Both runs (forms, Job-Room) show their refusals through this one helper since #419.
  "uebersicht.js": [["liste.map(a => Texte.t(\"{firma}: {grund}\", { firma: a.firma, grund: a.grund })).join(\" · \")", 1]],
  "treffer.js": [["b.auffaellig.join(\" · \")", 1]],
};

const isComment = line => /^\s*(\/\/|\/\*|\*)/.test(line);

/** The code lines of `name` that hold a «·», comments left out. */
function dotLines(name) {
  return read(name).split("\n").filter(line => line.includes("·") && !isComment(line));
}

test("every page loads dot-line.js after meldungen.js and before app.js", () => {
  for (const name of files(".html")) {
    const html = read(name);
    const helper = html.indexOf('<script src="/dot-line.js"></script>');
    assert.ok(helper > html.indexOf('<script src="/meldungen.js"></script>'), `${name} loads dot-line.js after meldungen.js`);
    assert.ok(helper < html.indexOf('<script src="/app.js"></script>'), `${name} loads dot-line.js before app.js`);
    assert.equal(html.split('<script src="/dot-line.js"></script>').length, 2, `${name} loads dot-line.js once`);
  }
});

test("no page script joins a visible line with «·» by hand", () => {
  const found = [];
  for (const name of files(".js").filter(name => name !== "dot-line.js")) {
    const allowed = LEFT_ALONE[name] || [];
    for (const line of dotLines(name)) {
      if (!allowed.some(([part]) => line.includes(part))) found.push(`${name}: ${line.trim()}`);
    }
  }
  assert.deepEqual(found, [], "join these through DotLine.render");
});

test("each join left alone is still there, as often as listed", () => {
  for (const [name, parts] of Object.entries(LEFT_ALONE)) {
    for (const [part, count] of parts) assert.equal(dotLines(name).filter(l => l.includes(part)).length, count, `${name}: ${part}`);
  }
});

test("the markup carries a «·» only as the hidden mark of a whole part", () => {
  // angaben.html is built from onboarding/src, which holds its own check (onboarding/tests/dot_lines.test.cjs, #351);
  // its markup keeps a «·» only in comments, in the nav CSS it shares with stil.css and in the plain fallback of
  // dotLine for the standalone file, which loads no dot-line.js.
  for (const name of files(".html").filter(name => name !== "angaben.html")) {
    const rest = read(name)
      .replaceAll('<span aria-hidden="true">&nbsp;·</span><span class="visually-hidden">,</span>', "")
      .replace(/<h4 class="cv-create__step"[^>]*>\d · [^<]+<\/h4>/g, "");
    assert.deepEqual([...rest.matchAll(/.{0,40}·.{0,20}/g)].map(m => m[0]), [], name);
  }
});

test("the static «·» lines on Heute are whole parts", () => {
  const html = read("uebersicht.html");
  const eyebrow = /<p class="path__eyebrow">(.*?)<\/p>/.exec(html)[1];
  assert.equal(eyebrow, '<span class="whole-part">Nächster Schritt<span aria-hidden="true">&nbsp;·</span>'
    + '<span class="visually-hidden">,</span></span> <span class="whole-part">etwa 20&nbsp;Minuten</span>');
  for (const [, title] of html.matchAll(/<p class="path__title">(.*?)<\/p>/g)) {
    assert.match(title, /^<span class="whole-part"><strong[^>]*>[^<]+<\/strong><span aria-hidden="true">&nbsp;·<\/span><span class="visually-hidden">,<\/span><\/span> <span class="whole-part path__state"[^>]*>[^<·]+<\/span>$/, title);
  }
  assert.match(read("uebersicht.js"), /\$\("weg-einrichtung-stand"\)\.textContent = bereit \? Texte\.t\("erledigt"\) : Texte\.t\("noch offen"\);/);
});

test("the kununu badge before the «·» of the company is an inline box, so the «·» cannot start a line", () => {
  // A line may break after an inline-block even before a no-break space; the browser sweep found «·» starting a
  // line in the hit row whenever the company and its badge filled the line.
  const rule = /\.kununu-mark \{([^}]*)\}/.exec(fs.readFileSync(path.join(SEITEN, "firmen.css"), "utf8"))[1];
  assert.match(rule, /display: inline;/);
  assert.match(rule, /white-space: nowrap;/);
});

test("the station detail in «Lebenslauf erstellen» breaks a word only when it overflows, never before its «·»", () => {
  // overflow-wrap: anywhere lets a narrow row break between a company and its no-break «·»; break-word keeps
  // «Muster GmbH ·» together whenever it fits the row.
  const rule = /\.cv-create__detail \{([^}]*)\}/.exec(read("stil.css"))[1];
  assert.match(rule, /overflow-wrap: break-word;/);
});
