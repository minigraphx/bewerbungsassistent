// A small stand-in for the DOM, enough for the views built with el() in dom.js, and a loader that runs the page
// scripts in one sandbox the way build_template.py inlines them (later files use earlier ones).
"use strict";
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const SRC = path.join(__dirname, "..", "src");

class FakeNode {
  constructor(tagName) {
    this.tagName = tagName;
    this.children = [];
    this.attributes = {};
    this.dataset = {};
    this.listeners = {};
    this.scrolledIntoView = 0;
  }

  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.children = nodes; }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  getAttribute(name) { return name in this.attributes ? this.attributes[name] : null; }
  addEventListener(type, handler) { this.listeners[type] = handler; }
  scrollIntoView() { this.scrolledIntoView += 1; }
  focus() {}
  click() { if (this.onclick) this.onclick({ target: this }); }

  get textContent() {
    return this.text !== undefined ? this.text : this.children.map((c) => c.textContent).join("");
  }

  set textContent(value) {
    this.children = [];
    this.text = String(value);
  }
}

class FakeText {
  constructor(text) { this.textContent = text; }
}

function fakeDocument() {
  return {
    createElement: (tag) => new FakeNode(tag),
    createTextNode: (text) => new FakeText(text),
  };
}

/** Every element below `node` (itself included) for which `match` holds. */
function findAll(node, match) {
  if (!(node instanceof FakeNode)) return [];
  return [...(match(node) ? [node] : []), ...node.children.flatMap((child) => findAll(child, match))];
}

/** The page scripts in one sandbox; `extra` adds globals such as a fake backend. Returns the sandbox. */
function loadScripts(names, extra = {}) {
  const context = vm.createContext({ document: fakeDocument(), console, ...extra });
  for (const name of names) {
    vm.runInContext(fs.readFileSync(path.join(SRC, name), "utf8"), context, { filename: name });
  }
  return context;
}

module.exports = { FakeNode, findAll, loadScripts };
