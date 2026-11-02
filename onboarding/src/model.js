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
  const result = {};
  if (!isPlainObject(item)) return result;
  for (const field of fieldsFor(section, track)) {
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
  return { ...state, data: { ...state.data, [sectionId]: list.filter((_, i) => i !== index) } };
}

if (typeof module !== "undefined") {
  module.exports = {
    sectionsFor, fieldsFor, linesToList, listToLines, collectBundle, draftBundle, isBlankItem, stateFromBundle,
    setValue, addItem, removeItem, BundleError,
  };
}
