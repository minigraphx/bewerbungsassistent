// Missing ad texts at the start of the app (G37, #275): the app names what it lacks, the extension loads it from
// portals that allow automatic loading and hands the texts back, with simulated tabs and app.
import assert from 'node:assert/strict';
import { test } from 'node:test';

import { fetchMissingAds, isNewStart, LOAD_PATH, LIST_PATH } from '../lib/missing-ads.js';

const SAVED = { art: 'bewerbung', id: 'muster-ag-data', portal: 'job-room', portal_id: 'jr-1', link: 'https://www.job-room.ch/job-search/jr-1' };
const HIT = { art: 'treffer', id: 'jobs-ch-abc', portal: 'jobs.ch', portal_id: 'abc', link: 'https://www.jobs.ch/de/stellenangebote/detail/abc/' };

function fakeApp(laden) {
  const calls = [];
  return {
    calls,
    async request(method, path, data) {
      calls.push([method, path, data]);
      if (path === LIST_PATH) return { laden };
      if (path === LOAD_PATH) return { gespeichert: data.texte.filter((t) => t.text).length };
      throw new Error(`unexpected ${path}`);
    },
  };
}

function fakeBrowser(details) {
  const log = [];
  return {
    log,
    async openTab(url, watching) { log.push(['open', url, watching]); return log.length; },
    async inject(tab, files) { log.push(['inject', files]); },
    async run(tab, portal, method, args) {
      log.push([method, portal, args[0]]);
      return details(portal, args[0]);
    },
    async closeTab(tab) { log.push(['close', tab]); },
  };
}

const deps = (app, browser) => ({ app, browser, sleep: async () => {} });

test('a saved job and a hit without text get it from their portal, in a tab in the background', async () => {
  const app = fakeApp([SAVED, HIT]);
  const browser = fakeBrowser((portal) => ({ ok: true, value: { text: `Inserat von ${portal}` } }));

  const result = await fetchMissingAds(deps(app, browser));

  assert.deepEqual(browser.log.filter(([kind]) => kind === 'open').map(([, url, watching]) => [url, watching]),
    [['https://www.job-room.ch/home/job-seeker', false], ['https://www.jobs.ch/de/', false]]);
  assert.deepEqual(browser.log.filter(([kind]) => kind === 'details').map(([, portal, job]) => [portal, job.portal_id, job.link]),
    [['job-room', 'jr-1', SAVED.link], ['jobs.ch', 'abc', HIT.link]]);
  const sent = app.calls.filter(([, path]) => path === LOAD_PATH).flatMap(([, , data]) => data.texte);
  assert.deepEqual(sent, [
    { art: 'bewerbung', id: 'muster-ag-data', text: 'Inserat von job-room' },
    { art: 'treffer', id: 'jobs-ch-abc', text: 'Inserat von jobs.ch' },
  ]);
  assert.equal(browser.log.filter(([kind]) => kind === 'close').length, 2, 'every tab is closed again');
  assert.deepEqual(result, { geladen: 2, fehlgeschlagen: 0 });
});

test('a portal without its own adapter is never opened, even if the app named it', async () => {
  const other = { art: 'bewerbung', id: 'x', portal: 'linkedin.com', portal_id: '', link: 'https://www.linkedin.com/jobs/view/1' };
  const app = fakeApp([other]);
  const browser = fakeBrowser(() => assert.fail('nothing to load'));

  const result = await fetchMissingAds(deps(app, browser));

  assert.deepEqual(browser.log, []);
  assert.deepEqual(app.calls.map(([, path]) => path), [LIST_PATH]);
  assert.deepEqual(result, { geladen: 0, fehlgeschlagen: 0 });
});

test('what could not be loaded goes back with its reason, so the app can name it', async () => {
  const app = fakeApp([SAVED, HIT]);
  const browser = fakeBrowser((portal) => (portal === 'job-room'
    ? { ok: false, fehler: 'Antwort 429' }
    : { ok: true, value: { text: '' } }));

  const result = await fetchMissingAds(deps(app, browser));

  const sent = app.calls.filter(([, path]) => path === LOAD_PATH).flatMap(([, , data]) => data.texte);
  assert.deepEqual(sent, [
    { art: 'bewerbung', id: 'muster-ag-data', text: '', fehler: 'Antwort 429' },
    { art: 'treffer', id: 'jobs-ch-abc', text: '' },
  ]);
  assert.deepEqual(result, { geladen: 0, fehlgeschlagen: 2 });
});

test('a portal that does not load names the reason for each of its jobs', async () => {
  const app = fakeApp([SAVED]);
  const browser = { ...fakeBrowser(() => assert.fail('no tab')), async openTab() { throw new Error('Die Seite lädt nicht.'); } };

  await fetchMissingAds(deps(app, browser));

  const sent = app.calls.filter(([, path]) => path === LOAD_PATH).flatMap(([, , data]) => data.texte);
  assert.deepEqual(sent, [{ art: 'bewerbung', id: 'muster-ag-data', text: '', fehler: 'Die Seite lädt nicht.' }]);
});

test('nothing goes to the AI: only the two routes of the missing texts are asked', async () => {
  const app = fakeApp([SAVED, HIT]);
  const browser = fakeBrowser(() => ({ ok: true, value: { text: 'Text' } }));

  await fetchMissingAds(deps(app, browser));

  assert.deepEqual([...new Set(app.calls.map(([, path]) => path))], [LIST_PATH, LOAD_PATH]);
});

test('once per start of the app: the same entry address is not asked again', () => {
  const hello = { app: 'http://127.0.0.1:5000/', einstieg: 'http://127.0.0.1:5000/?t=abc' };
  assert.equal(isNewStart(hello, null), true);
  assert.equal(isNewStart(hello, hello.einstieg), false);
  assert.equal(isNewStart({ ...hello, einstieg: 'http://127.0.0.1:5001/?t=def' }, hello.einstieg), true);
  assert.equal(isNewStart({ app: null, einstieg: null }, null), false, 'an app that does not run is not started for this');
});

test('„Alle prüfen“ asks the app for exactly its hits and loads them (#209)', async () => {
  const app = fakeApp([HIT]);
  const browser = fakeBrowser(() => ({ ok: true, value: { text: 'Inserat' } }));

  const result = await fetchMissingAds(deps(app, browser), { treffer: [HIT.id] });

  assert.deepEqual(app.calls[0], ['POST', LIST_PATH, { treffer: [HIT.id] }]);
  assert.deepEqual(result, { geladen: 1, fehlgeschlagen: 0 });
});

test('only the app page may ask for the texts of its hits', async () => {
  const { ALLOWED } = await import('../lib/senders.js');
  assert.ok(ALLOWED.app.has('inserate-holen') && !ALLOWED.popup.has('inserate-holen'));
});

test('„Alle prüfen“ without hits asks nothing, and nothing loads while a search runs', async () => {
  const { fetchHitAds, ADS_DURING_SEARCH } = await import('../lib/missing-ads.js');
  const app = fakeApp([HIT]);
  const browser = fakeBrowser(() => ({ ok: true, value: { text: 'Inserat' } }));
  const idle = { ...deps(app, browser), searching: () => false };

  assert.deepEqual(await fetchHitAds({ ids: [] }, idle), { geladen: 0, fehlgeschlagen: 0 });
  assert.deepEqual(await fetchHitAds({ ids: [3, ''] }, idle), { geladen: 0, fehlgeschlagen: 0 });
  assert.equal(app.calls.length, 0);
  await assert.rejects(fetchHitAds({ ids: [HIT.id] }, { ...idle, searching: () => true }), { message: ADS_DURING_SEARCH });
  assert.equal(app.calls.length, 0);
  assert.deepEqual(await fetchHitAds({ ids: [HIT.id, 7] }, idle), { geladen: 1, fehlgeschlagen: 0 });
  assert.deepEqual(app.calls[0], ['POST', LIST_PATH, { treffer: [HIT.id] }]);
});

test('ad loadings run one after the other, and a failed one fails only its caller', async () => {
  const { adQueue } = await import('../lib/missing-ads.js');
  const queue = adQueue();
  const order = [];
  let release;
  const gate = new Promise((resolve) => { release = resolve; });
  const first = queue.run(() => gate.then(() => { order.push('erste'); throw new Error('kaputt'); }));
  const second = queue.run(async () => { order.push('zweite'); return 'ok'; });
  assert.equal(queue.busy(), true);
  release();
  await assert.rejects(first, { message: 'kaputt' });
  assert.equal(await second, 'ok');
  assert.deepEqual(order, ['erste', 'zweite']);
  assert.equal(queue.busy(), false);
});
