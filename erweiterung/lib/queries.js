// Which searches run per portal: keyword × place from the plan of the app.

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
 * Queries of one portal, all of them (G43): the search runs them in stages instead of leaving some out.
 * job-room searches all cantons at once; the others once per place, the home first.
 * Niche keywords run without place on jobs.ch only: on jobscout24 and ictjobs they would need one to stay few.
 * bewerbungen/search_stages.py counts them the same way for the announcement (tests/fixtures/run-size.json).
 * @param {string} portal
 * @param {object} plan  as /api/suche/plan returns it
 * @returns {{queries: Array<object>}}
 */
export function buildQueries(portal, plan) {
  // The days since this portal's last successful run (G32); an older app sends only the window.
  const maxAge = plan.max_alter_tage_portale?.[portal] ?? plan.max_alter_tage;
  const keywords = plan.stichworte || [];
  const niches = plan.nischen || [];
  if (APPRENTICESHIP_PORTALS.has(portal)) return { queries: apprenticeshipQueries(plan) };
  if (portal === 'job-room') {
    return { queries: [
      ...keywords.map((keyword) => ({ keyword, cantons: plan.kantone || [], maxAge })),
      ...niches.map((keyword) => ({ keyword, cantons: [], maxAge })),
    ] };
  }
  if (!PLACE[portal]) return { queries: [] };
  const [field, key] = PLACE[portal];
  const free = portal === 'jobs.ch' ? niches.map((keyword) => ({ keyword, maxAge })) : [];
  const rounds = (plan[field] || []).map((place) => keywords.map((keyword) => ({ keyword, [key]: place, maxAge })));
  // No place for this portal, or no region chosen at all: the whole of Switzerland, right after the home.
  const everywhere = plan.schweizweit || !rounds.length ? keywords.map((keyword) => ({ keyword, maxAge })) : [];
  return { queries: [...(rounds[0] || []), ...free, ...everywhere, ...rounds.slice(1).flat()] };
}

/**
 * The place a query searches, for the progress (G43): its town, postcode, region or cantons; '' for a query without one.
 * @param {object} query  as buildQueries returns it
 * @returns {string}
 */
export function placeOf(query) {
  const single = query.place || query.postalCode || query.region || query.canton;
  if (single) return String(single);
  return (query.cantons || []).join(', ');
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
