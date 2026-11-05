// Further sites the person named (MIN-348): no adapter, the AI of the app reads the list from the page's text.
// The person enters only an address (MIN-387): the search uses the search form of that page if it finds one.
// Only with an own API key, only after the person started the search. Sign-ins and checks stay with the person:
// a page that asks for one ends the search on that site. The text of a page is data, nothing here acts on it.

import { chunks, hitKey } from './queries.js';
import { CANCELLED, screen, stopIfCancelled } from './steps.js';

export const MAX_SITE_QUERIES = 10; // pages per run on one site, the start page included
export const MAX_SITE_TEXTS = 30;
const SETTLE_MS = 1500; // lists of such pages often appear after the load event
const SITE_DELAY_MS = 3000; // gentler than on the portals: nobody agreed on anything with these sites
const SEND_SIZE = 10;
const NOTHING_FOUND = 'Hier wurden keine Stellen gefunden. Öffnen Sie im Browser die Seite mit den offenen Stellen und tragen Sie deren Adresse ein.';
const WALL_LOGIN = 'anmeldung';
const WALLS = {
  [WALL_LOGIN]: 'verlangt eine Anmeldung',
  pruefung: 'verlangt eine Prüfung (CAPTCHA)',
};

function searchTerms(plan) {
  return [...new Set([...(plan.stichworte || []), ...(plan.nischen || [])])];
}

function hasPlaceholders(site) {
  return /\{(begriff|ort)\}/.test(site.adresse);
}

/** Term × place of the plan, as far as the address has places for them. */
export function siteQueries(site, plan) {
  const terms = searchTerms(plan);
  const wantsTerm = site.adresse.includes('{begriff}');
  const wantsPlace = site.adresse.includes('{ort}');
  const places = wantsPlace && (plan.orte || []).length ? plan.orte : [''];
  const combos = wantsTerm
    ? terms.flatMap((keyword) => places.map((place) => ({ keyword, place })))
    : places.map((place) => ({ keyword: '', place }));
  const queries = combos.map(({ keyword, place }) => ({
    keyword,
    url: site.adresse.replaceAll('{begriff}', encodeURIComponent(keyword)).replaceAll('{ort}', encodeURIComponent(place)),
  }));
  return { queries: queries.slice(0, MAX_SITE_QUERIES), skipped: Math.max(0, queries.length - MAX_SITE_QUERIES) };
}

/**
 * The addresses for the search form of a page: the same as typing into it, without touching the page.
 * One place only, so the limit goes to the terms; in a search all over Switzerland none, hits near the home come first anyway.
 */
export function formQueries(form, plan) {
  const place = form.place && !plan.schweizweit ? (plan.orte || [])[0] : '';
  const queries = searchTerms(plan).map((keyword) => {
    const url = new URL(form.action);
    form.hidden.forEach(([name, value]) => url.searchParams.set(name, value));
    url.searchParams.set(form.term, keyword);
    if (place) url.searchParams.set(form.place, place);
    return { keyword, url: url.href };
  });
  const limit = MAX_SITE_QUERIES - 1;
  return { queries: queries.slice(0, limit), skipped: Math.max(0, queries.length - limit) };
}

/** Runs inside the tab through scripting.executeScript, so it must stay self-contained. */
export function readOpenPage() {
  const maxText = 30000;
  const maxLinks = 2000;
  const maxLinkText = 200;
  const visible = (element) => Boolean(element && element.offsetParent);
  const loginAddress = /\/(login|signin|sign-in|anmelden|authwall|checkpoint)\b/i;
  const checkTitle = /just a moment|nur einen moment|security check|sicherheitsprüfung|verify you are human/i;
  const termField = /(^|[^a-z])(q|query|keywords?|search|suche?n?|suchbegriff|begriff|stichw\w*|what|was|jobtitle|beruf|titel|title)([^a-z]|$)/i;
  const placeField = /(^|[^a-z])(l|where|wo|ort|location|city|place|plz|zip|region|standort)([^a-z]|$)/i;
  const notSearch = /log-?in|log-?out|sign-?in|sign-?out|anmeld|abmeld|newsletter|subscribe|abonn|kontakt|contact/i;
  const describe = (input) => [input.name, input.id, input.placeholder, input.getAttribute('aria-label')].filter(Boolean).join(' ');

  // Only forms that open a page with GET: the same as a link, nothing gets sent. A form without such fields is no search.
  const toSearchForm = (form) => {
    const action = form.getAttribute('action') || location.href;
    if ((form.getAttribute('method') || 'get').toLowerCase() !== 'get' || notSearch.test(action)) return null;
    const inputs = [...form.querySelectorAll('input')];
    if (inputs.some((input) => input.type === 'password')) return null;
    const fields = inputs.filter((input) => input.name && (input.type === 'search' || input.type === 'text'));
    const isPlace = (input) => placeField.test(describe(input));
    const term = fields.find((input) => termField.test(describe(input)) && !isPlace(input))
      || fields.find((input) => input.type === 'search' && !isPlace(input));
    if (!term) return null;
    const url = new URL(action, location.href);
    if (url.protocol !== 'https:' || url.port) return null;
    const hidden = inputs.filter((input) => input.type === 'hidden' && input.name).slice(0, 20);
    return {
      action: `${url.origin}${url.pathname}`,
      term: term.name,
      place: fields.find((input) => input !== term && isPlace(input))?.name || '',
      hidden: hidden.map((input) => [input.name, String(input.value || '').slice(0, 200)]),
    };
  };
  const main = document.querySelector('main, [role="main"]');
  const links = new Map();
  // The main part first: on larger sites menus and footers would use up the limit of the app.
  const inMain = main?.querySelectorAll ? [...main.querySelectorAll('a[href]')] : [];
  for (const link of [...inMain, ...document.querySelectorAll('a[href]')].slice(0, maxLinks)) {
    const text = (link.innerText || link.getAttribute('aria-label') || '').trim().replace(/\s+/g, ' ').slice(0, maxLinkText);
    if (text && /^https:/.test(link.href) && !links.has(link.href)) links.set(link.href, { text, href: link.href });
  }
  let wall = '';
  if (loginAddress.test(new URL(location.href).pathname) || visible(document.querySelector('input[type="password"]'))) wall = 'anmeldung';
  else if (checkTitle.test(document.title || '') || visible(document.querySelector('iframe[src*="captcha"], .g-recaptcha, .h-captcha, .cf-turnstile, #captcha, #challenge-form'))) wall = 'pruefung';
  return {
    title: (document.title || '').slice(0, 300),
    text: ((main && main.innerText) || document.body?.innerText || '').slice(0, maxText),
    links: [...links.values()],
    wall,
    host: location.hostname,
    searchForm: [...document.querySelectorAll('form')].map((form) => {
      try {
        return toSearchForm(form);
      } catch {
        return null; // an action that is no address
      }
    }).find(Boolean) || null,
  };
}

function onSite(page, site) {
  return !page.host || page.host === site.portal || page.host.endsWith(`.${site.portal}`);
}

/** Why this page cannot be used, or '': a login, a check, or a redirect, whose text would not belong to the site. */
function pageProblem(page, site) {
  if (page.wall) return `${site.portal} ${WALLS[page.wall] || WALLS[WALL_LOGIN]}. Das bleibt bei Ihnen: Seite selbst öffnen, danach nochmals suchen.`;
  if (!onSite(page, site)) return `${site.portal} leitet auf eine andere Seite weiter (${String(page.host).slice(0, 100)}), zum Beispiel zu einer Anmeldung. Die Suche dort hört hier auf. Ist das die richtige Seite, tragen Sie deren Adresse ein.`;
  return '';
}

/** A tab that starts on the first query's page. */
function pageOpener(plan, site, deps) {
  let tab = null;
  return {
    tab: () => tab,
    async go(url) {
      if (tab === null) tab = await deps.browser.openTab(url, Boolean(plan.zuschauen));
      else await deps.browser.navigate(tab, url);
      if (plan.zuschauen) await deps.browser.showWatching(tab, site.portal);
      await deps.sleep(SETTLE_MS);
      return deps.browser.readOpen(tab);
    },
  };
}

/** One page into the list of hits; returns what stops this site, or ''. */
async function visit(url, keyword, site, found, pages, deps) {
  stopIfCancelled(deps);
  deps.report({ portal: site.portal, phase: 'suche', stichwort: keyword || site.portal, seite: 1, gefunden: found.size });
  const page = await pages.go(url);
  const problem = pageProblem(page, site);
  if (problem) return { problem };
  try {
    const answer = await deps.app.request('POST', '/api/suche/seite-lesen', { portal: site.portal, titel: page.title, text: page.text, links: page.links });
    for (const hit of answer.treffer) found.set(hitKey(hit), hit);
  } catch (error) {
    return { problem: error.message };
  }
  await deps.sleep(SITE_DELAY_MS);
  return { page };
}

async function runQueries({ queries, skipped }, site, found, pages, deps) {
  const notes = skipped ? [`${skipped} Suchen ausgelassen (höchstens ${queries.length}).`] : [];
  for (const query of queries) {
    const { problem } = await visit(query.url, query.keyword, site, found, pages, deps);
    if (problem) return [...notes, problem];
  }
  return notes;
}

/** Only the address: the page itself, then its search form, if that stays on the site. */
async function listFromAddress(site, plan, found, pages, deps) {
  const { page, problem } = await visit(site.adresse, '', site, found, pages, deps);
  if (problem) return [problem];
  const form = page.searchForm;
  if (!form || !onSite({ host: new URL(form.action).hostname }, site)) return [];
  return runQueries(formQueries(form, plan), site, found, pages, deps);
}

async function listAll(site, plan, pages, deps) {
  const found = new Map();
  if (!hasPlaceholders(site)) return { found, notes: await listFromAddress(site, plan, found, pages, deps) };
  const planned = siteQueries(site, plan);
  if (!planned.queries.length) return { found, notes: ['Im Suchprofil fehlen Suchbegriffe für diese Adresse.'] };
  return { found, notes: await runQueries(planned, site, found, pages, deps) };
}

/** A fixed list can hold anything: what fits the search goes first, so the limit of texts takes those. */
function fittingFirst(hits, plan) {
  const terms = searchTerms(plan).map((term) => term.toLowerCase());
  const fits = (hit) => terms.some((term) => String(hit.stelle || '').toLowerCase().includes(term));
  return [...hits.filter(fits), ...hits.filter((hit) => !fits(hit))];
}

async function sendTexts(site, wanted, pages, deps) {
  let added = 0;
  let done = 0;
  let missing = 0;
  for (const part of chunks(wanted, SEND_SIZE)) {
    const full = [];
    let stop = '';
    for (const hit of part) {
      stopIfCancelled(deps);
      deps.report({ portal: site.portal, phase: 'texte', fertig: done, von: wanted.length });
      done += 1;
      const page = await pages.go(hit.link);
      await deps.sleep(SITE_DELAY_MS);
      stop = pageProblem(page, site);
      if (stop) break;
      if (!page.text) missing += 1;
      full.push({ ...hit, text: page.text || '' });
    }
    if (full.length) added += (await deps.app.request('POST', '/api/suche/treffer', { treffer: full })).neu;
    if (stop) return { added, missing, note: stop };
  }
  return { added, missing, note: '' };
}

/** Search one further site; problems end up in the summary. */
export async function searchSite(site, plan, deps) {
  const pages = pageOpener(plan, site, deps);
  try {
    const { found, notes } = await listAll(site, plan, pages, deps);
    const wanted = fittingFirst(await screen(found, deps.app), plan);
    const left = wanted.length - MAX_SITE_TEXTS;
    const { added, missing, note } = await sendTexts(site, wanted.slice(0, MAX_SITE_TEXTS), pages, deps);
    const later = left > 0 ? `${left} Inserate kommen bei der nächsten Suche.` : '';
    const empty = missing ? `${missing} Inserate ohne lesbaren Text.` : '';
    const nothing = !found.size && !notes.length ? NOTHING_FOUND : '';
    return { treffer: found.size, neu: added, problem: [...notes, nothing, note, empty, later].filter(Boolean).join(' ') };
  } catch (error) {
    if (error.cancelled || deps.cancelled?.()) return { treffer: 0, neu: 0, problem: `${site.portal}: ${CANCELLED}` };
    return { treffer: 0, neu: 0, problem: `${site.portal}: ${error.message}` };
  } finally {
    if (pages.tab() !== null) await deps.browser.closeTab(pages.tab()).catch(() => {});
  }
}

/** All further sites of the plan. The browser only asks for the access after a click: without it, one page explains. */
export async function searchSites(plan, deps) {
  const sites = plan.weitere_seiten || [];
  if (!sites.length) return {};
  const missing = `Zugriff fehlt. Eine Seite der Erweiterung fragt danach; nach dem Erlauben nochmals suchen.`;
  if (!(await deps.browser.hasAllPages())) {
    await deps.browser.askAllPages();
    return Object.fromEntries(sites.map((site) => [site.portal, { treffer: 0, neu: 0, problem: missing }]));
  }
  const results = {};
  for (const site of sites) {
    if (deps.cancelled?.()) break;
    results[site.portal] = await searchSite(site, plan, deps);
  }
  return results;
}

/**
 * The access to all pages goes with the key. Forms may have asked for it without a key: it is only given back
 * when this extension has seen a key before, also when the app was not reachable at the moment of removing it.
 * `eigener_schluessel` is null when the keychain cannot tell (locked): that changes nothing. A failure here must not
 * stop a search; the next contact with the app tries again, because the mark is only cleared after giving back.
 */
export async function followKey(plan, access) {
  if (!plan) return;
  try {
    if (plan.eigener_schluessel === true) await access.remember();
    else if (plan.eigener_schluessel === false && await access.remembered()) await access.release();
  } catch {
    // see above
  }
}
