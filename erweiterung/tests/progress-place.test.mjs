// G43 (#284): the progress names the place being searched right now, beside portal, term and stage; invented places.
import assert from 'node:assert/strict';
import { test } from 'node:test';

import { describeRun } from '../lib/progress.js';
import { buildQueries, placeOf } from '../lib/queries.js';
import { searchPortal } from '../lib/search.js';
import { searchSite } from '../lib/sites.js';

const PLAN = {
  art: 'stelle', portale: ['jobs.ch'], stichworte: ['Begriff1'], nischen: ['Nische1'], kantone: ['BE', 'ZH'],
  orte: ['Nordstadt'], plz: ['3999'], regionen: ['Region Nord'], max_seiten: 1,
};

/** The steps a portal reports while it searches, on simulated tabs without hits. */
async function reportedSteps(portal, plan) {
  const reports = [];
  const app = { async request(method, path) { return path === '/api/suche/sichten' ? { holen: [], bekannt: 0, gefiltert: [] } : {}; } };
  const browser = {
    async openTab() { return 1; },
    async inject() {},
    async run() { return { ok: true, value: { hits: [], more: false } }; },
    async closeTab() {},
  };
  await searchPortal(portal, plan, { app, browser, report: (step) => reports.push(step), sleep: async () => {} });
  return reports.filter((step) => step.phase === 'suche');
}

test('each kind of query names its place, a query without one names none', () => {
  const [home, free] = buildQueries('jobs.ch', PLAN).queries;
  assert.equal(placeOf(home), 'Nordstadt');
  assert.equal(placeOf(free), '');
  assert.equal(placeOf(buildQueries('jobscout24', PLAN).queries[0]), '3999');
  assert.equal(placeOf(buildQueries('ictjobs', PLAN).queries[0]), 'Region Nord');
  const [cantons, niche] = buildQueries('job-room', PLAN).queries;
  assert.equal(placeOf(cantons), 'BE, ZH');
  assert.equal(placeOf(niche), '');
  assert.equal(placeOf(buildQueries('LENA', { ...PLAN, orte: [] }).queries[0]), 'BE');
});

test('the search reports the place of the query it runs, and none for a query without place', async () => {
  const steps = await reportedSteps('jobs.ch', PLAN);
  assert.deepEqual(steps.map((step) => [step.stichwort, step.ort]), [['Begriff1', 'Nordstadt'], ['Nische1', undefined]]);
  assert.ok(!('ort' in steps[1]));
  const cantons = await reportedSteps('job-room', PLAN);
  assert.equal(cantons[0].ort, 'BE, ZH');
});

test('the popup names portal, term, place and stage', () => {
  const step = { portal: 'jobs.ch', phase: 'suche', stichwort: 'Begriff1', ort: 'Nordstadt', seite: 1, gefunden: 4, nummer: 32, abfragen: 67, etappe: 2, etappen: 3 };
  assert.equal(describeRun({ zustand: 'laeuft', schritt: step }).step,
    'jobs.ch: suche „Begriff1“ in Nordstadt, Seite 1 (4 bisher) · Suche 32 von 67, Etappe 2 von 3');
  const { ort, ...without } = step;
  assert.equal(describeRun({ zustand: 'laeuft', schritt: without }).step,
    'jobs.ch: suche „Begriff1“, Seite 1 (4 bisher) · Suche 32 von 67, Etappe 2 von 3');
});

test('a further site with places reports the place of each page', async () => {
  const site = { portal: 'beispiel.ch', adresse: 'https://www.beispiel.ch/suche?q={begriff}&ort={ort}' };
  const steps = [];
  const app = { async request(method, path) {
    if (path === '/api/suche/seite-lesen') return { treffer: [] };
    if (path === '/api/suche/sichten') return { holen: [], bekannt: 0, gefiltert: [] };
    return {};
  } };
  const browser = {
    async openTab() { return 7; },
    async navigate() {},
    async readOpen() { return { title: 'T', text: 'Seitentext', links: [], wall: '' }; },
    async closeTab() {},
  };
  await searchSite(site, { ...PLAN, orte: ['Nordstadt', 'Südstadt'], nischen: [] },
    { app, browser, report: (step) => steps.push(step), sleep: async () => {} });
  assert.deepEqual(steps.filter((s) => s.phase === 'suche').map((s) => s.ort), ['Nordstadt', 'Südstadt']);
});
