// Further sites of the search (MIN-348): queries, the run over a page without an adapter, the access to all pages.
import assert from 'node:assert/strict';
import { test } from 'node:test';

import { describePlan } from '../lib/progress.js';
import { runSearch } from '../lib/search.js';
import { MAX_SITE_QUERIES, MAX_SITE_TEXTS, followKey, formQueries, readOpenPage, searchSite, siteQueries } from '../lib/sites.js';

const SITE = { portal: 'beispiel.ch', adresse: 'https://www.beispiel.ch/suche?q={begriff}&ort={ort}' };
const PLAN = { stichworte: ['Daten', 'Büro & Verwaltung'], nischen: ['EdTech'], orte: ['Bern', 'Thun'], portale: [], weitere_seiten: [SITE], eigener_schluessel: true };

function job(id) {
  return { portal: 'beispiel.ch', portal_id: id, stelle: `Stelle ${id}`, link: `https://www.beispiel.ch/stelle/${id}` };
}

function fakeApp({ found = () => [job('1')], holen = (part) => part.map((h) => `${h.portal}:${h.portal_id}`), readError } = {}) {
  const calls = [];
  return {
    calls,
    sent: () => calls.filter(([, path]) => path === '/api/suche/treffer').flatMap(([, , data]) => data.treffer),
    async request(method, path, data) {
      calls.push([method, path, data]);
      if (path === '/api/suche/plan') return { plan: PLAN };
      if (path === '/api/suche/seite-lesen') {
        if (readError) throw new Error(readError);
        return { treffer: found(data) };
      }
      if (path === '/api/suche/sichten') return { holen: holen(data.treffer), bekannt: 0, gefiltert: [] };
      if (path === '/api/suche/treffer') return { neu: data.treffer.length };
      return {};
    },
  };
}

function fakeBrowser({ page = () => ({ title: 'T', text: 'Seitentext', links: [{ text: 'Stelle', href: 'https://www.beispiel.ch/stelle/1' }], wall: '' }), access = true } = {}) {
  const log = [];
  return {
    log,
    async openTab(url) { log.push(['open', url]); return 7; },
    async navigate(tab, url) { log.push(['navigate', url]); },
    async readOpen(tab) { log.push(['read']); return page(log.filter(([what]) => what === 'read').length); },
    async showWatching() { log.push(['watching']); },
    async closeTab(tab) { log.push(['close', tab]); },
    async hasAllPages() { return access; },
    async askAllPages() { log.push(['ask']); },
  };
}

function deps(overrides = {}) {
  return { app: fakeApp(), browser: fakeBrowser(), report: () => {}, sleep: async () => {}, ...overrides };
}

test('every term in every place, with the values encoded', () => {
  const { queries, skipped } = siteQueries(SITE, PLAN);
  assert.equal(skipped, 0);
  assert.equal(queries.length, 6);
  assert.equal(queries[0].url, 'https://www.beispiel.ch/suche?q=Daten&ort=Bern');
  assert.ok(queries.some((q) => q.url === 'https://www.beispiel.ch/suche?q=B%C3%BCro%20%26%20Verwaltung&ort=Thun'));
});

test('an address without {ort} runs once per term', () => {
  const { queries } = siteQueries({ ...SITE, adresse: 'https://a.ch/?q={begriff}' }, PLAN);
  assert.deepEqual(queries.map((q) => q.keyword), ['Daten', 'Büro & Verwaltung', 'EdTech']);
});

test('an address without placeholders runs once', () => {
  const { queries } = siteQueries({ ...SITE, adresse: 'https://a.ch/offene-stellen' }, PLAN);
  assert.deepEqual(queries.map((q) => q.url), ['https://a.ch/offene-stellen']);
});

test('{ort} without any place stays empty', () => {
  const { queries } = siteQueries(SITE, { ...PLAN, orte: [], nischen: [], stichworte: ['Daten'] });
  assert.equal(queries[0].url, 'https://www.beispiel.ch/suche?q=Daten&ort=');
});

test('the queries per site are limited', () => {
  const stichworte = Array.from({ length: 12 }, (_, n) => `B${n}`);
  const { queries, skipped } = siteQueries({ ...SITE, adresse: 'https://a.ch/?q={begriff}' }, { ...PLAN, stichworte, nischen: [] });
  assert.equal(queries.length, MAX_SITE_QUERIES);
  assert.equal(skipped, 2);
});

test('a page is read, screened and its new ads go to the app with their text', async () => {
  const d = deps();
  const summary = await searchSite(SITE, { ...PLAN, stichworte: ['Daten'], orte: ['Bern'], nischen: [] }, d);
  assert.deepEqual(summary, { treffer: 1, neu: 1, problem: '' });
  const read = d.app.calls.find(([, path]) => path === '/api/suche/seite-lesen')[2];
  assert.equal(read.portal, 'beispiel.ch');
  assert.equal(read.text, 'Seitentext');
  assert.deepEqual(d.app.sent().map((h) => [h.portal_id, h.text]), [['1', 'Seitentext']]);
  assert.deepEqual(d.browser.log.at(-1), ['close', 7]);
});

test('what the app does not want is not opened', async () => {
  const d = deps({ app: fakeApp({ holen: () => [] }) });
  await searchSite(SITE, { ...PLAN, stichworte: ['Daten'], orte: ['Bern'], nischen: [] }, d);
  assert.deepEqual(d.browser.log.filter(([what]) => what === 'navigate'), []);
});

test('a login or a check on the page stops the site and leaves it to the person', async () => {
  const d = deps({ browser: fakeBrowser({ page: () => ({ title: '', text: 'x', links: [], wall: 'anmeldung' }) }) });
  const summary = await searchSite(SITE, PLAN, d);
  assert.match(summary.problem, /Anmeldung/);
  assert.equal(d.app.calls.filter(([, path]) => path === '/api/suche/seite-lesen').length, 0);
  assert.equal(d.browser.log.filter(([what]) => what === 'read').length, 1);
});

test('a wall while reading ads keeps what came before', async () => {
  const pages = (n) => ({ title: '', text: `Text ${n}`, links: [{ text: 'x', href: 'https://www.beispiel.ch/x' }], wall: n === 3 ? 'pruefung' : '' });
  const app = fakeApp({ found: () => [job('1'), job('2')] });
  const d = deps({ app, browser: fakeBrowser({ page: pages }) });
  const summary = await searchSite(SITE, { ...PLAN, stichworte: ['Daten'], orte: ['Bern'], nischen: [] }, d);
  assert.deepEqual(app.sent().map((h) => h.portal_id), ['1']);
  assert.equal(summary.neu, 1);
  assert.match(summary.problem, /Prüfung/);
});

test('the ads of one run are limited, the rest comes next time', async () => {
  const many = Array.from({ length: MAX_SITE_TEXTS + 3 }, (_, n) => job(String(n)));
  const app = fakeApp({ found: () => many });
  const d = deps({ app });
  const summary = await searchSite(SITE, { ...PLAN, stichworte: ['Daten'], orte: ['Bern'], nischen: [] }, d);
  assert.equal(app.sent().length, MAX_SITE_TEXTS);
  assert.match(summary.problem, /nächsten Suche/);
});

test('an error of the AI ends the site with its message', async () => {
  const d = deps({ app: fakeApp({ readError: 'Das Guthaben reicht nicht.' }) });
  const summary = await searchSite(SITE, PLAN, d);
  assert.match(summary.problem, /Guthaben/);
  assert.equal(d.app.calls.filter(([, path]) => path === '/api/suche/seite-lesen').length, 1);
});

test('cancelling stops the site', async () => {
  const d = deps({ cancelled: () => true });
  const summary = await searchSite(SITE, PLAN, d);
  assert.match(summary.problem, /abgebrochen/);
});

test('a broken tab is a problem of this site only', async () => {
  const browser = { ...fakeBrowser(), openTab: async () => { throw new Error('Die Seite lädt nicht.'); } };
  const summary = await searchSite(SITE, PLAN, deps({ browser }));
  assert.match(summary.problem, /lädt nicht/);
});

test('with „Zuschauen“ the tab says so on every page', async () => {
  const d = deps();
  await searchSite(SITE, { ...PLAN, zuschauen: true, stichworte: ['Daten'], orte: ['Bern'], nischen: [] }, d);
  assert.ok(d.browser.log.filter(([what]) => what === 'watching').length >= 2);
});

test('the run takes the further sites along and names them in the summary', async () => {
  const d = deps();
  const result = await runSearch(d);
  assert.deepEqual(Object.keys(result.portale), ['beispiel.ch']);
  const finish = d.app.calls.find(([, path]) => path === '/api/suche/abschluss')[2];
  assert.ok(finish.portale['beispiel.ch']);
});

test('without access the run asks once and says what is missing', async () => {
  const d = deps({ browser: fakeBrowser({ access: false }) });
  const result = await runSearch(d);
  assert.deepEqual(d.browser.log, [['ask']]);
  assert.match(result.portale['beispiel.ch'].problem, /Zugriff/);
});

test('without further sites nothing asks for access', async () => {
  const app = fakeApp();
  const request = app.request;
  app.request = async (method, path, data) => (path === '/api/suche/plan' ? { plan: { ...PLAN, weitere_seiten: [] } } : request(method, path, data));
  const d = deps({ app, browser: fakeBrowser({ access: false }) });
  await runSearch(d);
  assert.deepEqual(d.browser.log, []);
});

test('the access is given back once the key is gone', async () => {
  const calls = [];
  const access = { remember: async () => calls.push('merken'), remembered: async () => calls.includes('merken'), release: async () => calls.push('abgeben') };
  await followKey({ eigener_schluessel: true }, access);
  assert.deepEqual(calls, ['merken']);
  await followKey({ eigener_schluessel: false }, access);
  assert.deepEqual(calls, ['merken', 'abgeben']);
});

test('without a key that was ever seen, the access stays: forms may have asked for it', async () => {
  const calls = [];
  const access = { remember: async () => calls.push('merken'), remembered: async () => false, release: async () => calls.push('abgeben') };
  await followKey({ eigener_schluessel: false }, access);
  await followKey(null, access);
  assert.deepEqual(calls, []);
});

test('the popup names the further sites', () => {
  const view = describePlan({ art: 'stelle', portale: ['jobs.ch'], weitere_seiten: [SITE] });
  assert.match(view.text, /jobs\.ch und beispiel\.ch/);
});

// The reader that runs in the tab, on a simulated page

function withPage({ text = 'Text', main = null, links = [], forms = [], password = null, captcha = null, href = 'https://www.beispiel.ch/suche', title = 'Titel' }, run) {
  const selectors = (selector) => {
    if (selector.includes('main')) return main ? { innerText: main } : null;
    if (selector.includes('password')) return password;
    if (selector.includes('captcha')) return captcha;
    return null;
  };
  globalThis.document = {
    title,
    body: { innerText: text },
    querySelector: selectors,
    querySelectorAll: (selector) => (selector === 'form' ? forms : links.map((link) => ({ innerText: link.text, href: link.href, getAttribute: () => link.aria || '' }))),
  };
  globalThis.location = { href, hostname: new URL(href).hostname };
  try {
    return run();
  } finally {
    delete globalThis.document;
    delete globalThis.location;
  }
}

test('the reader takes the main part of the page and the links with text', () => {
  const page = withPage({ main: 'Hauptteil', links: [{ text: ' Stelle  A ', href: 'https://www.beispiel.ch/a' }, { text: '', href: 'https://www.beispiel.ch/b' },
    { text: 'Mail', href: 'mailto:a@b.ch' }] }, readOpenPage);
  assert.equal(page.text, 'Hauptteil');
  assert.deepEqual(page.links, [{ text: 'Stelle A', href: 'https://www.beispiel.ch/a' }]);
  assert.equal(page.wall, '');
});

function form({ method = 'get', action = '/jobs', inputs }) {
  const attributes = { method, action };
  return {
    getAttribute: (name) => attributes[name] ?? null,
    querySelectorAll: () => inputs.map((input) => ({ type: 'text', name: '', id: '', placeholder: '', value: '', getAttribute: () => null, ...input })),
  };
}

test('the search form of a page is found with its fields, also with odd names', () => {
  const inputs = [{ name: 'q', placeholder: 'Stelle, Firma' }, { name: 'l', id: 'text-input-where' }, { type: 'hidden', name: 'from', value: 'home' }];
  const { searchForm } = withPage({ href: 'https://ch.indeed.example/', forms: [form({ inputs })] }, readOpenPage);
  assert.deepEqual(searchForm, { action: 'https://ch.indeed.example/jobs', term: 'q', place: 'l', hidden: [['from', 'home']] });
  const typed = withPage({ forms: [form({ inputs: [{ type: 'search', name: 'x7' }] })] }, readOpenPage).searchForm;
  assert.equal(typed.term, 'x7');
  assert.equal(typed.place, '');
});

test('a place field is not taken for the search term', () => {
  const inputs = [{ type: 'search', name: 'ort' }, { type: 'search', name: 'suche' }];
  const { searchForm } = withPage({ forms: [form({ inputs })] }, readOpenPage);
  assert.deepEqual([searchForm.term, searchForm.place], ['suche', 'ort']);
});

test('forms that send something or sign in are no search form', () => {
  const field = [{ name: 'q' }];
  for (const other of [
    form({ method: 'post', inputs: field }),
    form({ action: '/newsletter/subscribe', inputs: field }),
    form({ action: '/login', inputs: field }),
    form({ inputs: [{ name: 'q' }, { type: 'password', name: 'p' }] }),
    form({ action: 'http://www.beispiel.ch/jobs', inputs: field }),
    form({ inputs: [{ name: 'email' }] }),
    form({ action: 'https://jobs.beispiel.ch:8443/suche', inputs: field }),
  ]) {
    assert.equal(withPage({ forms: [other] }, readOpenPage).searchForm, null);
  }
});

test('a check of the kind big portals show is a wall by its title', () => {
  assert.equal(withPage({ title: 'Just a moment...' }, readOpenPage).wall, 'pruefung');
  assert.equal(withPage({ title: 'Sicherheitsprüfung' }, readOpenPage).wall, 'pruefung');
});

test('a search form makes the queries: term and place, hidden fields kept, values encoded', () => {
  const found = { action: 'https://a.ch/jobs', term: 'q', place: 'l', hidden: [['from', 'home']] };
  const { queries } = formQueries(found, { stichworte: ['Büro & Verwaltung'], nischen: [], orte: ['Bern', 'Thun'] });
  assert.deepEqual(queries.map((q) => q.url), ['https://a.ch/jobs?from=home&q=B%C3%BCro+%26+Verwaltung&l=Bern']);
});

test('searching all of Switzerland leaves the place of the form empty', () => {
  const found = { action: 'https://a.ch/jobs', term: 'q', place: 'l', hidden: [] };
  const { queries } = formQueries(found, { stichworte: ['Koch'], nischen: [], orte: ['Thun'], schweizweit: true });
  assert.deepEqual(queries.map((q) => q.url), ['https://a.ch/jobs?q=Koch']);
});

const PLAIN = { portal: 'beispiel.ch', adresse: 'https://www.beispiel.ch/' };
const PLAIN_FORM = { action: 'https://www.beispiel.ch/jobs', term: 'q', place: '', hidden: [] };
const pageOf = (searchForm) => () => ({ title: 'T', text: 'Seitentext', links: [{ text: 'Stelle', href: 'https://www.beispiel.ch/stelle/1' }], wall: '', searchForm });

test('with only the address the search reads the page and then uses its search form', async () => {
  const d = deps({ browser: fakeBrowser({ page: pageOf(PLAIN_FORM) }), app: fakeApp({ holen: () => [] }) });
  await searchSite(PLAIN, { ...PLAN, stichworte: ['Koch', 'Bäcker'], nischen: [] }, d);
  const visited = d.browser.log.filter(([what]) => what === 'open' || what === 'navigate').map(([, url]) => url);
  assert.deepEqual(visited, ['https://www.beispiel.ch/', 'https://www.beispiel.ch/jobs?q=Koch', 'https://www.beispiel.ch/jobs?q=B%C3%A4cker']);
});

test('the start page and the searches together stay within the limit', async () => {
  const d = deps({ browser: fakeBrowser({ page: pageOf(PLAIN_FORM) }), app: fakeApp({ holen: () => [] }) });
  const many = Array.from({ length: 20 }, (_, i) => `Beruf ${i}`);
  await searchSite(PLAIN, { ...PLAN, stichworte: many, nischen: [] }, d);
  assert.equal(d.browser.log.filter(([what]) => what === 'read').length, MAX_SITE_QUERIES);
});

test('a form that leads to another site is not used', async () => {
  const d = deps({ browser: fakeBrowser({ page: pageOf({ ...PLAIN_FORM, action: 'https://anderswo.ch/jobs' }) }), app: fakeApp({ holen: () => [] }) });
  await searchSite(PLAIN, { ...PLAN, stichworte: ['Koch'], nischen: [] }, d);
  assert.equal(d.browser.log.filter(([what]) => what === 'read').length, 1);
});

test('nothing found says what the person can do', async () => {
  const d = deps({ browser: fakeBrowser({ page: pageOf(null) }), app: fakeApp({ found: () => [] }) });
  const summary = await searchSite(PLAIN, { ...PLAN, stichworte: ['Koch'], nischen: [] }, d);
  assert.match(summary.problem, /keine Stellen gefunden/);
});

test('ads whose title fits a search term come first, so the limit takes those', async () => {
  const hits = [{ ...job('1'), stelle: 'Marketing' }, { ...job('2'), stelle: 'Koch EFZ' }];
  const d = deps({ browser: fakeBrowser({ page: pageOf(null) }), app: fakeApp({ found: () => hits }) });
  await searchSite(PLAIN, { ...PLAN, stichworte: ['Koch'], nischen: [] }, d);
  assert.deepEqual(d.app.sent().map((h) => h.portal_id), ['2', '1']);
});

test('a redirect of the start page names the address to enter instead', async () => {
  const d = deps({ browser: fakeBrowser({ page: () => ({ title: '', text: 'x', links: [], wall: '', host: 'ch.anderswo.ch' }) }) });
  const summary = await searchSite(PLAIN, PLAN, d);
  assert.match(summary.problem, /ch\.anderswo\.ch/);
});

test('a link without text may use its label, and each address counts once', () => {
  const page = withPage({ links: [{ text: '', aria: 'Stelle B', href: 'https://a.ch/b' }, { text: 'nochmals', href: 'https://a.ch/b' }] }, readOpenPage);
  assert.deepEqual(page.links, [{ text: 'Stelle B', href: 'https://a.ch/b' }]);
});

test('a visible password field or a login address is a wall', () => {
  assert.equal(withPage({ password: { offsetParent: {} } }, readOpenPage).wall, 'anmeldung');
  assert.equal(withPage({ href: 'https://www.beispiel.ch/login?next=x' }, readOpenPage).wall, 'anmeldung');
  assert.equal(withPage({ href: 'https://www.beispiel.ch/authwall' }, readOpenPage).wall, 'anmeldung');
});

test('a hidden password field is no wall: the list may be readable', () => {
  assert.equal(withPage({ password: { offsetParent: null } }, readOpenPage).wall, '');
});

test('a visible check is a wall', () => {
  assert.equal(withPage({ captcha: { offsetParent: {} } }, readOpenPage).wall, 'pruefung');
});

test('a redirect to another host ends the site: it may be a login, and its text is no ad', async () => {
  const d = deps({ browser: fakeBrowser({ page: () => ({ title: '', text: 'x', links: [], wall: '', host: 'login.anderswo.ch' }) }) });
  const summary = await searchSite(SITE, PLAN, d);
  assert.match(summary.problem, /andere Seite/);
  assert.equal(d.app.calls.filter(([, path]) => path === '/api/suche/seite-lesen').length, 0);
});

test('a subdomain of the site is still the site', async () => {
  const page = () => ({ title: 'T', text: 'Seitentext', links: [], wall: '', host: 'jobs.beispiel.ch' });
  const summary = await searchSite(SITE, { ...PLAN, stichworte: ['Daten'], orte: ['Bern'], nischen: [] }, deps({ browser: fakeBrowser({ page }) }));
  assert.equal(summary.problem, '');
});

test('an ad that redirects away is not stored with foreign text', async () => {
  const page = (n) => ({ title: '', text: `Text ${n}`, links: [], wall: '', host: n === 1 ? 'www.beispiel.ch' : 'anderswo.ch' });
  const d = deps({ browser: fakeBrowser({ page }) });
  const summary = await searchSite(SITE, { ...PLAN, stichworte: ['Daten'], orte: ['Bern'], nischen: [] }, d);
  assert.deepEqual(d.app.sent(), []);
  assert.match(summary.problem, /andere Seite/);
});

test('an ad without readable text is named in the summary', async () => {
  const page = (n) => ({ title: '', text: n === 1 ? 'Liste' : '', links: [], wall: '', host: 'www.beispiel.ch' });
  const summary = await searchSite(SITE, { ...PLAN, stichworte: ['Daten'], orte: ['Bern'], nischen: [] }, deps({ browser: fakeBrowser({ page }) }));
  assert.match(summary.problem, /ohne lesbaren Text/);
});

test('the same term twice runs once', () => {
  const { queries } = siteQueries({ ...SITE, adresse: 'https://a.ch/?q={begriff}' }, { ...PLAN, stichworte: ['Daten'], nischen: ['Daten'] });
  assert.equal(queries.length, 1);
});

test('an address that needs a term, without any term, says so', async () => {
  const d = deps();
  const summary = await searchSite(SITE, { ...PLAN, stichworte: [], nischen: [] }, d);
  assert.match(summary.problem, /Suchbegriffe/);
  assert.deepEqual(d.browser.log, []);
});

test('a fixed page reports its site instead of an empty term', async () => {
  const steps = [];
  const d = deps({ report: (step) => steps.push(step) });
  await searchSite({ ...SITE, adresse: 'https://www.beispiel.ch/offen' }, PLAN, d);
  assert.equal(steps[0].stichwort, 'beispiel.ch');
});

test('an unknown state of the key changes nothing: a locked keychain must not cost the access', async () => {
  const calls = [];
  const access = { remember: async () => calls.push('merken'), remembered: async () => true, release: async () => calls.push('abgeben') };
  await followKey({ eigener_schluessel: null }, access);
  assert.deepEqual(calls, []);
});

test('a failing release does not stop the search', async () => {
  const access = { remember: async () => {}, remembered: async () => true, release: async () => { throw new Error('nein'); } };
  await followKey({ eigener_schluessel: false }, access);
});

test('links inside the main part come first: menus must not use up the limit', () => {
  const menu = { innerText: 'Menü', href: 'https://a.ch/menu', getAttribute: () => '' };
  const job = { innerText: 'Stelle', href: 'https://a.ch/stelle', getAttribute: () => '' };
  globalThis.document = {
    title: '', body: { innerText: 'x' },
    querySelector: (s) => (s.includes('main') ? { innerText: 'x', querySelectorAll: () => [job] } : null),
    querySelectorAll: () => [menu, job],
  };
  globalThis.location = { href: 'https://a.ch/', hostname: 'a.ch' };
  try {
    assert.deepEqual(readOpenPage().links.map((l) => l.text), ['Stelle', 'Menü']);
    assert.equal(readOpenPage().host, 'a.ch');
  } finally {
    delete globalThis.document;
    delete globalThis.location;
  }
});
