// G105, #376: a term the profile limits to certain portals («- Nur job-room: …») is searched only there; invented data.
import assert from 'node:assert/strict';
import { test } from 'node:test';

import { buildQueries } from '../lib/queries.js';

const PLAN = {
  art: 'stelle', portale: ['job-room', 'jobs.ch', 'jobscout24', 'ictjobs'],
  stichworte: ['Kursplaner', 'Lernbegleiter'], nur_portale: { Lernbegleiter: ['job-room'] }, nischen: ['Nische1'],
  kantone: ['BE'], orte: ['Nordstadt', 'Südstadt'], plz: ['1111'], regionen: ['grossraum-bern'], schweizweit: false,
};

const keywordsOn = (portal, plan) => buildQueries(portal, plan).queries.map((query) => query.keyword);

test('a term marked nur job-room creates no searches on the other portals', () => {
  assert.deepEqual(keywordsOn('job-room', PLAN), ['Kursplaner', 'Lernbegleiter', 'Nische1']);
  assert.deepEqual(keywordsOn('jobs.ch', PLAN), ['Kursplaner', 'Nische1', 'Kursplaner']);
  assert.deepEqual(keywordsOn('jobscout24', PLAN), ['Kursplaner']);
  assert.deepEqual(keywordsOn('ictjobs', PLAN), ['Kursplaner']);
});

test('without a limit, or from an older app, every term runs on every portal', () => {
  const { nur_portale: _, ...older } = PLAN;
  assert.deepEqual(keywordsOn('ictjobs', older), ['Kursplaner', 'Lernbegleiter']);
  assert.deepEqual(keywordsOn('ictjobs', { ...PLAN, nur_portale: {} }), ['Kursplaner', 'Lernbegleiter']);
});

test('a limit that is no list of portals, or a term named like a property of objects, limits nothing', () => {
  const odd = { ...PLAN, stichworte: ['constructor', 'Lernbegleiter'], nur_portale: { Lernbegleiter: 'job-room' } };
  assert.deepEqual(keywordsOn('ictjobs', odd), ['constructor', 'Lernbegleiter']);
});
