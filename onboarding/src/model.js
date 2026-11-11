// Pure state handling of the onboarding template: no DOM, no storage.
// State: { track: "job" | "apprenticeship" | null, data: { [sectionId]: object | object[] } }.
// List fields hold arrays of lines; blank lines and empty items are dropped only when collecting.
// Tags (G24): a "tags" field holds an array of tags; a list marked "tags" holds lines as text or { text, tags }.
// What the form does not send stays in cv.yaml (G23): a missing tags key keeps the tags of the file, an empty list
// removes them. So tags go out wherever the page holds them, an empty list included; a plain text line keeps its tags.
// The same holds for sections and fields marked "keepUnlessGiven" in form.json (G25: projects, teaching, the website):
// they go out wherever the page holds them, empty too, and a state from before G25 sends no key, so cv.yaml keeps them.
// Levels (#123, G20): a list marked "levels" (keywords) holds lines as text or { text, level } with level "" or "1"–"6".
// As with tags, a plain line leaves the level to cv.yaml and an empty level removes it.
// A field with a "preset" (#218) goes out empty too once the person emptied it (#230): dropped, it would read as never
// filled when the saved answers come back, and the preset would fill it again.
// Two-language values {de, en} from cv.yaml (#167) stay as they are on text fields and as lines, and go back unchanged:
// validate.js lets them pass while cv.yaml holds them, and the app keeps them in the file until the person types anew.
"use strict";

/** A loaded file that is no bundle of this form; the message is German and shown as is. */
class BundleError extends Error {}

const isPlainObject = (v) => v !== null && typeof v === "object" && !Array.isArray(v);
const LANGUAGES = ["de", "en"];

/** A two-language value as cv.yaml writes it: { de, en } with text in each. */
function isBilingual(value) {
  const keys = isPlainObject(value) ? Object.keys(value) : [];
  return keys.length > 0 && keys.every((k) => LANGUAGES.includes(k) && typeof value[k] === "string");
}

/** The two languages of a value or of a line ({ de, en } or { text: { de, en }, tags }); null for plain text. */
function bilingualOf(value) {
  if (isBilingual(value)) return value;
  return isPlainObject(value) && isBilingual(value.text) ? value.text : null;
}

function trackApplies(item, track) {
  return !item.tracks || item.tracks.includes(track);
}

/** Sections shown for a track, in form order. */
function sectionsFor(form, track) {
  return form.sections.filter((s) => trackApplies(s, track));
}

/** Fields of a section that apply to a track: shown, or kept unseen (hiddenFor). */
function fieldsFor(section, track) {
  return section.fields.filter((f) => trackApplies(f, track));
}

/**
 * Fields of a section the page shows for a track. A field "hiddenFor" a track is no longer asked (#218: „Verfügbar ab“,
 * which frühester Start covers), but a value from before stays in the answers and goes on into the Bausteine.
 */
function shownFields(section, track) {
  return fieldsFor(section, track).filter((f) => !(f.hiddenFor || []).includes(track));
}

function linesToList(text) {
  return String(text).split(/\r?\n/);
}

function listToLines(list) {
  return Array.isArray(list) ? list.join("\n") : "";
}

/** Tags as typed: separated by commas, blanks dropped. */
function parseTags(text) {
  return String(text).split(",").map((t) => t.trim()).filter((t) => t);
}

function tagsToText(tags) {
  return Array.isArray(tags) ? tags.join(", ") : "";
}

function cleanTags(value, compact) {
  if (!Array.isArray(value)) return [];
  const tags = value.filter((t) => typeof t === "string").map((t) => (compact ? t.trim() : t));
  return compact ? tags.filter((t) => t) : tags;
}

/** One line of a list with tags: plain text (tags left to the file) or { text, tags }; null if it has no text. */
function cleanLine(value, compact) {
  if (typeof value === "string") return compact ? value.trim() : value;
  if (isBilingual(value)) return { ...value };
  if (isPlainObject(value) && isBilingual(value.text)) return { text: { ...value.text }, tags: cleanTags(value.tags, compact) };
  if (!isPlainObject(value) || typeof value.text !== "string") return null;
  return { text: compact ? value.text.trim() : value.text, tags: cleanTags(value.tags, compact) };
}

const lineText = (line) => (isPlainObject(line) ? (typeof line.text === "string" ? line.text : "") : String(line ?? ""));
/** True if a line or value holds something: text, or a value in two languages. */
const hasContent = (value) => Boolean(bilingualOf(value)) || lineText(value).trim() !== "";

/** One line of a list with levels: plain text (level left to the file) or { text, level }; null if it has no text. */
function cleanLeveledLine(value, compact) {
  if (typeof value === "string") return compact ? value.trim() : value;
  const shaped = isPlainObject(value) && Object.keys(value).every((k) => k === "text" || k === "level");
  if (!shaped || typeof value.text !== "string") return null;
  const level = typeof value.level === "string" ? value.level : "";
  return { text: compact ? value.text.trim() : value.text, level: compact ? level.trim() : level };
}

/** A line the person edited: with its tags, an empty list included, so removing the last tag removes it. */
function taggedLine(text, tags) {
  return { text, tags };
}

function cleanList(field, value, compact) {
  if (field.tags === true || field.levels === true) {
    const clean = field.levels === true ? cleanLeveledLine : cleanLine;
    const lines = value.map((v) => clean(v, compact)).filter((v) => v !== null);
    return compact ? lines.filter(hasContent) : lines;
  }
  const lines = value.filter((v) => typeof v === "string").map((v) => (compact ? v.trim() : v));
  return compact ? lines.filter((v) => v) : lines;
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
    if (field.type === "list" || field.type === "tags") {
      if (!Array.isArray(value)) continue;
      const kept = field.type === "tags" ? cleanTags(value, compact) : cleanList(field, value, compact);
      if (kept.length || field.type === "tags") result[field.id] = kept;
    } else if (typeof value === "string" && (!compact || value.trim() || field.keepUnlessGiven || field.preset !== undefined)) {
      result[field.id] = compact ? value.trim() : value;
    } else if (isBilingual(value)) {
      result[field.id] = { ...value };
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
      const kept = compact ? list.filter((item) => !isBlankItem(item)) : list;
      if (kept.length || section.keepUnlessGiven) result[section.id] = kept;
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

/** True if a repeated item has no content yet (such items are dropped when saving); tags on an empty line do not count. */
function isBlankItem(item) {
  if (!isPlainObject(item)) return true;
  return Object.values(item).every((v) => (Array.isArray(v) ? !v.some(hasContent) : !hasContent(v)));
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

const isBlankValue = (value) => (Array.isArray(value) ? !value.some(hasContent) : !hasContent(value));

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

const comparableLine = (v) => (isPlainObject(v) ? { text: lineText(v).trim(), tags: cleanTags(v.tags, true) } : String(v).trim());
const comparable = (value) => (Array.isArray(value) ? value.map(comparableLine).filter((v) => lineText(v)) : String(value ?? "").trim());

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

// Suggestions for tags: those the app found in the data folder (cv.yaml, varianten.yaml, jobs/) and those typed here.

const TAG_ORDER = (a, b) => a.toLowerCase().localeCompare(b.toLowerCase(), "de") || (a < b ? -1 : a > b ? 1 : 0);

function tagsOfItem(section, item) {
  if (!isPlainObject(item)) return [];
  return section.fields.flatMap((field) => {
    const value = item[field.id];
    if (!Array.isArray(value)) return [];
    if (field.type === "tags") return cleanTags(value, true);
    return field.tags === true ? value.flatMap((line) => (isPlainObject(line) ? cleanTags(line.tags, true) : [])) : [];
  });
}

/** Every tag the form can show once (format "tag"; long ones too), sorted without regard to case. */
function knownTags(form, state, fromApp) {
  const pattern = new RegExp(form.formats.tag.pattern);
  const valid = (t) => t !== "" && pattern.test(t);
  const typed = form.sections.filter((s) => s.repeat && Array.isArray(state.data[s.id]))
    .flatMap((s) => state.data[s.id].flatMap((item) => tagsOfItem(s, item)));
  const all = [...(Array.isArray(fromApp) ? fromApp : []), ...typed]
    .filter((t) => typeof t === "string").map((t) => t.trim()).filter(valid);
  return [...new Set(all)].sort(TAG_ORDER);
}

if (typeof module !== "undefined") {
  module.exports = {
    sectionsFor, fieldsFor, shownFields, linesToList, listToLines, parseTags, tagsToText, taggedLine, lineText, knownTags, isBilingual, bilingualOf,
    collectBundle, draftBundle, isBlankItem, stateFromBundle,
    setValue, addItem, removeItem, applySuggestions, fillFromCv, cleanSuggestions, confirmSuggestions, uncheckedSuggestions, BundleError,
  };
}
