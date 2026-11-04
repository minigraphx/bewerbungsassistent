// Search run, queries, progress and app connection of the extension (MIN-339), with simulated tabs and app.
import assert from 'node:assert/strict';
import { test } from 'node:test';

import { AppConnection, APP_MISSING, explain } from '../lib/app.js';
import { describePlan, describeRun } from '../lib/progress.js';
import { buildQueries, chunks } from '../lib/queries.js';
import { runSearch, searchPortal, SEND_SIZE } from '../lib/search.js';

const PLAN = {
  portale: ['job-room', 'jobs.ch'], stichworte: ['Python', 'Data'], nischen: ['EdTech'], kantone: ['BE'],
  orte: ['Bern', 'Thun'], plz: ['3000'], regionen: ['grossraum-bern'], max_seiten: 3, max_abfragen: 30,
  max_alter_tage: 45, hinweise: ['ictjobs: im Suchprofil fehlen Kantone'],
};

function hit(portal, id) {
  return { portal, portal_id: id, stelle: `Stelle ${id}`, firma: 'Muster AG', link: `https://www.jobs.ch/${id}` };
}

function fakeApp({ holen = (part) => part.map((h) => `${h.portal}:${h.portal_id}`), planError } = {}) {
  const calls = [];
  return {
    calls,
    async request(method, path, data) {
      calls.push([method, path, data]);
      if (path === '/api/suche/plan') {
        if (planError) throw new Error(planError);
        return { plan: PLAN };
      }
      if (path === '/api/suche/sichten') return { holen: holen(data.treffer), bekannt: 0, gefiltert: [] };
      if (path === '/api/suche/treffer') return { neu: data.treffer.length, zusammengefuehrt: 0, abgelehnt: [] };
      return {};
    },
  };
}

function fakeBrowser(pages) {
  const log = [];
  return {
    log,
    async openTab(url) { log.push(['open', url]); return 7; },
    async inject(tab, files) { log.push(['inject', files]); },
    async run(tab, portal, method, args) {
      log.push([method, args]);
      return pages(portal, method, args);
    },
    async closeTab(tab) { log.push(['close', tab]); },
  };
}

const deps = (app, browser) => ({ app, browser, report: () => {}, sleep: async () => {} });

const queries = (portal, plan) => buildQueries(portal, plan).queries;

test('job-room searches all cantons at once, niches without canton', () => {
  assert.deepEqual(queries('job-room', PLAN).map((q) => [q.keyword, q.cantons]),
    [['Python', ['BE']], ['Data', ['BE']], ['EdTech', []]]);
});

test('jobs.ch searches every keyword in the first place first, then niches, then the other places', () => {
  assert.deepEqual(queries('jobs.ch', PLAN).map((q) => [q.keyword, q.place]),
    [['Python', 'Bern'], ['Data', 'Bern'], ['EdTech', undefined], ['Python', 'Thun'], ['Data', 'Thun']]);
});

test('all over Switzerland: around the home first, then without a place', () => {
  const plan = { ...PLAN, schweizweit: true, kantone: [], stichworte: ['Python'], nischen: [], orte: ['Thun'], plz: ['3600'], regionen: [] };
  assert.deepEqual(queries('jobs.ch', plan).map((q) => [q.keyword, q.place]), [['Python', 'Thun'], ['Python', undefined]]);
  assert.deepEqual(queries('jobscout24', plan).map((q) => [q.keyword, q.postalCode]), [['Python', '3600'], ['Python', undefined]]);
  assert.deepEqual(queries('ictjobs', plan).map((q) => [q.keyword, q.region]), [['Python', undefined]]);
  assert.deepEqual(queries('job-room', plan).map((q) => [q.keyword, q.cantons]), [['Python', []]]);
});

test('a portal without its kind of place still searches', () => {
  const plan = { ...PLAN, stichworte: ['Python'], nischen: [], plz: [], regionen: [] };
  assert.deepEqual(queries('jobscout24', plan).map((q) => [q.keyword, q.postalCode]), [['Python', undefined]]);
});

test('jobscout24 and ictjobs need a place and skip niches', () => {
  assert.deepEqual(queries('jobscout24', PLAN).map((q) => q.postalCode), ['3000', '3000']);
  assert.deepEqual(queries('ictjobs', PLAN).map((q) => q.region), ['grossraum-bern', 'grossraum-bern']);
});

test('number of queries is bounded by the plan, and the rest is counted', () => {
  assert.deepEqual(buildQueries('jobs.ch', { ...PLAN, max_abfragen: 2 }).skipped, 3);
  assert.equal(queries('jobs.ch', { ...PLAN, max_abfragen: 2 }).length, 2);
  assert.equal(buildQueries('jobs.ch', PLAN).skipped, 0);
});

test('skipped queries are named in the summary', async () => {
  const browser = fakeBrowser(() => ({ ok: true, value: { hits: [], more: false } }));
  const summary = await searchPortal('jobs.ch', { ...PLAN, max_abfragen: 2 }, deps(fakeApp(), browser));
  assert.match(summary.problem, /3 Suchen ausgelassen/);
});

test('chunks splits into parts', () => {
  assert.deepEqual(chunks([1, 2, 3, 4, 5], 2), [[1, 2], [3, 4], [5]]);
});

test('the whole of Switzerland comes right after the home and is not cut first by the limit', () => {
  const plan = { ...PLAN, schweizweit: true, kantone: [], stichworte: ['A', 'B'], nischen: [], orte: ['Thun', 'Bern'], max_abfragen: 4 };
  const { queries: kept, skipped } = buildQueries('jobs.ch', plan);
  assert.deepEqual(kept.map((q) => [q.keyword, q.place]), [['A', 'Thun'], ['B', 'Thun'], ['A', undefined], ['B', undefined]]);
  assert.equal(skipped, 2);
});

test('hits near the home get their text first, across all parts of the list', async () => {
  const hits = Array.from({ length: 205 }, (_, i) => hit('jobs.ch', `h${i}`));
  const app = fakeApp();
  const sichten = app.request;
  app.request = async (method, path, data) => {
    const answer = await sichten(method, path, data);
    return path === '/api/suche/sichten'
      ? { ...answer, nah: data.treffer.filter((h) => h.portal_id === 'h204').map((h) => `${h.portal}:${h.portal_id}`) }
      : answer;
  };
  const browser = fakeBrowser((portal, method, args) => (method === 'list'
    ? { ok: true, value: { hits, more: false } }
    : { ok: true, value: { text: args[0].portal_id } }));
  await searchPortal('jobs.ch', { ...PLAN, stichworte: ['Python'], orte: ['Bern'], nischen: [], max_texte: 2 }, deps(app, browser));
  const sent = app.calls.filter(([, path]) => path === '/api/suche/treffer').flatMap(([, , body]) => body.treffer);
  assert.deepEqual(sent.map((h) => h.portal_id), ['h204', 'h0']);
});

test('a run fetches only so many texts per portal and says the rest comes next time', async () => {
  const app = fakeApp();
  const browser = fakeBrowser((portal, method, args) => (method === 'list'
    ? { ok: true, value: { hits: [hit('jobs.ch', 'a'), hit('jobs.ch', 'b'), hit('jobs.ch', 'c')], more: false } }
    : { ok: true, value: { text: args[0].portal_id } }));
  const summary = await searchPortal('jobs.ch', { ...PLAN, stichworte: ['Python'], orte: ['Bern'], nischen: [], max_texte: 2 }, deps(app, browser));
  assert.equal(summary.neu, 2);
  assert.match(summary.problem, /1 weitere neue Inserate kommen bei der nächsten Suche dran/);
});

test('a portal run lists, screens, fetches texts and sends the new hits', async () => {
  const app = fakeApp({ holen: () => ['jobs.ch:a'] });
  const browser = fakeBrowser((portal, method, args) => {
    if (method === 'list') return { ok: true, value: { hits: [hit('jobs.ch', 'a'), hit('jobs.ch', 'b')], more: false } };
    return { ok: true, value: { text: `Text ${args[0].portal_id}` } };
  });
  const summary = await searchPortal('jobs.ch', { ...PLAN, stichworte: ['Python'], orte: ['Bern'], nischen: [] },
    deps(app, browser));
  assert.deepEqual(summary, { treffer: 2, neu: 1, problem: '' });
  const sent = app.calls.find(([, path]) => path === '/api/suche/treffer')[2].treffer;
  assert.deepEqual(sent.map((h) => [h.portal_id, h.text]), [['a', 'Text a']]);
  assert.deepEqual(browser.log.at(-1), ['close', 7]);
});

test('pages are followed while there are more, up to the limit', async () => {
  const browser = fakeBrowser((portal, method) => (method === 'list'
    ? { ok: true, value: { hits: [], more: true } } : { ok: true, value: { text: '' } }));
  await searchPortal('jobs.ch', { ...PLAN, stichworte: ['Python'], orte: ['Bern'], nischen: [] }, deps(fakeApp(), browser));
  assert.equal(browser.log.filter(([kind]) => kind === 'list').length, PLAN.max_seiten);
});

test('a changed portal is reported and the tab is closed', async () => {
  const browser = fakeBrowser(() => ({ ok: false, fehler: 'Die Trefferliste wurde nicht gefunden.', changed: true }));
  const summary = await searchPortal('jobs.ch', PLAN, deps(fakeApp(), browser));
  assert.match(summary.problem, /hat sich verändert.*Trefferliste/);
  assert.deepEqual(browser.log.at(-1), ['close', 7]);
});

test('ads with an empty text are sent and counted in the summary', async () => {
  const browser = fakeBrowser((portal, method) => (method === 'list'
    ? { ok: true, value: { hits: [hit('jobs.ch', 'a')], more: false } } : { ok: true, value: { text: '' } }));
  const summary = await searchPortal('jobs.ch', { ...PLAN, stichworte: ['Python'], orte: ['Bern'], nischen: [] },
    deps(fakeApp(), browser));
  assert.equal(summary.neu, 1);
  assert.match(summary.problem, /1 Inserate ohne lesbaren Text/);
});

test('ads that could not be loaded are kept back for the next search', async () => {
  const app = fakeApp();
  const browser = fakeBrowser((portal, method) => (method === 'list'
    ? { ok: true, value: { hits: [hit('jobs.ch', 'a')], more: false } } : { ok: false, fehler: 'Antwort 429' }));
  const summary = await searchPortal('jobs.ch', { ...PLAN, stichworte: ['Python'], orte: ['Bern'], nischen: [] },
    deps(app, browser));
  assert.equal(summary.neu, 0);
  assert.equal(app.calls.filter(([, path]) => path === '/api/suche/treffer').length, 0);
  assert.match(summary.problem, /1 Inserate nicht geladen.*nächsten Suche/);
});

test('hits go to the app in small parts', async () => {
  const many = Array.from({ length: SEND_SIZE + 3 }, (_, i) => hit('jobs.ch', `h${i}`));
  const app = fakeApp();
  const browser = fakeBrowser((portal, method) => (method === 'list'
    ? { ok: true, value: { hits: many, more: false } } : { ok: true, value: { text: 'x' } }));
  await searchPortal('jobs.ch', { ...PLAN, stichworte: ['Python'], orte: ['Bern'], nischen: [] }, deps(app, browser));
  assert.deepEqual(app.calls.filter(([, path]) => path === '/api/suche/treffer').map(([, , d]) => d.treffer.length),
    [SEND_SIZE, 3]);
});

test('the whole run ends with a summary per portal', async () => {
  const app = fakeApp();
  const browser = fakeBrowser((portal, method) => (method === 'list'
    ? { ok: true, value: { hits: [], more: false } } : { ok: true, value: { text: '' } }));
  const result = await runSearch(deps(app, browser));
  assert.deepEqual(Object.keys(result.portale), ['job-room', 'jobs.ch']);
  assert.deepEqual(app.calls.at(-1)[1], '/api/suche/abschluss');
  assert.deepEqual(result.hinweise, PLAN.hinweise);
});

test('without search profile the run stops with the message of the app', async () => {
  await assert.rejects(runSearch(deps(fakeApp({ planError: 'Es gibt noch kein Suchprofil.' }), fakeBrowser(() => ({})))),
    /kein Suchprofil/);
});

test('progress lines for running, finished and failed runs', () => {
  assert.match(describeRun({ zustand: 'laeuft', schritt: { phase: 'suche', portal: 'jobs.ch', stichwort: 'Python', seite: 2, gefunden: 5 } }).step,
    /jobs.ch: suche „Python“, Seite 2/);
  const done = describeRun({ zustand: 'fertig', ergebnis: { portale: { 'jobs.ch': { treffer: 4, neu: 2, problem: '' },
    ictjobs: { treffer: 0, neu: 0, problem: 'kaputt' } }, hinweise: [] } });
  assert.equal(done.step, 'Fertig: 2 neue Treffer.');
  assert.deepEqual(done.portals.map((p) => p.problem), [false, true]);
  assert.equal(describeRun({ zustand: 'fehler', fehler: 'App fehlt' }).step, 'App fehlt');
});

function fakeRuntime() {
  const listeners = { message: [], disconnect: [] };
  const posted = [];
  const port = {
    onMessage: { addListener: (f) => listeners.message.push(f) },
    onDisconnect: { addListener: (f) => listeners.disconnect.push(f) },
    postMessage: (m) => posted.push(m),
    disconnect: () => {},
  };
  return {
    posted, lastError: null,
    connectNative: () => port,
    reply: (m) => listeners.message.forEach((f) => f(m)),
    drop(message) { this.lastError = { message }; listeners.disconnect.forEach((f) => f()); },
  };
}

test('answers are matched to their request by id', async () => {
  const runtime = fakeRuntime();
  const app = new AppConnection(runtime);
  const first = app.request('GET', '/api/suche/plan');
  const second = app.hello();
  runtime.reply({ id: 2, ok: true, daten: { version: '0.1.0' } });
  runtime.reply({ id: 1, ok: false, fehler: 'Es gibt noch kein Suchprofil.' });
  assert.deepEqual(await second, { version: '0.1.0' });
  await assert.rejects(first, /kein Suchprofil/);
  assert.deepEqual(runtime.posted[0], { art: 'anfrage', methode: 'GET', pfad: '/api/suche/plan', daten: undefined, id: 1 });
});

test('a missing app is explained', async () => {
  const runtime = fakeRuntime();
  const pending = new AppConnection(runtime).hello();
  runtime.drop('Specified native messaging host not found.');
  await assert.rejects(pending, (error) => error.message === APP_MISSING);
  assert.match(explain('Native host has exited.'), /nicht gefunden/);
});

test('only the popup and the page of the running app are trusted', async () => {
  const { senderKind } = await import('../lib/senders.js');
  const id = 'ghniboofenadplgmdgddmgjaaeeogejn';
  const app = 'http://127.0.0.1:61984/';
  assert.equal(senderKind({ id, url: `chrome-extension://${id}/popup.html` }, id, null), 'popup');
  assert.equal(senderKind({ id, url: 'http://127.0.0.1:61984/treffer', tab: {} }, id, app), 'app');
  assert.equal(senderKind({ id, url: 'http://127.0.0.1:8080/', tab: {} }, id, app), null);
  assert.equal(senderKind({ id, url: 'http://127.0.0.1:61984/treffer', tab: {} }, id, null), null);
  assert.equal(senderKind({ id: 'fremd', url: `chrome-extension://fremd/popup.html` }, id, app), null);
  assert.equal(senderKind({ id, url: `chrome-extension://${id}/popup.html`, tab: {} }, id, app), null);
});

const APPRENTICESHIP_PLAN = {
  art: 'lehrstelle', portale: ['LENA', 'yousty'], stichworte: ['Fachfrau Gesundheit EFZ', 'Assistentin EBA'], kantone: ['BE', 'SO'],
  orte: ['Bern'], umkreis_km: 25, lehrbeginn_jahre: [2027], max_seiten: 20, max_abfragen: 30,
};

test('apprenticeships: every profession around the place of residence', () => {
  assert.deepEqual(queries('yousty', APPRENTICESHIP_PLAN), [
    { keyword: 'Fachfrau Gesundheit EFZ', years: [2027], place: 'Bern', radius: 25 },
    { keyword: 'Assistentin EBA', years: [2027], place: 'Bern', radius: 25 },
  ]);
});

test('apprenticeships without a place of residence: every profession in each canton', () => {
  assert.deepEqual(queries('LENA', { ...APPRENTICESHIP_PLAN, orte: [], stichworte: ['Fachfrau Gesundheit EFZ'] }), [
    { keyword: 'Fachfrau Gesundheit EFZ', years: [2027], canton: 'BE' },
    { keyword: 'Fachfrau Gesundheit EFZ', years: [2027], canton: 'SO' },
  ]);
});

function pagesBrowser(handlers) {
  const browser = fakeBrowser((portal, method, args) => handlers[method](args));
  browser.navigate = async (tab, url) => { browser.log.push(['navigate', url]); };
  return browser;
}

const LENA_ONE_PROFESSION = { ...APPRENTICESHIP_PLAN, stichworte: ['Fachfrau Gesundheit EFZ'], orte: ['Bern'] };

test('LENA: the tab opens the list of the search and loads the adapters again before reading it', async () => {
  const browser = pagesBrowser({
    searchUrl: () => ({ ok: true, value: 'https://www.berufsberatung.ch/de/suche/lehrstellen?profession=1' }),
    list: () => ({ ok: true, value: { hits: [], more: false } }),
  });
  const summary = await searchPortal('LENA', LENA_ONE_PROFESSION, deps(fakeApp(), browser));
  assert.equal(summary.problem, '');
  const steps = browser.log.map(([name]) => name);
  assert.deepEqual(steps, ['open', 'inject', 'searchUrl', 'navigate', 'inject', 'list', 'close']);
  assert.deepEqual(browser.log[4][1], ['portals/common.js', 'portals/lena.js']);
});

test('LENA: an unknown profession is a note, and the next profession is still searched', async () => {
  const browser = pagesBrowser({
    searchUrl: ([query]) => (query.keyword === 'Assistentin EBA'
      ? { ok: true, value: 'https://www.berufsberatung.ch/x' }
      : { ok: false, fehler: 'Den Beruf kennt LENA nicht.' }),
    list: () => ({ ok: true, value: { hits: [], more: false } }),
  });
  const summary = await searchPortal('LENA', APPRENTICESHIP_PLAN, deps(fakeApp(), browser));
  assert.match(summary.problem, /Den Beruf kennt LENA nicht/);
  assert.equal(browser.log.filter(([name]) => name === 'list').length, 1);
});

test('LENA: a changed search form says that the extension needs an update', async () => {
  const browser = pagesBrowser({ searchUrl: () => ({ ok: false, fehler: 'Formular fehlt', changed: true }) });
  const summary = await searchPortal('LENA', APPRENTICESHIP_PLAN, deps(fakeApp(), browser));
  assert.match(summary.problem, /Update der Erweiterung/);
});

test('yousty needs no new page per search', async () => {
  const browser = pagesBrowser({ list: () => ({ ok: true, value: { hits: [], more: false } }) });
  await searchPortal('yousty', LENA_ONE_PROFESSION, deps(fakeApp(), browser));
  assert.deepEqual(browser.log.map(([name]) => name), ['open', 'inject', 'list', 'close']);
});

test('popup names the portals of the plan, and stays general without one', () => {
  assert.deepEqual(describePlan(APPRENTICESHIP_PLAN), {
    button: 'Lehrstellen suchen', text: 'Sucht auf LENA und yousty nach deinem Suchprofil. Die Treffer gehen in die App.',
  });
  assert.equal(describePlan({ art: 'stelle', portale: ['job-room', 'jobs.ch', 'ictjobs'] }).text,
    'Sucht auf job-room, jobs.ch und ictjobs nach Ihrem Suchprofil. Die Treffer gehen in die App.');
  assert.equal(describePlan(null).button, 'Suche starten');
});

test('apprenticeship queries follow the wanted offers', () => {
  const plan = { art: 'lehrstelle', stichworte: ['A', 'B'], orte: ['Bern'], umkreis_km: 25, lehrbeginn_jahre: [2027], max_abfragen: 30 };

  const both = buildQueries('yousty', { ...plan, angebote: ['lehrstelle', 'schnupperlehre'] }).queries;
  assert.equal(both.length, 4);
  assert.equal(both.filter((q) => q.trial).length, 2);
  assert.deepEqual(both.find((q) => q.trial).years, []);
  assert.deepEqual(both.find((q) => !q.trial).years, [2027]);

  assert.ok(buildQueries('LENA', { ...plan, angebote: ['schnupperlehre'] }).queries.every((q) => q.trial));
  assert.ok(buildQueries('LENA', plan).queries.every((q) => !q.trial), 'an older plan searches apprenticeships');
});

test('the popup names what is searched', () => {
  const plan = { art: 'lehrstelle', portale: ['LENA', 'yousty'] };
  assert.equal(describePlan({ ...plan, angebote: ['schnupperlehre'] }).button, 'Schnupperlehren suchen');
  assert.equal(describePlan({ ...plan, angebote: ['lehrstelle', 'schnupperlehre'] }).button, 'Lehrstellen und Schnupperlehren suchen');
  assert.equal(describePlan({ ...plan, angebote: ['lehrstelle'] }).button, 'Lehrstellen suchen');
  assert.equal(describePlan(plan).button, 'Lehrstellen suchen');
});

// Watching the search (MIN-370)


function pagesWithOneHit(portal, method) {
  if (method === 'list') return { ok: true, value: { hits: [hit(portal, '1')], more: false } };
  return { ok: true, value: { text: 'Inserat' } };
}

function watchingBrowser(pages = pagesWithOneHit) {
  const browser = fakeBrowser(pages);
  const openTab = browser.openTab;
  browser.opened = [];
  browser.openTab = (url, active) => { browser.opened.push(active); return openTab(url); };
  browser.showWatching = async (tab, portal) => { browser.log.push(['watching', portal]); };
  return browser;
}

test('by default the search stays in the background and shows nothing', async () => {
  const browser = watchingBrowser();
  await searchPortal('jobs.ch', PLAN, deps(fakeApp(), browser));
  assert.deepEqual(browser.opened, [false]);
  assert.equal(browser.log.filter((e) => e[0] === 'watching').length, 0);
});

test('with „Zuschauen“ the tab is active and says what is going on', async () => {
  const browser = watchingBrowser();
  await searchPortal('jobs.ch', { ...PLAN, zuschauen: true }, deps(fakeApp(), browser));
  assert.deepEqual(browser.opened, [true]);
  assert.deepEqual(browser.log.filter((e) => e[0] === 'watching'), [['watching', 'jobs.ch']]);
});

test('a portal that opens pages shows the message again on every page', async () => {
  const pages = (portal, method) => (method === 'searchUrl' ? { ok: true, value: 'https://www.berufsberatung.ch/x' } : { ok: true, value: { hits: [], more: false } });
  const browser = watchingBrowser(pages);
  browser.navigate = async () => {};
  const plan = { ...APPRENTICESHIP_PLAN, zuschauen: true };
  await searchPortal('LENA', plan, deps(fakeApp(), browser));
  assert.ok(browser.log.filter((e) => e[0] === 'watching').length >= 2);
});

test('cancelling stops before the next request, ends the run and still closes the tab', async () => {
  const browser = watchingBrowser();
  const app = fakeApp();
  let stop = false;
  const result = await runSearch({ ...deps(app, browser), cancelled: () => stop, report: (step) => { if (step.phase === 'suche') stop = true; } });
  assert.equal(result.abgebrochen, true);
  assert.deepEqual(Object.keys(result.portale), ['job-room'], 'the next portal does not start');
  assert.match(result.portale['job-room'].problem, /abgebrochen/);
  assert.equal(browser.log.filter((e) => e[0] === 'close').length, 1);
  assert.equal(app.calls.filter((c) => c[1] === '/api/suche/abschluss').length, 1, 'the summary is still written');
  assert.equal(app.calls.filter((c) => c[1] === '/api/suche/treffer').length, 0);
});

test('a tab closed by the person counts as cancelling, not as a problem of the portal', async () => {
  let stop = false;
  const pages = () => { stop = true; throw new Error('No tab with id: 7'); };
  const result = await searchPortal('jobs.ch', PLAN, { ...deps(fakeApp(), watchingBrowser(pages)), cancelled: () => stop });
  assert.match(result.problem, /abgebrochen/);
  assert.doesNotMatch(result.problem, /No tab/);
});

test('without cancelling the result says so', async () => {
  const result = await runSearch({ ...deps(fakeApp(), watchingBrowser()), cancelled: () => false });
  assert.equal(result.abgebrochen, false);
});

test('the popup says when a search was cancelled', () => {
  assert.match(describeRun({ zustand: 'fertig', ergebnis: { portale: {}, abgebrochen: true } }).step, /Abgebrochen/);
  assert.match(describeRun({ zustand: 'fertig', ergebnis: { portale: {} } }).step, /Fertig/);
});
