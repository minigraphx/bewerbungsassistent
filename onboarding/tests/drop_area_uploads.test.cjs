// What the drop area on „Meine Angaben“ does with the data folder (G84, #270): appuploads.js with the state of app.js
// stood in for. Invented file names only.
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

// The parts of app.js that appuploads.js uses; the backend only records what it is asked.
const APP_STATE = `
  let form = FORM; let state = { track: "job" }; let uploads = []; let uploadsUnderway = 0; let step = 0;
  const steps = () => [{ kind: "start" }];
  const drawn = []; const moves = []; const focused = [];
  function setUploads(list, messages) { uploads = list; drawn.push(messages); }
  let uploadTurn = Promise.resolve();
  function inTurn(work) { uploadTurn = uploadTurn.then(work); return uploadTurn; }
  function focusFirst(...selectors) { focused.push(selectors[0]); }
  const backend = {
    changeDocumentKind: async (track, datei, category) => {
      moves.push(category);
      const name = datei.split("/").pop();
      const moved = "dokumente/" + category + "/" + name;
      return { datei: moved, unterlagen: uploads.map((u) => u.datei === datei ? { ...u, category, datei: moved } : u) };
    },
    addDocument: async () => { throw new Error("not expected"); },
  };`;

/** A sandbox with a clock of its own: timers run only when the test moves it on. */
function sandbox(files) {
  let now = 0;
  let timers = [];
  const clock = {
    setTimeout: (run, ms) => { const t = { run, at: now + ms }; timers.push(t); return t; },
    clearTimeout: (t) => { timers = timers.filter((other) => other !== t); },
  };
  const page = loadScripts(SCRIPTS, { window: clock, FORM: form });
  page.document.getElementById = () => null; // no page drawn: the announcement is only kept
  vm.runInContext(APP_STATE, page);
  vm.runInContext(fs.readFileSync(path.join(SRC, "appuploads.js"), "utf8"), page, { filename: "appuploads.js" });
  page.UPLOADS = files;
  vm.runInContext("uploads = UPLOADS", page);
  const read = (name) => JSON.parse(JSON.stringify(vm.runInContext(name, page)));
  const advance = async (ms) => {
    now += ms;
    const due = timers.filter((t) => t.at <= now);
    timers = timers.filter((t) => t.at > now);
    for (const t of due) await t.run();
    await new Promise((resolve) => setImmediate(resolve));
  };
  return { page, read, advance };
}

const SCAN = { category: "zertifikate", name: "Scan_001.pdf", size: 10, datei: "dokumente/zertifikate/Scan_001.pdf" };

test("arrowing through the kinds moves the file once, to the kind it settles on", async () => {
  const { page, read, advance } = sandbox([SCAN]);
  for (const category of ["zeugnisse", "anschreiben-bisher", "lebenslauf-bisher"]) {
    page.changeUploadKind(SCAN, category);
    await advance(SETTLE_MS / 5);
  }
  assert.deepEqual(read("moves"), []);
  await advance(SETTLE_MS);
  assert.deepEqual(read("moves"), ["lebenslauf-bisher"]);
  assert.equal(read("uploadAnnouncement"), "Scan_001.pdf ist jetzt als Lebenslauf eingeordnet.");
  assert.deepEqual(read("uploads").map((u) => u.category), ["lebenslauf-bisher"]);
});

test("arrowing back to the kind it had moves nothing and says nothing", async () => {
  const { page, read, advance } = sandbox([SCAN]);
  page.changeUploadKind(SCAN, "zeugnisse");
  page.changeUploadKind(SCAN, "zertifikate");
  await advance(SETTLE_MS);
  assert.deepEqual(read("moves"), []);
  assert.equal(read("uploadAnnouncement"), "");
});

test("a full kind passed on the way is no refusal, only the kind it settles on counts", async () => {
  const references = Array.from({ length: 20 }, (_, i) => ({
    category: "zeugnisse", name: `Zeugnis ${i}.pdf`, size: 10, datei: `dokumente/zeugnisse/Zeugnis ${i}.pdf` }));
  const { page, read, advance } = sandbox([...references, SCAN]);
  page.changeUploadKind(SCAN, "zeugnisse");
  page.changeUploadKind(SCAN, "lebenslauf-bisher");
  await advance(SETTLE_MS);
  assert.deepEqual(read("drawn").filter((messages) => messages.length), []);
  assert.deepEqual(read("moves"), ["lebenslauf-bisher"]);

  page.changeUploadKind(read("uploads")[20], "zeugnisse");
  await advance(SETTLE_MS);
  assert.deepEqual(read("drawn").pop(), ["Zeugnisse: höchstens 20 Dateien. Entfernen Sie zuerst eine."]);
  assert.deepEqual(read("moves"), ["lebenslauf-bisher"]);
});

test("leaving the select saves its kind at once, without the wait", async () => {
  const { page, read, advance } = sandbox([SCAN]);
  page.changeUploadKind(SCAN, "zeugnisse");
  await page.leaveUploadKind(SCAN);
  assert.deepEqual(read("moves"), ["zeugnisse"]);
  assert.equal(read("uploadAnnouncement"), "Scan_001.pdf ist jetzt als Zeugnis eingeordnet.");
  await advance(SETTLE_MS);
  assert.deepEqual(read("moves"), ["zeugnisse"]); // the wait that was running moves nothing more
  await page.leaveUploadKind(SCAN); // left again without a change: nothing to save
  assert.deepEqual(read("moves"), ["zeugnisse"]);
});

test("after a move saved on leaving, the focus stays where the person went, else on the select", async () => {
  const { page, read } = sandbox([SCAN]);
  const control = (label, id = "") => ({ id, closest: () => ({}), getAttribute: () => label });
  page.document.activeElement = control("Scan_001.pdf entfernen");
  page.changeUploadKind(SCAN, "zeugnisse");
  await page.leaveUploadKind(SCAN);
  assert.equal(read("focused").pop(), '[aria-label="Scan_001.pdf entfernen"]');

  const moved = read("uploads")[0];
  page.document.activeElement = control(null, "prefill");
  page.changeUploadKind(moved, "zertifikate");
  await page.leaveUploadKind(moved);
  assert.equal(read("focused").pop(), "#prefill");

  page.document.activeElement = { id: "", closest: () => null, getAttribute: () => null }; // left the card
  page.changeUploadKind(read("uploads")[0], "zeugnisse");
  await page.settlePendingKinds();
  assert.equal(read("focused").pop(), 'select[data-datei="dokumente/zeugnisse/Scan_001.pdf"]');
});

test("the prefill waits for a kind still waiting, and reads the file under its new kind", async () => {
  const { page, read } = sandbox([SCAN]);
  page.changeUploadKind(SCAN, "lebenslauf-bisher");
  const pending = page.pendingDocumentWork();
  assert.ok(pending, "the prefill has something to wait for");
  assert.equal(read("uploadsUnderway"), 1);
  await pending;
  assert.deepEqual(read("moves"), ["lebenslauf-bisher"]);
  assert.deepEqual(read("uploads").map((u) => u.category), ["lebenslauf-bisher"]);
  assert.equal(read("uploadsUnderway"), 0);
  assert.equal(page.pendingDocumentWork(), null); // nothing left to wait for
});

test("leaving the page saves every kind still waiting", async () => {
  const { page, read } = sandbox([SCAN]);
  page.changeUploadKind(SCAN, "zeugnisse");
  await page.settlePendingKinds();
  assert.deepEqual(read("moves"), ["zeugnisse"]);
});

test("a move saved while a button is pressed is drawn only after its click", async () => {
  const { page, read, advance } = sandbox([SCAN]);
  const listeners = {};
  page.trackPointer({ addEventListener: (type, handler) => { listeners[type] = handler; } });
  listeners.pointerdown();
  page.changeUploadKind(SCAN, "zeugnisse");
  const saved = page.leaveUploadKind(SCAN);
  await new Promise((resolve) => setImmediate(resolve));
  assert.deepEqual(read("moves"), ["zeugnisse"]); // saved at once
  assert.deepEqual(read("drawn"), []); // but not drawn while the button is down
  listeners.pointerup();
  await advance(0); // the click of this press comes first
  await saved;
  assert.deepEqual(read("drawn"), [[]]);
});

test("a drop that adds nothing clears what the status said before", async () => {
  const { page, read, advance } = sandbox([SCAN]);
  vm.runInContext("uploadAnnouncement = 'Hinzugefügt: Lebenslauf.pdf als Lebenslauf.'", page);
  await page.addDroppedFiles([{ name: "Programm.exe", size: 10 }]);
  await advance(SETTLE_MS);
  assert.equal(read("uploadAnnouncement"), "");
  assert.equal(read("drawn").pop().length, 1);
});
