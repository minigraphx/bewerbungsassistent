// The popup never shows a run as running that a stopped service worker left behind (#148): it shows what the page
// Suche sees (lib/run-state.js currentRun, #142) and offers „Suche starten“.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { INTERRUPTED, currentRun } from '../lib/run-state.js';

const HTML = readFileSync(new URL('../popup.html', import.meta.url), 'utf8');
const LEFT_RUNNING = { zustand: 'laeuft', beginn: '2026-11-08T10:00:00.000Z', schritt: { phase: 'suche', portal: 'LENA', seite: 1 } };
const PLAN = { art: 'lehrstelle', portale: ['LENA', 'yousty'] };

function fakeElement(hidden = false) {
  const listeners = {};
  const classes = new Set();
  return {
    hidden,
    disabled: false,
    textContent: '',
    dataset: {},
    children: [],
    classList: {
      toggle: (name, on) => (on ? classes.add(name) : classes.delete(name)),
      add: (name) => classes.add(name),
      contains: (name) => classes.has(name),
    },
    addEventListener: (type, f) => { listeners[type] = f; },
    replaceChildren(...nodes) { this.children = nodes; },
    append(...nodes) { this.children = [...this.children, ...nodes]; },
    setAttribute() {},
  };
}

/** popup.html as fake elements by id, with the hidden attributes the page starts with. */
function fakeDocument() {
  const elements = new Map();
  for (const [, tag] of HTML.matchAll(/<[a-z0-9]+\s([^>]*\bid="[^"]+"[^>]*)>/g)) {
    elements.set(tag.match(/\bid="([^"]+)"/)[1], fakeElement(/\bhidden\b/.test(tag)));
  }
  return { elements, getElementById: (id) => elements.get(id), createElement: () => fakeElement() };
}

/** What the browser has after it stopped the worker during a run: the old „laeuft“ in storage.session, a new worker. */
function browserAfterStoppedWorker() {
  const session = { lauf: LEFT_RUNNING };
  const workerRunsSearch = false;
  return {
    storage: {
      session: { get: async (key) => ({ [key]: session[key] }) },
      local: { set: async () => {} },
      onChanged: { addListener: () => {} },
    },
    runtime: {
      // The answer of background.js status(): its run goes through currentRun, like the page's.
      sendMessage: async (message) => (message.art === 'status'
        ? { verbunden: true, version: '1', app: 'http://127.0.0.1:1', plan: PLAN, lauf: currentRun(session.lauf, workerRunsSearch) }
        : null),
    },
    tabs: { query: async () => [] },
  };
}

test('a run the stopped worker left as running shows as interrupted, and the search can start again', async () => {
  const document = fakeDocument();
  globalThis.document = document;
  globalThis.window = { close() {} };
  globalThis.chrome = browserAfterStoppedWorker();

  await import('../popup.js');
  await new Promise((resolve) => setTimeout(resolve, 0));

  const $ = (id) => document.elements.get(id);
  assert.equal($('lauf').hidden, true, 'no progress of a run that is over');
  assert.equal($('suchen').hidden, false);
  assert.equal($('suchen').disabled, false, '„Suche starten“ can be pressed');
  assert.equal($('suche-zeile').textContent, INTERRUPTED);
  assert.ok($('suche-zeile').classList.contains('fehler'));
});

test('the fake above answers like the worker: status() reports its run through currentRun', () => {
  const worker = readFileSync(new URL('../background.js', import.meta.url), 'utf8');
  assert.match(worker, /async function runNow\(\) \{\n.*\n\s*return currentRun\(lauf, running\);/);
  assert.match(worker, /async function status\(\) \{\s*const lauf = await runNow\(\);/);
  assert.match(worker, /return \{ verbunden: true, [^}]*\blauf \}/);
});
