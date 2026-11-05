// Helpers and JSON adapters (job-room, jobs.ch) of the extension, with answers shaped like the portals' own.
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { test } from 'node:test';

const require = createRequire(import.meta.url);
const common = require('../portals/common.js');
const jobroom = require('../portals/jobroom.js');
const jobsch = require('../portals/jobsch.js');

const TODAY = new Date('2026-11-03T12:00:00Z');

test('HTML of an ad becomes readable text', () => {
  const html = '<h2>Ihr Profil</h2><ul><li>Python &amp; SQL</li><li>Deutsch</li></ul><p>Wir&nbsp;freuen uns.<br>Team</p>'
    + '<script>alert(1)</script><span>​unsichtbar</span>';
  assert.equal(common.htmlToText(html), 'Ihr Profil\n\n- Python & SQL\n- Deutsch\n\nWir freuen uns.\nTeam\n\nunsichtbar');
});

test('ages from dates and short texts', () => {
  assert.equal(common.ageFromDate('2026-10-31', TODAY), 3);
  assert.equal(common.ageFromDate('kein Datum', TODAY), null);
  for (const [text, days] of [['1 T', 1], ['2 W', 14], ['1+M', 30], ['vor 3 Wochen', 21], ['vor 5 Stunden', 0],
    ['vor 2 Tagen', 2], ['vor 1 Monat', 30], ['Gestern', 1], ['', null]]) {
    assert.equal(common.ageFromText(text), days, text);
  }
});

test('workload from minimum and maximum', () => {
  assert.equal(common.workload('80', '100'), '80–100 %');
  assert.equal(common.workload(100, 100), '100 %');
  assert.equal(common.workload(null, null), '');
});

const JOBROOM_ITEM = {
  jobAdvertisement: {
    id: '4f1c-uuid', createdTime: '2026-10-30T08:00:00',
    publication: { startDate: '2026-11-01' },
    jobContent: {
      jobDescriptions: [{ languageIsoCode: 'fr', title: 'Ingénieur' }, { languageIsoCode: 'de', title: 'Data Engineer (a)', description: '<p>Python</p>' }],
      company: { name: 'Muster AG', city: 'Bern' },
      location: { city: 'Bern', postalCode: '3011', cantonCode: 'BE' },
      employment: { workloadPercentageMin: '80', workloadPercentageMax: '100' },
    },
  },
};

test('job-room result as hit, German title preferred', () => {
  assert.deepEqual(jobroom.toHit(JOBROOM_ITEM, TODAY), {
    portal: 'job-room', portal_id: '4f1c-uuid', stelle: 'Data Engineer (a)', firma: 'Muster AG', ort: '3011 Bern',
    pensum: '80–100 %', link: 'https://www.job-room.ch/job-search/4f1c-uuid', alter_tage: 2,
  });
});

test('job-room: a full page means there may be more', () => {
  assert.equal(jobroom.parseList(Array(100).fill(JOBROOM_ITEM), 1).more, true);
  assert.equal(jobroom.parseList([JOBROOM_ITEM], 1).more, false);
});

test('job-room: an unknown answer is a changed portal', () => {
  assert.throws(() => jobroom.parseList({ content: [] }, 1), (error) => error.changed === true);
  assert.throws(() => jobroom.parseList([{ other: 1 }], 1), (error) => error.changed === true);
  assert.deepEqual(jobroom.parseList([], 1), { hits: [], more: false });
});

const JOBSCH_DOC = {
  job_id: 'abc-123', title: 'Python Developer', company_name: 'Muster GmbH', place: 'Bern, Schweiz (und Homeoffice)',
  age: 13, employment_grades: [80, 90, 100], publication_date: '2026-10-21T04:02:19+02:00',
};

test('jobs.ch result as hit', () => {
  assert.deepEqual(jobsch.toHit(JOBSCH_DOC, TODAY), {
    portal: 'jobs.ch', portal_id: 'abc-123', stelle: 'Python Developer', firma: 'Muster GmbH',
    ort: 'Bern, Schweiz (und Homeoffice)', pensum: '80–100 %',
    link: 'https://www.jobs.ch/de/stellenangebote/detail/abc-123/', alter_tage: 13,
  });
});

test('jobs.ch pages follow num_pages, unknown answers are a changed portal', () => {
  assert.equal(jobsch.parseList({ documents: [JOBSCH_DOC], num_pages: 2 }, 1).more, true);
  assert.equal(jobsch.parseList({ documents: [JOBSCH_DOC], num_pages: 2 }, 2).more, false);
  assert.throws(() => jobsch.parseList({ results: [] }, 1), (error) => error.changed === true);
});

test('adapters register for the page', () => {
  assert.deepEqual(Object.keys(globalThis.bewerbungsbegleiterPortals).sort(), ['job-room', 'jobs.ch']);
});

test('job-room Markdown becomes plain text', () => {
  assert.equal(jobroom.markdownToText('**Möchtest du** IT\\-Infrastrukturen \\(Cloud\\) schützen\\?'),
    'Möchtest du IT-Infrastrukturen (Cloud) schützen\\?');
});
