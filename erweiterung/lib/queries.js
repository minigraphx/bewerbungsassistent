// Which searches run per portal: keyword × place from the plan of the app, with the limits of the skill.

/** Portal → its adapter file and the page the search tab opens. */
export const ADAPTERS = {
  'job-room': { file: 'portals/jobroom.js', start: 'https://www.job-room.ch/home/job-seeker' },
  'jobs.ch': { file: 'portals/jobsch.js', start: 'https://www.jobs.ch/de/' },
  jobscout24: { file: 'portals/jobscout24.js', start: 'https://www.jobscout24.ch/de/jobs/' },
  ictjobs: { file: 'portals/ictjobs.js', start: 'https://ictjobs.ch/' },
  // LENA fills its list in the page: each search opens its own address there (adapter method searchUrl).
  LENA: { file: 'portals/lena.js', start: 'https://www.berufsberatung.ch/de/suche/lehrstellen?mode=city', opensPages: true },
  yousty: { file: 'portals/yousty.js', start: 'https://www.yousty.ch/de-CH/lehrstellen' },
};

const APPRENTICESHIP_PORTALS = new Set(['LENA', 'yousty']);

/** Where each portal takes the place from: field of the plan and field of the query. */
const PLACE = {
  'jobs.ch': ['orte', 'place'],
  jobscout24: ['plz', 'postalCode'],
  ictjobs: ['regionen', 'region'],
};

/**
 * How many keywords each place may search (#175): the limit without the niches, shared evenly, the first places
 * taking the remainder, and at least one each. Otherwise the limit would run out in the first places.
 */
export function placeQuotas(places, limit) {
  const budget = Math.max(places, limit);
  return Array.from({ length: places }, (_, i) => Math.floor(budget / places) + (i < budget % places ? 1 : 0));
}

/** Every profession around the place of residence, or without one in each canton. */
function apprenticeshipQueries(plan) {
  const years = plan.lehrbeginn_jahre || [];
  const area = (plan.orte || []).length
    ? plan.orte.map((place) => ({ place, radius: plan.umkreis_km }))
    : (plan.kantone || []).map((canton) => ({ canton }));
  const offers = (plan.angebote || []).length ? plan.angebote : ['lehrstelle'];
  return offers.flatMap((offer) => (plan.stichworte || []).flatMap((keyword) => area.map((where) => (
    offer === 'schnupperlehre' ? { keyword, years: [], trial: true, ...where } : { keyword, years, ...where }))));
}

/**
 * Queries of one portal. job-room searches all cantons at once; the others once per place, the home first. Each
 * place searches its top keywords within its share of the limit, so every place gets searched.
 * Niche keywords run without place on jobs.ch only: on jobscout24 and ictjobs they would need one to stay few.
 * @param {string} portal
 * @param {object} plan  as /api/suche/plan returns it
 * @returns {{queries: Array<object>, skipped: number}}
 */
export function buildQueries(portal, plan) {
  // The days since this portal's last successful run (G32); an older app sends only the window.
  const maxAge = plan.max_alter_tage_portale?.[portal] ?? plan.max_alter_tage;
  const keywords = plan.stichworte || [];
  const niches = plan.nischen || [];
  let all = [];
  let capped = 0; // queries a place's share leaves out, counted with the ones the limit cuts
  if (APPRENTICESHIP_PORTALS.has(portal)) {
    all = apprenticeshipQueries(plan);
  } else if (portal === 'job-room') {
    all = [
      ...keywords.map((keyword) => ({ keyword, cantons: plan.kantone || [], maxAge })),
      ...niches.map((keyword) => ({ keyword, cantons: [], maxAge })),
    ];
  } else if (PLACE[portal]) {
    const [field, key] = PLACE[portal];
    const free = portal === 'jobs.ch' ? niches.map((keyword) => ({ keyword, maxAge })) : [];
    const places = plan[field] || [];
    const quotas = placeQuotas(places.length, (plan.max_abfragen || Infinity) - free.length);
    const rounds = places.map((place, i) => keywords.slice(0, quotas[i]).map((keyword) => ({ keyword, [key]: place, maxAge })));
    capped = places.length * keywords.length - rounds.flat().length;
    // No place for this portal, or no region chosen at all: the whole of Switzerland, right after the home,
    // so the limit of queries does not take it first.
    const everywhere = plan.schweizweit || !rounds.length ? keywords.map((keyword) => ({ keyword, maxAge })) : [];
    all = [...(rounds[0] || []), ...free, ...everywhere, ...rounds.slice(1).flat()];
  }
  const limit = plan.max_abfragen || all.length;
  return { queries: all.slice(0, limit), skipped: Math.max(0, all.length - limit) + capped };
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
