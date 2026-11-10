// Validation of onboarding bundles against form.json, for the browser.
// Mirrors validation.py; both run the shared cases in tests/cases.json. The limits of tags hold for typed tags only:
// `known` names the tags already in the data folder (G24), which never block saving. In the same way `loaded`, the
// answers the app read from cv.yaml (G23), never blocks saving: an entry, a value or a line the file holds at that place
// is not checked, two-language values {de, en} included, and a section or list may keep as many entries as the file has.
"use strict";

const SINGLE_LINE = new Set(["text", "list", "select", "choice", "tags"]);
const TAGGED_LINE_KEYS = new Set(["text", "tags"]);
const LEVELED_LINE_KEYS = new Set(["text", "level"]);
const LEVELS = ["", "1", "2", "3", "4", "5", "6"];  // "" leaves a line without level (#123)
const LINE = "Zeile";
const TAG = "Tag";
const TAGS_NAME = "Tags";
const TOP_LEVEL_KEYS = new Set(["format", "version", "track", "data", "saved"]);

const MESSAGES = {
  required: "Bitte ausfüllen.",
  type: "Unerwarteter Wert, bitte neu eingeben.",
  max: "Zu lang (höchstens {max} Zeichen).",
  maxItems: "Zu viele Einträge (höchstens {maxItems}).",
  format: "Ungültiges Format, zum Beispiel: {example}.",
  option: "Bitte einen der vorgeschlagenen Werte wählen.",
  notBefore: "Liegt vor dem Beginn.",
  newline: "Bitte ohne Zeilenumbruch.",
  unknown: "Gehört nicht zu dieser Vorlage.",
  bundle: "Die Datei ist keine Einstiegsdatei dieser Version.",
  track: "Unbekannte Art der Suche.",
};

const isObject = (v) => v !== null && typeof v === "object" && !Array.isArray(v);
const err = (path, code) => ({ path, code });

function applies(item, track) {
  return !item.tracks || item.tracks.includes(track);
}

/** True if track names a track of the form (a string key, not inherited). */
function isTrack(form, track) {
  return typeof track === "string" && Object.prototype.hasOwnProperty.call(form.tracks, track);
}

function forTrack(value, track) {
  return isObject(value) ? value[track] : value;
}

function textLimit(form, field) {
  return field.max ?? form.limits[field.type === "textarea" ? "textarea" : "text"];
}

/** The rules of one list of tags (G24), on an entry or on a line. */
function tagRules(form) {
  return { type: "tags", format: "tag", max: form.limits.tag, maxItems: form.limits.tags };
}

/** A line with tags, as cv.yaml writes it: { text, tags }. */
function isTaggedLine(value) {
  return isObject(value) && Object.keys(value).every((k) => TAGGED_LINE_KEYS.has(k)) && typeof value.text === "string"
    && (value.tags === undefined || Array.isArray(value.tags));
}

/** A line with a level, as the page sends it: { text, level } with level as text. */
function isLeveledLine(value) {
  return isObject(value) && Object.keys(value).every((k) => LEVELED_LINE_KEYS.has(k)) && typeof value.text === "string"
    && (value.level === undefined || typeof value.level === "string");
}

const lineOf = (value) => (isObject(value) ? value.text : value);

/** A value as it counts when compared with cv.yaml: trimmed, blank as "", a line without tags as its text. */
function storedValue(value) {
  if (value === null || value === undefined) return "";
  if (typeof value === "string") return value.trim();
  if (Array.isArray(value)) {
    const lines = value.map(storedLine).filter((line) => line !== "");
    return lines.length ? lines : "";
  }
  return value;
}

function storedLine(value) {
  if (isObject(value) && "level" in value && Object.keys(value).every((k) => LEVELED_LINE_KEYS.has(k))) {
    const text = typeof value.text === "string" ? storedValue(value.text) : value.text;
    const level = typeof value.level === "string" ? value.level.trim() : value.level;
    return level && text !== "" ? { text, level } : text;
  }
  if (isObject(value) && "text" in value && Object.keys(value).every((k) => TAGGED_LINE_KEYS.has(k))) {
    const text = typeof value.text === "string" ? storedValue(value.text) : value.text;
    const tags = Array.isArray(value.tags) ? storedValue(value.tags) : value.tags;
    return tags && text !== "" ? { text, tags } : text;
  }
  return typeof value === "string" ? storedValue(value) : value;
}

/** Deep equality of JSON values; the order of keys does not count. */
function sameValue(a, b) {
  if (Array.isArray(a) || Array.isArray(b)) {
    return Array.isArray(a) && Array.isArray(b) && a.length === b.length && a.every((x, i) => sameValue(x, b[i]));
  }
  if (isObject(a) || isObject(b)) {
    if (!isObject(a) || !isObject(b)) return false;
    const keys = Object.keys(a);
    return keys.length === Object.keys(b).length && keys.every((k) => Object.prototype.hasOwnProperty.call(b, k) && sameValue(a[k], b[k]));
  }
  return a === b;
}

/** The entries of a section as read from cv.yaml; one entry for a section that does not repeat. */
function loadedEntries(section, loaded) {
  const value = isObject(loaded) && section.cv ? loaded[section.id] : undefined;
  return (Array.isArray(value) ? value : [value]).filter(isObject);
}

function isLoadedEntry(section, track, item, before) {
  const ids = section.fields.filter((f) => applies(f, track) && f.cv !== false).map((f) => f.id);
  return before.some((entry) => ids.every((id) => sameValue(storedValue(item[id]), storedValue(entry[id]))));
}

function isLoadedValue(id, value, before) {
  const shown = storedValue(value);
  return shown !== "" && before.some((entry) => sameValue(storedValue(entry[id]), shown));
}

const loadedLines = (id, before) => before.flatMap((entry) => storedValue(entry[id]) || []);
const loadedCount = (id, before) => Math.max(0, ...before.map((entry) => (storedValue(entry[id]) || []).length));

function validateBundle(form, bundle, known, loaded) {
  const knownTags = new Set(Array.isArray(known) ? known : []);
  if (!isObject(bundle)) return [err("", "type")];
  if (bundle.format !== form.format) return [err("format", "bundle")];
  if (bundle.version !== form.version) return [err("version", "bundle")];
  const track = bundle.track;
  if (!isTrack(form, track)) return [err("track", "track")];
  const data = bundle.data;
  if (!isObject(data)) return [err("data", "type")];
  const errors = Object.keys(bundle).filter((k) => !TOP_LEVEL_KEYS.has(k)).map((k) => err(k, "unknown"));
  const sections = form.sections.filter((s) => applies(s, track));
  const ids = new Set(sections.map((s) => s.id));
  errors.push(...Object.keys(data).filter((k) => !ids.has(k)).map((k) => err(k, "unknown")));
  for (const section of sections) {
    const before = loadedEntries(section, loaded);
    errors.push(...validateSection(form, section, track, data[section.id], knownTags, before));
  }
  return errors;
}

function validateSection(form, section, track, value, known, before) {
  const sid = section.id;
  if (!section.repeat) {
    const item = value ?? {};
    return isObject(item) ? validateItem(form, section, track, item, sid, known, before) : [err(sid, "type")];
  }
  if (value == null) return [];
  if (!Array.isArray(value)) return [err(sid, "type")];
  const errors = [];
  if (value.length > Math.max(section.maxItems ?? form.limits.repeatItems, before.length)) errors.push(err(sid, "maxItems"));
  value.forEach((item, index) => {
    const path = `${sid}.${index}`;
    if (!isObject(item)) errors.push(err(path, "type"));
    else errors.push(...validateItem(form, section, track, item, path, known, before));
  });
  return errors;
}

function validateItem(form, section, track, item, path, known, before) {
  const fields = section.fields.filter((f) => applies(f, track));
  const ids = new Set(fields.map((f) => f.id));
  const errors = Object.keys(item).filter((k) => !ids.has(k)).map((k) => err(`${path}.${k}`, "unknown"));
  const same = isLoadedEntry(section, track, item, before);
  for (const field of fields) {
    if ((same && field.cv !== false) || isLoadedValue(field.id, item[field.id], before)) continue;
    errors.push(...validateField(form, field, track, item, `${path}.${field.id}`, known, before));
  }
  return errors;
}

function validateField(form, field, track, item, path, known, before) {
  const value = item[field.id];
  if (field.type === "tags") return validateTags(form, value, path, known);
  if (field.type === "list") return validateList(form, field, value, path, known, before);
  const text = value ?? "";
  if (typeof text !== "string") return [err(path, "type")];
  if (!text.trim()) return isRequired(field, item) ? [err(path, "required")] : [];
  const code = checkText(form, field, track, text);
  if (code) return [err(path, code)];
  if (field.notBefore && isBefore(text, item[field.notBefore])) return [err(path, "notBefore")];
  return [];
}

/** Required, unless the field named by requiredUnless holds text: a free text stands in for what it replaces (G25). */
function isRequired(field, item) {
  const other = field.requiredUnless === undefined ? undefined : item[field.requiredUnless];
  return Boolean(field.required) && !(typeof other === "string" && other.trim());
}

/** A list of tags: known ones may be longer or more than the limits allow, typed ones may not. */
function validateTags(form, value, path, known) {
  const list = value ?? [];
  if (!Array.isArray(list) || !list.every((v) => typeof v === "string")) return [err(path, "type")];
  const rules = tagRules(form);
  const tags = list.map((v) => v.trim()).filter((v) => v);
  const typed = tags.filter((tag) => !known.has(tag));
  const errors = tags.length > rules.maxItems && typed.length ? [err(path, "maxItems")] : [];
  list.forEach((tag, index) => {
    if (!tag.trim()) return;
    const code = checkText(form, known.has(tag.trim()) ? { ...rules, max: Infinity } : rules, null, tag);
    if (code) errors.push(err(`${path}.${index}`, code));
  });
  return errors;
}

/** A list of lines; lines cv.yaml holds in this field are not checked, two-language ones included. */
function validateList(form, field, value, path, known, before) {
  const list = value ?? [];
  if (!Array.isArray(list)) return [err(path, "type")];
  const tagged = field.tags === true;
  const lines = loadedLines(field.id, before);
  const inFile = list.map((v) => lines.some((line) => sameValue(line, storedLine(v))));
  const leveled = field.levels === true;
  const fits = (v, i) => inFile[i] || typeof v === "string" || (tagged && isTaggedLine(v)) || (leveled && isLeveledLine(v));
  if (!list.every(fits)) return [err(path, "type")];
  const items = list.filter((v, i) => inFile[i] || lineOf(v).trim());
  if (!items.length) return field.required ? [err(path, "required")] : [];
  const errors = [];
  if (items.length > Math.max(field.maxItems ?? form.limits.listItems, loadedCount(field.id, before))) errors.push(err(path, "maxItems"));
  list.forEach((entry, index) => {
    const text = inFile[index] ? "" : lineOf(entry);
    if (!text.trim()) return;
    const code = checkText(form, field, null, text);
    if (code) errors.push(err(`${path}.${index}`, code));
    if (isObject(entry) && tagged) errors.push(...validateTags(form, entry.tags, `${path}.${index}.tags`, known));
    if (isObject(entry) && leveled && !LEVELS.includes((entry.level ?? "").trim())) errors.push(err(`${path}.${index}.level`, "option"));
  });
  return errors;
}

function checkText(form, field, track, value) {
  if (SINGLE_LINE.has(field.type) && /[\r\n]/.test(value)) return "newline";
  // Count code points like Python's len(), not UTF-16 units.
  if (Array.from(value).length > textLimit(form, field)) return "max";
  if (field.format && !new RegExp(form.formats[field.format].pattern).test(value.trim())) return "format";
  if (field.type === "select" && !field.options.includes(value)) return "option";
  if (field.type === "choice" && !field.allowOwn && !forTrack(field.options, track).includes(value)) return "option";
  return null;
}

function isBefore(end, start) {
  if (typeof start !== "string" || !start.trim()) return false;
  const e = end.trim();
  const s = start.trim();
  if (e.length === 4 || s.length === 4) return e.slice(0, 4) < s.slice(0, 4);
  return e < s;
}

function locate(form, track, path) {
  const parts = path ? path.split(".") : [];
  const section = form.sections.find((s) => parts.length && s.id === parts[0]);
  if (!section) return { where: "", field: null, section: null };
  const names = [forTrack(section.title, track) || section.id];
  let rest = parts.slice(1);
  if (section.repeat && rest.length && /^\d+$/.test(rest[0])) {
    names.push(`${forTrack(section.itemTitle, track)} ${Number(rest[0]) + 1}`);
    rest = rest.slice(1);
  }
  let field = section.fields.find((f) => rest.length && f.id === rest[0]) || null;
  if (field) {
    names.push((forTrack(field.label, track) || field.id).split(" (")[0]);
    const below = lineNames(rest.slice(1), field.type === "tags" ? TAG : LINE);
    names.push(...below.names);
    if (field.type === "tags" || below.inTags) field = tagRules(form);
  }
  return { where: names.join(", "), field, section };
}

/** Names below a field, the line ("Zeile 2") and on a line its tags ("Tags, Tag 1"); inTags if it reaches tags. */
function lineNames(rest, unit) {
  if (!rest.length || !/^\d+$/.test(rest[0])) return { names: [], inTags: false };
  const line = `${unit} ${Number(rest[0]) + 1}`;
  if (rest.length < 2 || rest[1] !== "tags") return { names: [line], inTags: false };
  return { names: [line, TAGS_NAME, ...lineNames(rest.slice(2, 3), TAG).names], inTags: true };
}

/** Message without location, for display next to the field. */
function messageText(form, track, error) {
  return describeParts(form, track, error).text;
}

/** Message with location (section, item, field), for summaries. */
function describe(form, track, error) {
  const { where, text } = describeParts(form, track, error);
  return where ? `${where}: ${text}` : text;
}

function describeParts(form, track, error) {
  const { where, field, section } = locate(form, track, error.path);
  const params = { max: "?", maxItems: "?", example: "?" };
  if (field) {
    params.max = textLimit(form, field);
    params.maxItems = field.maxItems ?? form.limits.listItems;
    if (field.format) params.example = form.formats[field.format].example;
  } else if (section) {
    params.maxItems = section.maxItems ?? form.limits.repeatItems;
  }
  const text = (MESSAGES[error.code] || error.code).replace(/\{(\w+)\}/g, (_, k) => params[k]);
  return { where, text };
}

if (typeof module !== "undefined") {
  module.exports = { validateBundle, describe, messageText, applies, forTrack, isTrack };
}
