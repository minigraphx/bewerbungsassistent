// «·» lines on Meine Angaben (#351), as on the other pages of the app (#342): the page is built from onboarding/src
// and renders them through dot-line.js of the app, so no line starts with «·» and screen readers hear commas.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { FakeNode, loadScripts } = require("./fake_dom.cjs");
const DotLine = require("../../bewerbungen/seiten/dot-line.js");

const SRC = path.join(__dirname, "..", "src");
const SEITEN = path.join(__dirname, "..", "..", "bewerbungen", "seiten");
const page = loadScripts(["dom.js"], { DotLine });

const isComment = (line) => /^\s*(\/\/|\/\*|\*)/.test(line);
const wholePartRule = (css) => (/\.whole-part \{[^}]*\}/.exec(css) || [null])[0];
const shown = (node) => (node instanceof FakeNode
  ? (node.className === "visually-hidden" ? "" : node.children.map(shown).join("")) : node.textContent ?? node);
const heard = (node) => (node instanceof FakeNode
  ? (node.getAttribute("aria-hidden") === "true" ? "" : node.children.map(heard).join("")) : node.textContent ?? node);

test("dotLine builds whole parts with the page's el, each but the last carrying its «·»", () => {
  const link = page.el("a", { href: "/" }, "Zu den Bewerbungen");
  const nodes = page.dotLine(["Zu den Inhalten", "", link]);
  assert.equal(nodes.length, 3, "an empty part is left out, so no «·» stands alone");
  const [first, gap, last] = nodes;
  assert.equal(gap, " ", "a plain space between two parts is the only place a line may break");
  for (const part of [first, last]) {
    assert.equal(part.tagName, "span");
    assert.equal(part.className, "whole-part");
  }
  const [text, dot, comma] = first.children;
  assert.equal(text.textContent, "Zu den Inhalten");
  assert.equal(dot.getAttribute("aria-hidden"), "true");
  assert.equal(dot.textContent, " ·");
  assert.equal(comma.className, "visually-hidden");
  assert.equal(comma.textContent, ",");
  assert.deepEqual(last.children, [link]);
});

test("the eye reads «·», a screen reader hears a comma", () => {
  const nodes = page.dotLine(["Gesucht wird: eine Stelle", "Anrede: Sie", "RAV: ja"]);
  assert.equal(nodes.map(shown).join(""), "Gesucht wird: eine Stelle · Anrede: Sie · RAV: ja");
  assert.equal(nodes.map(heard).join(""), "Gesucht wird: eine Stelle, Anrede: Sie, RAV: ja");
});

test("no script of the page joins a visible line with «·» by hand", () => {
  const found = fs.readdirSync(SRC).filter((name) => name.endsWith(".js")).flatMap((name) => fs
    .readFileSync(path.join(SRC, name), "utf8").split("\n")
    .filter((line) => line.includes("·") && !isComment(line))
    .map((line) => `${name}: ${line.trim()}`));
  assert.deepEqual(found, [], "join these through dotLine");
});

test("the page styles a whole part as the other pages do, in both built files", () => {
  const rule = wholePartRule(fs.readFileSync(path.join(SEITEN, "stil.css"), "utf8"));
  assert.ok(rule, "stil.css has the rule");
  assert.equal(wholePartRule(fs.readFileSync(path.join(SRC, "style.css"), "utf8")), rule);
  const app = fs.readFileSync(path.join(SEITEN, "angaben.html"), "utf8");
  assert.equal(wholePartRule(/<style>([\s\S]*?)<\/style>/.exec(app)[1]), rule);
  assert.ok(app.indexOf('<script src="/dot-line.js"></script>') < app.indexOf("<script>"),
    "the app page loads dot-line.js before its own script");
});
