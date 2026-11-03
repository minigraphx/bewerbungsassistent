// Which searches run per portal: keyword × place from the plan of the app, with the limits of the skill.

/** Portal → its adapter file and the page the search tab opens. */
export const ADAPTERS = {
  'job-room': { file: 'portals/jobroom.js', start: 'https://www.job-room.ch/home/job-seeker' },
  'jobs.ch': { file: 'portals/jobsch.js', start: 'https://www.jobs.ch/de/' },
  jobscout24: { file: 'portals/jobscout24.js', start: 'https://www.jobscout24.ch/de/jobs/' },
  ictjobs: { file: 'portals/ictjobs.js', start: 'https://ictjobs.ch/' },
};

/** Where each portal takes the place from: field of the plan and field of the query. */
const PLACE = {
  'jobs.ch': ['orte', 'place'],
  jobscout24: ['plz', 'postalCode'],
  ictjobs: ['regionen', 'region'],
};

/**
 * Queries of one portal. job-room searches all cantons at once; the others once per place, every keyword in
 * the first place first, so the limit cuts the farther places before the keywords.
 * Niche keywords run without place, except on portals that need one (jobscout24, ictjobs).
 * @param {string} portal
 * @param {object} plan  as /api/suche/plan returns it
 * @returns {{queries: Array<object>, skipped: number}}
 */
export function buildQueries(portal, plan) {
  const maxAge = plan.max_alter_tage;
  const keywords = plan.stichworte || [];
  const niches = plan.nischen || [];
  let all = [];
  if (portal === 'job-room') {
    all = [
      ...keywords.map((keyword) => ({ keyword, cantons: plan.kantone || [], maxAge })),
      ...niches.map((keyword) => ({ keyword, cantons: [], maxAge })),
    ];
  } else if (PLACE[portal]) {
    const [field, key] = PLACE[portal];
    const rounds = (plan[field] || []).map((place) => keywords.map((keyword) => ({ keyword, [key]: place, maxAge })));
    const free = portal === 'jobs.ch' ? niches.map((keyword) => ({ keyword, maxAge })) : [];
    all = rounds.length ? [...rounds[0], ...free, ...rounds.slice(1).flat()] : [];
  }
  const limit = plan.max_abfragen || all.length;
  return { queries: all.slice(0, limit), skipped: Math.max(0, all.length - limit) };
}

/** Split a list into parts of at most `size` items. */
export function chunks(items, size) {
  const parts = [];
  for (let i = 0; i < items.length; i += size) parts.push(items.slice(i, i + size));
  return parts;
}

/** Key of a hit as the app uses it in `holen`. */
export function hitKey(hit) {
  return `${hit.portal}:${hit.portal_id}`;
}
