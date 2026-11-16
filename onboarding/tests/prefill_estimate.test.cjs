// Cost and time before „Vorbefüllen“ (G85, #271): the line under the button, in its states, worded like „Alle prüfen“
// (TrefferLogik.estimateLine, G44), in CHF with the credit of the mediation (G46, G80). Invented file names only.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { findAll, loadScripts } = require("./fake_dom.cjs");

const form = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "form.json"), "utf8"));
const page = loadScripts(["../../bewerbungen/seiten/dateien-logik.js", "../../bewerbungen/seiten/treffer-logik.js",
  "../../bewerbungen/seiten/texte.js", "validate.js", "model.js", "dom.js", "documents.js", "uploads.js", "kindguess.js",
  "droparea.js", "prefill.js"]);
const IDLE = { running: false, problem: null, report: null };
const UPLOADS = [
  { category: "lebenslauf-bisher", name: "Lebenslauf_Erika_Beispiel.pdf", size: 10, datei: "dokumente/lebenslauf-bisher/Lebenslauf_Erika_Beispiel.pdf" },
  { category: "zeugnisse", name: "Zeugnis_Beispiel_AG.pdf", size: 10, datei: "dokumente/zeugnisse/Zeugnis_Beispiel_AG.pdf" },
];
const ANSWER = { anzahl: 2, kosten: 0.04, dauer_minuten: 1, waehrung: "USD", guthaben: null, danach: null, nicht_gelesen: [], gekuerzt: [] };
const VIA_MEDIATION = { ...ANSWER, waehrung: "CHF", guthaben: 4.25, danach: 4.21 };
const ready = (answer) => ({ phase: "ready", answer, problem: null });

function card({ estimate = ready(ANSWER), run = IDLE, track = "job", hasName = true, onEstimate = () => {} } = {}) {
  return page.prefillCard({
    form, track, uploads: UPLOADS, messages: [], run, hasName, notes: {}, announcement: "", estimate,
    titleOf: (id) => id, onRun() {}, onGoTo() {}, onAddFiles() {}, onChangeKind() {}, onRemove() {}, onByHand() {}, onEstimate,
  });
}

const byId = (node, id) => findAll(node, (n) => n.id === id)[0];
const parentOf = (root, child) => findAll(root, (n) => n.children.includes(child))[0];
const status = (node) => byId(node, "prefill-status");
const files = (node) => byId(node, "prefill-files");
const paragraphs = (node) => findAll(status(node), (n) => n.tagName === "p").map((p) => p.textContent);
const fileParagraphs = (node) => findAll(files(node), (n) => n.tagName === "p").map((p) => p.textContent);
const items = (node) => findAll(files(node), (n) => n.tagName === "li").map((li) => li.textContent);
const buttonsNamed = (node, name) => findAll(node, (n) => n.tagName === "button" && n.textContent === name);
const estimating = (more = {}) => ({ phase: "estimating", answer: null, problem: null, held: null, slow: true, ...more });

test("the line stands right under the button, in a status the button points to with the file lists", () => {
  const node = card();
  const button = byId(node, "prefill");
  const line = status(node);
  assert.equal(line.getAttribute("role"), "status");
  assert.equal(button.getAttribute("aria-describedby"), "prefill-status prefill-files");
  const actions = parentOf(node, button);
  const row = parentOf(node, actions);
  assert.equal(row.children[row.children.indexOf(actions) + 1], line);
  assert.equal(row.children[row.children.indexOf(line) + 1], files(node));
  assert.notEqual(button.disabled, true);
});

test("the status holds only the sentences: the file lists stand beside it and are not read out at each change", () => {
  const answer = { ...ANSWER, anzahl: 1, nicht_gelesen: [{ name: "Zeugnis_Scan.png", grund: "Bild: bleibt hier." }],
    gekuerzt: ["Lebenslauf_Erika_Beispiel.pdf"] };
  const node = card({ estimate: ready(answer) });
  assert.deepEqual(findAll(status(node), (n) => n.tagName === "ul"), []);
  assert.equal(findAll(files(node), (n) => n.tagName === "ul").length, 2);
  assert.equal(files(node).getAttribute("role"), null);
  assert.equal(files(node).getAttribute("aria-live"), null);
});

test("the status is busy while files upload or the estimate is pending, and not otherwise", () => {
  const busy = (estimate) => status(card({ estimate })).getAttribute("aria-busy");
  assert.equal(busy({ phase: "uploading", answer: null, problem: null }), "true");
  assert.equal(busy(estimating()), "true");
  assert.equal(busy(estimating({ slow: false, held: ready(ANSWER) })), "true");
  assert.equal(busy(ready(ANSWER)), null);
  assert.equal(busy({ phase: "failed", answer: null, problem: "Die App antwortet nicht." }), null);
});

test("for the first moment of estimating again the old figures stay, with the run disabled", () => {
  const node = card({ estimate: estimating({ slow: false, held: ready(ANSWER) }) });
  assert.deepEqual(paragraphs(node), ["2 Dateien gehen an die KI. Etwa USD\u00a00.04 und 1\u00a0Minute."]);
  assert.equal(byId(node, "prefill").disabled, true);
  const none = { ...ANSWER, anzahl: 0, kosten: 0 };
  assert.equal(byId(card({ estimate: estimating({ slow: false, held: ready(none) }) }), "prefill"), undefined);
  assert.deepEqual(paragraphs(card({ estimate: estimating({ slow: false }) })), []);
  assert.deepEqual(paragraphs(card({ estimate: estimating({ held: ready(ANSWER) }) })), ["Kosten und Dauer werden geschätzt …"]);
});

test("it names the files for the AI and cost and time worded exactly as „Alle prüfen“", () => {
  for (const track of ["job", "apprenticeship"]) {
    assert.deepEqual(paragraphs(card({ track })), ["2 Dateien gehen an die KI. Etwa USD\u00a00.04 und 1\u00a0Minute."]);
    const one = { ...ANSWER, anzahl: 1, kosten: 0.12, dauer_minuten: 3 };
    assert.deepEqual(paragraphs(card({ track, estimate: ready(one) })),
      [`1 Datei geht an die KI. ${page.TrefferLogik.estimateLine(one)}`]);
  }
});

test("with the mediation it is in CHF and says what stays of the credit, as „Alle prüfen“ does", () => {
  const lines = paragraphs(card({ estimate: ready(VIA_MEDIATION) }));
  assert.deepEqual(lines, ["2 Dateien gehen an die KI. Etwa CHF\u00a00.04 und 1\u00a0Minute.", "Danach bleiben CHF\u00a04.21 im Guthaben."]);
  assert.equal(lines.join(" "), `2 Dateien gehen an die KI. ${page.TrefferLogik.estimateLine({ ...VIA_MEDIATION, reicht_fuer: null })}`);
});

test("an estimate above the credit left warns, and the run stays possible", () => {
  const node = card({ estimate: ready({ ...VIA_MEDIATION, guthaben: 0.02, danach: 0 }) });
  assert.deepEqual(paragraphs(node), ["2 Dateien gehen an die KI. Etwa CHF\u00a00.04 und 1\u00a0Minute.",
    "Im Guthaben sind noch CHF 0.02, das reicht vielleicht nicht."]);
  assert.notEqual(byId(node, "prefill").disabled, true);
});

test("a used-up credit says so with a link to request a new code, and the run is disabled", () => {
  const node = card({ estimate: ready({ ...VIA_MEDIATION, guthaben: 0, danach: 0 }) });
  // the link names that it opens a new tab, for screen readers only
  assert.equal(paragraphs(node)[1], "Das Guthaben ist aufgebraucht: neuen Code anfordern, öffnet neuen Tab.");
  const link = findAll(status(node), (n) => n.tagName === "a")[0];
  assert.equal(link.href, page.Texte.CODE_REQUEST_URL);
  assert.match(link.textContent, /^anfordern/);
  assert.match(paragraphs(node)[1], /^Das Guthaben ist aufgebraucht: neuen Code anfordern/);
  assert.equal(byId(node, "prefill").disabled, true);
});

test("while files are uploading or the estimate is pending, the run waits with the reason", () => {
  for (const track of ["job", "apprenticeship"]) {
    const uploading = card({ track, estimate: { phase: "uploading", answer: null, problem: null } });
    assert.deepEqual(paragraphs(uploading), ["Die Dateien werden noch hochgeladen. Danach nennt die App Kosten und Dauer."]);
    assert.equal(byId(uploading, "prefill").disabled, true);
    const pending = card({ track, estimate: estimating() });
    assert.deepEqual(paragraphs(pending), ["Kosten und Dauer werden geschätzt …"]);
    assert.equal(byId(pending, "prefill").disabled, true);
  }
});

test("while the very first files upload the line says so already, without a run button yet", () => {
  const node = page.prefillCard({
    form, track: "job", uploads: [], messages: [], run: IDLE, hasName: true, notes: {}, announcement: "",
    estimate: { phase: "uploading", answer: null, problem: null }, titleOf: (id) => id,
    onRun() {}, onGoTo() {}, onAddFiles() {}, onChangeKind() {}, onRemove() {}, onByHand() {}, onEstimate() {},
  });
  assert.deepEqual(paragraphs(node), ["Die Dateien werden noch hochgeladen. Danach nennt die App Kosten und Dauer."]);
  assert.equal(byId(node, "prefill"), undefined);
});

test("files that will not go to the AI or only in part are named with today's reasons", () => {
  const answer = { ...ANSWER, anzahl: 1, nicht_gelesen: [{ name: "Zeugnis_Scan.png", grund: "Bild: bleibt hier." }],
    gekuerzt: ["Lebenslauf_Erika_Beispiel.pdf"] };
  const node = card({ estimate: ready(answer) });
  assert.deepEqual(paragraphs(node), ["1 Datei geht an die KI. Etwa USD\u00a00.04 und 1\u00a0Minute."]);
  assert.deepEqual(fileParagraphs(node), ["Geht nicht an die KI:", "Nur der Anfang geht an die KI, die Datei ist zu lang:"]);
  assert.deepEqual(items(node), ["Zeugnis_Scan.png: Bild: bleibt hier.", "Lebenslauf_Erika_Beispiel.pdf"]);
});

test("when no file can be read there is no run button, only filling in by hand", () => {
  const none = { ...ANSWER, anzahl: 0, kosten: 0, nicht_gelesen: [{ name: "Scan.png", grund: "Bild." }] };
  const texts = {
    job: "Keine dieser Dateien geht an die KI. Bilder, Scans und alte Word-Dateien ergänzen Sie von Hand.",
    apprenticeship: "Keine dieser Dateien geht an die KI. Bilder, Scans und alte Word-Dateien ergänzt du von Hand.",
  };
  for (const [track, text] of Object.entries(texts)) {
    const node = card({ track, estimate: ready(none) });
    assert.equal(byId(node, "prefill"), undefined);
    assert.deepEqual(paragraphs(node), [text]);
    assert.deepEqual(fileParagraphs(node), ["Geht nicht an die KI:"]);
    assert.equal(buttonsNamed(node, "Lieber von Hand ausfüllen")[0].className, "primary");
  }
});

test("a failed estimate names the reason, offers to estimate again and keeps the run disabled", () => {
  let asked = 0;
  const node = card({ estimate: { phase: "failed", answer: null, problem: "Die App antwortet nicht." }, onEstimate: () => { asked += 1; } });
  assert.equal(paragraphs(node)[0], "Die Schätzung fehlt: Die App antwortet nicht.");
  assert.equal(byId(node, "prefill").disabled, true);
  const again = buttonsNamed(status(node), "Neu schätzen")[0];
  assert.equal(again.type, "button");
  again.click();
  assert.equal(asked, 1);
});

test("while running, the text names the estimated minutes", () => {
  const texts = {
    job: "Die Unterlagen werden gelesen. Das dauert etwa 2 Minuten; Sie können in dieser Zeit weiterarbeiten.",
    apprenticeship: "Die Unterlagen werden gelesen. Das dauert etwa 2 Minuten; du kannst in dieser Zeit weiterarbeiten.",
  };
  for (const [track, text] of Object.entries(texts)) {
    const node = card({ track, run: { ...IDLE, running: true, minutes: 2 }, estimate: ready({ ...ANSWER, dauer_minuten: 2 }) });
    assert.deepEqual(paragraphs(node), [text]);
    assert.equal(byId(node, "prefill").disabled, true);
  }
  const one = card({ run: { ...IDLE, running: true, minutes: 1 } });
  assert.match(paragraphs(one)[0], /Das dauert etwa 1 Minute;/);
});

test("a failed run says why in an alert of its own, above the line", () => {
  const node = card({ run: { ...IDLE, problem: "Vor der ersten KI-Nutzung braucht es die Einwilligung." } });
  const problem = byId(node, "prefill-problem");
  assert.equal(problem.getAttribute("role"), "alert");
  assert.match(problem.textContent, /Einwilligung/);
  assert.deepEqual(paragraphs(node), ["2 Dateien gehen an die KI. Etwa USD\u00a00.04 und 1\u00a0Minute."]);
});
