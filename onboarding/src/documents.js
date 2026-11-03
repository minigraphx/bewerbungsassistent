// Rules for uploaded documents, for the browser. Mirrors documents.py; both run the shared
// "documentCases" in tests/cases.json. An entry is { category, name, size }.
"use strict";

const BYTES_PER_MB = 1000000;
const MAX_NAME_CHARS = 120;
const FALLBACK_NAME = "unterlage";
const DOCUMENT_MESSAGES = {
  type: "Unerwarteter Eintrag.",
  category: "Unbekannte Art von Unterlage.",
  name: "Ungültiger Dateiname.",
  extension: "Dieser Dateityp geht nicht. Erlaubt sind {allowed}.",
  size: "Die Datei ist zu gross (höchstens {maxFileMB} MB).",
  duplicate: "Diese Datei ist schon dabei.",
  maxFiles: "Zu viele Dateien (höchstens {maxFiles}).",
  total: "Zusammen sind die Dateien zu gross (höchstens {maxTotalMB} MB).",
};

const titleForTrack = (value, track) => (value !== null && typeof value === "object" ? value[track] : value);
const isDocumentObject = (v) => v !== null && typeof v === "object" && !Array.isArray(v);
const isSize = (v) => typeof v === "number" && Number.isInteger(v) && v > 0;

function documentCategories(form) {
  return new Map(form.documents.categories.map((c) => [c.id, c]));
}

function documentExtension(name) {
  const dot = name.lastIndexOf(".");
  return dot < 0 ? "" : name.slice(dot + 1).toLowerCase();
}

/** File extensions a category accepts, from its file types (e.g. images only for certificates). */
function allowedExtensions(form, category) {
  const types = form.documents.fileTypes;
  return category.fileTypes.flatMap((t) => types[t].extensions);
}

/** German list of the accepted file types, e.g. „PDF, Word (.docx, .doc) und Textdateien (.txt)“. */
function allowedText(form, category) {
  const types = form.documents.fileTypes;
  const labels = category.fileTypes.flatMap((t) => types[t].labels);
  return labels.length === 1 ? labels[0] : `${labels.slice(0, -1).join(", ")} und ${labels[labels.length - 1]}`;
}

function validateDocuments(form, entries) {
  if (!Array.isArray(entries)) return [{ path: "documents", code: "type" }];
  const rules = form.documents;
  const known = documentCategories(form);
  const errors = [];
  const seen = new Set();
  const counts = new Map();
  let total = 0;
  entries.forEach((entry, index) => {
    const code = documentEntryError(form, known, entry, seen);
    if (code) errors.push({ path: `documents.${index}`, code });
    if (isDocumentObject(entry) && typeof entry.category === "string" && known.has(entry.category)) {
      counts.set(entry.category, (counts.get(entry.category) || 0) + 1);
    }
    if (isDocumentObject(entry) && isSize(entry.size)) total += entry.size;
  });
  for (const [id, count] of counts) {
    if (count > known.get(id).maxFiles) errors.push({ path: `documents.${id}`, code: "maxFiles" });
  }
  if (total > rules.maxTotalBytes) errors.push({ path: "documents", code: "total" });
  return errors;
}

function documentEntryError(form, known, entry, seen) {
  const rules = form.documents;
  if (!isDocumentObject(entry)) return "type";
  const { category, name, size } = entry;
  if (typeof category !== "string" || !known.has(category)) return "category";
  if (typeof name !== "string" || !new RegExp(rules.namePattern, "u").test(name)) return "name";
  if (!allowedExtensions(form, known.get(category)).includes(documentExtension(name))) return "extension";
  if (!isSize(size) || size > rules.maxFileBytes) return "size";
  const key = `${category}/${name.toLowerCase()}`;
  if (seen.has(key)) return "duplicate";
  seen.add(key);
  return null;
}

/** German message: category and file name, then what is wrong. */
function describeDocument(form, track, entries, error) {
  const rules = form.documents;
  const known = documentCategories(form);
  const parts = error.path.split(".");
  const params = {
    maxFileMB: Math.floor(rules.maxFileBytes / BYTES_PER_MB),
    maxTotalMB: Math.floor(rules.maxTotalBytes / BYTES_PER_MB),
    maxFiles: "?",
    allowed: "?",
  };
  let where = "";
  if (parts.length === 2 && known.has(parts[1])) {
    const category = known.get(parts[1]);
    params.maxFiles = category.maxFiles;
    where = titleForTrack(category.title, track);
  } else if (parts.length === 2 && /^[0-9]+$/.test(parts[1]) && Number(parts[1]) < entries.length) {
    const entry = entries[Number(parts[1])];
    if (isDocumentObject(entry)) {
      const category = typeof entry.category === "string" ? known.get(entry.category) : undefined;
      if (category) params.allowed = allowedText(form, category);
      where = [category ? titleForTrack(category.title, track) : "", entry.name]
        .filter((n) => typeof n === "string" && n).join(", ");
    }
  }
  const text = (DOCUMENT_MESSAGES[error.code] || error.code).replace(/\{(\w+)\}/g, (_, k) => params[k]);
  return where ? `${where}: ${text}` : text;
}

/** A file name from the person's computer, made safe: no folders, no special characters, at most 120 characters. */
function safeDocumentName(raw) {
  const base = String(raw).normalize("NFC").split(/[\\/]/).pop();
  let name = base.replace(/[:*?"<>|\u0000-\u001f\u007f]/g, "-").replace(/^[.\s]+/, "").replace(/[.\s]+$/, "");
  if (!/[^\-.\s]/.test(name)) return FALLBACK_NAME;
  const chars = Array.from(name);
  if (chars.length <= MAX_NAME_CHARS) return name;
  const ext = documentExtension(name);
  const suffix = ext && ext.length < 10 ? `.${ext}` : "";
  return chars.slice(0, MAX_NAME_CHARS - suffix.length).join("").replace(/[.\s]+$/, "") + suffix;
}

// Uploads in the template: which chosen files to take, and the ZIP layout shared with archive.py.

const UPLOAD_BUNDLE = "einstieg.json";
const UPLOAD_DIR = "dokumente";

/** A ZIP that is no file of this template; the message is German and shown as is. */
class UploadError extends Error {}

/**
 * Which of the chosen files (each { name, size }) to add to a category, checked against the rules
 * together with what is already there. Returns { accepted: [{ index, category, name, size }], messages }.
 */
function planUploads(form, track, current, category, chosen) {
  const accepted = [];
  const messages = [];
  chosen.forEach((file, index) => {
    const entry = { category, name: safeDocumentName(file.name), size: file.size };
    const entries = [...current, ...accepted, entry].map(({ category: c, name, size }) => ({ category: c, name, size }));
    const [error] = validateDocuments(form, entries).filter((e) => isAbout(e, entries.length - 1, category));
    if (error) messages.push(describeDocument(form, track, entries, error)); // one message per file is enough
    else accepted.push({ index, ...entry });
  });
  return { accepted, messages };
}

function isAbout(error, last, category) {
  return error.path === `documents.${last}` || error.path === `documents.${category}` || error.path === "documents";
}

/** ZIP entries for the saved file: the answers plus each upload under dokumente/<category>/<name>. */
function uploadZipEntries(bundleBytes, uploads) {
  return [
    { name: UPLOAD_BUNDLE, data: bundleBytes },
    ...uploads.map((u) => ({ name: `${UPLOAD_DIR}/${u.category}/${u.name}`, data: u.data })),
  ];
}

/** Split the entries of a loaded ZIP into the answers (bytes) and uploads; throws UploadError. */
function splitUploadZip(form, entries) {
  const bundles = entries.filter((e) => e.name === UPLOAD_BUNDLE);
  if (bundles.length !== 1) throw new UploadError(`Die Datei muss genau eine ${UPLOAD_BUNDLE} enthalten.`);
  const uploads = entries.filter((e) => e.name !== UPLOAD_BUNDLE).map((e) => {
    const parts = e.name.split("/");
    if (parts.length !== 3 || parts[0] !== UPLOAD_DIR) throw new UploadError(`Unerwarteter Inhalt in der Datei: ${e.name}`);
    return { category: parts[1], name: parts[2], size: e.data.length, data: e.data };
  });
  const [error] = validateDocuments(form, uploads.map(({ category, name, size }) => ({ category, name, size })));
  if (error) throw new UploadError(describeDocument(form, "job", uploads, error));
  return { bundle: bundles[0].data, uploads };
}

/** Most entries a saved ZIP can have: the answers plus the most files of every category. */
function maxUploadEntries(form) {
  return 1 + form.documents.categories.reduce((sum, c) => sum + c.maxFiles, 0);
}

if (typeof module !== "undefined") {
  module.exports = {
    validateDocuments, describeDocument, safeDocumentName, documentCategories, documentExtension, allowedExtensions, allowedText,
    planUploads, uploadZipEntries, splitUploadZip, maxUploadEntries, UploadError,
  };
}
