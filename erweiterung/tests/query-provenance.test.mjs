// Which query found each hit (G103, #375): every hit names its queries, the summary counts each query, empty ones too.
// Invented terms and places only.
import assert from 'node:assert/strict';
import { test } from 'node:test';

import { runSearch, searchPortal } from '../lib/search.js';

const PLAN = {
  portale: ['jobs.ch'], stichworte: ['Lernbegleiter', 'Kursleiter'], nischen: [], kantone: ['AG', 'SO'],
  orte: ['Aarau', 'Olten'], plz: [], regionen: [], max_seiten: 1, max_alter_tage: 45,
};

const ad = (id) => ({ portal: 'jobs.ch', portal_id: id, stelle: `Stelle ${id}`, firma: 'Muster AG', link: `https://www.jobs.ch/${id}` });

function fakeApp() {
  const calls = [];
  return {
    calls,
    async request(method, path, data) {
      calls.push([method, path, data]);
      if (path === '/api/suche/plan') return { plan: PLAN };
      if (path === '/api/suche/sichten') return { holen: data.treffer.map((h) => `${h.portal}:${h.portal_id}`), gefiltert: [] };
      if (path === '/api/suche/treffer') return { neu: data.treffer.length };
      return {};
    },
  };
}

// In Aarau, Lernbegleiter finds a and b, Kursleiter finds a again; Olten finds nothing.
function fakeBrowser({ failing = '' } = {}) {
  return {
    async openTab() { return 3; },
    async inject() {},
    async closeTab() {},
    async run(tab, portal, method, [query]) {
      if (method === 'details') return { ok: true, value: { text: 'Text' } };
      if (query.keyword === failing) return { ok: false, fehler: 'zu viele Abrufe' };
      if (query.place !== 'Aarau') return { ok: true, value: { hits: [], more: false } };
      return { ok: true, value: { hits: query.keyword === 'Lernbegleiter' ? [ad('a'), ad('b')] : [ad('a')], more: false } };
    },
  };
}

const deps = (app, browser) => ({ app, browser, report: () => {}, sleep: async () => {} });
const sent = (app, path) => app.calls.filter(([, p]) => p === path).flatMap(([, , body]) => body.treffer);

test('a hit names every query that found it, on the way to screening and with its text', async () => {
  const app = fakeApp();
  await searchPortal('jobs.ch', PLAN, deps(app, fakeBrowser()));
  for (const path of ['/api/suche/sichten', '/api/suche/treffer']) {
    const [first, second] = sent(app, path);
    assert.deepEqual(first.abfragen, [{ stichwort: 'Lernbegleiter', ort: 'Aarau' }, { stichwort: 'Kursleiter', ort: 'Aarau' }]);
    assert.deepEqual(second.abfragen, [{ stichwort: 'Lernbegleiter', ort: 'Aarau' }]);
  }
});

test('the summary of a portal counts the hits of each query, also the queries without any', async () => {
  const summary = await searchPortal('jobs.ch', PLAN, deps(fakeApp(), fakeBrowser()));
  assert.deepEqual(summary.abfragen, [
    { stichwort: 'Lernbegleiter', ort: 'Aarau', treffer: 2 }, { stichwort: 'Kursleiter', ort: 'Aarau', treffer: 1 },
    { stichwort: 'Lernbegleiter', ort: 'Olten', treffer: 0 }, { stichwort: 'Kursleiter', ort: 'Olten', treffer: 0 }]);
});

test('a query that failed is not counted as one that found nothing', async () => {
  const summary = await searchPortal('jobs.ch', PLAN, deps(fakeApp(), fakeBrowser({ failing: 'Kursleiter' })));
  assert.deepEqual(summary.abfragen.map((q) => [q.stichwort, q.ort]), [['Lernbegleiter', 'Aarau'], ['Lernbegleiter', 'Olten']]);
  assert.match(summary.problem, /zu viele Abrufe/);
});

test('job-room names its cantons as the place of a query, a niche an empty place', async () => {
  const plan = { ...PLAN, portale: ['job-room'], stichworte: ['Lernbegleiter'], nischen: ['Lernatelier'] };
  const browser = { ...fakeBrowser(), run: async (tab, portal, method) => (method === 'list'
    ? { ok: true, value: { hits: [], more: false } } : { ok: true, value: { text: '' } }) };
  const summary = await searchPortal('job-room', plan, deps(fakeApp(), browser));
  assert.deepEqual(summary.abfragen, [{ stichwort: 'Lernbegleiter', ort: 'AG, SO', treffer: 0 }, { stichwort: 'Lernatelier', ort: '', treffer: 0 }]);
});

test('the end of the run sends the queries of each portal to the app', async () => {
  const app = fakeApp();
  await runSearch(deps(app, fakeBrowser()));
  const [, , body] = app.calls.find(([, path]) => path === '/api/suche/abschluss');
  assert.equal(body.portale['jobs.ch'].abfragen.length, 4);
});
