// „Vorbefüllen“ shows at once that it started, next to the button and in view (#156).
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { findAll, loadScripts } = require("./fake_dom.cjs");

const form = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "form.json"), "utf8"));
const page = loadScripts(["validate.js", "model.js", "dom.js", "documents.js", "uploads.js", "prefill.js"]);
const IDLE = { running: false, waiting: false, problem: null, report: null };

function card(run, track = "job") {
  return page.prefillCard({
    form, track, uploads: [{ category: "lebenslauf-bisher", name: "cv.pdf", size: 10 }], messages: [], run, hasName: true,
    titleOf: (id) => id, onRun() {}, onGoTo() {}, onAdd() {}, onRemove() {}, onByHand() {},
  });
}

const byId = (node, id) => findAll(node, (n) => n.id === id)[0];
const parentOf = (root, child) => findAll(root, (n) => n.children.includes(child))[0];

test("while running the button is busy and the running text stands right after the buttons", () => {
  const node = card({ ...IDLE, running: true });
  const button = byId(node, "prefill");
  const status = byId(node, "prefill-status");
  assert.equal(button.disabled, true);
  assert.equal(button.getAttribute("aria-busy"), "true");
  assert.match(button.textContent, /Wird gelesen/);
  assert.match(status.textContent, /Die Unterlagen werden gelesen/);
  assert.equal(status.getAttribute("role"), "status");
  const actions = parentOf(node, button);
  const row = parentOf(node, actions);
  assert.equal(row.children[row.children.indexOf(actions) + 1], status);
});

test("when uploads have to finish first, the page says so", () => {
  for (const track of ["job", "apprenticeship"]) {
    const status = byId(card({ ...IDLE, running: true, waiting: true }, track), "prefill-status");
    assert.match(status.textContent, /noch hochgeladen/);
  }
});

test("a problem takes the place of the running text", () => {
  const status = byId(card({ ...IDLE, problem: "Vor der ersten KI-Nutzung braucht es die Einwilligung." }), "prefill-status");
  assert.equal(status.getAttribute("role"), "alert");
  assert.match(status.textContent, /Einwilligung/);
});

test("before running there is no busy state", () => {
  const node = card(IDLE);
  assert.equal(byId(node, "prefill").disabled, undefined);
  assert.equal(byId(node, "prefill-status"), undefined);
});

function flow({ pending = null, current = () => true } = {}) {
  const log = [];
  const run = page.startPrefill({
    show: (state) => log.push(["show", state.waiting]),
    reveal: () => log.push(["reveal"]),
    pendingUploads: () => pending,
    isCurrent: current,
    ask: async () => { log.push(["ask"]); return { suggestions: {} }; },
  });
  return { log, run };
}

test("the busy state shows and is brought into view before anything is awaited", async () => {
  const { log, run } = flow();
  assert.deepEqual(log.slice(0, 2), [["show", false], ["reveal"]]); // synchronous: no request, no upload holds it up
  assert.deepEqual(await run, { suggestions: {} });
  assert.deepEqual(log, [["show", false], ["reveal"], ["ask"]]);
});

test("uploads still on their way finish before the app is asked", async () => {
  let done;
  const pending = new Promise((resolve) => { done = resolve; });
  const { log, run } = flow({ pending });
  await new Promise((resolve) => setImmediate(resolve));
  assert.deepEqual(log, [["show", true], ["reveal"]]);
  done();
  await run;
  assert.deepEqual(log, [["show", true], ["reveal"], ["show", false], ["reveal"], ["ask"]]);
});

test("a run overtaken while uploads finish asks nothing", async () => {
  const { log, run } = flow({ pending: Promise.resolve(), current: () => false });
  assert.equal(await run, null);
  assert.ok(!log.some(([step]) => step === "ask"));
});
