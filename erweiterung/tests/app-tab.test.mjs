// „Treffer in der App ansehen“ uses a tab of the app that is already open (MIN-405).
import assert from 'node:assert/strict';
import test from 'node:test';

import { showHits } from '../lib/app-tab.js';

const APP = 'http://127.0.0.1:5000/';
const HITS = 'http://127.0.0.1:5000/treffer';

function browser(openTabs) {
  const calls = [];
  return {
    calls,
    tabs: {
      query: async () => openTabs,
      create: async (props) => { calls.push(['create', props]); return { id: 99 }; },
      update: async (id, props) => { calls.push(['update', id, props]); return { id }; },
    },
    windows: { update: async (id, props) => { calls.push(['window', id, props]); } },
  };
}

test('without a tab of the app a new one opens', async () => {
  const b = browser([{ id: 1, windowId: 7, url: 'https://www.jobs.ch/' }]);
  await showHits(APP, b);
  assert.deepEqual(b.calls, [['create', { url: HITS }]]);
});

test('the link with the token starts the session in this browser', async () => {
  const b = browser([]);
  await showHits(APP, b, `${APP}?t=abc`);
  assert.deepEqual(b.calls, [['create', { url: `${HITS}?t=abc` }]]);
});

test('an open page of hits comes to the front with its window and shows the current state', async () => {
  const b = browser([{ id: 1, windowId: 7, url: `${APP}` }, { id: 2, windowId: 8, url: HITS }]);
  await showHits(APP, b);
  assert.deepEqual(b.calls, [['update', 2, { url: HITS, active: true }], ['window', 8, { focused: true }]]);
});

test('the overview turns into the hits, it holds nothing to lose', async () => {
  const b = browser([{ id: 1, windowId: 7, url: APP }]);
  await showHits(APP, b);
  assert.deepEqual(b.calls, [['update', 1, { url: HITS, active: true }], ['window', 7, { focused: true }]]);
});

test('a page where something may be half typed stays as it is', async () => {
  for (const page of ['bewerbung?id=a1', 'angaben', 'einstellungen', 'inhalte', 'foto']) {
    const b = browser([{ id: 1, windowId: 7, url: `${APP}${page}` }]);
    await showHits(APP, b);
    assert.deepEqual(b.calls, [['create', { url: HITS }]], page);
  }
});

test('another local service on the same address is not touched', async () => {
  const b = browser([{ id: 1, windowId: 7, url: 'http://127.0.0.1:8080/' }, { id: 2, windowId: 7, url: 'http://127.0.0.1:8080/treffer' }]);
  await showHits(APP, b);
  assert.deepEqual(b.calls, [['create', { url: HITS }]]);
});

test('tabs without a readable address do not get in the way', async () => {
  const b = browser([{ id: 1, windowId: 7 }, { id: 2, windowId: 7, url: 'kein gültiger Link' }]);
  await showHits(APP, b);
  assert.deepEqual(b.calls, [['create', { url: HITS }]]);
});
