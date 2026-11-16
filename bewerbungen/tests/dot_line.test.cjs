// «·» lines (#331, #337, #340): one shared helper renders them as whole parts, so a line never starts with «·».
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const DotLine = require("../seiten/dot-line.js");

const SEITEN = path.join(__dirname, "..", "seiten");
const read = name => fs.readFileSync(path.join(SEITEN, name), "utf8");

const el = (tag, attrs = {}, ...children) => ({ tag, attrs, children: children.flat() });
const isEl = n => typeof n === "object";
const shown = n => (isEl(n) ? (n.attrs.class === "visually-hidden" ? "" : n.children.map(shown).join("")) : n);
const heard = n => (isEl(n) ? (n.attrs["aria-hidden"] === "true" ? "" : n.children.map(heard).join("")) : n);
const line = nodes => ({ shown: nodes.map(shown).join(""), heard: nodes.map(heard).join("") });

test("each part is whole and carries its «·», glued with a no-break space; the last part has none", () => {
  const nodes = DotLine.render(["Danach: 5 von 15 Suchbegriffen", "bis 10 Suchen pro Portal"], el);
  assert.equal(nodes.length, 3);
  const [first, gap, last] = nodes;
  assert.equal(gap, " ", "a plain space between two parts is the only place a line may break");
  for (const part of [first, last]) {
    assert.equal(part.tag, "span");
    assert.deepEqual(part.attrs, { class: "whole-part" });
  }
  assert.deepEqual(first.children, ["Danach: 5 von 15 Suchbegriffen",
    { tag: "span", attrs: { "aria-hidden": "true" }, children: ["\u00a0·"] },
    { tag: "span", attrs: { class: "visually-hidden" }, children: [","] }]);
  assert.deepEqual(last.children, ["bis 10 Suchen pro Portal"]);
});

test("the eye reads «·», a screen reader hears a comma", () => {
  assert.deepEqual(line(DotLine.render(["Vorschlag der KI", "1 Änderung"], el)),
    { shown: "Vorschlag der KI\u00a0· 1 Änderung", heard: "Vorschlag der KI, 1 Änderung" });
  assert.deepEqual(line(DotLine.render(["7 Seiten", "Anschreiben enger gesetzt", "Lebenslauf so eng wie möglich"], el)),
    { shown: "7 Seiten\u00a0· Anschreiben enger gesetzt\u00a0· Lebenslauf so eng wie möglich",
      heard: "7 Seiten, Anschreiben enger gesetzt, Lebenslauf so eng wie möglich" });
});

test("one part has no «·», and empty parts are left out instead of leaving a «·» alone", () => {
  assert.deepEqual(DotLine.render(["1 Seite"], el), [el("span", { class: "whole-part" }, "1 Seite")]);
  assert.deepEqual(DotLine.render([], el), []);
  assert.deepEqual(line(DotLine.render(["", "CHF\u00a00.02", null, "16.11.2026", undefined], el)),
    { shown: "CHF\u00a00.02\u00a0· 16.11.2026", heard: "CHF\u00a00.02, 16.11.2026" });
});

test("a whole part breaks only as a whole, in the shared style of every page", () => {
  const rule = read("stil.css").split("\n").find(l => l.startsWith(".whole-part {"));
  assert.ok(rule, ".whole-part has its rule in stil.css");
  assert.match(rule, /display: inline-block; max-width: 100%;/);
});

test("the pages of #331 and #337 no longer build «·» parts of their own", () => {
  for (const name of ["suchbegriffe.js", "suchbegriffe-logik.js", "unterlagen-schritt.js", "unterlagen-ergebnis.js"]) {
    assert.doesNotMatch(read(name), /\\u00a0·|&nbsp;·|\u00a0·/, `${name} glues a «·» by hand`);
    assert.doesNotMatch(read(name), /whole-part/, `${name} builds whole parts by hand`);
    assert.doesNotMatch(read(name), /· \$\{|" · "|join\(" · "\)/, `${name} joins a line with «·» into one string`);
  }
  assert.ok(!fs.readdirSync(SEITEN).some(name => /\.(css|js|html)$/.test(name) && read(name).includes("doc-tile__part")),
    "the tile uses the shared .whole-part");
});

test("every page whose scripts draw a «·» line loads the helper first, and the app serves it", () => {
  const users = fs.readdirSync(SEITEN).filter(name => name.endsWith(".js") && read(name).includes("DotLine."));
  assert.ok(users.includes("suchbegriffe.js") && users.includes("unterlagen-schritt.js"), users.join(", "));
  const pages = fs.readdirSync(SEITEN).filter(name => name.endsWith(".html"));
  for (const page of pages) {
    const html = read(page);
    for (const user of users) {
      const at = html.indexOf(`<script src="/${user}"></script>`);
      if (at < 0) continue;
      const helper = html.indexOf('<script src="/dot-line.js"></script>');
      assert.ok(helper >= 0 && helper < at, `${page} loads dot-line.js before ${user}`);
    }
  }
  assert.match(fs.readFileSync(path.join(__dirname, "..", "app.py"), "utf8"), /"\/dot-line\.js": "dot-line\.js",/);
});
