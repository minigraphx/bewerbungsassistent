// G43 (#284): every long step of a run says how far it is, and the line changes at least every few seconds.
import assert from 'node:assert/strict';
import { test } from 'node:test';

import { fetchMissingAds, LIST_PATH, LOAD_PATH } from '../lib/missing-ads.js';
import { portalRows } from '../lib/popup-view.js';
import { describeRun } from '../lib/progress.js';
import { searchPortal, STAGE_PAUSE_S } from '../lib/search.js';

const FEW_SECONDS_MS = 5000;

test('while reading ads the popup names the ad it reads now', () => {
  const step = { phase: 'texte', portal: 'jobs.ch', fertig: 3, von: 9 };
  assert.equal(describeRun({ zustand: 'laeuft', schritt: step }).step, 'jobs.ch: lese Inserat 4 von 9');
  assert.equal(portalRows({ portale: ['jobs.ch'] }, { zustand: 'laeuft', schritt: step })[0].text, 'lese Inserat 4 von 9');
});

test('the pause between stages counts down in steps of a few seconds', async () => {
  const reports = [];
  const sleeps = [];
  const app = { async request(method, path) { return path === '/api/suche/sichten' ? { holen: [], bekannt: 0, gefiltert: [] } : {}; } };
  const browser = {
    async openTab() { return 1; },
    async inject() {},
    async run() { return { ok: true, value: { hits: [], more: false } }; },
    async closeTab() {},
  };
  const plan = { portale: ['jobs.ch'], stichworte: ['Begriff1'], nischen: ['Nische1'], orte: ['Nordstadt'], max_seiten: 1, etappe_abfragen: 1 };
  await searchPortal('jobs.ch', plan, { app, browser, report: (step) => reports.push(step), sleep: async (ms) => { sleeps.push(ms); } });
  const left = reports.filter((step) => step.phase === 'pause').map((step) => step.sekunden);
  assert.equal(left[0], STAGE_PAUSE_S);
  assert.ok(left.every((seconds, i) => i === 0 || left[i - 1] - seconds <= FEW_SECONDS_MS / 1000), `pause steps ${left}`);
  assert.ok(sleeps.every((ms) => ms <= FEW_SECONDS_MS), `sleeps ${sleeps}`);
});

test('loading missing ads reports which ad of all it loads now', async () => {
  const jobs = [
    { art: 'treffer', id: 'a', portal: 'jobs.ch', portal_id: 'a', link: 'https://www.jobs.ch/de/stellenangebote/detail/a/' },
    { art: 'treffer', id: 'b', portal: 'job-room', portal_id: 'b', link: 'https://www.job-room.ch/job-search/b' },
    { art: 'treffer', id: 'c', portal: 'jobs.ch', portal_id: 'c', link: 'https://www.jobs.ch/de/stellenangebote/detail/c/' },
  ];
  const app = { async request(method, path) {
    if (path === LIST_PATH) return { laden: jobs };
    if (path === LOAD_PATH) return {};
    throw new Error(`unexpected ${path}`);
  } };
  const browser = {
    async openTab() { return 1; },
    async inject() {},
    async run() { return { ok: true, value: { text: 'Inserat' } }; },
    async closeTab() {},
  };
  const reports = [];
  await fetchMissingAds({ app, browser, sleep: async () => {}, report: (stand) => reports.push(stand) });
  assert.deepEqual(reports, [{ fertig: 0, von: 3 }, { fertig: 1, von: 3 }, { fertig: 2, von: 3 }]);
});
