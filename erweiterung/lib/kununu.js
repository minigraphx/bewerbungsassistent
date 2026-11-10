// kununu on the person's click (G35, #189): open the company or its search on kununu.com/ch, kununu.com/de only when
// /ch finds nothing, and read score and number of reviews from the page's schema.org data (AggregateRating).
// A page without that data, such as a verification page, gives nothing: the person then enters the value by hand.
// Nothing but the company name goes to kununu; nothing goes to the AI.

const ORIGIN = 'https://www.kununu.com';
const SITES = ['ch', 'de'];
const NOT_A_COMPANY = new Set(['search', 'suche', 'login', 'user', 'jobs']);
const MAX_CANDIDATES = 10;
const MAX_NAME = 200;
const MAX_DEPTH = 6;
const COMPANY_TYPES = new Set(['Organization', 'Corporation', 'LocalBusiness', 'Company', 'EmployerAggregateRating']);
const RATING_TYPES = new Set(['AggregateRating', 'EmployerAggregateRating']);
export const NO_NAME = 'Der Firmenname fehlt.';

/** The search for a company on one site of kununu.com; the name is the only thing it carries. */
export function searchUrl(name, site = 'ch') {
  return `${ORIGIN}/${site}/search?q=${encodeURIComponent(name)}`;
}

function parts(url) {
  try {
    const parsed = new URL(url);
    return parsed.origin === ORIGIN && parsed.protocol === 'https:' ? parsed.pathname.split('/').filter(Boolean) : null;
  } catch {
    return null;
  }
}

/** A company page on kununu.com/ch or /de without query and fragment, or null. */
export function companyLink(url) {
  const segments = typeof url === 'string' ? parts(url) : null;
  if (!segments || segments.length < 2 || !SITES.includes(segments[0]) || NOT_A_COMPANY.has(segments[1].toLowerCase())) return null;
  return `${ORIGIN}/${segments.join('/')}`;
}

function isSearch(url) {
  const segments = parts(url);
  return Boolean(segments && SITES.includes(segments[0]) && segments[1] === 'search');
}

function parsed(text) {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

/** Every object in the JSON-LD blocks, also inside arrays and @graph, but not inside each other. */
function items(structured) {
  const found = [];
  const walk = (value, depth) => {
    if (!value || typeof value !== 'object' || depth > MAX_DEPTH) return;
    if (Array.isArray(value)) value.forEach((item) => walk(item, depth + 1));
    else if (value['@graph']) walk(value['@graph'], depth + 1);
    else found.push(value);
  };
  (Array.isArray(structured) ? structured : []).forEach((text) => walk(parsed(text), 0));
  return found;
}

const types = (item) => [item && item['@type']].flat().filter((type) => typeof type === 'string');
const hasType = (item, set) => types(item).some((type) => set.has(type));

/** A number as kununu may write it: 3.8, "3.8", "3,8", "1’312". */
function number(value) {
  if (typeof value === 'number') return Number.isFinite(value) ? value : null;
  if (typeof value !== 'string') return null;
  const text = value.trim().replace(/[’'\s]/g, '').replace(',', '.');
  return /^\d+(\.\d+)?$/.test(text) ? Number(text) : null;
}

/** Score 1–5 and count from an AggregateRating; null when it is on another scale or not a rating. */
function rating(raw) {
  if (!raw || typeof raw !== 'object') return null;
  const best = raw.bestRating === undefined ? 5 : number(raw.bestRating);
  const value = number(raw.ratingValue);
  const count = number(raw.reviewCount ?? raw.ratingCount);
  if (best !== 5 || value === null || value < 1 || value > 5 || count === null || !Number.isInteger(count)) return null;
  return { wert: value, bewertungen: count };
}

function companyReading(found, url) {
  const company = found.find((item) => hasType(item, COMPANY_TYPES));
  if (!company) return null;
  const raw = hasType(company, RATING_TYPES) ? company : company.aggregateRating;
  if (raw === undefined) return { art: 'firma', zustand: 'keine', link: url };
  const read = rating(raw);
  if (!read) return null;
  return read.bewertungen > 0 ? { art: 'firma', zustand: 'gefunden', ...read, link: url } : { art: 'firma', zustand: 'keine', link: url };
}

function candidate(element) {
  const item = element && typeof element.item === 'object' ? element.item : element;
  const link = companyLink(item && item.url);
  const name = typeof item?.name === 'string' ? item.name.trim().slice(0, MAX_NAME) : '';
  if (!link || !name) return null;
  const place = item.address && typeof item.address === 'object' ? item.address.addressLocality : '';
  const count = rating(item.aggregateRating)?.bewertungen;
  return { name, link, ...(typeof place === 'string' && place.trim() ? { ort: place.trim() } : {}),
    ...(count !== undefined ? { bewertungen: count } : {}) };
}

function searchReading(found) {
  const list = found.find((item) => hasType(item, new Set(['ItemList'])));
  if (!list) return null;
  const elements = Array.isArray(list.itemListElement) ? list.itemListElement : [];
  return { art: 'suche', kandidaten: elements.map(candidate).filter(Boolean).slice(0, MAX_CANDIDATES) };
}

/**
 * What a page of kununu says, or null when it says nothing readable.
 * @param {{url: string, structured: string[]}|null} page  as structuredData returns it from the tab
 */
export function interpret(page) {
  if (!page || typeof page.url !== 'string') return null;
  const found = items(page.structured);
  if (isSearch(page.url)) return searchReading(found);
  const link = companyLink(page.url);
  return link ? companyReading(found, link) : null;
}

const forApp = ({ art, ...reading }) => reading;

async function readCompany(link, open) {
  const read = interpret(await open(link));
  return read && read.art === 'firma' ? forApp(read) : null;
}

/**
 * The reading for the app, or null when a page could not be read (the tab then stays for the person).
 * @param {{name: string, link?: string}} company
 * @param {(url: string) => Promise<{url: string, structured: string[]}>} open  loads a page in the tab and reads it
 */
export async function checkCompany(company, open) {
  const name = typeof company?.name === 'string' ? company.name.trim().slice(0, MAX_NAME) : '';
  if (!name) throw new Error(NO_NAME);
  const assigned = companyLink(company.link);
  if (assigned) return readCompany(assigned, open);
  for (const site of SITES) {
    const found = interpret(await open(searchUrl(name, site)));
    if (!found || found.art !== 'suche') return null;
    if (found.kandidaten.length === 1) return readCompany(found.kandidaten[0].link, open);
    if (found.kandidaten.length > 1) return { zustand: 'mehrere', kandidaten: found.kandidaten };
  }
  return { zustand: 'nicht_gefunden' };
}

/** Runs inside the kununu tab through scripting.executeScript, so it must stay self-contained. */
export function structuredData() {
  const maxBlocks = 20;
  const maxLength = 200000;
  const blocks = [...document.querySelectorAll('script[type="application/ld+json"]')].slice(0, maxBlocks);
  return { url: location.href, structured: blocks.map((block) => String(block.textContent || '').slice(0, maxLength)) };
}
