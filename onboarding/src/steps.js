// The steps of the template (MIN-369): the sections of form.json grouped into five steps, as in the design.
// Pure data and lookups, no DOM; tested in tests/steps.test.cjs.
"use strict";

// On the page words.js comes first and T is its T; required alone (tests), steps.js takes it from there (#432). A var,
// because the pages inline every script into one, where a const would clash with the T of words.js.
var T = typeof module !== "undefined" && typeof require === "function" ? require("./words.js").T : T;

/**
 * Sections per step, in the order shown; a section that does not apply to the track is left out. Title and line are
 * said when the steps are drawn, so they follow the app language (#432).
 */
const STEP_GROUPS = [
  {
    id: "person",
    title: { job: () => T("Person und Kontakt"), apprenticeship: () => T("Du und deine Kontakte") },
    meta: { job: () => T("Name, Adresse, Kontakt"), apprenticeship: () => T("Name, Adresse, Kontakt") },
    sections: { job: ["person"], apprenticeship: ["person"] },
  },
  {
    id: "career",
    title: { job: () => T("Werdegang"), apprenticeship: () => T("Schule und Schnuppern") },
    meta: { job: () => T("Stationen, Lehre, Projekte, Ausbildung, Kurse"), apprenticeship: () => T("Schule, Schnupperlehren, Tests") },
    sections: { job: ["work", "teaching", "projects", "education", "certificates"], apprenticeship: ["education", "work", "certificates"] },
  },
  {
    id: "abilities",
    title: { job: () => T("Können"), apprenticeship: () => T("Was du kannst") },
    meta: { job: () => T("Sprachen, Kenntnisse, Stärken"), apprenticeship: () => T("Sprachen, Stärken, Hobbys") },
    sections: { job: ["languages", "skills", "strengths", "interests"], apprenticeship: ["languages", "skills", "strengths", "interests"] },
  },
  {
    id: "search",
    title: { job: () => T("Was Sie suchen"), apprenticeship: () => T("Was du suchst") },
    meta: { job: () => T("Stellen, Region, Rahmen"), apprenticeship: () => T("Berufe, Region, Lehrbeginn") },
    sections: { job: ["searchJob", "frame"], apprenticeship: ["searchApprenticeship", "frame"] },
  },
  {
    id: "writing",
    title: { job: () => T("Wie Sie schreiben"), apprenticeship: () => T("Wie du schreibst") },
    meta: { job: () => T("Kurzprofil, Lücken, Ton"), apprenticeship: () => T("Lücken, Ton") },
    sections: { job: ["summary", "gaps", "style"], apprenticeship: ["gaps", "style"] },
  },
];

/** The five steps for a track: { id, title, meta, sections }; `sections` are those of the track (model.sectionsFor). */
function stepGroups(sections, track) {
  const byId = new Map(sections.map((s) => [s.id, s]));
  return STEP_GROUPS.map((group) => ({
    id: group.id,
    title: group.title[track](),
    meta: group.meta[track](),
    sections: group.sections[track].map((id) => byId.get(id)).filter(Boolean),
  }));
}

/** Index of the group that holds a section, -1 if none does. */
function groupOfSection(groups, sectionId) {
  return groups.findIndex((g) => g.sections.some((s) => s.id === sectionId));
}

if (typeof module !== "undefined") {
  module.exports = { STEP_GROUPS, stepGroups, groupOfSection };
}
