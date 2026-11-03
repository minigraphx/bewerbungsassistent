// Search run, queries, progress and app connection of the extension (MIN-339), with simulated tabs and app.
import assert from 'node:assert/strict';
import { test } from 'node:test';

import { AppConnection, APP_MISSING, explain } from '../lib/app.js';
import { describeRun } from '../lib/progress.js';
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
