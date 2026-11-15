// G43: every search runs, per portal in stages of at most 30 with a longer pause in between; invented terms and places.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

import { describePlan, describeRun } from '../lib/progress.js';
import { portalRows } from '../lib/popup-view.js';
import { buildQueries } from '../lib/queries.js';
import { DELAY_MS, searchPortal, STAGE_PAUSE_S, STAGE_SIZE } from '../lib/search.js';

const CASES = JSON.parse(readFileSync(new URL('./fixtures/run-size.json', import.meta.url), 'utf8')).cases;
const TERMS = Array.from({ length: 16 }, (_, i) => `Begriff${i + 1}`);
const PLAN = {
  art: 'stelle', portale: ['jobs.ch'], stichworte: TERMS, nischen: ['Nische1', 'Nische2', 'Nische3'], kantone: ['BE'],
  orte: ['Nordstadt', 'Südstadt', 'Oststadt', 'Weststadt'], plz: [], regionen: [], max_seiten: 1, max_abfragen: 30,
};

/** A run on simulated tabs that records each list request and each pause, in order. */
function recordedRun(plan) {
  const events = [];
  const reports = [];
  const app = {
    async request(method, path) {
      if (path === '/api/suche/sichten') return { holen: [], bekannt: 0, gefiltert: [] };
      return {};
    },
  };
  const browser = {
    async openTab() { return 1; },
    async inject() {},
    async run(tab, portal, method, args) {
      if (method === 'list') events.push(['list', args[0]]);
      return { ok: true, value: { hits: [], more: false } };
    },
    async closeTab() {},
  };
  const deps = { app, browser, report: (step) => reports.push(step), sleep: async (ms) => { events.push(['sleep', ms]); } };
  return { events, reports, done: searchPortal('jobs.ch', plan, deps) };
}

/** The list requests between the longer pauses, and the time slept in each gap between two stages. */
function stagesOf(events) {
  const stages = [[]];
  const gaps = [];
  let slept = 0;
  for (const [kind, value] of events) {
    if (kind === 'sleep') { slept += value; continue; }
    if (slept > DELAY_MS && stages.at(-1).length) { stages.push([]); gaps.push(slept); }
    stages.at(-1).push(value);
    slept = 0;
  }
  return { stages, gaps };
}

test('every query of a portal is built, none is left out', () => {
  const { queries } = buildQueries('jobs.ch', PLAN);
  assert.equal(queries.length, TERMS.length * PLAN.orte.length + PLAN.nischen.length);
  for (const place of PLAN.orte) {
    assert.deepEqual(queries.filter((q) => q.place === place).map((q) => q.keyword), TERMS);
  }
});

test('the app counts the same searches per portal as the extension builds', () => {
  for (const { name, plan, searches } of CASES) {
    for (const portal of plan.portale) {
      assert.equal(buildQueries(portal, plan).queries.length, searches[portal], `${name}: ${portal}`);
    }
  }
});

test('more than 30 searches on a portal all run, in stages of at most 30', async () => {
  const run = recordedRun(PLAN);
  const summary = await run.done;
  const { stages } = stagesOf(run.events);
  assert.equal(stages.flat().length, 67);
  assert.deepEqual(stages.map((stage) => stage.length), [30, 30, 7]);
  assert.ok(stages.every((stage) => stage.length <= STAGE_SIZE));
  assert.equal(STAGE_SIZE, 30);
  assert.doesNotMatch(summary.problem, /ausgelassen/);
});

test('between stages the run pauses much longer than between two searches', async () => {
  const run = recordedRun(PLAN);
  await run.done;
  const { gaps } = stagesOf(run.events);
  assert.equal(gaps.length, 2);
  assert.ok(STAGE_PAUSE_S * 1000 >= 50 * DELAY_MS, 'the stage pause is far longer than the pause between searches');
  for (const gap of gaps) assert.ok(gap >= STAGE_PAUSE_S * 1000, `a gap of ${gap} ms`);
});

test('the plan of the app sets the stage size and the pause', async () => {
  const run = recordedRun({ ...PLAN, etappe_abfragen: 20, etappe_pause_sekunden: 30 });
  await run.done;
  const { stages, gaps } = stagesOf(run.events);
  assert.deepEqual(stages.map((stage) => stage.length), [20, 20, 20, 7]);
  assert.ok(gaps.every((gap) => gap >= 30000 && gap < STAGE_PAUSE_S * 1000));
});

test('a run with few searches has one stage and no longer pause', async () => {
  const run = recordedRun({ ...PLAN, stichworte: ['Begriff1'], nischen: [] });
  await run.done;
  const { stages, gaps } = stagesOf(run.events);
  assert.deepEqual(stages.map((stage) => stage.length), [4]);
  assert.deepEqual(gaps, []);
});

test('the progress names the search, the stage and the pause', async () => {
  const run = recordedRun(PLAN);
  await run.done;
  const searching = run.reports.filter((step) => step.phase === 'suche');
  assert.deepEqual(searching.map((step) => step.nummer), Array.from({ length: 67 }, (_, i) => i + 1));
  assert.deepEqual(searching[31], { portal: 'jobs.ch', phase: 'suche', stichwort: 'Begriff13', seite: 1, gefunden: 0,
    nummer: 32, abfragen: 67, etappe: 2, etappen: 3 });
  const pauses = run.reports.filter((step) => step.phase === 'pause');
  assert.ok(pauses.length >= 2);
  assert.deepEqual(pauses[0], { portal: 'jobs.ch', phase: 'pause', etappe: 2, etappen: 3, sekunden: STAGE_PAUSE_S });
  assert.ok(pauses.some((step) => step.etappe === 3));
});

test('the popup and the progress line read the stage and the pause', () => {
  const step = { portal: 'jobs.ch', phase: 'suche', stichwort: 'Begriff2', seite: 1, gefunden: 4, nummer: 32, abfragen: 67, etappe: 2, etappen: 3 };
  assert.equal(describeRun({ zustand: 'laeuft', schritt: step }).step,
    'jobs.ch: suche „Begriff2“, Seite 1 (4 bisher) · Suche 32 von 67, Etappe 2 von 3');
  const single = { ...step, nummer: 3, abfragen: 5, etappe: 1, etappen: 1 };
  assert.equal(describeRun({ zustand: 'laeuft', schritt: single }).step, 'jobs.ch: suche „Begriff2“, Seite 1 (4 bisher) · Suche 3 von 5');
  const pause = { portal: 'jobs.ch', phase: 'pause', etappe: 3, etappen: 3, sekunden: 40 };
  assert.equal(describeRun({ zustand: 'laeuft', schritt: pause }).step, 'jobs.ch: Pause vor Etappe 3 von 3, noch 40 Sekunden');
  const rows = portalRows({ portale: ['jobs.ch'] }, { zustand: 'laeuft', schritt: pause });
  assert.equal(rows[0].text, 'Pause vor Etappe 3 von 3');
  assert.equal(portalRows({ portale: ['jobs.ch'] }, { zustand: 'laeuft', schritt: step })[0].text, 'Suche 32 von 67, Seite 1');
});

test('before a long run the popup says what the app announces', () => {
  const text = 'Diese Suche dauert etwa 15 Minuten: 150 Suchen in 6 Etappen, mit je einer Minute Pause dazwischen.';
  const long = describePlan({ art: 'stelle', portale: ['jobs.ch'], umfang: { lang: true, text } });
  assert.ok(long.text.endsWith(` ${text}`), long.text);
  const short = describePlan({ art: 'stelle', portale: ['jobs.ch'], umfang: { lang: false, text: '' } });
  assert.equal(short.text, 'Sucht auf jobs.ch nach dem Suchprofil. Die Treffer gehen in die App.');
});
