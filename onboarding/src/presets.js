// Presets of Meine Angaben (#218, G41): a field the person never filled gets the answer that fits nearly everyone,
// so fewer fields block taking over. form.json names it per field as "preset": a text, {"option": n} for the n-th
// option of the track, or {"from": "section.field"} for a value given earlier (the Ort under Person).
// Only a value the page never held is filled: what the person typed or emptied stays. The page fills the sections of
// the step it shows, and all of them on the last step, so suggestions from documents still reach empty fields first.
"use strict";

const isPresetObject = (v) => v !== null && typeof v === "object" && !Array.isArray(v);

function presetApplies(item, track) {
  return !item.tracks || item.tracks.includes(track);
}

/** The options of a select or choice field for a track. */
function presetOptions(field, track) {
  if (Array.isArray(field.options)) return field.options;
  return isPresetObject(field.options) && Array.isArray(field.options[track]) ? field.options[track] : [];
}

/** The preset of one field as text; "" when there is none yet (an Ort not given, an option missing). */
function presetValue(field, track, data) {
  const preset = field.preset;
  if (typeof preset === "string") return preset;
  if (!isPresetObject(preset)) return "";
  if (Number.isInteger(preset.option)) {
    const option = presetOptions(field, track)[preset.option];
    return typeof option === "string" ? option : "";
  }
  if (typeof preset.from !== "string") return "";
  const [sectionId, fieldId] = preset.from.split(".");
  const source = isPresetObject(data[sectionId]) ? data[sectionId][fieldId] : undefined;
  return typeof source === "string" ? source.trim() : "";
}

/** The presets missing in one single section, as { fieldId: value }. */
function missingPresets(section, track, data) {
  const current = isPresetObject(data[section.id]) ? data[section.id] : {};
  const filled = {};
  for (const field of section.fields) {
    if (field.preset === undefined || !presetApplies(field, track) || current[field.id] !== undefined) continue;
    const value = presetValue(field, track, data);
    if (value) filled[field.id] = value;
  }
  return filled;
}

/**
 * New state with the presets of the named sections filled in (all sections when sectionIds is null).
 * Returns the same state when nothing was missing, so a caller can tell whether anything changed.
 */
function withPresets(form, state, sectionIds) {
  if (!state.track) return state;
  let data = isPresetObject(state.data) ? state.data : {};
  for (const section of form.sections) {
    if (section.repeat || !presetApplies(section, state.track)) continue;
    if (sectionIds && !sectionIds.includes(section.id)) continue;
    const filled = missingPresets(section, state.track, data);
    if (!Object.keys(filled).length) continue;
    const current = isPresetObject(data[section.id]) ? data[section.id] : {};
    data = { ...data, [section.id]: { ...current, ...filled } };
  }
  return data === state.data ? state : { ...state, data };
}

if (typeof module !== "undefined") {
  module.exports = { withPresets, presetValue };
}
