// Validation of onboarding bundles against form.json, for the browser.
// Mirrors validation.py; both run the shared cases in tests/cases.json.
"use strict";

const SINGLE_LINE = new Set(["text", "list", "select", "choice"]);
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

function validateBundle(form, bundle) {
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
  for (const section of sections) errors.push(...validateSection(form, section, track, data[section.id]));
  return errors;
}

function validateSection(form, section, track, value) {
  const sid = section.id;
  if (!section.repeat) {
    const item = value ?? {};
    return isObject(item) ? validateItem(form, section, track, item, sid) : [err(sid, "type")];
  }
  if (value == null) return [];
  if (!Array.isArray(value)) return [err(sid, "type")];
  const errors = [];
  if (value.length > (section.maxItems ?? form.limits.repeatItems)) errors.push(err(sid, "maxItems"));
  value.forEach((item, index) => {
    const path = `${sid}.${index}`;
    if (!isObject(item)) errors.push(err(path, "type"));
    else errors.push(...validateItem(form, section, track, item, path));
  });
  return errors;
}

function validateItem(form, section, track, item, path) {
  const fields = section.fields.filter((f) => applies(f, track));
  const ids = new Set(fields.map((f) => f.id));
  const errors = Object.keys(item).filter((k) => !ids.has(k)).map((k) => err(`${path}.${k}`, "unknown"));
  for (const field of fields) errors.push(...validateField(form, field, track, item, `${path}.${field.id}`));
  return errors;
}

function validateField(form, field, track, item, path) {
  const value = item[field.id];
  if (field.type === "list") return validateList(form, field, value, path);
  const text = value ?? "";
  if (typeof text !== "string") return [err(path, "type")];
  if (!text.trim()) return field.required ? [err(path, "required")] : [];
  const code = checkText(form, field, track, text);
  if (code) return [err(path, code)];
  if (field.notBefore && isBefore(text, item[field.notBefore])) return [err(path, "notBefore")];
  return [];
}

function validateList(form, field, value, path) {
  const list = value ?? [];
  if (!Array.isArray(list) || !list.every((v) => typeof v === "string")) return [err(path, "type")];
  const items = list.filter((v) => v.trim());
  if (!items.length) return field.required ? [err(path, "required")] : [];
  const errors = [];
  if (items.length > (field.maxItems ?? form.limits.listItems)) errors.push(err(path, "maxItems"));
  list.forEach((entry, index) => {
    if (!entry.trim()) return;
    const code = checkText(form, field, null, entry);
    if (code) errors.push(err(`${path}.${index}`, code));
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
  const field = section.fields.find((f) => rest.length && f.id === rest[0]) || null;
  if (field) {
    names.push((forTrack(field.label, track) || field.id).split(" (")[0]);
    if (rest.length > 1 && /^\d+$/.test(rest[1])) names.push(`Zeile ${Number(rest[1]) + 1}`);
  }
  return { where: names.join(", "), field, section };
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
