// When the line before „Vorbefüllen“ is estimated again (G85, #271): after every add, remove and settled kind change,
// once the files are in the data folder; never while uploads or kinds are still on their way. appuploads.js and
// appestimate.js with the state of app.js stood in for. Invented file names only.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { loadScripts } = require("./fake_dom.cjs");

const SRC = path.join(__dirname, "..", "src");
const form = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "form.json"), "utf8"));
const SCRIPTS = ["../../bewerbungen/seiten/dateien-logik.js", "validate.js", "model.js", "dom.js", "documents.js",
  "uploads.js", "kindguess.js", "droparea.js"];
const SETTLE_MS = 500;
const ANSWER = { anzahl: 1, kosten: 0.04, dauer_minuten: 1, waehrung: "USD", guthaben: null, danach: null, nicht_gelesen: [], gekuerzt: [] };

// The parts of app.js that appuploads.js and appestimate.js use; the backend answers when the test says so.
const APP_STATE = `
  let form = FORM; let state = { track: "job" }; let uploads = []; let uploadsUnderway = 0; let step = 0;
  const steps = () => [{ kind: "start" }];
  const estimated = []; const phases = [];
  function setUploads(list, messages) { uploads = list; }
  let uploadTurn = Promise.resolve();
  function inTurn(work) { uploadTurn = uploadTurn.then(work); return uploadTurn; }
  function focusFirst() {}
  function prefillCardContext() { return null; }
  const backend = {
    estimatePrefill: (track) => { estimated.push(track); return ESTIMATE_ANSWER(); },
    addDocument: async (track, category, name) => {
      await UPLOAD_DONE();
      return { unterlagen: [...uploads, { category, name, size: 10, datei: "dokumente/" + category + "/" + name }] };
    },
    removeDocument: async (datei) => ({ unterlagen: uploads.filter((u) => u.datei !== datei) }),
    changeDocumentKind: async (track, datei, category) => {
      const moved = "dokumente/" + category + "/" + datei.split("/").pop();
      return { datei: moved, unterlagen: uploads.map((u) => u.datei === datei ? { ...u, category, datei: moved } : u) };
    },
  };`;

function sandbox(files, { answer = async () => ANSWER, uploadDone = async () => {} } = {}) {
  let now = 0;
  let timers = [];
  const clock = {
    setTimeout: (run, ms) => { const t = { run, at: now + ms }; timers.push(t); return t; },
    clearTimeout: (t) => { timers = timers.filter((other) => other !== t); },
  };
  const page = loadScripts(SCRIPTS, { window: clock, FORM: form, ESTIMATE_ANSWER: answer, UPLOAD_DONE: uploadDone });
  page.document.getElementById = () => null;
  page.document.querySelector = () => null; // no page drawn: only the state is kept
  vm.runInContext(APP_STATE, page);
  for (const name of ["appuploads.js", "appestimate.js"]) {
    vm.runInContext(fs.readFileSync(path.join(SRC, name), "utf8"), page, { filename: name });
  }
  page.UPLOADS = files;
  vm.runInContext("uploads = UPLOADS", page);
  const read = (name) => JSON.parse(JSON.stringify(vm.runInContext(name, page)));
  const settle = async () => { for (let i = 0; i < 10; i += 1) await new Promise((resolve) => setImmediate(resolve)); };
  const advance = async (ms) => {
    now += ms;
    const due = timers.filter((t) => t.at <= now);
    timers = timers.filter((t) => t.at > now);
    for (const t of due) await t.run();
    await settle();
  };
  return { page, read, advance, settle };
}

const SCAN = { category: "zertifikate", name: "Scan_001.pdf", size: 10, datei: "dokumente/zertifikate/Scan_001.pdf" };
const file = (name) => ({ name, size: 10, arrayBuffer: async () => new ArrayBuffer(10) });

test("after files are added the line is estimated, and not while they upload", async () => {
  let finish;
  const arrived = new Promise((resolve) => { finish = resolve; });
  const { page, read, settle } = sandbox([], { uploadDone: () => arrived });
  const added = page.addDroppedFiles([file("Lebenslauf_Erika_Beispiel.pdf")]);
  await settle();
  assert.equal(read("prefillEstimate").phase, "uploading");
  assert.deepEqual(read("estimated"), []);
  finish();
  await added;
  await settle();
  assert.deepEqual(read("estimated"), ["job"]);
  assert.deepEqual(read("prefillEstimate"), { phase: "ready", answer: ANSWER, problem: null });
});

test("after a removal the line is estimated again", async () => {
  const { page, read, settle } = sandbox([SCAN, { ...SCAN, name: "cv.pdf", datei: "dokumente/zertifikate/cv.pdf" }]);
  await page.removeDroppedUpload(0);
  await settle();
  assert.equal(read("estimated").length, 1);
  assert.equal(read("prefillEstimate").phase, "ready");
});

test("a kind change is estimated once it settled, not at every step of the arrows", async () => {
  const { page, read, advance } = sandbox([SCAN]);
  for (const category of ["zeugnisse", "anschreiben-bisher", "lebenslauf-bisher"]) {
    page.changeUploadKind(SCAN, category);
    await advance(SETTLE_MS / 5);
    assert.equal(read("prefillEstimate").phase, "estimating");
  }
  assert.deepEqual(read("estimated"), []);
  await advance(SETTLE_MS);
  assert.equal(read("estimated").length, 1);
  assert.equal(read("prefillEstimate").phase, "ready");
});

test("a kind arrowed back to where it was is estimated again too, so the run is not left disabled", async () => {
  const { page, read, advance } = sandbox([SCAN]);
  page.changeUploadKind(SCAN, "zeugnisse");
  page.changeUploadKind(SCAN, "zertifikate");
  await advance(SETTLE_MS);
  assert.equal(read("prefillEstimate").phase, "ready");
});

test("a failed estimate keeps its reason, and estimating again replaces it", async () => {
  let fail = true;
  const { page, read, settle } = sandbox([SCAN], { answer: async () => {
    if (fail) throw new Error("Die App antwortet nicht. Läuft sie noch?");
    return ANSWER;
  } });
  page.requestEstimate();
  await settle();
  assert.deepEqual(read("prefillEstimate"), { phase: "failed", answer: null, problem: "Die App antwortet nicht. Läuft sie noch?" });
  fail = false;
  page.requestEstimate();
  await settle();
  assert.equal(read("prefillEstimate").phase, "ready");
});

test("an answer overtaken by a later change does not count", async () => {
  const answers = [];
  const { page, read, settle } = sandbox([SCAN], { answer: () => new Promise((resolve) => { answers.push(resolve); }) });
  page.requestEstimate();
  await settle();
  page.requestEstimate();
  await settle();
  answers[0]({ ...ANSWER, anzahl: 9 });
  await settle();
  assert.equal(read("prefillEstimate").phase, "estimating");
  answers[1](ANSWER);
  await settle();
  assert.equal(read("prefillEstimate").answer.anzahl, 1);
});

test("without files there is nothing to estimate", async () => {
  const { page, read, settle } = sandbox([]);
  page.requestEstimate();
  await settle();
  assert.deepEqual(read("estimated"), []);
  assert.equal(read("prefillEstimate").phase, "none");
});
