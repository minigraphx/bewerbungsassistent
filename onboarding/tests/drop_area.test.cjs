// One drop area on „Meine Angaben“ (G84, #270): the app guesses the kind of each file from its name, the person
// corrects it per row. Invented file names only.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { findAll, loadScripts } = require("./fake_dom.cjs");

const form = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "form.json"), "utf8"));
const SHARED_LOGIC = "../../bewerbungen/seiten/dateien-logik.js";
const SCRIPTS = [SHARED_LOGIC, "validate.js", "model.js", "dom.js", "documents.js", "uploads.js", "kindguess.js",
  "droparea.js", "prefill.js"];
const page = loadScripts(SCRIPTS);
const IDLE = { running: false, waiting: false, problem: null, report: null };
const MB = 1000000;
// Values from the sandbox have its own prototypes; compare them as plain data.
const same = (actual, expected, message) => assert.deepEqual(JSON.parse(JSON.stringify(actual)), expected, message);

const CV = "lebenslauf-bisher";
const REFERENCE = "zeugnisse";
const CERTIFICATE = "zertifikate";
const LETTER = "anschreiben-bisher";

// name → [category, recognised by name]
const GUESSES = [
  ["Lebenslauf_2025.pdf", CV, true],
  ["CV-Muster.docx", CV, true],
  ["cv.txt", CV, true],
  ["Curriculum Vitae.pdf", CV, true],
  ["Résumé Erika.pdf", CV, true],
  ["resume.doc", CV, true],
  ["LinkedIn_Export.pdf", CV, true],
  ["Profile.pdf", CV, true],
  ["Lebenslauf_und_Zeugnisse.pdf", CV, true],
  ["Anschreiben_Muster_AG.pdf", LETTER, true],
  ["Bewerbungsschreiben.docx", LETTER, true],
  ["Motivationsschreiben-Beispiel.pdf", LETTER, true],
  ["Motivationsbrief.txt", LETTER, true],
  ["Begleitschreiben.pdf", LETTER, true],
  ["Cover_Letter.docx", LETTER, true],
  ["coverletter.pdf", LETTER, true],
  ["Lettre de motivation.pdf", LETTER, true],
  ["Diplom_Kauffrau.pdf", CERTIFICATE, true],
  ["Fähigkeitszeugnis_EFZ.pdf", CERTIFICATE, true],
  ["Faehigkeitszeugnis.pdf", CERTIFICATE, true],
  ["Maturitätszeugnis.pdf", CERTIFICATE, true],
  ["Bachelor-Urkunde.pdf", CERTIFICATE, true],
  ["Zertifikat_Excel.pdf", CERTIFICATE, true],
  ["Zertifizierung.pdf", CERTIFICATE, true],
  ["Certificate.png", CERTIFICATE, true],
  ["Kursbestätigung_Erste_Hilfe.pdf", CERTIFICATE, true],
  ["Teilnahmebestaetigung.pdf", CERTIFICATE, true],
  ["Sprachdiplom.pdf", CERTIFICATE, true],
  ["Goethe_B2.jpg", CERTIFICATE, true],
  ["DELF_B1.png", CERTIFICATE, true],
  ["DALF.pdf", CERTIFICATE, true],
  ["Cambridge_First.pdf", CERTIFICATE, true],
  ["TOEFL.pdf", CERTIFICATE, true],
  ["IELTS_Ergebnis.pdf", CERTIFICATE, true],
  ["Multicheck.pdf", CERTIFICATE, true],
  ["Stellwerk-Test.pdf", CERTIFICATE, true],
  ["Basic-Check.pdf", CERTIFICATE, true],
  ["Arbeitszeugnis_Muster_AG.pdf", REFERENCE, true],
  ["Zwischenzeugnis.docx", REFERENCE, true],
  ["Zeugnis_Scan.jpg", REFERENCE, true],
  ["Referenzschreiben.pdf", REFERENCE, true],
  ["Arbeitsbestätigung.pdf", REFERENCE, true],
  ["Reference_Letter.pdf", REFERENCE, true],
  ["Schnupperlehre_Bericht.pdf", REFERENCE, true],
  ["Schnuppertag.png", REFERENCE, true],
  ["Bewerbung_Muster.pdf", CERTIFICATE, false],
  ["MyCVnotes.pdf", CERTIFICATE, false],
  ["Scan_001.pdf", CERTIFICATE, false],
  ["Lebenslauf.jpg", CERTIFICATE, false],
  ["Anschreiben.png", CERTIFICATE, false],
];

test("the kind of a file is guessed from its name in the order of the brief", () => {
  for (const [name, category, sure] of GUESSES) {
    same({ ...page.guessDocumentKind(form, name) }, { category, sure }, name);
  }
});

test("the guess folds case, umlauts and separators and leaves out the extension", () => {
  assert.equal(page.foldDocumentName("Kurs-Bestätigung_Zürich.PDF"), "kurs bestatigung zurich");
  assert.equal(page.foldDocumentName("Résumé.v2.docx"), "resume v2");
  assert.equal(page.guessDocumentKind(form, "notes.cv").sure, false); // the extension is no name
});

test("the guess reuses the names of Lebenslauf und Dateien, not a copy of them", () => {
  const source = fs.readFileSync(path.join(__dirname, "..", "src", "kindguess.js"), "utf8");
  assert.match(source, /DateienLogik\.DIPLOMA_NAME/);
  assert.match(source, /DateienLogik\.REFERENCE_NAME/);
  assert.doesNotMatch(source, /f\(\?:ä\|ae\|a\)higkeitszeugnis/);
});

test("guessing sends nothing: no AI, no request, nothing but the name", () => {
  const calls = [];
  const trap = (what) => (...args) => { calls.push(what); throw new Error(`${what} must not be used`); };
  class Trapped { constructor() { trap("XMLHttpRequest")(); } }
  const sandbox = loadScripts(SCRIPTS, {
    fetch: trap("fetch"), XMLHttpRequest: Trapped, WebSocket: Trapped, EventSource: Trapped,
    navigator: { sendBeacon: trap("sendBeacon") }, createAppBackend: trap("createAppBackend"),
  });
  for (const [name] of GUESSES) sandbox.guessDocumentKind(form, name);
  sandbox.planDrop(form, "job", [], GUESSES.map(([name]) => ({ name, size: 10 })));
  same(calls, []);
  for (const file of ["kindguess.js", "droparea.js"]) {
    const source = fs.readFileSync(path.join(__dirname, "..", "src", file), "utf8");
    assert.doesNotMatch(source, /fetch\(|XMLHttpRequest|sendBeacon|WebSocket|backend|vorbefuellen|\.prefill\(/i, file);
  }
});

test("each kind offers only what its file type allows, in the words of the track", () => {
  const labels = (track, name) => page.kindOptions(form, track, name).map((o) => `${o.id}=${o.label}`);
  same(labels("job", "a.pdf"), [
    `${CV}=Lebenslauf`, `${REFERENCE}=Zeugnis`, `${CERTIFICATE}=Zertifikat oder Diplom`, `${LETTER}=Früheres Anschreiben`]);
  same(labels("apprenticeship", "a.docx"), [
    `${CV}=Lebenslauf`, `${REFERENCE}=Zeugnis oder Bericht`, `${CERTIFICATE}=Zertifikat oder Diplom`,
    `${LETTER}=Früheres Motivationsschreiben`]);
  for (const track of ["job", "apprenticeship"]) {
    same(page.kindOptions(form, track, "a.jpg").map((o) => o.id), [REFERENCE, CERTIFICATE]);
  }
});

test("a drop puts each file into the category of its guess", () => {
  const { accepted, messages } = page.planDrop(form, "job", [], [
    { name: "Lebenslauf_2025.pdf", size: 10 }, { name: "Zeugnis_Muster.pdf", size: 20 }, { name: "Scan.png", size: 30 }]);
  same(messages, []);
  same(accepted.map((a) => [a.index, a.category, a.name, a.size, a.sure]), [
    [0, CV, "Lebenslauf_2025.pdf", 10, true], [1, REFERENCE, "Zeugnis_Muster.pdf", 20, true], [2, CERTIFICATE, "Scan.png", 30, false]]);
});

test("each refused file has its own line with today's message, the other files of the drop stay", () => {
  const current = [{ category: REFERENCE, name: "Arbeitszeugnis.pdf", size: 10, datei: "dokumente/zeugnisse/Arbeitszeugnis.pdf" }];
  const { accepted, messages } = page.planDrop(form, "job", current, [
    { name: "Programm.exe", size: 10 },
    { name: "Gross.pdf", size: 15 * MB + 1 },
    { name: "arbeitszeugnis.pdf", size: 10 },
    { name: "Lebenslauf.pdf", size: 10 },
  ]);
  same(accepted.map((a) => a.name), ["Lebenslauf.pdf"]);
  same(messages, [
    "Programm.exe: Dieser Dateityp geht nicht. Erlaubt sind PDF, Word (.docx, .doc), Textdateien (.txt), Bilder (.jpg, .png).",
    "Gross.pdf: Die Datei ist zu gross (höchstens 15 MB).",
    "arbeitszeugnis.pdf: Diese Datei ist schon dabei.",
  ]);
});

test("the limit of each kind and of all files together still holds", () => {
  for (const { id, maxFiles } of form.documents.categories) {
    same([id, maxFiles], [id, { [CV]: 10, [REFERENCE]: 20, [CERTIFICATE]: 30, [LETTER]: 10 }[id]]);
  }
  const references = Array.from({ length: 19 }, (_, i) => ({ category: REFERENCE, name: `Zeugnis ${i}.pdf`, size: 10 }));
  const full = page.planDrop(form, "job", references, [
    { name: "Zeugnis A.pdf", size: 10 }, { name: "Zeugnis B.pdf", size: 10 }, { name: "Lebenslauf.pdf", size: 10 }]);
  same(full.accepted.map((a) => a.name), ["Zeugnis A.pdf", "Lebenslauf.pdf"]);
  same(full.messages, ["Zeugnisse: höchstens 20 Dateien. Eine Datei wurde nicht hinzugefügt."]);

  const big = Array.from({ length: 4 }, (_, i) => ({ category: CERTIFICATE, name: `Diplom ${i}.pdf`, size: 14 * MB }));
  const total = page.planDrop(form, "job", big, [{ name: "Diplom 9.pdf", size: 5 * MB }, { name: "cv.txt", size: 10 }]);
  same(total.accepted.map((a) => a.name), ["cv.txt"]);
  same(total.messages, ["Diplom 9.pdf: Zusammen sind die Dateien zu gross (höchstens 60 MB)."]);
});

function card(uploads, extra = {}) {
  return page.prefillCard({
    form, track: "job", uploads, messages: [], run: IDLE, hasName: true, notes: {}, announcement: "",
    titleOf: (id) => id, onRun() {}, onGoTo() {}, onAddFiles() {}, onChangeKind() {}, onRemove() {}, onByHand() {},
    ...extra,
  });
}

const byTag = (node, tag) => findAll(node, (n) => n.tagName === tag);
const byId = (node, id) => findAll(node, (n) => n.id === id)[0];

test("without files the card has intro, one area and its hint, and „Lieber von Hand ausfüllen“ leads", () => {
  for (const [track, intro, hint] of [
    ["job", "Lebenslauf, Zeugnisse, Zertifikate und frühere Anschreiben, alles zusammen. Die KI liest sie und füllt nur leere Felder. Sie prüfen jeden Abschnitt.",
      "PDF, Word, Text oder Bild. Die App ordnet jede Datei selbst ein, Sie können das ändern."],
    ["apprenticeship", "Lebenslauf, Zeugnisse, Zertifikate und frühere Motivationsschreiben, alles zusammen. Die KI liest sie und füllt nur leere Felder. Du prüfst jeden Abschnitt.",
      "PDF, Word, Text oder Bild. Die App ordnet jede Datei selbst ein, du kannst das ändern."],
  ]) {
    const node = card([], { track });
    const paragraphs = byTag(node, "p").map((p) => p.textContent).filter(Boolean);
    same(paragraphs, [intro, "Dateien hierher ziehen", hint], track);
    assert.equal(byTag(node, "fieldset").length, 0);
    assert.equal(byId(node, "prefill"), undefined);
    const buttons = byTag(node, "button");
    same(buttons.map((b) => b.textContent), ["Dateien wählen", "Lieber von Hand ausfüllen"]);
    assert.equal(buttons[1].className, "primary");
    assert.equal(buttons[0].type, "button");
    assert.equal(buttons[0].id, "drop-choose");
    assert.equal(buttons[0].tabIndex, undefined); // reachable by Tab like any button
  }
});

test("one file dialog takes several files of every allowed type", () => {
  const added = [];
  const node = card([], { onAddFiles: (files) => added.push(files) });
  const inputs = byTag(node, "input");
  assert.equal(inputs.length, 1);
  assert.equal(inputs[0].type, "file");
  assert.equal(inputs[0].multiple, true);
  assert.equal(inputs[0].accept, ".pdf,.docx,.doc,.txt,.jpg,.jpeg,.png");
  let opened = 0;
  inputs[0].click = () => { opened += 1; };
  byId(node, "drop-choose").onclick();
  assert.equal(opened, 1);
  inputs[0].onchange({ target: { files: ["chosen"] } });
  same(added, [["chosen"]]);
});

test("files dropped on the card are added and the browser does not open them", () => {
  const added = [];
  const node = card([], { onAddFiles: (files) => added.push(files) });
  const prevented = [];
  const event = (files) => ({ preventDefault: () => prevented.push(true), dataTransfer: { files, dropEffect: "" }, relatedTarget: null });
  const over = event([]);
  node.ondragover(over);
  assert.equal(over.dataTransfer.dropEffect, "copy");
  node.ondrop(event(["a.pdf", "b.pdf"]));
  node.ondrop(event([]));
  same(added, [["a.pdf", "b.pdf"]]);
  assert.equal(prevented.length, 3);
});

test("a file dropped elsewhere on the page never navigates away", () => {
  const listeners = {};
  const doc = { addEventListener: (type, handler) => { listeners[type] = handler; } };
  page.guardPageDrops(doc);
  for (const type of ["dragover", "drop"]) {
    let prevented = false;
    const transfer = { dropEffect: "copy" };
    listeners[type]({ preventDefault: () => { prevented = true; }, dataTransfer: transfer, target: { closest: () => null } });
    assert.equal(prevented, true, type);
    if (type === "dragover") assert.equal(transfer.dropEffect, "none");
  }
});

const uploads = [
  { category: CV, name: "Lebenslauf_2025.pdf", size: 120000, datei: "dokumente/lebenslauf-bisher/Lebenslauf_2025.pdf" },
  { category: CERTIFICATE, name: "Scan_001.pdf", size: 2500000, datei: "dokumente/zertifikate/Scan_001.pdf" },
  { category: REFERENCE, name: "Zeugnis_Scan.jpg", size: 900000, datei: "dokumente/zeugnisse/Zeugnis_Scan.jpg" },
  { category: LETTER, name: "Anschreiben_alt.doc", size: 40000, datei: "dokumente/anschreiben-bisher/Anschreiben_alt.doc" },
];
const notes = { [uploads[0].datei]: true, [uploads[1].datei]: false };

test("each row has name, size, how it was recognised, a labelled kind and „Entfernen“", () => {
  const node = card(uploads, { notes });
  const rows = byTag(node, "li");
  assert.equal(rows.length, 4);
  const [cv, scan, image, word] = rows;
  assert.match(cv.textContent, /^Lebenslauf_2025\.pdf120 KBAm Namen erkannt/);
  assert.match(scan.textContent, /Scan_001\.pdf2[.,]5 MBNicht sicher erkannt, bitte prüfen/);
  assert.doesNotMatch(image.textContent, /erkannt/); // filed before: nothing about the guess
  assert.match(image.textContent, /Bild: bleibt auf Ihrem Computer, die KI liest es nicht\./);
  assert.match(word.textContent, /Altes Word-Format: die KI liest es nicht\. Als PDF speichern und neu hochladen\./);
  const selects = byTag(node, "select");
  same(selects.map((s) => s.getAttribute("aria-label")), uploads.map((u) => `Art von ${u.name}`));
  same(byTag(selects[2], "option").map((o) => o.textContent), ["Zeugnis", "Zertifikat oder Diplom"]);
  same(selects.map((s) => byTag(s, "option").find((o) => o.selected).value), uploads.map((u) => u.category));
  same(rows.map((r) => byTag(r, "button").map((b) => b.textContent)), [["Entfernen"], ["Entfernen"], ["Entfernen"], ["Entfernen"]]);
  const image2 = card(uploads, { track: "apprenticeship" });
  assert.match(byTag(image2, "li")[2].textContent, /Bild: bleibt auf deinem Computer, die KI liest es nicht\./);
});

test("changing the kind and removing go to the page, with the row they belong to", () => {
  const changed = [];
  const removed = [];
  const node = card(uploads, { onChangeKind: (upload, category) => changed.push([upload.name, category]), onRemove: (i) => removed.push(i) });
  const select = byTag(node, "select")[1];
  select.onchange({ target: { value: REFERENCE } });
  byTag(byTag(node, "li")[3], "button")[0].onclick();
  same(changed, [["Scan_001.pdf", REFERENCE]]);
  same(removed, [3]);
  assert.equal(select.dataset.datei, uploads[1].datei);
});

test("with files the run button comes and the announcements have their own status region", () => {
  const node = card(uploads, { announcement: "Scan_001.pdf entfernt.", messages: ["x.exe: Dieser Dateityp geht nicht."] });
  assert.equal(byId(node, "prefill").textContent, "Vorbefüllen");
  assert.equal(byId(node, "upload-status").getAttribute("role"), "status");
  assert.equal(byId(node, "upload-status").textContent, "Scan_001.pdf entfernt.");
  assert.equal(byId(node, "upload-messages").getAttribute("role"), "alert");
  same(byTag(byId(node, "upload-messages"), "p").map((p) => p.textContent), ["x.exe: Dieser Dateityp geht nicht."]);
});

test("adding, changing and removing are announced in words", () => {
  assert.equal(page.addedStatus(form, "job", [{ name: "Lebenslauf_2025.pdf", category: CV }, { name: "Zeugnis_Muster.pdf", category: REFERENCE }]),
    "Hinzugefügt: Lebenslauf_2025.pdf als Lebenslauf, Zeugnis_Muster.pdf als Zeugnis.");
  assert.equal(page.changedStatus(form, "job", "Scan_001.pdf", REFERENCE), "Scan_001.pdf ist jetzt als Zeugnis eingeordnet.");
  assert.equal(page.changedStatus(form, "apprenticeship", "Scan_001.pdf", REFERENCE), "Scan_001.pdf ist jetzt als Zeugnis oder Bericht eingeordnet.");
  assert.equal(page.removedStatus("Scan_001.pdf"), "Scan_001.pdf entfernt.");
  assert.equal(page.kindFailed("Die App antwortet nicht."), "Die Art liess sich nicht ändern: Die App antwortet nicht.");
});

test("a change to a full or forbidden kind is refused before anything moves", () => {
  const references = Array.from({ length: 20 }, (_, i) => ({ category: REFERENCE, name: `Zeugnis ${i}.pdf`, size: 10 }));
  const scan = { category: CERTIFICATE, name: "Scan.pdf", size: 10, datei: "dokumente/zertifikate/Scan.pdf" };
  assert.equal(page.kindChangeProblem(form, "job", [...references, scan], scan, REFERENCE),
    "Zeugnisse: höchstens 20 Dateien. Entfernen Sie zuerst eine.");
  assert.equal(page.kindChangeProblem(form, "apprenticeship", [...references, scan], scan, REFERENCE),
    "Zeugnisse: höchstens 20 Dateien. Entferne zuerst eine.");
  const photo = { category: CERTIFICATE, name: "Foto.jpg", size: 10, datei: "dokumente/zertifikate/Foto.jpg" };
  assert.equal(page.kindChangeProblem(form, "job", [photo], photo, CV),
    "Die Art liess sich nicht ändern: Dieser Dateityp geht nicht. Erlaubt sind PDF, Word (.docx, .doc) und Textdateien (.txt).");
  assert.equal(page.kindChangeProblem(form, "job", [scan], scan, CV), null);
});

test("the card keeps every control at least 44 px, the rows wrap at 375 px and stay one line at 1280 px", () => {
  const css = fs.readFileSync(path.join(__dirname, "..", "src", "droparea.css"), "utf8");
  assert.match(css, /\.prefill-card :is\(button, select\)[^{]*\{[^}]*min-height: 44px;[^}]*min-width: 44px;/);
  assert.match(css, /\.drop-file__name[^{]*\{[^}]*overflow-wrap: anywhere;/);
  assert.match(css, /\.drop-file \{[^}]*flex-wrap: wrap;/);
  assert.match(css, /\.drop-status, \.prefill-card #upload-messages \{ overflow-wrap: anywhere; \}/);
});
