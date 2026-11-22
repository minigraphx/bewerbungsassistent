// #395: the jobs.ch search asks for the newest ads first, so the 3 pages a query reads hold the ads since the last run.
// The portal is a stand-in for fetch with an invented answer of 5 pages; no request leaves the test.
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { afterEach, test } from 'node:test';

const require = createRequire(import.meta.url);
const jobsch = require('../portals/jobsch.js');

const ROWS = 20;
const PAGES = 5;
const PAGES_READ = 3; // MAX_PAGES in bewerbungen/search_plan.py
const realFetch = globalThis.fetch;

// Invented ads, one per day back; by relevance the newest ten come last, as on a broad search.
const ADS = Array.from({ length: ROWS * PAGES }, (_, age) => ({
  job_id: `job-${age}`, title: `Stelle ${age}`, company_name: 'Muster AG', place: 'Musterstadt', age,
}));
const BY_RELEVANCE = [...ADS.slice(10), ...ADS.slice(0, 10)];

/** The invented portal: pages of 20, ordered by date only when the request asks for it. */
function fakePortal(requests) {
  return async (url) => {
    const params = new URL(url, 'https://www.jobs.ch').searchParams;
    requests.push(params);
    const ordered = params.get('sort') === 'date' ? ADS : BY_RELEVANCE;
    const page = Number(params.get('page'));
    const documents = ordered.slice((page - 1) * ROWS, page * ROWS);
    return { ok: true, status: 200, json: async () => ({ documents, num_pages: PAGES, total_hits: ADS.length }) };
  };
}

afterEach(() => {
  globalThis.fetch = realFetch;
});

test('every jobs.ch page asks for the newest ads first', async () => {
  const requests = [];
  globalThis.fetch = fakePortal(requests);
  for (let page = 1; page <= PAGES_READ; page += 1) await jobsch.list({ keyword: 'Kursplaner', place: 'Musterstadt' }, page);
  await jobsch.list({ keyword: 'Nische1' }, 1);
  assert.deepEqual(requests.map((params) => params.get('sort')), ['date', 'date', 'date', 'date']);
});

test('on a search of more than 3 pages the pages read hold the newest ads', async () => {
  globalThis.fetch = fakePortal([]);
  const ages = [];
  for (let page = 1; page <= PAGES_READ; page += 1) {
    const { hits, more } = await jobsch.list({ keyword: 'Kursplaner', place: 'Musterstadt' }, page);
    assert.equal(more, true);
    ages.push(...hits.map((hit) => hit.alter_tage));
  }
  assert.deepEqual(ages, Array.from({ length: ROWS * PAGES_READ }, (_, age) => age));
});
