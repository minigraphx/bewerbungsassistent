// The page Suche never waits for a run the extension no longer has (#142): the bridge's port, its answers, the run state.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import vm from 'node:vm';
import { INTERRUPTED, SearchTabs, currentRun } from '../lib/run-state.js';

const BRIDGE = readFileSync(new URL('../app-bridge.js', import.meta.url), 'utf8');
const PAGE = 'http://127.0.0.1:1';

/** A port as chrome.runtime.connect gives it; disconnect() is what the browser does when it stops an idle worker. */
function fakePort() {
  const listeners = { message: [], disconnect: [] };
  return {
    onMessage: { addListener: (f) => listeners.message.push(f) },
    onDisconnect: { addListener: (f) => listeners.disconnect.push(f) },
    deliver: (message) => listeners.message.forEach((f) => f(message)),
    disconnect: () => listeners.disconnect.forEach((f) => f()),
  };
}

/** app-bridge.js in a sandbox; `answer` is what chrome.runtime.sendMessage does. */
function bridge({ answer = async () => ({ gestartet: true }) } = {}) {
  const ports = [];
  const toPage = [];
  let onPage = null;
  const context = {
    document: { querySelector: () => ({}), documentElement: { dataset: {} } },
    window: { addEventListener: (type, f) => { if (type === 'message') onPage = f; }, postMessage: (m) => toPage.push(m) },
    location: { origin: PAGE },
    setTimeout,
    chrome: {
      runtime: {
        id: 'x',
        getManifest: () => ({ version: '1' }),
        connect: () => {
          if (!context.chrome.runtime.id) throw new Error('Extension context invalidated.');
          const port = fakePort();
          ports.push(port);
          return port;
        },
        sendMessage: (message) => answer(message),
      },
    },
  };
  context.globalThis = context;
  vm.runInNewContext(BRIDGE, context);
  const fromPage = (art) => onPage({ source: context.window, origin: PAGE, data: { quelle: 'bewerbungsbegleiter-seite', art } });
  const settle = () => new Promise((resolve) => setTimeout(resolve, 0));
  return { context, ports, toPage, fromPage, settle };
}

test('the bridge connects again after the worker dropped its port, and progress reaches the page', async () => {
  const b = bridge();
  assert.equal(b.ports.length, 1);
  b.ports[0].disconnect();

  b.fromPage('suche-starten');
  await b.settle();

  assert.equal(b.ports.length, 2, 'a new port before the start, so the new worker can report to this page');
  b.ports[1].deliver({ art: 'lauf', lauf: { zustand: 'fertig' } });
  assert.ok(b.toPage.some((m) => m.art === 'lauf' && m.lauf.zustand === 'fertig'));
});

test('a start the extension does not take comes back to the page as an answer with a message to reload', async () => {
  const b = bridge({ answer: () => Promise.reject(new Error('Could not establish connection. Receiving end does not exist.')) });

  b.fromPage('suche-starten');
  await b.settle();

  const answer = b.toPage.find((m) => m.art === 'antwort' && m.frage === 'suche-starten');
  assert.ok(answer, 'the page hears back');
  assert.match(answer.antwort.fehler, /Seite neu laden/);
});

test('a bridge of a reloaded extension answers the page instead of throwing', async () => {
  const b = bridge();
  b.ports[0].disconnect();
  b.context.chrome.runtime.id = undefined;
  b.context.chrome.runtime.sendMessage = () => { throw new Error('Extension context invalidated.'); };

  b.fromPage('suche-starten');
  await b.settle();

  const answer = b.toPage.find((m) => m.art === 'antwort' && m.frage === 'suche-starten');
  assert.match(answer.antwort.fehler, /Seite neu laden/);
});

test('a run that a stopped worker left as running is over for the page', () => {
  const started = { zustand: 'laeuft', beginn: '2026-11-08T10:00:00.000Z', schritt: { phase: 'start' } };
  assert.deepEqual(currentRun(started, false), { ...started, zustand: 'fehler', fehler: INTERRUPTED });
  assert.equal(currentRun(started, true), started);
  const done = { zustand: 'fertig', beginn: started.beginn, ergebnis: {} };
  assert.equal(currentRun(done, false), done);
  assert.equal(currentRun(undefined, false), null);
});

test('closing a tab of the search by hand stops it, watched or not; the search closing its own tab does not', () => {
  const tabs = new SearchTabs();
  tabs.opened(7);
  tabs.opened(8);
  tabs.closedBySearch(7);

  assert.equal(tabs.removed(7), false);
  assert.equal(tabs.removed(99), false, 'a tab of something else');
  assert.equal(tabs.removed(8), true);
  assert.equal(tabs.removed(8), false, 'only once');
});
