// #394, G124: the jobs.ch search asks the semantic search the website uses, and falls back to the classic public API
// when it fails, saying so in the run. fetch is a stand-in with invented answers; no request leaves the test.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { afterEach, test } from 'node:test';

import { describeRun } from '../lib/progress.js';
import { searchPortal } from '../lib/search.js';

const require = createRequire(import.meta.url);
const jobsch = require('../portals/jobsch.js');

const SEMANTIC = JSON.parse(readFileSync(new URL('./fixtures/jobsch-semantic.json', import.meta.url), 'utf8'));
const TODAY = new Date('2026-11-03T12:00:00Z');
const DAY_MS = 24 * 60 * 60 * 1000;
const SEMANTIC_HOST = 'job-search-api.jobs.ch';
const FALLBACK = 'jobs.ch: Die gründliche Suche ging diesmal nicht. '
  + 'Gefunden wurden nur Inserate, die den Suchbegriff genau so enthalten.';
const CATCH_UP = 'Die nächste Suche holt die übrigen Inserate nach.';
const realFetch = globalThis.fetch;
const realWarn = console.warn;

const CLASSIC = {
  documents: [{ job_id: 'classic-1', title: 'Lagerist/in', company_name: 'Erfunden AG', place: 'Musterstadt', age: 2 }],
  num_pages: 1,
};

afterEach(() => {
  globalThis.fetch = realFetch;
  console.warn = realWarn;
});

function json(body, status = 200) {
  return { ok: status < 400, status, json: async () => body };
}

/** The invented jobs.ch: `semantic` answers the semantic search, the classic API always gives CLASSIC. */
function fakeJobsch(semantic, requests = []) {
  return async (url) => {
    const target = new URL(url, 'https://www.jobs.ch');
    requests.push(target);
    if (target.host === SEMANTIC_HOST) return semantic(target);
    return json(CLASSIC);
  };
}

test('a semantic answer becomes hits with title, company, place, workload and age from the publication date', () => {
  const { hits, more, oldest } = jobsch.parseSemantic(SEMANTIC, 1, TODAY);
  assert.deepEqual(hits, [
    {
      portal: 'jobs.ch', portal_id: '0f0e0d0c-0000-4000-8000-000000000001', stelle: 'Logistiker/in EFZ',
      firma: 'Muster Transporte AG', ort: 'Musterstadt', pensum: '80–100 %',
      link: 'https://www.jobs.ch/de/stellenangebote/detail/0f0e0d0c-0000-4000-8000-000000000001/', alter_tage: 1,
    },
    {
      portal: 'jobs.ch', portal_id: '0f0e0d0c-0000-4000-8000-000000000002', stelle: 'Mitarbeiter/in Lager und Versand',
      firma: 'Beispiel Lager GmbH', ort: 'Beispielhausen', pensum: '100 %',
      link: 'https://www.jobs.ch/de/stellenangebote/detail/0f0e0d0c-0000-4000-8000-000000000002/', alter_tage: 3,
    },
    {
      portal: 'jobs.ch', portal_id: '0f0e0d0c-0000-4000-8000-000000000003', stelle: 'Disponent/in Strassentransport',
      firma: 'Fiktiv Spedition SA', ort: 'Dorfikon', pensum: '',
      link: 'https://www.jobs.ch/de/stellenangebote/detail/0f0e0d0c-0000-4000-8000-000000000003/', alter_tage: 14,
    },
  ]);
  assert.equal(more, true);
  assert.equal(oldest, 14);
  assert.equal(jobsch.parseSemantic(SEMANTIC, 2, TODAY).more, false);
  assert.deepEqual(jobsch.parseSemantic({ ...SEMANTIC, documents: [], numPages: 0 }, 1, TODAY), { hits: [], more: false, oldest: null });
});

test('an unknown semantic answer is a changed portal', () => {
  assert.throws(() => jobsch.parseSemantic({ results: [] }, 1, TODAY), (error) => error.changed === true);
  assert.throws(() => jobsch.parseSemantic({ documents: [{ job_id: 'x', name: 'y' }], numPages: 1 }, 1, TODAY),
    (error) => error.changed === true);
});

test('a jobs.ch page asks the semantic search, newest first, with keyword, place and page', async () => {
  const requests = [];
  globalThis.fetch = fakeJobsch(() => json(SEMANTIC), requests);
  const result = await jobsch.list({ keyword: 'Logistik', place: 'Musterstadt' }, 2);
  assert.equal(requests.length, 1);
  const [asked] = requests;
  assert.equal(`${asked.origin}${asked.pathname}`, 'https://job-search-api.jobs.ch/search/semantic');
  assert.deepEqual(Object.fromEntries(asked.searchParams),
    { query: 'Logistik', location: 'Musterstadt', rows: '20', page: '2', sort: 'date' });
  assert.deepEqual(result.hits.map((hit) => hit.portal_id), SEMANTIC.documents.map((doc) => doc.id));
  assert.equal(result.fallback, undefined);
  await jobsch.list({ keyword: 'Nische1' }, 1);
  assert.equal(requests[1].searchParams.has('location'), false);
});

test('when the semantic search fails, the page comes from the classic API and says why', async () => {
  const cases = [
    [() => json({}, 503), 'Antwort 503'],
    [() => { throw new TypeError('Failed to fetch'); }, 'keine Antwort'],
    [() => json({ results: [] }), 'Die Suche liefert keine Liste mehr.'],
  ];
  for (const [semantic, reason] of cases) {
    const requests = [];
    globalThis.fetch = fakeJobsch(semantic, requests);
    const result = await jobsch.list({ keyword: 'Logistik', place: 'Musterstadt' }, 1);
    assert.equal(result.fallback, reason);
    assert.deepEqual(result.hits.map((hit) => hit.portal_id), ['classic-1']);
    const classic = requests.find((target) => target.host !== SEMANTIC_HOST);
    assert.equal(classic.pathname, '/api/v1/public/search');
    assert.deepEqual(Object.fromEntries(classic.searchParams),
      { rows: '20', page: '1', query: 'Logistik', sort: 'date', location: 'Musterstadt' });
  }
});

test('when both searches fail, the page fails as before', async () => {
  globalThis.fetch = async () => json({}, 500);
  await assert.rejects(jobsch.list({ keyword: 'Logistik' }, 1), /Antwort 500/);
});

const PLAN = {
  portale: ['jobs.ch'], stichworte: ['Logistik', 'Lager'], nischen: [], kantone: [], orte: ['Musterstadt'],
  max_seiten: 10, max_alter_tage: 2,
};

/** A browser that runs the real adapter, as background.js does in the portal tab. */
function adapterBrowser(pages) {
  return {
    async openTab() { return 7; },
    async inject() {},
    async closeTab() {},
    async run(tab, portal, method, args) {
      if (method === 'details') return { ok: true, value: { text: '' } };
      pages.push(args[1]);
      try {
        return { ok: true, value: await jobsch[method](...args) };
      } catch (error) {
        return { ok: false, fehler: String(error.message), changed: Boolean(error.changed) };
      }
    },
  };
}

const APP = {
  async request(method, path) {
    return path === '/api/suche/sichten' ? { holen: [] } : {};
  },
};

async function run(plan) {
  const pages = [];
  const summary = await searchPortal('jobs.ch', plan, { app: APP, browser: adapterBrowser(pages), report: () => {}, sleep: async () => {} });
  return { pages, summary };
}

test('a run whose semantic search fails names the fallback once and keeps the classic hits', async () => {
  globalThis.fetch = fakeJobsch(() => json({}, 503));
  const warnings = [];
  console.warn = (...args) => warnings.push(args.join(' '));
  const { summary } = await run(PLAN);
  assert.equal(summary.problem, FALLBACK);
  assert.equal(summary.rueckfall, true);
  assert.equal(summary.treffer, 1);
  assert.deepEqual(summary.abfragen.map((query) => query.treffer), [1, 1]);
  // The reason is for support only: in the extension's log, never in the line the person reads.
  assert.ok(warnings.length > 0 && warnings.every((line) => line.includes('Antwort 503')), warnings.join('\n'));
});

test('a run on the semantic search has no problem', async () => {
  globalThis.fetch = fakeJobsch(() => json(SEMANTIC));
  const { summary } = await run({ ...PLAN, stichworte: ['Logistik'], max_seiten: 1 });
  assert.equal(summary.problem, '');
  assert.equal(summary.rueckfall, undefined);
  assert.equal(summary.treffer, SEMANTIC.documents.length);
});

test('the popup adds that the next search catches up, only to a fallback line', () => {
  const portale = {
    'jobs.ch': { treffer: 4, neu: 2, problem: FALLBACK, rueckfall: true },
    jobscout24: { treffer: 0, neu: 0, problem: 'jobscout24: Antwort 500' },
  };
  const { portals } = describeRun({ zustand: 'fertig', ergebnis: { portale } });
  assert.deepEqual(portals, [
    { text: `jobs.ch: 4 gefunden, 2 neu – ${FALLBACK} ${CATCH_UP}`, problem: true },
    { text: 'jobscout24: 0 gefunden, 0 neu – jobscout24: Antwort 500', problem: true },
  ]);
});

test('the semantic search sorted by date stops paging past the last run (G123)', async () => {
  // Page p holds two invented ads aged 2p-2 and 2p-1 days; with 2 days since the last run page 3 is the last one read.
  globalThis.fetch = fakeJobsch((target) => {
    const page = Number(target.searchParams.get('page'));
    const documents = [2 * page - 2, 2 * page - 1].map((age) => ({
      id: `id-${page}-${age}`, title: `Stelle ${age}`, company: { name: 'Muster AG' }, place: 'Musterstadt',
      publicationDate: new Date(Date.now() - age * DAY_MS - 60 * 60 * 1000).toISOString(),
    }));
    return json({ numPages: 10, currentPage: page, documents });
  });
  const { pages, summary } = await run({ ...PLAN, stichworte: ['Logistik'] });
  assert.deepEqual(pages, [1, 2, 3]);
  assert.equal(summary.problem, '');
});
