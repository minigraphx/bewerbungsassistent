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
 * Whether a term runs on this portal: a term the profile limits to some portals (G105, `nur_portale`) only there.
 * An older app sends no limits, so every term runs everywhere.
 * @param {object} plan
 * @param {string} term
 * @param {string} portal
 * @returns {boolean}
 */
export function runsOn(plan, term, portal) {
  const limits = plan.nur_portale;
  const only = limits && typeof limits === 'object' && Object.hasOwn(limits, term) ? limits[term] : null;
  return !Array.isArray(only) || only.includes(portal);
}

/** The jobscout24 regions of the plan (G107), each with id and name; an older app sends none. */
function jobscout24Regions(plan) {
  const regions = Array.isArray(plan.regionen_jobscout24) ? plan.regionen_jobscout24 : [];
  return regions.filter((region) => region && typeof region.id === 'string' && region.id);
}

/** One search in all regions: jobscout24 repeats regidl per region, and reads more pages than at one postcode. */
function regionsOf(regions, plan) {
  const pages = Number.isInteger(plan.max_seiten_regionen) ? { maxPages: plan.max_seiten_regionen } : {};
  return { regionIds: regions.map((region) => region.id), regionNames: regions.map((region) => region.name || region.id).join(', '), ...pages };
}

/**
 * Queries of one portal, all of them (G43): the search runs them in stages instead of leaving some out.
 * job-room searches all cantons at once; the others once per place, the home first.
 * Niche keywords run without place on jobs.ch only: on jobscout24 and ictjobs they would need one to stay few.
 * jobscout24 with regions (G107) runs one query per keyword in all of them instead of one per postcode.
 * A keyword limited to other portals (runsOn) has no query here.
 * bewerbungen/search_stages.py counts them the same way for the announcement (tests/fixtures/run-size.json).
 * @param {string} portal
 * @param {object} plan  as /api/suche/plan returns it
 * @returns {{queries: Array<object>}}
 */
export function buildQueries(portal, plan) {
  // The days since this portal's last successful run (G32); an older app sends only the window.
  const maxAge = plan.max_alter_tage_portale?.[portal] ?? plan.max_alter_tage;
  const keywords = (plan.stichworte || []).filter((keyword) => runsOn(plan, keyword, portal));
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
  const regions = portal === 'jobscout24' ? jobscout24Regions(plan) : [];
  const rounds = regions.length
    ? [keywords.map((keyword) => ({ keyword, ...regionsOf(regions, plan), maxAge }))]
    : (plan[field] || []).map((place) => keywords.map((keyword) => ({ keyword, [key]: place, maxAge })));
  // No place for this portal, or no region chosen at all: the whole of Switzerland, right after the home.
  const everywhere = plan.schweizweit || !rounds.length ? keywords.map((keyword) => ({ keyword, maxAge })) : [];
  return { queries: [...(rounds[0] || []), ...free, ...everywhere, ...rounds.slice(1).flat()] };
}

/**
 * The result pages a query reads at most: a jobscout24 region search its own limit (G107), every other the plan's.
 * bewerbungen/search_stages.py weighs the time estimate by these pages (#391, tests/fixtures/run-size.json).
 * @param {object} query  as buildQueries returns it
 * @param {object} plan
 * @returns {number}
 */
export function pagesOf(query, plan) {
  return query.maxPages || plan.max_seiten;
}

/**
 * The place a query searches, for the progress (G43): its town, postcode, region or cantons; '' for a query without one.
 * @param {object} query  as buildQueries returns it
 * @returns {string}
 */
export function placeOf(query) {
  const single = query.place || query.postalCode || query.region || query.regionNames || query.canton;
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
