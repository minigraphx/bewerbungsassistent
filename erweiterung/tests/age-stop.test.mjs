// G123, #397: on a portal sorted by date, a query stops paging after the page whose oldest regular ad is older
// than the days since the last run plus a margin. A fake browser serves an invented answer of 10 pages.
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { test } from 'node:test';

import { ADAPTERS, buildQueries, pagesOf } from '../lib/queries.js';
import { searchPortal } from '../lib/search.js';

const require = createRequire(import.meta.url);
const jobsch = require('../portals/jobsch.js');

const PAGES = 10;
const PLAN = {
  portale: ['jobs.ch'], stichworte: ['Kursplaner'], nischen: [], kantone: [], orte: ['Musterstadt'], plz: ['1111'],
  regionen: ['Mittelland'], max_seiten: PAGES, max_seiten_regionen: PAGES, max_alter_tage: 2,
};
const REGION_PLAN = { ...PLAN, regionen_jobscout24: [{ id: '3', name: 'Region Musterland' }] };

/** Page p holds two invented ads aged 2p-2 and 2p-1 days, so its oldest ad is 2p-1 days old. */
function answer(page, portal, { withoutOldest = [] } = {}) {
  const ages = [2 * page - 2, 2 * page - 1];
  const hits = ages.map((age) => ({ portal, portal_id: `${page}-${age}`, stelle: `Stelle ${page}-${age}`, alter_tage: age }));
  return { hits, more: page < PAGES, oldest: withoutOldest.includes(page) ? null : Math.max(...ages) };
}

/** The invented portal: records each page a query asks for. */
function fakeBrowser(options) {
  const pages = [];
  return {
    pages,
    async openTab() { return 7; },
    async inject() {},
    async closeTab() {},
    async run(tab, portal, method, [query, page]) {
      if (method === 'details') return { ok: true, value: { text: '' } };
      pages.push(page);
      return { ok: true, value: answer(page, portal, options) };
    },
  };
}

function fakeApp() {
  return {
    async request(method, path) {
      if (path === '/api/suche/sichten') return { holen: [], gefiltert: [] };
      return {};
    },
  };
}

async function pagesRead(portal, plan, options) {
  const browser = fakeBrowser(options);
  const summary = await searchPortal(portal, plan, { app: fakeApp(), browser, report: () => {}, sleep: async () => {} });
  return { pages: browser.pages, summary };
}

test('jobs.ch and jobscout24 are marked as sorted by date, the other portals are not', () => {
  assert.deepEqual(Object.keys(ADAPTERS).filter((portal) => ADAPTERS[portal].dateSorted), ['jobs.ch', 'jobscout24']);
});

test('with 2 days since the last run, a date-sorted query stops after the first page older than 4 days', async () => {
  for (const [portal, plan] of [['jobs.ch', PLAN], ['jobscout24', PLAN], ['jobscout24', REGION_PLAN]]) {
    const { pages } = await pagesRead(portal, plan);
    assert.deepEqual(pages, [1, 2, 3], portal);
  }
});

test('the same answer on a portal not sorted by date reads every page', async () => {
  const { pages } = await pagesRead('ictjobs', { ...PLAN, portale: ['ictjobs'] });
  assert.deepEqual(pages, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]);
});

test('a page without an oldest age does not stop the query', async () => {
  const { pages } = await pagesRead('jobs.ch', PLAN, { withoutOldest: [3] });
  assert.deepEqual(pages, [1, 2, 3, 4]);
});

test('a query without days since the last run reads every page', async () => {
  const older = { ...PLAN };
  delete older.max_alter_tage;
  const { pages } = await pagesRead('jobs.ch', older);
  assert.equal(pages.length, PAGES);
});

test('with 21 days since the last run, the query reads up to its page cap', async () => {
  const wide = { ...PLAN, max_alter_tage: 21, max_seiten: 3 };
  assert.deepEqual((await pagesRead('jobs.ch', wide)).pages, [1, 2, 3]);
  assert.equal((await pagesRead('jobscout24', { ...REGION_PLAN, max_alter_tage: 21 })).pages.length, PAGES);
});

test('a query that stopped early stays in the run log, and the estimate stays an upper bound', async () => {
  const { pages, summary } = await pagesRead('jobs.ch', PLAN);
  assert.deepEqual(summary.abfragen, [{ stichwort: 'Kursplaner', ort: 'Musterstadt', treffer: 6 }]);
  const [query] = buildQueries('jobs.ch', PLAN).queries;
  assert.equal(pagesOf(query, PLAN), PAGES);
  assert.ok(pages.length <= pagesOf(query, PLAN));
});

test('a jobs.ch page reports the age of its oldest ad', () => {
  const documents = [3, 0, 5, 1].map((age) => ({ job_id: `job-${age}`, title: `Stelle ${age}`, age }));
  assert.equal(jobsch.parseList({ documents, num_pages: 4 }, 1).oldest, 5);
  assert.equal(jobsch.parseList({ documents: [], num_pages: 0 }, 1).oldest, null);
  const undated = [{ job_id: 'job-x', title: 'Stelle x' }];
  assert.equal(jobsch.parseList({ documents: undated, num_pages: 1 }, 1).oldest, null);
});
