// Only in the page „Meine Angaben“ of the app (G84, design A8): one area for all documents, each file filed under the
// kind kindguess.js guesses, one row per file to correct it. File names are only ever set as text.
// Depends on dom.js, documents.js, uploads.js and kindguess.js (inlined before this file by build_template.py).
"use strict";

// Said when they are shown, so they follow the app language (#433).
const DROP_TEXT = {
  job: {
    intro: () => T("Lebenslauf, Zeugnisse, Zertifikate und frühere Anschreiben, alles zusammen. Die KI liest sie und füllt nur leere Felder. Sie prüfen jeden Abschnitt."),
    hint: () => T("PDF, Word, Text oder Bild. Die App ordnet jede Datei selbst ein, Sie können das ändern."),
    image: () => T("Bild: bleibt auf Ihrem Computer, die KI liest es nicht."),
    full: (values) => T("{title}: höchstens {maxFiles} Dateien. Entfernen Sie zuerst eine.", values),
  },
  apprenticeship: {
    intro: () => T("Lebenslauf, Zeugnisse, Zertifikate und frühere Motivationsschreiben, alles zusammen. Die KI liest sie und füllt nur leere Felder. Du prüfst jeden Abschnitt."),
    hint: () => T("PDF, Word, Text oder Bild. Die App ordnet jede Datei selbst ein, du kannst das ändern."),
    image: () => T("Bild: bleibt auf deinem Computer, die KI liest es nicht."),
    full: (values) => T("{title}: höchstens {maxFiles} Dateien. Entferne zuerst eine.", values),
  },
};
const DROP_WORDS = {
  area: () => T("Dateien hierher ziehen"),
  choose: () => T("Dateien wählen"),
  remove: () => T("Entfernen"),
  sure: () => T("Am Namen erkannt"),
  unsure: () => T("Nicht sicher erkannt, bitte prüfen"),
  oldWord: () => T("Altes Word-Format: die KI liest es nicht. Als PDF speichern und neu hochladen."),
  unreadable: () => T("Die Datei liess sich nicht lesen. Bitte nochmals wählen."),
};
const OLD_WORD_EXTENSION = "doc";
const DROP_CARD = ".prefill-card";
const CHOOSE_ID = "drop-choose";

/** A file named with what is wrong with it: „programm.exe: Dieser Dateityp geht nicht. …“. */
const fileMessage = (name, problem) => T("{datei}: {fehler}", { datei: name, fehler: problem });

/** Every file type of the area, e.g. „PDF, Word (.docx, .doc), Textdateien (.txt), Bilder (.jpg, .png)“. */
function allTypesText(form) {
  return Object.values(form.documents.fileTypes).flatMap((type) => type.labels).map((label) => T(label)).join(", ");
}

function allExtensions(form) {
  return Object.values(form.documents.fileTypes).flatMap((type) => type.extensions);
}

/** Today's message for a rule (DOCUMENT_MESSAGES), without the kind in front. */
function documentText(form, code) {
  const rules = form.documents;
  const message = DOCUMENT_MESSAGES[code];
  return message ? message({
    maxFileMB: Math.floor(rules.maxFileBytes / BYTES_PER_MB), maxTotalMB: Math.floor(rules.maxTotalBytes / BYTES_PER_MB),
    allowed: allTypesText(form),
  }) : code;
}

/** Why a file cannot come in whatever its kind; null if it may. */
function fileProblem(form, taken, entry) {
  const rules = form.documents;
  if (!new RegExp(rules.namePattern, "u").test(entry.name)) return documentText(form, "name");
  if (!allExtensions(form).includes(documentExtension(entry.name))) return documentText(form, "extension");
  if (!Number.isInteger(entry.size) || entry.size <= 0 || entry.size > rules.maxFileBytes) return documentText(form, "size");
  if (taken.some((u) => u.name.toLowerCase() === entry.name.toLowerCase())) return documentText(form, "duplicate");
  return null;
}

/**
 * Which dropped or chosen files (each { name, size }) to add, each under the kind of its guess, checked against the
 * rules together with what is there. Returns { accepted: [{ index, category, name, size, sure }], messages }: one line
 * per refused file, and one per kind whose limit left files out.
 */
function planDrop(form, track, current, chosen) {
  const accepted = [];
  const messages = [];
  const leftOut = new Map();
  chosen.forEach((file, index) => {
    const name = safeDocumentName(file.name);
    const problem = fileProblem(form, [...current, ...accepted], { name, size: file.size });
    if (problem) return messages.push(fileMessage(name, problem));
    const { category, sure } = guessDocumentKind(form, name);
    const entries = [...current, ...accepted, { category, name, size: file.size }]
      .map(({ category: c, name: n, size }) => ({ category: c, name: n, size }));
    const [error] = validateDocuments(form, entries).filter((e) => isAbout(e, entries.length - 1, category));
    if (error && error.code === "maxFiles") return leftOut.set(category, (leftOut.get(category) || 0) + 1);
    if (error) return messages.push(fileMessage(name, documentText(form, error.code)));
    accepted.push({ index, category, name, size: file.size, sure });
    return null;
  });
  const limits = [...leftOut].map(([category, count]) => dropLeftOut(form, track, category, count));
  return { accepted, messages: [...messages, ...limits] };
}

/** „Lebensläufe“ and „10“ for „Lebensläufe: höchstens 10 Dateien. …“: the kind in the plural, not a section title. */
function kindLimit(form, track, category) {
  return { title: kindPlural(form, track, category), maxFiles: documentCategories(form).get(category).maxFiles };
}

function dropLeftOut(form, track, category, count) {
  const values = { ...kindLimit(form, track, category), count };
  return count === 1 ? DOCUMENT_MESSAGES.leftOutOne(values) : DOCUMENT_MESSAGES.leftOutMany(values);
}

function kindFailed(reason) {
  return T("Die Art liess sich nicht ändern: {grund}", { grund: reason });
}

/** Why a file cannot change to a kind, before anything moves; null if it can. */
function kindChangeProblem(form, track, uploads, upload, category) {
  const target = documentCategories(form).get(category);
  if (!target) return kindFailed(DOCUMENT_MESSAGES.category());
  if (!allowedExtensions(form, target).includes(documentExtension(upload.name))) {
    return kindFailed(DOCUMENT_MESSAGES.extension({ allowed: allowedText(form, target) }));
  }
  const { count, maxFiles } = categoryRoom(form, uploads, category);
  if (count < maxFiles) return null;
  return DROP_TEXT[track].full(kindLimit(form, track, category));
}

function addedStatus(form, track, added) {
  const files = added.map((u) => T("{datei} als {art}", { datei: u.name, art: kindInSentence(form, track, u.category) }));
  return T("Hinzugefügt: {dateien}.", { dateien: files.join(", ") });
}

function changedStatus(form, track, name, category) {
  return T("{datei} ist jetzt als {art} eingeordnet.", { datei: name, art: kindInQuotes(form, track, category) });
}

function removedStatus(name) {
  return T("{datei} entfernt.", { datei: name });
}

/** The select of a row, to give it the focus again after the page is drawn anew. */
const kindSelector = (datei) => `select[data-datei="${String(datei).replace(/["\\]/g, "\\$&")}"]`;
const CHOOSE_SELECTOR = `#${CHOOSE_ID}`;

/** The area with „Dateien wählen“: one dialog for several files of every allowed type. */
function dropAreaView(ctx) {
  const accept = allExtensions(ctx.form).map((ext) => `.${ext}`).join(",");
  const input = el("input", {
    type: "file", multiple: true, accept, className: "visually-hidden", tabIndex: -1, "aria-hidden": "true",
    onchange: (e) => ctx.onAddFiles(e.target.files),
  });
  return el("div", { className: "drop-area" }, [
    el("p", { className: "drop-area__text" }, DROP_WORDS.area()),
    el("button", { type: "button", id: CHOOSE_ID, className: "drop-area__choose", onclick: () => input.click() }, DROP_WORDS.choose()),
    input,
  ]);
}

/** Files dropped on the card are added; the browser must not open them instead. */
function dropHandlers(ctx) {
  const dragging = (card, on) => {
    if (card && card.dataset) card.dataset.dragging = on ? "true" : "";
  };
  return {
    ondragover: (e) => {
      e.preventDefault();
      if (e.dataTransfer) e.dataTransfer.dropEffect = "copy";
      dragging(e.currentTarget, true);
    },
    ondragleave: (e) => {
      const card = e.currentTarget;
      if (card && !(e.relatedTarget && card.contains(e.relatedTarget))) dragging(card, false);
    },
    ondrop: (e) => {
      e.preventDefault();
      dragging(e.currentTarget, false);
      const files = e.dataTransfer && e.dataTransfer.files;
      if (files && files.length) ctx.onAddFiles(files);
    },
  };
}

/** Outside the card a dropped file would replace the page; the page takes no drop there. */
function guardPageDrops(doc) {
  const outside = (e) => !(e.target && typeof e.target.closest === "function" && e.target.closest(DROP_CARD));
  doc.addEventListener("dragover", (e) => {
    if (!outside(e)) return;
    e.preventDefault();
    if (e.dataTransfer) e.dataTransfer.dropEffect = "none";
  });
  doc.addEventListener("drop", (e) => e.preventDefault());
}

function rowNotes(ctx, upload) {
  const guess = ctx.notes[upload.datei];
  const ext = documentExtension(upload.name);
  return [
    guess === undefined ? null : el("p", { className: "drop-file__note" }, guess ? DROP_WORDS.sure() : DROP_WORDS.unsure()),
    isImageName(ctx.form, upload.name) ? el("p", { className: "drop-file__note" }, DROP_TEXT[ctx.track].image()) : null,
    ext === OLD_WORD_EXTENSION ? el("p", { className: "drop-file__note" }, DROP_WORDS.oldWord()) : null,
  ];
}

function kindSelect(ctx, upload) {
  const options = kindOptions(ctx.form, ctx.track, upload.name).map((option) => el("option", {
    value: option.id, selected: option.id === upload.category,
  }, option.label));
  return el("select", {
    className: "drop-file__kind", "aria-label": T("Art von {datei}", { datei: upload.name }), dataset: { datei: upload.datei },
    onchange: (e) => ctx.onChangeKind(upload, e.target.value), onblur: () => ctx.onLeaveKind(upload),
  }, options);
}

/** A file name wraps after „_“, „-“ and „.“ first, so „Lebenslauf_Erika_Beispiel.pdf“ breaks between its words. */
function nameWithBreaks(name) {
  // No lookbehind: Safari before 16.4 refuses it while parsing, and with it the whole inlined script.
  return String(name).match(/[^_.\-]*[_.\-]?/g).filter(Boolean).flatMap((part, i) => (i ? [el("wbr", {}), part] : [part]));
}

function fileRowView(ctx, upload, index) {
  return el("li", { className: "drop-file" }, [
    el("div", { className: "drop-file__info" }, [
      el("span", { className: "drop-file__name" }, nameWithBreaks(upload.name)),
      el("span", { className: "drop-file__size" }, formatSize(upload.size)),
      ...rowNotes(ctx, upload),
    ]),
    el("div", { className: "drop-file__actions" }, [
      kindSelect(ctx, upload),
      el("button", {
        type: "button", className: "remove", "aria-label": T("{name} entfernen", { name: upload.name }),
        onclick: () => ctx.onRemove(index),
      }, DROP_WORDS.remove()),
    ]),
  ]);
}

function dropFilesView(ctx) {
  return ctx.uploads.length ? el("ul", { className: "drop-files" }, ctx.uploads.map((u, i) => fileRowView(ctx, u, i))) : null;
}
