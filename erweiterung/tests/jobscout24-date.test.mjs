// #396: jobscout24 lists the newest ads first, reads «New» as today and reports the oldest regular ad of a page.
// An invented result page stands in for the portal; no request leaves the test.
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { test } from 'node:test';

const require = createRequire(import.meta.url);
const common = require('../portals/common.js');
const jobscout24 = require('../portals/jobscout24.js');

/** One list item as the page renders it, reduced to what the adapter reads. */
function item(id, date, source = '') {
  const attributes = { 'data-job-id': id, 'data-job-detail-url': `/de/job/${id}/`, 'data-view-source': source };
  const one = { 'a.job-title, .job-title': { textContent: `Stelle ${id}` }, '.job-date': { textContent: date } };
  const all = { 'p.job-attributes span': [{ textContent: 'Muster AG' }, { textContent: 'Musterstadt' }] };
  return {
    getAttribute: (name) => attributes[name] || null,
    querySelector: (selector) => one[selector] || null,
    querySelectorAll: (selector) => all[selector] || [],
  };
}

function page(items) {
  return {
    querySelectorAll: (selector) => (selector === 'li.job-list-item' ? items : []),
    querySelector: () => ({ textContent: `${items.length} Stellen gefunden` }),
  };
}

// Sponsored ads ignore the sort: two on top, two at the bottom, older than the regular ones.
const RESULT_PAGE = page([
  item('top-1', '2 W', 'toplisting'), item('top-2', '1+M', 'toplisting'),
  item('a', 'New'), item('b', 'New'), item('c', '1 T'), item('d', '3 T'),
  item('bottom-1', '1+M', 'bottomlisting'), item('bottom-2', '2 W', 'bottomlisting'),
]);

test('every jobscout24 page asks for the newest ads first, by region and by postcode', async (t) => {
  const asked = [];
  t.mock.method(common, 'fetchPage', async (url) => { asked.push(new URL(url, 'https://www.jobscout24.ch').searchParams); return page([]); });
  await jobscout24.list({ keyword: 'Kursplaner', regionIds: ['3', '14'] }, 1);
  await jobscout24.list({ keyword: 'Kursplaner', regionIds: ['3', '14'] }, 2);
  await jobscout24.list({ keyword: 'Kursplaner', postalCode: '1111' }, 1);
  await jobscout24.list({ keyword: 'Kursplaner', postalCode: '1111' }, 3);
  assert.deepEqual(asked.map((params) => params.get('sort')), ['1', '1', '1', '1']);
  assert.equal(asked[2].get('psz'), '1111');
});

test('an ad dated «New» is from today', () => {
  assert.equal(common.ageFromText('New'), 0);
  const hits = jobscout24.parseList(RESULT_PAGE).hits;
  assert.deepEqual(hits.filter((hit) => ['a', 'b'].includes(hit.portal_id)).map((hit) => hit.alter_tage), [0, 0]);
});

test('the oldest regular ad of a page counts, sponsored ads stay in the hits', () => {
  const { hits, oldest } = jobscout24.parseList(RESULT_PAGE);
  assert.equal(oldest, 3);
  assert.deepEqual(hits.map((hit) => hit.portal_id), ['top-1', 'top-2', 'a', 'b', 'c', 'd', 'bottom-1', 'bottom-2']);
  assert.equal(jobscout24.parseList(page([item('top-1', '2 W', 'toplisting')])).oldest, null);
});
