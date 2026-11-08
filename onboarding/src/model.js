// Pure state handling of the onboarding template: no DOM, no storage.
// State: { track: "job" | "apprenticeship" | null, data: { [sectionId]: object | object[] } }.
// List fields hold arrays of lines; blank lines and empty items are dropped only when collecting.
"use strict";

/** A loaded file that is no bundle of this form; the message is German and shown as is. */
class BundleError extends Error {}

const isPlainObject = (v) => v !== null && typeof v === "object" && !Array.isArray(v);

function trackApplies(item, track) {
  return !item.tracks || item.tracks.includes(track);
}

/** Sections shown for a track, in form order. */
function sectionsFor(form, track) {
  return form.sections.filter((s) => trackApplies(s, track));
}

/** Fields of a section shown for a track. */
function fieldsFor(section, track) {
  return section.fields.filter((f) => trackApplies(f, track));
}

function linesToList(text) {
  return String(text).split(/\r?\n/);
}

function listToLines(list) {
  return Array.isArray(list) ? list.join("\n") : "";
}

/** Copy of an item with only known fields of the right type. */
function cleanItem(section, track, item, compact) {
  return pickFields(fieldsFor(section, track), item, compact);
}

function pickFields(fields, item, compact) {
  const result = {};
  if (!isPlainObject(item)) return result;
  for (const field of fields) {
    const value = item[field.id];
    if (field.type === "list") {
      if (!Array.isArray(value)) continue;
      const lines = value.filter((v) => typeof v === "string").map((v) => (compact ? v.trim() : v));
      const kept = compact ? lines.filter((v) => v) : lines;
      if (kept.length) result[field.id] = kept;
    } else if (typeof value === "string" && (!compact || value.trim())) {
      result[field.id] = compact ? value.trim() : value;
    }
  }
  return result;
}

function cleanData(form, track, data, compact) {
  const result = {};
  for (const section of sectionsFor(form, track)) {
    const value = isPlainObject(data) ? data[section.id] : undefined;
    if (section.repeat) {
      if (!Array.isArray(value)) continue;
      const list = value.map((item) => cleanItem(section, track, item, compact));
      const kept = compact ? list.filter((item) => Object.keys(item).length) : list;
      if (kept.length) result[section.id] = kept;
    } else if (isPlainObject(value)) {
      const item = cleanItem(section, track, value, compact);
      if (Object.keys(item).length) result[section.id] = item;
    }
  }
  return result;
}

/** The bundle written to einstieg.json: current track only, trimmed, without empty values. */
function collectBundle(form, state, now) {
  return {
    format: form.format,
    version: form.version,
    track: state.track,
    saved: now.toISOString(),
    data: cleanData(form, state.track, state.data, true),
  };
}

/** Bundle for live checks while typing: keeps item positions so error paths match the form. */
function draftBundle(form, state) {
  return { format: form.format, version: form.version, track: state.track, data: cleanData(form, state.track, state.data, false) };
}

/** True if a repeated item has no content yet (such items are dropped when saving). */
function isBlankItem(item) {
  if (!isPlainObject(item)) return true;
  return Object.values(item).every((v) => (Array.isArray(v) ? v.every((x) => !String(x).trim()) : !String(v ?? "").trim()));
}

/** State from a loaded file; throws an Error with a German message if it is no bundle of this form. */
function stateFromBundle(form, bundle) {
  const ok = isPlainObject(bundle) && bundle.format === form.format && bundle.version === form.version
    && typeof bundle.track === "string" && Object.prototype.hasOwnProperty.call(form.tracks, bundle.track);
  if (!ok) throw new BundleError("Die Datei ist keine Einstiegsdatei dieser Vorlage.");
  return { track: bundle.track, data: cleanData(form, bundle.track, bundle.data, false) };
}

/** New state with the value at path (e.g. ["work", 0, "position"]) replaced; creates missing containers. */
function setValue(state, path, value) {
  const update = (container, keys) => {
    const [key, ...rest] = keys;
    const base = container ?? (typeof key === "number" ? [] : {});
    const copy = Array.isArray(base) ? [...base] : { ...base };
    copy[key] = rest.length ? update(base[key], rest) : value;
    return copy;
  };
  return { ...state, data: update(state.data, path) };
}

function addItem(state, sectionId) {
  const list = Array.isArray(state.data[sectionId]) ? state.data[sectionId] : [];
  return { ...state, data: { ...state.data, [sectionId]: [...list, {}] } };
}

function removeItem(state, sectionId, index) {
  const list = state.data[sectionId] || [];
  const next = { ...state, data: { ...state.data, [sectionId]: list.filter((_, i) => i !== index) } };
  return state.suggested ? { ...next, suggested: shiftSuggestions(state.suggested, sectionId, index) } : next;
}

// Suggestions from documents (page of the app): state.suggested = { "work.0": { file, place }, "style": { file, place } }.
// A mark says „not checked yet“. It stays while the person edits, because changing one value says nothing about
// the others in the entry; it goes when the person confirms the entry or removes it.

function confirmSuggestions(state, keys) {
  const marks = Object.entries(state.suggested || {}).filter(([key]) => !keys.includes(key));
  return { ...state, suggested: Object.fromEntries(marks) };
}

/** Marks that count now; those of sections in the other track stay, in case the person switches back. */
function uncheckedSuggestions(form, state) {
  const shown = new Set(sectionsFor(form, state.track).map((s) => s.id));
  return Object.keys(state.suggested || {}).filter((key) => shown.has(key.split(".")[0]));
}

function shiftSuggestions(marks, sectionId, removed) {
  const shifted = {};
  for (const [key, source] of Object.entries(marks)) {
    const [section, position] = key.split(".");
    const index = Number(position);
    if (section !== sectionId || position === undefined) shifted[key] = source;
    else if (index !== removed) shifted[`${section}.${index > removed ? index - 1 : index}`] = source;
  }
  return shifted;
}

const isBlankValue = (value) => (Array.isArray(value) ? value.every((v) => !String(v).trim()) : !String(value ?? "").trim());

/** Marks kept in a stored state; it comes from a file, so only what has the expected shape stays. */
function cleanSuggestions(marks) {
  if (!isPlainObject(marks)) return {};
  const valid = ([, s]) => isPlainObject(s) && typeof s.file === "string" && typeof s.place === "string";
  return Object.fromEntries(Object.entries(marks).filter(valid).map(([key, s]) => [key, { file: s.file, place: s.place }]));
}

function suggestRepeated(data, marks, section, found) {
  const current = Array.isArray(data[section.id]) ? data[section.id] : [];
  if (!current.every(isBlankItem)) return null;
  const kept = Object.entries(marks).filter(([key]) => !key.startsWith(`${section.id}.`));
  const added = found.map((entry, index) => [`${section.id}.${index}`, entry.source]);
  return { data: { ...data, [section.id]: found.map((entry) => entry.values) }, marks: Object.fromEntries([...kept, ...added]) };
}

function suggestSingle(data, marks, section, found) {
  const current = isPlainObject(data[section.id]) ? data[section.id] : {};
  const free = Object.entries(found.values).filter(([key]) => isBlankValue(current[key]));
  if (!free.length) return null;
  return { data: { ...data, [section.id]: { ...current, ...Object.fromEntries(free) } }, marks: { ...marks, [section.id]: found.source } };
}

/**
 * New state with the suggestions in empty places only: what the person has written always stays.
 * Returns { state, filled, kept } with section ids: where suggestions went, and where they did not.
 */
function applySuggestions(form, state, suggestions) {
  let result = { data: state.data, marks: state.suggested || {} };
  const filled = [];
  const kept = [];
  for (const section of sectionsFor(form, state.track)) {
    const found = suggestions[section.id];
    if (!found) continue;
    const merged = (section.repeat ? suggestRepeated : suggestSingle)(result.data, result.marks, section, found);
    (merged ? filled : kept).push(section.id);
    result = merged || result;
  }
  return { state: { ...state, data: result.data, suggested: result.marks }, filled, kept };
}

// The page of the app opens on the CV in the data folder (G23): the app reads cv.yaml (onboarding/cv_read.py), and the
// sections marked "cv" in form.json follow it. A field marked "cv": false is not in the file; it stays on its entry.

const cvFields = (section) => section.fields.filter((f) => f.cv !== false);

const comparable = (value) => (Array.isArray(value) ? value.map((v) => String(v).trim()).filter((v) => v) : String(value ?? "").trim());

function sameInCv(section, a, b) {
  return cvFields(section).every((f) => JSON.stringify(comparable(a[f.id])) === JSON.stringify(comparable(b[f.id])));
}

/** Entries from the CV with the fields only the form holds, taken from the stored entry that matches. */
function withFormFields(section, entries, stored) {
  const own = section.fields.filter((f) => f.cv === false);
  const previous = Array.isArray(stored) ? stored.filter(isPlainObject) : [];
  if (!own.length || !previous.length) return entries;
  const used = new Set();
  return entries.map((entry) => {
    const match = previous.findIndex((item, index) => !used.has(index) && sameInCv(section, item, entry));
    if (match < 0) return entry;
    used.add(match);
    return { ...entry, ...pickFields(own, previous[match], false) };
  });
}

/** New state with the CV sections taken from the answers the app read from cv.yaml; unchanged without them. */
function fillFromCv(form, state, cv) {
  if (!isPlainObject(cv)) return state;
  const sections = form.sections.filter((s) => s.cv);
  const data = { ...state.data };
  for (const section of sections) {
    const value = cv[section.id];
    if (section.repeat) {
      const entries = (Array.isArray(value) ? value : []).map((item) => pickFields(cvFields(section), item, true))
        .filter((item) => Object.keys(item).length);
      data[section.id] = withFormFields(section, entries, state.data[section.id]);
    } else {
      data[section.id] = pickFields(cvFields(section), value, true);
    }
  }
  if (!state.suggested) return { ...state, data };
  const filled = new Set(sections.map((s) => s.id));
  const marks = Object.entries(state.suggested).filter(([key]) => !filled.has(key.split(".")[0]));
  return { ...state, data, suggested: Object.fromEntries(marks) };
}

if (typeof module !== "undefined") {
  module.exports = {
    sectionsFor, fieldsFor, linesToList, listToLines, collectBundle, draftBundle, isBlankItem, stateFromBundle,
    setValue, addItem, removeItem, applySuggestions, fillFromCv, cleanSuggestions, confirmSuggestions, uncheckedSuggestions, BundleError,
  };
}
