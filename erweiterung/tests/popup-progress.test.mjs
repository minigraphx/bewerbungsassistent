// G43 (#284): the row of the running portal in the popup, as popup.js renders it, names term, place and stage, the
// time left in a pause and the ad being read. Invented terms and places only.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const HTML = readFileSync(new URL('../popup.html', import.meta.url), 'utf8');
const PLAN = { art: 'stelle', portale: ['jobs.ch', 'job-room'] };
const SEARCHING = {
  portal: 'jobs.ch', phase: 'suche', stichwort: 'Begriff2', ort: 'Nordstadt', seite: 1, gefunden: 4,
  nummer: 32, abfragen: 67, etappe: 2, etappen: 3,
};

function fakeElement(hidden = false) {
  return {
    hidden,
    disabled: false,
    textContent: '',
    className: '',
    dataset: {},
    children: [],
    classList: { toggle() {}, add() {}, contains: () => false },
    addEventListener() {},
    replaceChildren(...nodes) { this.children = nodes; },
    append(...nodes) { this.children = [...this.children, ...nodes]; },
    setAttribute() {},
  };
}

function fakeDocument() {
  const elements = new Map();
  for (const [, tag] of HTML.matchAll(/<[a-z0-9]+\s([^>]*\bid="[^"]+"[^>]*)>/g)) {
    elements.set(tag.match(/\bid="([^"]+)"/)[1], fakeElement(/\bhidden\b/.test(tag)));
  }
  return { elements, getElementById: (id) => elements.get(id), createElement: () => fakeElement() };
}

/** A browser whose worker runs a search at SEARCHING; later steps arrive through storage.onChanged. */
function browserWithRun() {
  const changed = [];
  const lauf = { zustand: 'laeuft', beginn: '2026-11-15T10:00:00.000Z', schritt: SEARCHING };
  return {
    changed,
    storage: {
      session: { get: async (key) => ({ [key]: undefined }) },
      local: { set: async () => {} },
      onChanged: { addListener: (listener) => changed.push(listener) },
    },
    runtime: {
      sendMessage: async (message) => (message.art === 'status'
        ? { verbunden: true, version: '1', app: 'http://127.0.0.1:1', plan: PLAN, lauf }
        : null),
    },
    tabs: { query: async () => [] },
  };
}

/** The text of the portal row the popup shows as current, as its spans read together. */
function currentRow(document) {
  const row = document.elements.get('portale').children.find((item) => item.dataset.state === 'current');
  return row.children.map((span) => span.textContent).join(' ');
}

test('the popup row of the running portal names portal, term, place, stage, pause and ad', async () => {
  const document = fakeDocument();
  globalThis.document = document;
  globalThis.window = { close() {} };
  const browser = browserWithRun();
  globalThis.chrome = browser;

  await import('../popup.js');
  await new Promise((resolve) => setTimeout(resolve, 0));

  assert.equal(document.elements.get('lauf').hidden, false);
  assert.equal(currentRow(document),
    'jobs.ch suche „Begriff2“ in Nordstadt, Seite 1 (4 bisher) · Suche 32 von 67, Etappe 2 von 3');

  const next = (schritt) => browser.changed.forEach((listener) => listener({ lauf: { newValue: { zustand: 'laeuft', schritt } } }, 'session'));
  next({ portal: 'job-room', phase: 'pause', etappe: 3, etappen: 3, sekunden: 40 });
  assert.equal(currentRow(document), 'job-room Pause vor Etappe 3 von 3, noch 40\u00a0Sekunden');
  next({ portal: 'job-room', phase: 'texte', fertig: 3, von: 9 });
  assert.equal(currentRow(document), 'job-room lese Inserat 4 von 9');
});
