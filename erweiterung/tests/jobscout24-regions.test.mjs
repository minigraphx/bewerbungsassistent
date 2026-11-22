// G107, #380: jobscout24 searches once per term in all chosen regions instead of once per postcode; invented data.
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { test } from 'node:test';

import { buildQueries, placeOf } from '../lib/queries.js';
import { searchPortal } from '../lib/search.js';

const require = createRequire(import.meta.url);
const common = require('../portals/common.js');
const jobscout24 = require('../portals/jobscout24.js');

const REGIONS = [{ id: '3', name: 'Region Bern (BE/FR/SO)' }, { id: '14', name: 'Homeoffice / Remote' }];
const PLAN = {
  art: 'stelle', portale: ['jobscout24'], stichworte: ['Kursplaner', 'Lernbegleiter', 'Datenpfleger'], nischen: ['Nische1'],
  kantone: ['BE'], orte: ['Nordstadt'], plz: ['1111', '2222', '3333'], regionen: [], schweizweit: false,
  regionen_jobscout24: [REGIONS[0]], max_seiten: 3, max_seiten_regionen: 10,
};

test('with one region, jobscout24 runs one search per term instead of one per postcode and term', () => {
  const { queries } = buildQueries('jobscout24', PLAN);
  assert.equal(queries.length, PLAN.stichworte.length);
  assert.deepEqual(queries.map((query) => query.keyword), PLAN.stichworte);
  assert.ok(queries.every((query) => !query.postalCode && query.regionIds.join() === '3'));
});

test('all chosen regions go into the same search, and the postcodes come back without them', () => {
  const both = buildQueries('jobscout24', { ...PLAN, regionen_jobscout24: REGIONS }).queries;
  assert.equal(both.length, 3);
  assert.deepEqual(both[0].regionIds, ['3', '14']);
  assert.equal(placeOf(both[0]), 'Region Bern (BE/FR/SO), Homeoffice / Remote');
  const without = buildQueries('jobscout24', { ...PLAN, regionen_jobscout24: [] }).queries;
  assert.equal(without.length, 9);
  assert.deepEqual([...new Set(without.map((query) => query.postalCode))], ['1111', '2222', '3333']);
  const older = { ...PLAN };
  delete older.regionen_jobscout24;
  assert.equal(buildQueries('jobscout24', older).queries.length, 9);
});

test('a region search reads more pages, since it covers what several postcodes did', () => {
  const [query] = buildQueries('jobscout24', PLAN).queries;
  assert.equal(query.maxPages, 10);
  assert.equal(buildQueries('jobscout24', { ...PLAN, regionen_jobscout24: [] }).queries[0].maxPages, undefined);
});

test('the other portals ignore the jobscout24 regions', () => {
  assert.equal(buildQueries('jobs.ch', PLAN).queries.length, 3 + 1);
});

test('the list request repeats regidl once per region, without a postcode', async (t) => {
  const asked = [];
  const page = { querySelectorAll: () => [], querySelector: () => ({ textContent: '0 Stellen gefunden' }) };
  t.mock.method(common, 'fetchPage', async (url) => { asked.push(url); return page; });
  await jobscout24.list({ keyword: 'Kursplaner', regionIds: ['3', '14'] }, 2);
  const params = new URL(asked[0], 'https://www.jobscout24.ch').searchParams;
  assert.deepEqual(params.getAll('regidl'), ['3', '14']);
  assert.equal(params.get('psz'), null);
  assert.equal(params.get('p'), '2');
});

test('the run reads a region search up to its own page limit', async () => {
  const pages = [];
  const deps = {
    app: { async request(method, path) { return path === '/api/suche/sichten' ? { holen: [], bekannt: 0, gefiltert: [] } : {}; } },
    browser: {
      async openTab() { return 1; },
      async inject() {},
      async run(tab, portal, method, args) {
        if (method === 'list') pages.push(args[1]);
        return { ok: true, value: { hits: [], more: true } };
      },
      async closeTab() {},
    },
    report() {},
    sleep: async () => {},
  };
  await searchPortal('jobscout24', { ...PLAN, stichworte: ['Kursplaner'] }, deps);
  assert.deepEqual(pages, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]);
});
