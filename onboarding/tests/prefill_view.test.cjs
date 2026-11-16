// „Vorbefüllen“ shows at once that it started, next to the button and in view (#156).
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { findAll, loadScripts } = require("./fake_dom.cjs");

const form = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "form.json"), "utf8"));
const page = loadScripts(["../../bewerbungen/seiten/dateien-logik.js", "../../bewerbungen/seiten/treffer-logik.js",
  "validate.js", "model.js", "dom.js", "documents.js", "uploads.js", "kindguess.js", "droparea.js", "prefill.js"]);
const IDLE = { running: false, problem: null, report: null };
// the run waits for the estimate (#271); the states of the estimate are in prefill_estimate.test.cjs
const ESTIMATE = { phase: "ready", problem: null, answer: { anzahl: 1, kosten: 0.03, dauer_minuten: 1, waehrung: "USD",
  guthaben: null, danach: null, nicht_gelesen: [], gekuerzt: [] } };

function card(run, track = "job") {
  return page.prefillCard({
    form, track, uploads: [{ category: "lebenslauf-bisher", name: "cv.pdf", size: 10, datei: "dokumente/lebenslauf-bisher/cv.pdf" }],
    messages: [], run, hasName: true, notes: {}, announcement: "", estimate: ESTIMATE,
    titleOf: (id) => id, onRun() {}, onGoTo() {}, onAddFiles() {}, onChangeKind() {}, onRemove() {}, onByHand() {}, onEstimate() {},
  });
}

const byId = (node, id) => findAll(node, (n) => n.id === id)[0];
const parentOf = (root, child) => findAll(root, (n) => n.children.includes(child))[0];

test("while running the button is busy and the running text stands right after the buttons", () => {
  const node = card({ ...IDLE, running: true, minutes: 1 });
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

test("a problem of the run is an alert right under the buttons, above the line", () => {
  const node = card({ ...IDLE, problem: "Vor der ersten KI-Nutzung braucht es die Einwilligung." });
  const problem = byId(node, "prefill-problem");
  assert.equal(problem.getAttribute("role"), "alert");
  assert.match(problem.textContent, /Einwilligung/);
  const row = parentOf(node, problem);
  const actions = parentOf(node, byId(node, "prefill"));
  assert.equal(row.children[row.children.indexOf(problem) - 1], actions);
  assert.equal(row.children[row.children.indexOf(problem) + 1], byId(node, "prefill-status"));
});

test("before running there is no busy state", () => {
  const node = card(IDLE);
  assert.equal(byId(node, "prefill").disabled, undefined);
  assert.equal(byId(node, "prefill").getAttribute("aria-busy"), null);
  assert.doesNotMatch(byId(node, "prefill-status").textContent, /werden gelesen/);
});

function flow({ pending = null, current = () => true } = {}) {
  const log = [];
  const run = page.startPrefill({
    show: () => log.push(["show"]),
    reveal: () => log.push(["reveal"]),
    pendingUploads: () => pending,
    isCurrent: current,
    ask: async () => { log.push(["ask"]); return { suggestions: {} }; },
  });
  return { log, run };
}

test("the busy state shows and is brought into view before anything is awaited", async () => {
  const { log, run } = flow();
  assert.deepEqual(log.slice(0, 2), [["show"], ["reveal"]]); // synchronous: no request, no upload holds it up
  assert.deepEqual(await run, { suggestions: {} });
  assert.deepEqual(log, [["show"], ["reveal"], ["ask"]]);
});

test("a kind saved on this very click is in the data folder before the app is asked", async () => {
  let done;
  const pending = new Promise((resolve) => { done = resolve; });
  const { log, run } = flow({ pending });
  await new Promise((resolve) => setImmediate(resolve));
  assert.deepEqual(log, [["show"], ["reveal"]]);
  done();
  await run;
  assert.deepEqual(log, [["show"], ["reveal"], ["ask"]]);
});

test("a run overtaken while uploads finish asks nothing", async () => {
  const { log, run } = flow({ pending: Promise.resolve(), current: () => false });
  assert.equal(await run, null);
  assert.ok(!log.some(([step]) => step === "ask"));
});
