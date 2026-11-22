// #398: job-room ads created days after their start date are found by a daily run and kept by the screen by age.
// An invented job-room answer stands in for the portal; no request leaves the test.
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { test } from 'node:test';

import { buildQueries } from '../lib/queries.js';

const require = createRequire(import.meta.url);
const common = require('../portals/common.js');
const jobroom = require('../portals/jobroom.js');

const DAY_MS = 24 * 60 * 60 * 1000;
const TODAY = new Date();
const daysBack = (days) => new Date(TODAY.getTime() - days * DAY_MS).toISOString().slice(0, 10);

// Last successful run yesterday: search_plan.portal_days gives the days since then, that day included.
const WINDOW_SINCE_YESTERDAY = 2;
const PLAN = {
  art: 'stelle', portale: ['job-room'], stichworte: ['Kursplaner'], nischen: [], kantone: ['BE'],
  max_alter_tage: 21, max_alter_tage_portale: { 'job-room': WINDOW_SINCE_YESTERDAY },
};

// Created today, but dated 3 days back: such ads only reach the index after their start date.
const LATE_AD = {
  jobAdvertisement: {
    id: 'late-1', createdTime: `${daysBack(0)}T07:30:00`, publication: { startDate: daysBack(3) },
    jobContent: {
      jobDescriptions: [{ languageIsoCode: 'de', title: 'Kursplaner (a)' }],
      company: { name: 'Muster AG' }, location: { city: 'Musterstadt', postalCode: '1111' }, employment: {},
    },
  },
};

test('the job-room search reaches back to ads dated 3 days before they were created', async (t) => {
  const bodies = [];
  t.mock.method(common, 'fetchJson', async (url, options) => { bodies.push(JSON.parse(options.body)); return [LATE_AD]; });
  const [query] = buildQueries('job-room', PLAN).queries;
  await jobroom.list(query, 1);
  assert.ok(bodies[0].onlineSince >= WINDOW_SINCE_YESTERDAY + 3, `onlineSince ${bodies[0].onlineSince}`);
});

test('a job-room hit created today counts as new, so the screen keeps it', async (t) => {
  t.mock.method(common, 'fetchJson', async () => [LATE_AD]);
  const [query] = buildQueries('job-room', PLAN).queries;
  const { hits } = await jobroom.list(query, 1);
  assert.equal(hits[0].alter_tage, 0);
  assert.ok(hits[0].alter_tage <= WINDOW_SINCE_YESTERDAY);
});

test('an older app without a window still sends none', async (t) => {
  const bodies = [];
  t.mock.method(common, 'fetchJson', async (url, options) => { bodies.push(JSON.parse(options.body)); return []; });
  await jobroom.list({ keyword: 'Kursplaner', cantons: [] }, 1);
  assert.equal(bodies[0].onlineSince, undefined);
});
