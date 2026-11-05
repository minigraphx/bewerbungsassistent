// The steps of the template (MIN-369): the sections of form.json grouped into five steps, as in the design.
// Pure data and lookups, no DOM; tested in tests/steps.test.cjs.
"use strict";

/** Sections per step, in the order shown; a section that does not apply to the track is left out. */
const STEP_GROUPS = [
  {
    id: "person",
    title: { job: "Person und Kontakt", apprenticeship: "Du und deine Kontakte" },
    meta: { job: "Name, Adresse, Kontakt", apprenticeship: "Name, Adresse, Kontakt" },
    sections: { job: ["person"], apprenticeship: ["person"] },
  },
  {
    id: "career",
    title: { job: "Werdegang", apprenticeship: "Schule und Schnuppern" },
    meta: { job: "Stationen, Ausbildung, Kurse", apprenticeship: "Schule, Schnupperlehren, Tests" },
    sections: { job: ["work", "education", "certificates"], apprenticeship: ["education", "work", "certificates"] },
  },
  {
    id: "abilities",
    title: { job: "Können", apprenticeship: "Was du kannst" },
    meta: { job: "Sprachen, Kenntnisse, Stärken", apprenticeship: "Sprachen, Stärken, Hobbys" },
    sections: { job: ["languages", "skills", "strengths", "interests"], apprenticeship: ["languages", "skills", "strengths", "interests"] },
  },
  {
    id: "search",
    title: { job: "Was Sie suchen", apprenticeship: "Was du suchst" },
    meta: { job: "Stellen, Region, Rahmen", apprenticeship: "Berufe, Region, Lehrbeginn" },
    sections: { job: ["searchJob", "frame"], apprenticeship: ["searchApprenticeship", "frame"] },
  },
  {
    id: "writing",
    title: { job: "Wie Sie schreiben", apprenticeship: "Wie du schreibst" },
    meta: { job: "Kurzprofil, Lücken, Ton", apprenticeship: "Lücken, Ton" },
    sections: { job: ["summary", "gaps", "style"], apprenticeship: ["gaps", "style"] },
  },
];

/** The five steps for a track: { id, title, meta, sections }; `sections` are those of the track (model.sectionsFor). */
function stepGroups(sections, track) {
  const byId = new Map(sections.map((s) => [s.id, s]));
  return STEP_GROUPS.map((group) => ({
    id: group.id,
    title: group.title[track],
    meta: group.meta[track],
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
