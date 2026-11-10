// The ad on the open page (MIN-345): readPage runs in the tab after a click, the rest here works on what it returned.
// All of it is data from a foreign page: it is shown with textContent and goes to the app as text.

export const MAX_TEXT = 30000;
const MIN_SELECTION = 100;
const MIN_POSTING = 40;
const MIN_PAGE_TEXT = 400;
const MIN_JOB_WORDS = 2;
const JOB_WORDS = /\b(bewerb\w*|stelle\w*|aufgaben|anforderung\w*|profil|pensum|arbeitsort|lehrstelle|lehrbeginn|apply|application|responsibilit\w*|requirements?|qualifications?|vacancy|candidat\w*|poste|emploi|mansioni)\b/gi;
const PORTALS = /^(linkedin|indeed|xing|glassdoor|jobs\.ch|jobscout24|jobup|monster|stepstone)/i;
const LINKEDIN_TITLE = /^([^|]{1,150}?) (?:hiring|sucht|recrute|cerca) ([^|]{1,150}?) (?:in|à|a) ([^|]{1,150}?) \| LinkedIn/;
// Signed in there is no og:title: the tab says "(3) Job | Company | LinkedIn". Other pages have fewer parts.
const LINKEDIN_TAB = /^(?:\(\d+\) )?([^|]{1,150}?) \| ([^|]{1,150}?) \| LinkedIn$/;
const LINKEDIN_HOST = /^(?:[a-z]{2,3}\.|www\.)?linkedin\.com$/;
const LINKEDIN_AD_PATH = /^\/jobs\/view\/(?:[^/]*-)?(\d+)\/?$/;
const LINKEDIN_AD_ID = /^\d+$/;
const MAX_FIELD = 300;
const MAX_DESCRIPTION = 60000;
const ROUTE_FRAGMENT = /#!?\//;
const ENTITIES = { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ' };
export const NO_AD = 'Auf dieser Seite wurde kein Inserat gefunden. Den Inseratstext markieren und nochmals versuchen.';

/** Runs inside the tab through scripting.executeScript, so it must stay self-contained. */
export function readPage() {
  const meta = (name) => document.querySelector(`meta[property="${name}"], meta[name="${name}"]`)?.content || '';
  const limit = 200000;
  const field = 300;
  // The main part of the page where it has one: side panels may show messages and names of other people.
  const main = document.querySelector('main, [role="main"], article');
  // The link to the company's page beside the title of the ad; a page may list other companies further away.
  const companyIn = (box) => [...box.querySelectorAll('a[href*="/company/"]')].map((link) => (link.innerText || '').trim().split('\n')[0]).find(Boolean) || '';
  const companyLink = () => {
    let box = document.querySelector('h1');
    for (let level = 0; box && level < 8; level += 1, box = box.parentElement) {
      const name = companyIn(box);
      if (name) return name;
    }
    return main ? companyIn(main) : '';
  };
  return {
    url: location.href,
    title: (document.title || '').slice(0, field),
    heading: (document.querySelector('h1')?.innerText || '').trim().slice(0, field),
    siteName: meta('og:site_name').slice(0, field),
    ogTitle: meta('og:title').slice(0, field),
    companyLink: companyLink().slice(0, field),
    structured: [...document.querySelectorAll('script[type="application/ld+json"]')].slice(0, 20).map((s) => s.textContent.slice(0, limit)),
    selection: String(globalThis.getSelection?.() || '').trim().slice(0, limit),
    text: ((main && main.innerText) || document.body?.innerText || '').slice(0, limit),
  };
}

function character(code) {
  return code > 0 && code <= 0x10ffff ? String.fromCodePoint(code) : '';
}

/** Without script and style blocks; searched step by step, because a page can leave thousands of them open. */
function withoutBlocks(html) {
  const lower = html.toLowerCase();
  const parts = [];
  let at = 0;
  for (;;) {
    const openings = ['<script', '<style'].map((tag) => lower.indexOf(tag, at)).filter((index) => index >= 0);
    if (!openings.length) return parts.join('') + html.slice(at);
    const open = Math.min(...openings);
    parts.push(html.slice(at, open));
    const closing = lower.startsWith('<script', open) ? '</script' : '</style';
    const end = lower.indexOf(closing, open);
    if (end < 0) return parts.join('');
    const close = lower.indexOf('>', end);
    if (close < 0) return parts.join('');
    at = close + 1;
  }
}

/** Plain text from the HTML of a description; it is never parsed as a page. */
export function cleanHtml(html) {
  return withoutBlocks(String(html || '').slice(0, MAX_DESCRIPTION))
    .replace(/<(?:br|\/p|\/li|\/div|\/h\d|\/ul)\b[^<>]*>/gi, '\n')
    .replace(/<[^<>]*>/g, '')
    .replace(/&#x([0-9a-f]+);/gi, (_, code) => character(parseInt(code, 16)))
    .replace(/&#(\d+);/g, (_, code) => character(Number(code)))
    .replace(/&(amp|lt|gt|quot|apos|nbsp);/g, (_, name) => ENTITIES[name])
    .replace(/[ \t ]+/g, ' ')
    .trim();
}

function isPosting(item) {
  const type = item && item['@type'];
  return Array.isArray(type) ? type.includes('JobPosting') : type === 'JobPosting';
}

function findPosting(value, depth = 0) {
  if (!value || typeof value !== 'object' || depth > 4) return null;
  if (Array.isArray(value)) return value.map((item) => findPosting(item, depth + 1)).find(Boolean) || null;
  return isPosting(value) ? value : findPosting(value['@graph'], depth + 1);
}

function parsed(text) {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

/** The schema.org JobPosting of the page, if it has one. */
export function jobPosting(structured) {
  return structured.map((text) => findPosting(parsed(text))).find(Boolean) || null;
}

const text = (value) => (typeof value === 'string' ? value.trim() : '');

function placeOf(location) {
  const first = Array.isArray(location) ? location[0] : location;
  const address = first && typeof first === 'object' ? first.address : null;
  if (typeof address === 'string') return address.trim();
  return text(address && address.addressLocality);
}

function companyOf(organisation) {
  return typeof organisation === 'string' ? organisation.trim() : text(organisation && organisation.name);
}

function looksLikeAd(pageText) {
  return pageText.length >= MIN_PAGE_TEXT && (pageText.match(JOB_WORDS) || []).length >= MIN_JOB_WORDS;
}

function body(page, posting) {
  if (page.selection.length >= MIN_SELECTION) return { inhalt: page.selection, quelle: 'markiert' };
  const description = posting ? cleanHtml(posting.description) : '';
  if (description.length >= MIN_POSTING) return { inhalt: description, quelle: 'strukturiert' };
  return looksLikeAd(page.text.trim()) ? { inhalt: page.text.trim(), quelle: 'seite' } : null;
}

function withoutFragment(url) {
  return ROUTE_FRAGMENT.test(url) ? url : url.split('#')[0];
}

/** The number of the ad on LinkedIn: in the path, or in the list where the person opened it beside other ads. */
function linkedinAd(url) {
  let parts;
  try {
    parts = new URL(url);
  } catch {
    return '';
  }
  if (!LINKEDIN_HOST.test(parts.hostname)) return '';
  const inPath = parts.pathname.match(LINKEDIN_AD_PATH);
  if (inPath) return inPath[1];
  const inList = parts.searchParams.get('currentJobId') || '';
  return parts.pathname.startsWith('/jobs/') && LINKEDIN_AD_ID.test(inList) ? inList : '';
}

/** One address per ad: lists on LinkedIn carry the search in theirs, and „Bewerben“ should open the ad. */
function adLink(url) {
  const id = linkedinAd(url);
  return id ? `https://www.linkedin.com/jobs/view/${id}/` : withoutFragment(url);
}

function cut(value) {
  return String(value || '').slice(0, MAX_FIELD);
}

/** Title, company, place, link and text of the ad, or {fehler} instead of an empty entry. */
export function toAd(page) {
  const posting = jobPosting(page.structured);
  const found = body(page, posting);
  if (!found) return { fehler: NO_AD };
  const ogTitle = cut(page.ogTitle);
  const pageTitle = cut(page.title);
  const siteName = cut(page.siteName);
  const linkedin = ogTitle.match(LINKEDIN_TITLE) || [];
  const onLinkedin = Boolean(linkedinAd(page.url));
  const linkedinTab = (onLinkedin && pageTitle.match(LINKEDIN_TAB)) || [];
  const companyLink = onLinkedin ? cut(page.companyLink) : '';
  const tail = pageTitle.split(/\s[|–—-]\s/)[0].trim();
  return {
    stelle: cut(text(posting && posting.title) || linkedin[2] || linkedinTab[1] || page.heading || ogTitle || tail),
    firma: cut(companyOf(posting && posting.hiringOrganization) || linkedin[1] || linkedinTab[2] || companyLink || (PORTALS.test(siteName) ? '' : siteName)),
    ort: cut(placeOf(posting && posting.jobLocation) || linkedin[3] || ''),
    link: adLink(page.url),
    text: found.inhalt.slice(0, MAX_TEXT),
    quelle: found.quelle,
  };
}

/** Only web pages, and not the pages of the running app itself. */
export function canCheck(url, appUrl) {
  if (!/^https?:\/\//.test(url || '')) return false;
  return !(appUrl && new URL(url).origin === new URL(appUrl).origin);
}

function listLine(label, items) {
  return Array.isArray(items) && items.length ? [{ text: `${label}: ${items.join('; ')}` }] : [];
}

/** The answer of a check as title and lines for the popup. */
export function describeCheck({ bewertung, vorhanden, hinweis }) {
  const known = vorhanden ? [{ text: `Schon im Register: ${vorhanden.firma} – ${vorhanden.stelle} (${vorhanden.status})`, problem: true }] : [];
  return {
    titel: `Note ${bewertung.note}`,
    zeilen: [
      ...known,
      ...(bewertung.zusammenfassung ? [{ text: bewertung.zusammenfassung }] : []),
      ...listLine('Passt', bewertung.passt),
      ...listLine('Haken', bewertung.haken),
      ...listLine('Neue Lücken', bewertung.neue_luecken),
      ...(bewertung.unsicher ? [{ text: `Note unsicher: ${bewertung.unsicher}` }] : []),
      ...(hinweis ? [{ text: hinweis }] : []),
      ...(bewertung.auffaellig && bewertung.auffaellig.length
        ? [{ text: `Auffällig im Inserat, von der KI nicht befolgt: ${bewertung.auffaellig.join('; ')}`, problem: true }] : []),
    ],
  };
}

/** What is still needed before asking the app; saving makes a register entry, so it needs a company. */
export function missingField(ad, saving) {
  if (!ad.stelle.trim()) return 'Bitte die Stelle eintragen.';
  return saving && !ad.firma.trim() ? 'Bitte die Firma eintragen.' : '';
}

/** Results belong to one ad: several ads can share an address. Corrected title or company do not change it. */
export function adKey(ad) {
  let hash = 5381;
  for (let i = 0; i < ad.text.length; i += 1) hash = (hash * 33 + ad.text.charCodeAt(i)) % 2147483647;
  return `${ad.link}|${hash}`;
}

/** Said when the whole page was read, because more than the ad may then reach the AI. */
export function sourceHint(source) {
  return source === 'seite' ? 'Gelesen wurde der Text der ganzen Seite. Genauer wird es, wenn nur der Inseratstext markiert ist.' : '';
}
