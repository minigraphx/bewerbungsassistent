// Only in the page „Meine Angaben“ of the app (G84, design A8): one area for all documents, each file filed under the
// kind kindguess.js guesses, one row per file to correct it. File names are only ever set as text.
// Depends on dom.js, documents.js, uploads.js and kindguess.js (inlined before this file by build_template.py).
"use strict";

const DROP_TEXT = {
  job: {
    intro: "Lebenslauf, Zeugnisse, Zertifikate und frühere Anschreiben, alles zusammen. Die KI liest sie und füllt nur leere Felder. Sie prüfen jeden Abschnitt.",
    hint: "PDF, Word, Text oder Bild. Die App ordnet jede Datei selbst ein, Sie können das ändern.",
    image: "Bild: bleibt auf Ihrem Computer, die KI liest es nicht.",
    firstRemove: "Entfernen Sie zuerst eine.",
  },
  apprenticeship: {
    intro: "Lebenslauf, Zeugnisse, Zertifikate und frühere Motivationsschreiben, alles zusammen. Die KI liest sie und füllt nur leere Felder. Du prüfst jeden Abschnitt.",
    hint: "PDF, Word, Text oder Bild. Die App ordnet jede Datei selbst ein, du kannst das ändern.",
    image: "Bild: bleibt auf deinem Computer, die KI liest es nicht.",
    firstRemove: "Entferne zuerst eine.",
  },
};
const DROP_WORDS = {
  area: "Dateien hierher ziehen",
  choose: "Dateien wählen",
  remove: "Entfernen",
  sure: "Am Namen erkannt",
  unsure: "Nicht sicher erkannt, bitte prüfen",
  oldWord: "Altes Word-Format: die KI liest es nicht. Als PDF speichern und neu hochladen.",
  unreadable: "Die Datei liess sich nicht lesen. Bitte nochmals wählen.",
};
const OLD_WORD_EXTENSION = "doc";
const DROP_CARD = ".prefill-card";
const CHOOSE_ID = "drop-choose";

const fillIn = (template, params) => template.replace(/\{(\w+)\}/g, (_, key) => params[key]);

/** Every file type of the area, e.g. „PDF, Word (.docx, .doc), Textdateien (.txt), Bilder (.jpg, .png)“. */
function allTypesText(form) {
  return Object.values(form.documents.fileTypes).flatMap((type) => type.labels).join(", ");
}

function allExtensions(form) {
  return Object.values(form.documents.fileTypes).flatMap((type) => type.extensions);
}

/** Today's message for a rule (DOCUMENT_MESSAGES), without the kind in front. */
function documentText(form, code) {
  const rules = form.documents;
  return fillIn(DOCUMENT_MESSAGES[code] || code, {
    maxFileMB: Math.floor(rules.maxFileBytes / BYTES_PER_MB), maxTotalMB: Math.floor(rules.maxTotalBytes / BYTES_PER_MB),
    allowed: allTypesText(form),
  });
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
    if (problem) return messages.push(`${name}: ${problem}`);
    const { category, sure } = guessDocumentKind(form, name);
    const entries = [...current, ...accepted, { category, name, size: file.size }]
      .map(({ category: c, name: n, size }) => ({ category: c, name: n, size }));
    const [error] = validateDocuments(form, entries).filter((e) => isAbout(e, entries.length - 1, category));
    if (error && error.code === "maxFiles") return leftOut.set(category, (leftOut.get(category) || 0) + 1);
    if (error) return messages.push(`${name}: ${documentText(form, error.code)}`);
    accepted.push({ index, category, name, size: file.size, sure });
    return null;
  });
  const limits = [...leftOut].map(([category, count]) => dropLeftOut(form, track, category, count));
  return { accepted, messages: [...messages, ...limits] };
}

/** „Lebensläufe: höchstens 10 Dateien.“: the kind in the plural, not the title of a section of the saved file. */
function kindLimit(form, track, category) {
  return `${kindPlural(form, track, category)}: höchstens ${documentCategories(form).get(category).maxFiles} Dateien.`;
}

function dropLeftOut(form, track, category, count) {
  return `${kindLimit(form, track, category)} ${count === 1 ? "Eine Datei wurde" : `${count} Dateien wurden`} nicht hinzugefügt.`;
}

function kindFailed(reason) {
  return `Die Art liess sich nicht ändern: ${reason}`;
}

/** Why a file cannot change to a kind, before anything moves; null if it can. */
function kindChangeProblem(form, track, uploads, upload, category) {
  const target = documentCategories(form).get(category);
  if (!target) return kindFailed(DOCUMENT_MESSAGES.category);
  if (!allowedExtensions(form, target).includes(documentExtension(upload.name))) {
    return kindFailed(fillIn(DOCUMENT_MESSAGES.extension, { allowed: allowedText(form, target) }));
  }
  const { count, maxFiles } = categoryRoom(form, uploads, category);
  if (count < maxFiles) return null;
  return `${kindLimit(form, track, category)} ${DROP_TEXT[track].firstRemove}`;
}

function addedStatus(form, track, added) {
  return `Hinzugefügt: ${added.map((u) => `${u.name} als ${kindInSentence(form, track, u.category)}`).join(", ")}.`;
}

function changedStatus(form, track, name, category) {
  return `${name} ist jetzt als ${kindInSentence(form, track, category)} eingeordnet.`;
}

function removedStatus(name) {
  return `${name} entfernt.`;
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
    el("p", { className: "drop-area__text" }, DROP_WORDS.area),
    el("button", { type: "button", id: CHOOSE_ID, className: "drop-area__choose", onclick: () => input.click() }, DROP_WORDS.choose),
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
    guess === undefined ? null : el("p", { className: "drop-file__note" }, guess ? DROP_WORDS.sure : DROP_WORDS.unsure),
    isImageName(ctx.form, upload.name) ? el("p", { className: "drop-file__note" }, DROP_TEXT[ctx.track].image) : null,
    ext === OLD_WORD_EXTENSION ? el("p", { className: "drop-file__note" }, DROP_WORDS.oldWord) : null,
  ];
}

function kindSelect(ctx, upload) {
  const options = kindOptions(ctx.form, ctx.track, upload.name).map((option) => el("option", {
    value: option.id, selected: option.id === upload.category,
  }, option.label));
  return el("select", {
    className: "drop-file__kind", "aria-label": `Art von ${upload.name}`, dataset: { datei: upload.datei },
    onchange: (e) => ctx.onChangeKind(upload, e.target.value),
  }, options);
}

/** A file name wraps after „_“, „-“ and „.“ first, so „Lebenslauf_Erika_Beispiel.pdf“ breaks between its words. */
function nameWithBreaks(name) {
  return String(name).split(/(?<=[_.\-])/).flatMap((part, i) => (i ? [el("wbr", {}), part] : [part]));
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
        type: "button", className: "remove", "aria-label": `${upload.name} entfernen`, onclick: () => ctx.onRemove(index),
      }, DROP_WORDS.remove),
    ]),
  ]);
}

function dropFilesView(ctx) {
  return ctx.uploads.length ? el("ul", { className: "drop-files" }, ctx.uploads.map((u, i) => fileRowView(ctx, u, i))) : null;
}
